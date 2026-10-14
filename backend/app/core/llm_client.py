"""Shared NVIDIA NIM client.

`main.py` and `app.rag.embeddings` both need an OpenAI-compatible client pointed
at NVIDIA NIM. `app.rag` cannot import it from `main` because `main` imports
`app.rag` (circular), so the client lives here and both sides import it.

The client is built lazily: a missing NVIDIA_API_KEY must degrade at call time,
not break the import graph at startup.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

# main.py calls load_dotenv() at line 44, but its `from app.*` imports run
# before that, so anything reading os.environ during import would see an empty
# environment. Load it here too, from an absolute path so the result does not
# depend on the process working directory. Repeat calls are harmless.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

NIM_BASE_URL = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")

_client: Optional[OpenAI] = None


def api_key() -> str:
    """Read the key at call time so a late .env load is still picked up."""
    return (os.getenv("NVIDIA_API_KEY") or "").strip()


def is_configured() -> bool:
    """True when an API key is present. Callers use this to pick a fallback."""
    return bool(api_key())


def get_client() -> OpenAI:
    """Return the memoized NIM client, building it on first use."""
    global _client
    if _client is None:
        _client = OpenAI(base_url=NIM_BASE_URL, api_key=api_key())
    return _client
