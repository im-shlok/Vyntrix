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
from typing import Any, Dict, List, Optional, Tuple

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
    # Key of the structured guide this chunk belongs to: a seed dict key such
    # as "snake_bite", or the `guide_key` in a markdown file's front matter.
    # Lets retrieval *select* a guide while the structured record still
    # supplies the step arrays the frontend renders.
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


def _infer_category(text: str) -> str:
    """Classify a KNOWLEDGE_BASE entry so category-filtered search finds it.

    These entries carry no category of their own, and defaulting everything to
    agronomy hides the first-aid and disaster entries from the healthcare and
    disaster agents, which retrieve with a category filter.
    """
    lowered = text.lower()
    if any(term in lowered for term in
           ("poison", "first aid", "antidote", "snake", "venom", "heat stroke")):
        return CATEGORY_HEALTH
    if any(term in lowered for term in
           ("lightning", "flood", "cyclone", "storm", "disaster", "evacuat")):
        return CATEGORY_DISASTER
    return CATEGORY_AGRONOMY


def _from_knowledge_base() -> List[Document]:
    documents = []
    for item in KNOWLEDGE_BASE:
        source, body = _split_source(item["content"], "KVK Advisory")
        category = _infer_category(f"{item['query']} {item['content']}")
        # The query phrasing is embedded alongside the body because it mirrors
        # how a farmer actually asks, which improves the match.
        documents.append(Document(
            id=_make_id(category, item["query"]),
            text=f"{item['query']}. {body}",
            title=item["query"].title(),
            source=source,
            category=category,
        ))
    return documents


def scheme_key(name: str) -> str:
    """Stable key for a scheme name, e.g. "PM-KISAN (Pradhan ...)" -> "pm_kisan".

    A markdown file under scheme/ declares this key to supersede a seed entry.
    """
    base = name.split(" (", 1)[0]
    return re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")


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
            guide_key=scheme_key(scheme["name"]),
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


_FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+?)\s*$")

# Maps a `##` heading onto the structured field it supplies. Checked in order,
# so "First aid steps" lands on steps and "Signs and symptoms" on symptoms.
# Headings that match nothing ("Do not", "Prevention") stay retrievable text.
_SECTION_ALIASES = (
    ("symptoms", ("symptom", "signs")),
    ("documents", ("document",)),
    ("benefits", ("benefit",)),
    ("eligibility", ("eligib", "who can apply")),
    ("summary", ("summary", "overview")),
    ("steps", ("step", "first aid", "what to do", "how to apply")),
)


def _parse_front_matter(raw: str) -> Tuple[Dict[str, str], str]:
    """Split an optional `---` block of `key: value` lines off the top."""
    match = _FRONT_MATTER_RE.match(raw)
    if not match:
        return {}, raw
    meta: Dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip():
            meta[key.strip().lower()] = value.strip().strip("\"'")
    return meta, raw[match.end():].strip()


def _canonical_section(heading: str) -> Optional[str]:
    lowered = heading.lower()
    for name, needles in _SECTION_ALIASES:
        if any(needle in lowered for needle in needles):
            return name
    return None


def _clean_inline(text: str) -> str:
    """Drop markdown emphasis so card text renders as plain prose."""
    return re.sub(r"\*{1,3}([^*\n]+?)\*{1,3}", r"\1", text).strip()


def _parse_sections(body: str) -> Dict[str, Dict[str, List[str]]]:
    """Collect list items and prose under each recognised `##` heading."""
    sections: Dict[str, Dict[str, List[str]]] = {}
    current: Optional[str] = None
    for line in body.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            # `##` opens a section and `#` closes it; deeper headings stay
            # inside whatever section is open.
            if level == 2:
                current = _canonical_section(heading.group(2))
                if current:
                    sections.setdefault(current, {"items": [], "text": []})
            elif level == 1:
                current = None
            continue
        if current is None or not line.strip():
            continue
        item = _LIST_ITEM_RE.match(line)
        if item:
            sections[current]["items"].append(_clean_inline(item.group(1)))
        else:
            sections[current]["text"].append(_clean_inline(line))
    return sections


def _structured_record(title: str, meta: Dict[str, str],
                       sections: Dict[str, Dict[str, List[str]]]) -> Dict[str, Any]:
    """The fields agents render: steps for first-aid and disaster cards,
    benefits and documents for schemes, summary and duration for tutorials."""

    def items(name: str) -> List[str]:
        return list(sections.get(name, {}).get("items", []))

    def prose(name: str) -> str:
        section = sections.get(name)
        if not section:
            return ""
        parts = [" ".join(section["text"])] if section["text"] else []
        if section["items"]:
            parts.append("; ".join(section["items"]))
        return " ".join(parts).strip()

    return {
        "title": title,
        "steps": items("steps"),
        "symptoms": items("symptoms"),
        "documents": items("documents"),
        "benefits": prose("benefits"),
        "eligibility": prose("eligibility"),
        "summary": meta.get("summary") or prose("summary"),
        "meta": meta,
    }


def _from_markdown() -> Tuple[List[Document], Dict[str, Dict[str, Dict[str, Any]]]]:
    """Index operator-supplied markdown under backend/data/corpus/.

    This is where real ICAR/KVK material belongs. Category comes from the
    containing directory when it names a known category. A file whose front
    matter declares a `guide_key` also becomes a structured guide that agents
    can select and render, so adding a file adds a card without code changes.
    """
    documents: List[Document] = []
    guides: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if not CORPUS_DIR.is_dir():
        return documents, guides

    for path in sorted(CORPUS_DIR.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        try:
            # utf-8-sig drops the byte-order mark Windows editors often add,
            # which would otherwise hide the front matter.
            raw = path.read_text(encoding="utf-8-sig").strip()
        except Exception as exc:
            print(f"[Corpus] Skipping {path.name}: {exc}")
            continue

        meta, body = _parse_front_matter(raw)
        if not body:
            continue

        parent = path.parent.name.lower()
        category = parent if parent in KNOWN_CATEGORIES else CATEGORY_AGRONOMY

        heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = heading.group(1).strip() if heading else path.stem.replace("_", " ").title()
        guide_key = meta.get("guide_key", "")

        if guide_key:
            category_guides = guides.setdefault(category, {})
            if guide_key in category_guides:
                print(f"[Corpus] Duplicate guide_key '{guide_key}' in {category}/; "
                      f"{path.name} replaces the earlier file.")
            category_guides[guide_key] = _structured_record(title, meta, _parse_sections(body))

        for index, chunk in enumerate(chunk_text(body)):
            # Only the first chunk contains the `# Title` line. Prefixing the
            # title to the rest keeps a chunk such as "Documents required: ..."
            # attributable to its scheme in both dense and lexical search.
            text = chunk if index == 0 else f"{title}\n\n{chunk}"
            documents.append(Document(
                id=_make_id(category, f"{path.stem}-{title}", index),
                text=text,
                title=title,
                source=path.name,
                category=category,
                crop=meta.get("crop", ""),
                guide_key=guide_key,
            ))
    return documents, guides


_corpus: Optional[List[Document]] = None
_guides: Dict[str, Dict[str, Dict[str, Any]]] = {}


def build_corpus() -> List[Document]:
    """Assemble every document, dropping superseded seed entries and duplicate ids."""
    global _guides

    markdown, guides = _from_markdown()
    _guides = guides

    # A markdown file that declares a seed entry's guide_key supersedes it, so
    # the corpus never holds two competing versions of one guide.
    claimed = {(d.category, d.guide_key) for d in markdown if d.guide_key}
    seed = (
        _from_knowledge_base()
        + _from_schemes()
        + _from_healthcare()
        + _from_disaster()
        + _from_education()
    )
    seed = [d for d in seed if not (d.guide_key and (d.category, d.guide_key) in claimed)]

    seen = set()
    unique = []
    for document in seed + markdown:
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


def get_guides(category: str) -> Dict[str, Dict[str, Any]]:
    """Structured guides defined by markdown files in one category, by guide_key."""
    get_corpus()
    return _guides.get(category, {})


def corpus_by_id() -> Dict[str, Document]:
    return {document.id: document for document in get_corpus()}
