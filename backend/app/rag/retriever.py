"""Hybrid retrieval: dense vectors fused with BM25.

Hybrid matters for this corpus specifically. Dense retrieval handles
paraphrase and cross-language matching, which is what an 11-language app
needs; BM25 handles the exact terms dense retrieval is worst at — "PM-KISAN",
"Mancozeb", "Hexaconazole", "Alternaria solani". Reciprocal rank fusion
combines them without needing the two score scales to be comparable.

Every path degrades rather than failing: no embeddings means lexical-only
retrieval, and the chosen mode is reported on each result so a silent
downgrade is visible in /api/rag/status rather than being mistaken for a
quality problem.
"""

import math
import os
import re
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

from app.rag import embeddings
from app.rag.corpus import Document, get_corpus
from app.rag.store import MemoryStore, connect_qdrant

# Cosine floor for dense hits. bge-m3 puts genuinely related text well above
# this and unrelated text below it; tunable because it depends on the model.
# Cosine floor for dense hits, calibrated against the active embedding model.
# Measured separation for nvidia/nemotron-3-embed-1b: correct matches land at
# 0.41-0.66, same-domain-but-wrong at 0.21-0.30, off-domain at 0.06-0.09.
# 0.35 sits in the gap. Re-measure if EMBED_MODEL changes.
MIN_DENSE_SCORE = float(os.getenv("RAG_MIN_DENSE_SCORE", "0.35"))
# Absolute and relative floors that together reject stopword-only BM25 matches.
MIN_LEXICAL_SCORE = float(os.getenv("RAG_MIN_LEXICAL_SCORE", "1.0"))
LEXICAL_RELATIVE_FLOOR = 0.15
RRF_K = 60
# Chunks allowed from any one source document. Without a cap, a long document
# takes every slot with near-identical chunks and crowds out other sources.
MAX_CHUNKS_PER_DOC = 2

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)

# Function words carry no retrieval signal but still score under BM25 on a
# small corpus, which is enough to make an off-topic query match something.
_STOPWORDS = frozenset("""
a an the and or but if then than that this these those there here
i me my mine we us our you your he him his she her it its they them their
is am are was were be been being do does did doing done have has had having
can could should would will shall may might must
of in on at to from by for with without about into over under again
how what when where which who whom why whose
not no nor so too very just only also any some all each both few more most
other such own same as up down out off again once
""".split())


def tokenize(text: str, drop_stopwords: bool = True) -> List[str]:
    """Unicode-aware tokenizer.

    `\\w` under re.UNICODE covers Devanagari, Gurmukhi, Tamil, Telugu, Kannada,
    Gujarati, Bengali, Malayalam and Odia, so Indic queries tokenize correctly
    instead of collapsing to nothing. Only English function words are dropped;
    Indic tokens are left intact since they carry the signal.
    """
    tokens = _TOKEN_RE.findall(text.lower())
    if drop_stopwords:
        return [token for token in tokens if token not in _STOPWORDS]
    return tokens


@dataclass
class RetrievedDoc:
    id: str
    text: str
    title: str
    source: str
    category: str
    score: float
    dense_score: float = 0.0
    lexical_score: float = 0.0
    mode: str = "hybrid"
    crop: str = ""
    guide_key: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


class BM25:
    """Okapi BM25 over the in-memory corpus. No external dependency."""

    def __init__(self, documents: List[Document], k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = documents
        self.k1 = k1
        self.b = b

        # Title is included so a query echoing a document title ranks it.
        self._tokens = [tokenize(f"{d.title} {d.text}") for d in documents]
        self._freqs = [Counter(tokens) for tokens in self._tokens]
        self._lengths = [len(tokens) for tokens in self._tokens]
        self._avg_length = (sum(self._lengths) / len(self._lengths)) if self._lengths else 0.0

        document_frequency: Counter = Counter()
        for tokens in self._tokens:
            document_frequency.update(set(tokens))

        total = len(documents)
        self._idf = {
            term: math.log(1 + (total - count + 0.5) / (count + 0.5))
            for term, count in document_frequency.items()
        }

    def search(self, query: str, limit: int = 4,
               category: Optional[str] = None) -> List[tuple]:
        terms = tokenize(query)
        if not terms or not self.documents:
            return []

        scored = []
        for index, document in enumerate(self.documents):
            if category and document.category != category:
                continue
            frequencies = self._freqs[index]
            length = self._lengths[index]
            score = 0.0
            for term in terms:
                frequency = frequencies.get(term)
                if not frequency:
                    continue
                idf = self._idf.get(term, 0.0)
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * (length / self._avg_length if self._avg_length else 1)
                )
                score += idf * (frequency * (self.k1 + 1)) / denominator
            if score > 0:
                scored.append((document.id, score))

        if not scored:
            return []

        scored.sort(key=lambda item: item[1], reverse=True)
        # Reject weak matches that come only from low-information terms.
        top = scored[0][1]
        floor = max(MIN_LEXICAL_SCORE, LEXICAL_RELATIVE_FLOOR * top)
        return [item for item in scored if item[1] >= floor][:limit]


_store = None
_bm25: Optional[BM25] = None
_indexed = 0
_dense_ready = False


def index_corpus(refresh: bool = False) -> Dict:
    """Build the lexical and dense indexes. Called once at startup.

    Document vectors come from the disk cache after the first run, so a restart
    normally costs no API quota.
    """
    global _store, _bm25, _indexed, _dense_ready

    documents = get_corpus(refresh=refresh)
    _indexed = len(documents)

    # Lexical index always builds; it needs no network.
    _bm25 = BM25(documents)
    print(f"[RAG] Lexical index built over {_indexed} documents.")

    _dense_ready = False
    _store = None

    if not embeddings.is_available():
        print("[RAG] NVIDIA_API_KEY missing; retrieval will run lexical-only.")
        return get_status()

    vectors = embeddings.embed_documents([document.text for document in documents])
    embeddings.flush_cache()
    if vectors is None:
        print("[RAG] Could not embed corpus; retrieval will run lexical-only.")
        return get_status()

    dim = embeddings.embedding_dim() or len(vectors[0])
    _store = connect_qdrant(dim) or MemoryStore()
    _store.upsert(documents, vectors)
    _dense_ready = True
    print(f"[RAG] Dense index ready: {_indexed} documents, {dim}-dim, "
          f"backend={_store.backend}.")
    return get_status()


def _reciprocal_rank_fusion(rankings: List[List[str]]) -> Dict[str, float]:
    """Standard RRF. Rank position, not raw score, so scales need not align."""
    fused: Dict[str, float] = {}
    for ranking in rankings:
        for position, doc_id in enumerate(ranking):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (RRF_K + position + 1)
    return fused


def retrieve(query: str, limit: int = 4, category: Optional[str] = None,
             query_vector: Optional[List[float]] = None) -> List[RetrievedDoc]:
    """Retrieve documents for a query.

    `query_vector` lets the caller supply an already-computed embedding so one
    request costs a single embedding call no matter how many agents retrieve.
    """
    if not query or not query.strip():
        return []
    if _bm25 is None:
        index_corpus()

    documents = {document.id: document for document in get_corpus()}

    # Over-fetch from each retriever so fusion has material to work with, and
    # so the per-document cap has alternatives to fall back on.
    fetch = max(limit * 4, 16)

    dense_scores: Dict[str, float] = {}
    if _store is not None and _dense_ready:
        vector = query_vector
        if vector is None:
            vector = embeddings.embed_query(query)
        if vector is not None:
            for doc_id, score in _store.search(vector, limit=fetch, category=category):
                if score >= MIN_DENSE_SCORE:
                    dense_scores[doc_id] = score

    lexical_scores: Dict[str, float] = {}
    if _bm25 is not None:
        for doc_id, score in _bm25.search(query, limit=fetch, category=category):
            lexical_scores[doc_id] = score

    if not dense_scores and not lexical_scores:
        return []

    rankings = []
    if dense_scores:
        rankings.append(sorted(dense_scores, key=lambda k: dense_scores[k], reverse=True))
    if lexical_scores:
        rankings.append(sorted(lexical_scores, key=lambda k: lexical_scores[k], reverse=True))

    fused = _reciprocal_rank_fusion(rankings)
    ordered = sorted(fused, key=lambda k: fused[k], reverse=True)

    if dense_scores and lexical_scores:
        mode = "hybrid"
    elif dense_scores:
        mode = "dense"
    else:
        mode = "lexical"

    results = []
    per_document: Dict[tuple, int] = {}
    for doc_id in ordered:
        if len(results) >= limit:
            break
        document = documents.get(doc_id)
        if document is None:
            # Indexed under an earlier corpus version; skip rather than guess.
            continue

        # Chunks of one markdown file share a title and source. Cap them so a
        # single long document cannot occupy every slot.
        key = (document.title, document.source)
        taken = per_document.get(key, 0)
        if taken >= MAX_CHUNKS_PER_DOC:
            continue
        per_document[key] = taken + 1

        results.append(RetrievedDoc(
            id=document.id,
            text=document.text,
            title=document.title,
            source=document.source,
            category=document.category,
            crop=document.crop,
            guide_key=document.guide_key,
            score=round(fused[doc_id], 6),
            dense_score=round(dense_scores.get(doc_id, 0.0), 4),
            lexical_score=round(lexical_scores.get(doc_id, 0.0), 4),
            mode=mode,
        ))
    return results


def dense_supported(documents: List[RetrievedDoc]) -> List[RetrievedDoc]:
    """Keep only results the dense retriever agrees with, when it agreed with any.

    BM25-only hits next to dense-confirmed ones are almost always matches on an
    incidental word ("loan" inside a solar-pump scheme). Used wherever results
    become a card or a reference the LLM is told to trust. In lexical-only mode
    (no embedder) nothing has dense support, so everything is kept.
    """
    if any(document.dense_score > 0 for document in documents):
        return [document for document in documents if document.dense_score > 0]
    return documents


def get_status() -> Dict:
    """Introspection for /api/rag/status."""
    return {
        "documents_indexed": _indexed,
        "dense_retrieval": _dense_ready,
        "vector_store": _store.backend if _store is not None else None,
        "vector_dim": embeddings.embedding_dim(),
        "embed_model": embeddings.EMBED_MODEL,
        "embedder_configured": embeddings.is_available(),
        "retrieval_mode": "hybrid" if _dense_ready else "lexical",
        "min_dense_score": MIN_DENSE_SCORE,
        "embedding_stats": embeddings.stats(),
    }
