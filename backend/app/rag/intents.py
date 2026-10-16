"""Semantic intent routing for the planner.

The keyword lists stay in place as the fallback for when the embedder is
unavailable or no intent clears the confidence threshold.
"""

import os
from typing import Dict, List, Optional

import numpy as np

from app.rag import embeddings

# Cosine floor for accepting an intent. Below this the query is treated as
# unroutable and the caller falls back to keyword matching. Measured for
# nvidia/nemotron-3-embed-1b: clear intents score 0.40-0.86, off-domain queries
# 0.07-0.19. 0.35 sits in the gap. Re-measure if EMBED_MODEL changes.
INTENT_THRESHOLD = float(os.getenv("RAG_INTENT_THRESHOLD", "0.35"))
# Secondary intents must score within this margin of the best one, so a query
# that clearly means one thing does not drag in loosely related agents.
INTENT_MARGIN = 0.15
# Cap on intents per query, to bound how long the agent pipeline grows.
MAX_INTENTS = 4

# Agent lists mirror the keyword branches in planner_agent so semantic routing
# produces the same pipelines for the same intents.
INTENTS: Dict[str, Dict] = {
    "disease": {
        "agents": ["vision", "knowledge", "agriculture", "government"],
        "exemplars": [
            "there are yellow spots on my tomato leaves",
            "my crop has a disease, what should I do",
            "brown patches are spreading on the rice leaves",
            "insects and pests are eating my plants",
            "the leaves are curling and turning yellow",
            "my plants are wilting and dying",
            "identify this plant disease from a photo",
            "white powder on the underside of leaves",
            "weeds are taking over my field",
        ],
    },
    "weather": {
        "agents": ["weather", "disaster", "agriculture"],
        "exemplars": [
            "will it rain tomorrow",
            "what is the weather forecast for my farm",
            "is it too hot to spray pesticide today",
            "should I irrigate given the humidity",
            "when is the next rainfall expected",
            "frost warning for my crops",
        ],
    },
    "market": {
        "agents": ["market", "agriculture"],
        "exemplars": [
            "what is the mandi price for my crop",
            "where should I sell my harvest",
            "is the market rate going up or down",
            "what is the minimum support price",
            "best time to sell tomatoes for profit",
            "which mandi is paying the most",
        ],
    },
    "soil": {
        "agents": ["soil", "agriculture", "market"],
        "exemplars": [
            "what fertilizer should I apply",
            "my soil pH is too low",
            "how much urea and potash per acre",
            "nitrogen deficiency in my field",
            "soil moisture is very low",
            "how do I improve soil health",
        ],
    },
    "scheme": {
        "agents": ["government", "knowledge"],
        "exemplars": [
            "which government scheme am I eligible for",
            "how do I apply for PM-KISAN",
            "is there a subsidy for farm machinery",
            "crop insurance for my land",
            "I need an agricultural loan",
            "what documents are needed for the yojana",
            "government help to install solar panels for irrigation",
            "free soil testing from the government",
            "selling produce through the online national market",
            "micro irrigation sprinkler subsidy",
            "kisan credit card for farm expenses",
        ],
    },
    "health": {
        "agents": ["healthcare", "knowledge"],
        "exemplars": [
            "a snake bit me while working in the field",
            "first aid for pesticide poisoning",
            "I feel dizzy after spraying chemicals",
            "heat stroke symptoms and treatment",
            "where is the nearest hospital",
            "someone swallowed pesticide by accident",
            "electrocuted by a live wire near the borewell",
            "injured badly by a thresher machine",
            "worker fainted in the heat during harvest",
            "stung by a scorpion while lifting stones",
            "bitten by a stray dog",
        ],
    },
    "disaster": {
        "agents": ["disaster", "healthcare", "knowledge"],
        "exemplars": [
            "my field is flooded",
            "what to do during a lightning storm",
            "a cyclone is approaching my village",
            "how do I estimate flood crop damage",
            "emergency evacuation from the farm",
            "heavy storm destroyed my crops",
            "hail damaged the wheat crop",
            "extreme heat wave affecting crops",
            "no rainfall and crops are drying due to drought",
        ],
    },
    "education": {
        "agents": ["education", "knowledge"],
        "exemplars": [
            "teach me about drip irrigation",
            "I want to learn modern farming techniques",
            "is there a tutorial or video on this",
            "how is vermicompost prepared",
            "steps to take soil samples for the lab",
            "learn pest management without too many chemicals",
            "how to do seed treatment with fungicide",
            "take a quiz about crop diseases",
            "explain how composting works",
        ],
    },
    "agriculture": {
        "agents": ["agriculture", "knowledge"],
        "exemplars": [
            "general advice for growing my crop",
            "when should I sow the seeds",
            "how much water does this crop need",
            "how do I increase my yield",
            "what crop should I plant this season",
            "how often should I weed the field",
        ],
    },
}

_matrix: Optional[np.ndarray] = None
_labels: List[str] = []


def _build() -> bool:
    """Embed every exemplar once. Vectors come from the disk cache on restart."""
    global _matrix, _labels
    if _matrix is not None:
        return True
    if not embeddings.is_available():
        return False

    texts: List[str] = []
    labels: List[str] = []
    for intent, spec in INTENTS.items():
        for exemplar in spec["exemplars"]:
            texts.append(exemplar)
            labels.append(intent)

    # Exemplars take the document side of the asymmetric model, so the caller's
    # query vector (input_type="query") can be reused here unchanged.
    vectors = embeddings.embed_documents(texts)
    embeddings.flush_cache()
    if vectors is None:
        return False

    matrix = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    _matrix = matrix / norms
    _labels = labels
    print(f"[RAG] Intent router ready: {len(INTENTS)} intents, {len(texts)} exemplars.")
    return True


def is_ready() -> bool:
    return _matrix is not None


def warm_up() -> bool:
    """Pre-embed exemplars at startup so the first request is not slower."""
    return _build()


def route(query_vector: Optional[List[float]]) -> Optional[List[str]]:
    """Map a query vector to an agent pipeline.

    Returns None when routing is not possible or not confident, which tells the
    planner to fall back to keyword matching.
    """
    if query_vector is None:
        return None
    if not _build():
        return None

    query = np.asarray(query_vector, dtype=np.float32)
    norm = float(np.linalg.norm(query))
    if norm == 0:
        return None
    scores = _matrix @ (query / norm)

    # An intent scores as well as its single best exemplar.
    best: Dict[str, float] = {}
    for label, score in zip(_labels, scores):
        value = float(score)
        if value > best.get(label, -1.0):
            best[label] = value

    if not best:
        return None
    top = max(best.values())
    floor = max(INTENT_THRESHOLD, top - INTENT_MARGIN)
    accepted = [
        (intent, score) for intent, score in best.items()
        if score >= floor
    ]
    if not accepted:
        return None

    accepted.sort(key=lambda item: item[1], reverse=True)

    agents: List[str] = []
    for intent, _ in accepted[:MAX_INTENTS]:
        for agent in INTENTS[intent]["agents"]:
            if agent not in agents:
                agents.append(agent)
    return agents


def debug_scores(query_vector: Optional[List[float]]) -> Dict[str, float]:
    """Per-intent scores, for inspecting routing decisions."""
    if query_vector is None or not _build():
        return {}
    query = np.asarray(query_vector, dtype=np.float32)
    norm = float(np.linalg.norm(query))
    if norm == 0:
        return {}
    scores = _matrix @ (query / norm)

    best: Dict[str, float] = {}
    for label, score in zip(_labels, scores):
        value = round(float(score), 4)
        if value > best.get(label, -1.0):
            best[label] = value
    return dict(sorted(best.items(), key=lambda item: item[1], reverse=True))
