"""Builds the retrieval corpus from seed data and user-supplied markdown.

The old implementation indexed only KNOWLEDGE_BASE (4 entries) while the real
knowledge — schemes, first-aid protocols, disaster guides, tutorials — sat in
Python dicts reached by ``if "snake" in query``. Everything is indexed here.

MANDI_PRICES is deliberately excluded. Prices are volatile structured facts
already served directly by ``marketplace_agent``; freezing them into a vector
store is how a RAG system ends up confidently quoting a stale number.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.core.seed_data import (
    DISASTER_GUIDES,
    EDUCATION_TUTORIALS,
    GOVERNMENT_SCHEMES,
    HEALTHCARE_GUIDES,
    KNOWLEDGE_BASE,
    QUIZZES,
)

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "corpus"

CATEGORY_AGRONOMY = "agronomy"
CATEGORY_SCHEME = "scheme"
CATEGORY_HEALTH = "health"
CATEGORY_DISASTER = "disaster"
CATEGORY_EDUCATION = "education"

KNOWN_CATEGORIES = {
    CATEGORY_AGRONOMY,
    CATEGORY_SCHEME,
    CATEGORY_HEALTH,
    CATEGORY_DISASTER,
    CATEGORY_EDUCATION,
}

MAX_CHUNK_CHARS = 800
CHUNK_OVERLAP_CHARS = 120


@dataclass
class Document:
    """One retrievable chunk."""

    id: str
    text: str
    title: str
    source: str
    category: str
    crop: str = ""
    # Original key in the structured seed dicts (e.g. "snake_bite", "flood").
    # Lets retrieval *select* a guide while the dict still supplies the
    # step arrays the frontend renders.
    guide_key: str = ""

    @property
    def point_id(self) -> int:
        """Qdrant accepts only unsigned ints or UUIDs, not arbitrary strings.

        60 bits of the id hash stays well inside the unsigned-64 range while
        keeping collisions implausible for a corpus of this size.
        """
        return int(self.id[:15], 16)

    def payload(self) -> Dict[str, str]:
        return {
            "doc_id": self.id,
            "text": self.text,
            "title": self.title,
            "source": self.source,
            "category": self.category,
            "crop": self.crop,
            "guide_key": self.guide_key,
        }


def _make_id(category: str, title: str, index: int = 0) -> str:
    raw = f"{category}|{title}|{index}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS,
               overlap: int = CHUNK_OVERLAP_CHARS) -> List[str]:
    """Split on paragraph boundaries, carrying a short overlap between chunks.

    The overlap keeps a sentence that straddles a boundary retrievable from
    either side.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    current = ""

    for paragraph in paragraphs:
        # A single paragraph longer than the budget is hard-split so no chunk
        # grows unbounded.
        while len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars - overlap:]

        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{paragraph}".strip() if tail else paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph

    if current:
        chunks.append(current)
    return chunks


def _split_source(content: str, default: str) -> tuple:
    """Pull the citation prefix out of seed content.

    KNOWLEDGE_BASE entries are written as "ICAR Tomato Manual: Yellow spots...",
    so the prefix is a real citable source worth surfacing separately.
    """
    match = re.match(r"^([A-Z][^:]{3,60}):\s*(.+)$", content, re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return default, content


def _from_knowledge_base() -> List[Document]:
    documents = []
    for item in KNOWLEDGE_BASE:
        source, body = _split_source(item["content"], "KVK Advisory")
        # The query phrasing is embedded alongside the body because it mirrors
        # how a farmer actually asks, which improves the match.
        documents.append(Document(
            id=_make_id(CATEGORY_AGRONOMY, item["query"]),
            text=f"{item['query']}. {body}",
            title=item["query"].title(),
            source=source,
            category=CATEGORY_AGRONOMY,
        ))
    return documents


def _from_schemes() -> List[Document]:
    documents = []
    for scheme in GOVERNMENT_SCHEMES:
        text = (
            f"{scheme['name']}. Benefits: {scheme['benefits']} "
            f"Eligibility: {scheme['eligibility']} "
            f"Required documents: {', '.join(scheme['documents'])}. "
            f"Application steps: {' '.join(scheme['steps'])}"
        )
        documents.append(Document(
            id=_make_id(CATEGORY_SCHEME, scheme["name"]),
            text=text,
            title=scheme["name"],
            source="Government of India Scheme Guidelines",
            category=CATEGORY_SCHEME,
            guide_key=scheme["name"],
        ))
    return documents


def _from_healthcare() -> List[Document]:
    documents = []
    for key, guide in HEALTHCARE_GUIDES.items():
        parts = [guide["title"]]
        if guide.get("symptoms"):
            parts.append(f"Symptoms: {', '.join(guide['symptoms'])}.")
        parts.append(" ".join(guide["steps"]))
        documents.append(Document(
            id=_make_id(CATEGORY_HEALTH, key),
            text=" ".join(parts),
            title=guide["title"],
            source="Rural First Aid Protocol",
            category=CATEGORY_HEALTH,
            guide_key=key,
        ))
    return documents


def _from_disaster() -> List[Document]:
    documents = []
    for key, guide in DISASTER_GUIDES.items():
        documents.append(Document(
            id=_make_id(CATEGORY_DISASTER, key),
            text=f"{guide['title']}. {' '.join(guide['steps'])}",
            title=guide["title"],
            source="National Disaster Management Authority",
            category=CATEGORY_DISASTER,
            guide_key=key,
        ))
    return documents


def _from_education() -> List[Document]:
    documents = []
    for tutorial in EDUCATION_TUTORIALS:
        documents.append(Document(
            id=_make_id(CATEGORY_EDUCATION, tutorial["id"]),
            text=f"{tutorial['title']}. {tutorial['summary']}",
            title=tutorial["title"],
            source="Krishi Academy Tutorial",
            category=CATEGORY_EDUCATION,
            crop=tutorial.get("crop", ""),
            guide_key=tutorial["id"],
        ))

    # Quiz explanations are short, factual and genuinely useful as grounding.
    for quiz in QUIZZES:
        for index, question in enumerate(quiz.get("questions", [])):
            explanation = question.get("explanation", "").strip()
            if not explanation:
                continue
            documents.append(Document(
                id=_make_id(CATEGORY_EDUCATION, f"{quiz['id']}-q{index}"),
                text=f"{question['question']} {question.get('answer', '')}. {explanation}",
                title=quiz["title"],
                source="Krishi Academy Quiz",
                category=CATEGORY_EDUCATION,
                guide_key=quiz["id"],
            ))
    return documents


def _from_markdown() -> List[Document]:
    """Index operator-supplied markdown under backend/data/corpus/.

    This is where real ICAR/KVK material belongs. Category comes from the
    containing directory when it names a known category.
    """
    documents: List[Document] = []
    if not CORPUS_DIR.is_dir():
        return documents

    for path in sorted(CORPUS_DIR.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        try:
            raw = path.read_text(encoding="utf-8").strip()
        except Exception as exc:
            print(f"[Corpus] Skipping {path.name}: {exc}")
            continue
        if not raw:
            continue

        parent = path.parent.name.lower()
        category = parent if parent in KNOWN_CATEGORIES else CATEGORY_AGRONOMY

        heading = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
        title = heading.group(1).strip() if heading else path.stem.replace("_", " ").title()

        for index, chunk in enumerate(chunk_text(raw)):
            documents.append(Document(
                id=_make_id(category, f"{path.stem}-{title}", index),
                text=chunk,
                title=title,
                source=f"{path.name}",
                category=category,
            ))
    return documents


_corpus: Optional[List[Document]] = None


def build_corpus() -> List[Document]:
    """Assemble every document, dropping any duplicate ids."""
    documents = (
        _from_knowledge_base()
        + _from_schemes()
        + _from_healthcare()
        + _from_disaster()
        + _from_education()
        + _from_markdown()
    )

    seen = set()
    unique = []
    for document in documents:
        if document.id in seen:
            continue
        seen.add(document.id)
        unique.append(document)
    return unique


def get_corpus(refresh: bool = False) -> List[Document]:
    """Memoized corpus. BM25 and the in-memory store both read from this."""
    global _corpus
    if _corpus is None or refresh:
        _corpus = build_corpus()
    return _corpus


def corpus_by_id() -> Dict[str, Document]:
    return {document.id: document for document in get_corpus()}
