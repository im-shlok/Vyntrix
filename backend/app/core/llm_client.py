"""Shared LLM clients.

`main.py`, the agents and `app.rag.embeddings` all call hosted models. They
cannot import a client from `main` because `main` imports them (circular), so
the clients live here.

Clients are built lazily: a missing API key must degrade at call time, not
break the import graph at startup.
"""

import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import APIConnectionError, APITimeoutError, OpenAI

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

NIM_BASE_URL = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

_client: Optional[OpenAI] = None


def api_key() -> str:
    """Read the key at call time so a late .env load is still picked up."""
    return (os.getenv("NVIDIA_API_KEY") or "").strip()


def is_configured() -> bool:
    """True when an API key is present. Callers use this to pick a fallback."""
    return bool(api_key())


def get_client() -> OpenAI:
    """Return the memoized NIM client used for embeddings, building it on first use."""
    global _client
    if _client is None:
        # Measured: 0.2-0.3s per query embedding (3s when cold), about 1s per
        # 32-document batch. The SDK defaults (600s timeout, 2 retries) could
        # stall a request for minutes, and embeddings.py already retries with
        # backoff, so the SDK must not retry on top of it.
        _client = OpenAI(base_url=NIM_BASE_URL, api_key=api_key(), timeout=15.0, max_retries=0)
    return _client


# Chat models, tried in order until one answers. Override with the CHAT_MODELS
# env var as comma-separated "provider:model" entries.
#
# Measured on the dashboard's explanation prompt: Groq gpt-oss-120b answers in
# about 1s with correct Hindi, while NIM gemma-4-31b took 44-119s per call from
# queueing on the free hosted endpoint, and timed out at 90s even on a
# one-sentence prompt. Groq rate-limits each model separately, so a
# rate-limited model hands over to the next within a second.
#
# NIM is deliberately not in the default chain. During a Groq outage it would
# make each call wait up to 90s and usually time out anyway, so the farmer
# would get the non-LLM fallback text after minutes instead of seconds. Append
# "nim:google/gemma-4-31b-it" to CHAT_MODELS to opt back in.
DEFAULT_CHAT_MODELS = (
    "groq:openai/gpt-oss-120b,"
    "groq:qwen/qwen3.8-27b,"
    "groq:openai/gpt-oss-20b"
)

# The timeout bounds a hung request. NIM's is long because its queue routinely
# takes most of a minute.
_PROVIDERS = {
    "groq": {"base_url": GROQ_BASE_URL, "key_env": "GROQ_API_KEY", "timeout": 20.0},
    "nim": {"base_url": NIM_BASE_URL, "key_env": "NVIDIA_API_KEY", "timeout": 90.0},
}

# gpt-oss and Qwen3 are reasoning models. Low or no reasoning keeps latency down
# and leaves the max_tokens budget for the answer itself.
_MODEL_OPTIONS = {
    "openai/gpt-oss-120b": {"reasoning_effort": "low"},
    "openai/gpt-oss-20b": {"reasoning_effort": "low"},
    "qwen/qwen3.8-27b": {"reasoning_effort": "none"},
}

_chat_clients: Dict[str, Optional[OpenAI]] = {}

# Qwen3 can return its reasoning inline; it must never reach a farmer.
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _chat_client(provider: str) -> Optional[OpenAI]:
    """Memoized client per provider, or None when its API key is missing."""
    if provider not in _chat_clients:
        settings = _PROVIDERS[provider]
        key = (os.getenv(settings["key_env"]) or "").strip()
        _chat_clients[provider] = OpenAI(
            base_url=settings["base_url"],
            api_key=key,
            timeout=settings["timeout"],
            # The chain is the retry strategy: a rate-limited model should hand
            # over to the next one immediately rather than back off and wait.
            max_retries=0,
        ) if key else None
    return _chat_clients[provider]


def _chat_chain() -> List[Tuple[str, str]]:
    # `or` rather than a getenv default: docker-compose passes an empty string
    # when the variable is unset on the host.
    entries = os.getenv("CHAT_MODELS") or DEFAULT_CHAT_MODELS
    chain = []
    for entry in entries.split(","):
        provider, _, model = entry.strip().partition(":")
        if provider in _PROVIDERS and model:
            chain.append((provider, model))
        elif entry.strip():
            print(f"[LLM] Ignoring malformed CHAT_MODELS entry '{entry.strip()}'.")
    return chain


def chat_completion(messages: List[Dict[str, str]], temperature: float = 0.2,
                    top_p: float = 0.8, max_tokens: int = 1000) -> Tuple[str, str]:
    """Return (answer, "provider:model") from the first model in the chain that answers.

    Returns ("", "") when every model fails, so callers fall back to their
    non-LLM output instead of raising.
    """
    # A provider that timed out or refused the connection is down for every
    # model it hosts, so its remaining models are skipped instead of each one
    # waiting out the same timeout.
    unreachable = set()
    for provider, model in _chat_chain():
        if provider in unreachable:
            continue
        client = _chat_client(provider)
        if client is None:
            continue
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                extra_body=_MODEL_OPTIONS.get(model) or None,
            )
            answer = _THINK_RE.sub("", response.choices[0].message.content or "").strip()
            elapsed = time.perf_counter() - started
            if answer:
                print(f"[LLM] {provider}:{model} answered in {elapsed:.1f}s.")
                return answer, f"{provider}:{model}"
            # A reasoning model returns no content when reasoning used up max_tokens.
            print(f"[LLM] {provider}:{model} returned an empty answer after {elapsed:.1f}s "
                  f"(finish_reason={response.choices[0].finish_reason}); trying the next model.")
        except (APITimeoutError, APIConnectionError) as exc:
            unreachable.add(provider)
            print(f"[LLM] {provider}:{model} unreachable after {time.perf_counter() - started:.1f}s "
                  f"({type(exc).__name__}); skipping the rest of {provider}.")
        except Exception as exc:
            print(f"[LLM] {provider}:{model} failed after {time.perf_counter() - started:.1f}s "
                  f"({type(exc).__name__}: {str(exc)[:160]}); trying the next model.")
    print("[LLM] Every chat model failed; callers will use their fallback output.")
    return "", ""
