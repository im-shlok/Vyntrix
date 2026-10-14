"""Vector store backends.

Qdrant is used when reachable; otherwise an in-memory numpy index takes over.
The corpus is small enough that brute-force cosine over a matrix is effectively
instant, so losing Qdrant degrades durability rather than functionality.
"""

import os
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.rag.corpus import Document

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "kisaan_kb")

# (doc_id, score)
ScoredId = Tuple[str, float]


class MemoryStore:
    """Brute-force cosine index over a numpy matrix."""

    backend = "memory"

    def __init__(self) -> None:
        self._ids: List[str] = []
        self._categories: List[str] = []
        self._matrix: Optional[np.ndarray] = None

    def upsert(self, documents: List[Document], vectors: List[List[float]]) -> None:
        if not documents or not vectors:
            return
        matrix = np.asarray(vectors, dtype=np.float32)
        # Normalize once so search is a plain dot product.
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._matrix = matrix / norms
        self._ids = [document.id for document in documents]
        self._categories = [document.category for document in documents]

    def search(self, vector: List[float], limit: int = 4,
               category: Optional[str] = None) -> List[ScoredId]:
        if self._matrix is None or not self._ids:
            return []

        query = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(query))
        if norm == 0:
            return []
        scores = self._matrix @ (query / norm)

        candidates = range(len(self._ids))
        if category:
            candidates = [i for i in candidates if self._categories[i] == category]
            if not candidates:
                return []

        ranked = sorted(candidates, key=lambda i: float(scores[i]), reverse=True)
        return [(self._ids[i], float(scores[i])) for i in ranked[:limit]]

    def count(self) -> int:
        return len(self._ids)


class QdrantStore:
    """Qdrant-backed index, created lazily once the vector dimension is known."""

    backend = "qdrant"

    def __init__(self, client, dim: int) -> None:
        self._client = client
        self._dim = dim
        self._count = 0
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        from qdrant_client.http.models import Distance, VectorParams

        collections = self._client.get_collections().collections
        existing = next((c for c in collections if c.name == COLLECTION_NAME), None)

        if existing is not None:
            current_dim = self._collection_dim()
            if current_dim is not None and current_dim != self._dim:
                # The previous build used 384-dim hash vectors. A collection
                # cannot be resized, so it has to be rebuilt.
                print(
                    f"[Qdrant] Collection '{COLLECTION_NAME}' is {current_dim}-dim "
                    f"but the embedder returns {self._dim}-dim. Recreating it."
                )
                self._client.delete_collection(COLLECTION_NAME)
                existing = None

        if existing is None:
            self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
            )
            print(f"[Qdrant] Created collection '{COLLECTION_NAME}' ({self._dim}-dim).")

        self._ensure_category_index()

    def _collection_dim(self) -> Optional[int]:
        try:
            info = self._client.get_collection(COLLECTION_NAME)
            params = info.config.params.vectors
            # Qdrant returns either VectorParams or a named-vector mapping.
            if hasattr(params, "size"):
                return int(params.size)
            if isinstance(params, dict) and params:
                return int(next(iter(params.values())).size)
        except Exception as exc:
            print(f"[Qdrant] Could not read collection config: {exc}")
        return None

    def _ensure_category_index(self) -> None:
        """Index `category` so filtered retrieval does not full-scan."""
        from qdrant_client.http.models import PayloadSchemaType

        try:
            self._client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="category",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            # Already present, which is the common case on restart.
            pass

    def upsert(self, documents: List[Document], vectors: List[List[float]]) -> None:
        from qdrant_client.http.models import PointStruct

        points = [
            PointStruct(id=document.point_id, vector=vector, payload=document.payload())
            for document, vector in zip(documents, vectors)
        ]
        if not points:
            return
        self._client.upsert(collection_name=COLLECTION_NAME, points=points)
        self._count = len(points)

        # Drop points from earlier corpus versions so retrieval cannot surface
        # a document that no longer exists.
        self._prune(keep={document.point_id for document in documents})

    def _prune(self, keep: set) -> None:
        try:
            stale = []
            offset = None
            while True:
                records, offset = self._client.scroll(
                    collection_name=COLLECTION_NAME,
                    limit=256,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False,
                )
                stale.extend(r.id for r in records if r.id not in keep)
                if offset is None:
                    break
            if stale:
                self._client.delete(collection_name=COLLECTION_NAME, points_selector=stale)
                print(f"[Qdrant] Pruned {len(stale)} stale point(s).")
        except Exception as exc:
            print(f"[Qdrant] Prune skipped: {exc}")

    def search(self, vector: List[float], limit: int = 4,
               category: Optional[str] = None) -> List[ScoredId]:
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        query_filter = None
        if category:
            query_filter = Filter(must=[
                FieldCondition(key="category", match=MatchValue(value=category))
            ])

        try:
            # query_points is the current API; older clients only have search.
            if hasattr(self._client, "query_points"):
                response = self._client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=vector,
                    limit=limit,
                    query_filter=query_filter,
                    with_payload=True,
                )
                hits = response.points
            else:
                hits = self._client.search(
                    collection_name=COLLECTION_NAME,
                    query_vector=vector,
                    limit=limit,
                    query_filter=query_filter,
                )
            return [
                (str((hit.payload or {}).get("doc_id", hit.id)), float(hit.score))
                for hit in hits
            ]
        except Exception as exc:
            print(f"[Qdrant] Search failed, falling back: {exc}")
            return []

    def count(self) -> int:
        try:
            return int(self._client.count(COLLECTION_NAME, exact=True).count)
        except Exception:
            return self._count


def connect_qdrant(dim: int):
    """Return a QdrantStore, or None when the server is unreachable."""
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=QDRANT_URL, timeout=2.0)
        client.get_collections()
        store = QdrantStore(client, dim)
        print("[Qdrant] Connected.")
        return store
    except Exception as exc:
        print(f"[Qdrant] Unavailable ({exc}); using in-memory vector index.")
        return None
