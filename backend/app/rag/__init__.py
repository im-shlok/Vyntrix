"""Retrieval-augmented generation for Agriva.

Public surface:

    index_corpus()   build the lexical and dense indexes (called at startup)
    retrieve()       hybrid search, optionally filtered by category
    embed_query()    one query vector, reused across every agent in a request
    route_intent()   semantic planner routing, None when not confident
    get_status()     introspection for /api/rag/status
"""

from app.rag.corpus import (
    CATEGORY_AGRONOMY,
    CATEGORY_DISASTER,
    CATEGORY_EDUCATION,
    CATEGORY_HEALTH,
    CATEGORY_SCHEME,
    Document,
    get_corpus,
)
from app.rag.embeddings import embed_query
from app.rag.intents import debug_scores as intent_scores
from app.rag.intents import route as route_intent
from app.rag.intents import warm_up as warm_up_intents
from app.rag.retriever import RetrievedDoc, get_status, index_corpus, retrieve

__all__ = [
    "CATEGORY_AGRONOMY",
    "CATEGORY_DISASTER",
    "CATEGORY_EDUCATION",
    "CATEGORY_HEALTH",
    "CATEGORY_SCHEME",
    "Document",
    "RetrievedDoc",
    "embed_query",
    "get_corpus",
    "get_status",
    "index_corpus",
    "intent_scores",
    "retrieve",
    "route_intent",
    "warm_up_intents",
]
