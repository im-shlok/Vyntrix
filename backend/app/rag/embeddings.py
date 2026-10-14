"""NVIDIA NIM text embeddings with a persistent cache.

Embeddings are a network call, so two safeguards matter:

* A disk cache keyed by content hash. The corpus is embedded once ever, not
  once per boot, so restarts cost no API quota.
* Every function returns ``None`` instead of raising when the API is
  unreachable, letting callers fall back to lexical retrieval.

The vector dimension is probed from the first successful response rather than
hardcoded, so swapping EMBED_MODEL needs no code change and a wrong assumption
about a model's dimension cannot corrupt the vector store.
"""

import hashlib
import os
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from app.core.llm_client import get_client, is_configured

EMBED_MODEL = os.getenv("EMBED_MODEL", "nvidia/nemotron-3-embed-1b")

# bge-m3 is asymmetric: documents and queries use different input types, and
# mixing them up measurably degrades ranking quality.
INPUT_TYPE_DOCUMENT = "passage"
INPUT_TYPE_QUERY = "query"

BATCH_SIZE = 32
MAX_RETRIES = 3
QUERY_CACHE_SIZE = 256

CACHE_DIR = Path(__file__).resolve().parents[2] / ".rag_cache"
CACHE_FILE = CACHE_DIR / "embeddings.npz"

_lock = threading.Lock()
_disk_cache: Optional[Dict[str, np.ndarray]] = None
_disk_cache_dirty = False
_query_cache: "OrderedDict[str, List[float]]" = OrderedDict()
_dim: Optional[int] = None

# Set once if the endpoint rejects the input_type parameter, so we stop sending
# it instead of paying a failed request on every call.
_input_type_supported = True

_stats = {"api_calls": 0, "disk_hits": 0, "query_cache_hits": 0, "failures": 0}


def _cache_key(text: str, input_type: str) -> str:
    raw = f"{EMBED_MODEL}\x00{input_type}\x00{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _load_disk_cache() -> Dict[str, np.ndarray]:
    """Load the persisted vectors, tolerating a missing or corrupt cache file."""
    global _disk_cache, _dim
    if _disk_cache is not None:
        return _disk_cache

    _disk_cache = {}
    if CACHE_FILE.is_file():
        try:
            with np.load(CACHE_FILE, allow_pickle=False) as data:
                keys = data["keys"]
                vectors = data["vectors"]
            _disk_cache = {str(k): vectors[i] for i, k in enumerate(keys)}
            if len(vectors):
                _dim = int(vectors.shape[1])
            print(f"[Embeddings] Loaded {len(_disk_cache)} cached vectors from disk.")
        except Exception as exc:
            # A corrupt cache must never block startup; re-embedding is the
            # only cost of discarding it.
            print(f"[Embeddings] Ignoring unreadable cache ({exc}); will re-embed.")
            _disk_cache = {}
    return _disk_cache


def flush_cache() -> None:
    """Persist newly computed vectors. Safe to call when nothing changed."""
    global _disk_cache_dirty
    with _lock:
        if not _disk_cache_dirty or not _disk_cache:
            return
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            keys = list(_disk_cache.keys())
            vectors = np.vstack([_disk_cache[k] for k in keys]).astype(np.float32)
            np.savez_compressed(CACHE_FILE, keys=np.array(keys), vectors=vectors)
            _disk_cache_dirty = False
            print(f"[Embeddings] Persisted {len(keys)} vectors to {CACHE_FILE.name}.")
        except Exception as exc:
            print(f"[Embeddings] Could not persist cache: {exc}")


def _call_api(texts: List[str], input_type: str) -> Optional[List[List[float]]]:
    """Embed a single batch, retrying transient failures with backoff."""
    global _input_type_supported, _dim

    client = get_client()
    for attempt in range(MAX_RETRIES):
        try:
            kwargs = {"model": EMBED_MODEL, "input": texts}
            if _input_type_supported:
                kwargs["extra_body"] = {"input_type": input_type, "truncate": "END"}
            else:
                kwargs["extra_body"] = {"truncate": "END"}

            response = client.embeddings.create(**kwargs)
            _stats["api_calls"] += 1

            # Providers do not guarantee response ordering, so sort by index.
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors = [list(item.embedding) for item in ordered]
            if vectors and _dim is None:
                _dim = len(vectors[0])
                print(f"[Embeddings] {EMBED_MODEL} returned dimension {_dim}.")
            return vectors

        except Exception as exc:
            message = str(exc).lower()
            # Some NIM models reject input_type; drop it and retry once rather
            # than failing every subsequent call.
            if _input_type_supported and ("input_type" in message or "extra" in message):
                print("[Embeddings] Endpoint rejected input_type; retrying without it.")
                _input_type_supported = False
                continue
            if attempt == MAX_RETRIES - 1:
                print(f"[Embeddings] Failed after {MAX_RETRIES} attempts: {exc}")
                _stats["failures"] += 1
                return None
            time.sleep(0.5 * (2 ** attempt))
    return None


def _embed(texts: List[str], input_type: str) -> Optional[List[List[float]]]:
    """Embed texts, serving cache hits and batching the remainder."""
    if not texts:
        return []
    if not is_configured():
        return None

    global _disk_cache_dirty
    cache = _load_disk_cache()
    keys = [_cache_key(text, input_type) for text in texts]

    results: List[Optional[np.ndarray]] = []
    pending: List[str] = []
    pending_positions: List[int] = []
    for position, (text, key) in enumerate(zip(texts, keys)):
        hit = cache.get(key)
        if hit is not None:
            _stats["disk_hits"] += 1
            results.append(hit)
        else:
            results.append(None)
            pending.append(text)
            pending_positions.append(position)

    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]
        vectors = _call_api(batch, input_type)
        if vectors is None or len(vectors) != len(batch):
            return None
        with _lock:
            for offset, vector in enumerate(vectors):
                position = pending_positions[start + offset]
                array = np.asarray(vector, dtype=np.float32)
                results[position] = array
                cache[keys[position]] = array
                _disk_cache_dirty = True

    if any(item is None for item in results):
        return None
    return [item.tolist() for item in results]


def embed_documents(texts: List[str]) -> Optional[List[List[float]]]:
    """Embed corpus documents. Returns None if the API is unavailable."""
    return _embed(texts, INPUT_TYPE_DOCUMENT)


def embed_query(text: str) -> Optional[List[float]]:
    """Embed a single search query, with an in-process LRU for repeats.

    The dashboard reissues the same "telemetry status" query constantly, so the
    LRU removes a round-trip from the common path.
    """
    if not text or not text.strip():
        return None

    key = _cache_key(text, INPUT_TYPE_QUERY)
    with _lock:
        cached = _query_cache.get(key)
        if cached is not None:
            _query_cache.move_to_end(key)
            _stats["query_cache_hits"] += 1
            return cached

    vectors = _embed([text], INPUT_TYPE_QUERY)
    if not vectors:
        return None

    with _lock:
        _query_cache[key] = vectors[0]
        if len(_query_cache) > QUERY_CACHE_SIZE:
            _query_cache.popitem(last=False)
    return vectors[0]


def embedding_dim() -> Optional[int]:
    """Probed vector dimension, or None before the first successful call."""
    if _dim is None:
        _load_disk_cache()
    return _dim


def is_available() -> bool:
    """Whether dense retrieval can be attempted at all."""
    return is_configured()


def stats() -> Dict[str, int]:
    return dict(_stats)
