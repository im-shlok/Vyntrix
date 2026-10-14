"""Knowledge agent: hybrid retrieval over the agricultural corpus.

This replaces an implementation that was dead code (the graph imported a
different `knowledge_agent` from `agents.py`) and that, where it did run, built
"embeddings" from SHA-256 digests. Hashing destroys input similarity by design,
so cosine distance between two such vectors carried no semantic signal.

This agent only *retrieves*. Generation belongs to `explanation_agent`, which
injects `retrieved_docs` into its prompt. Previously retrieved text was
appended to `state.explanation` and then discarded, because that field is read
only when the LLM is unreachable.
"""

from typing import Any, Dict, List

from app.agents.state import AgentState
from app.rag.retriever import index_corpus, retrieve

# main.py imports this name at startup. Indexing now covers both the lexical
# and dense backends, so the old Qdrant-only seeding function is an alias.
seed_qdrant_knowledge = index_corpus

TOP_K = 4

FALLBACK_ADVISORY = (
    "KVK Advisory: Standard farming procedures suggest maintaining clean "
    "drainage, periodic weeding, and using seed varieties certified by "
    "regional agricultural universities."
)


def knowledge_agent(state: AgentState) -> Dict[str, Any]:
    """Retrieve grounding documents for the user's query."""
    documents = retrieve(
        state.user_query,
        limit=TOP_K,
        # Reuse the planner's vector so this costs no extra embedding call.
        query_vector=state.query_vector,
    )

    if not documents:
        return {
            "explanation": state.explanation + (
                "\n\n[Knowledge Retrieval]\nNo reference document cleared the "
                f"relevance threshold. {FALLBACK_ADVISORY}"
            ),
            "messages": state.messages + [{
                "role": "assistant",
                "content": "[Knowledge Agent] No documents cleared the relevance threshold.",
            }],
        }

    retrieved: List[Dict[str, Any]] = [document.to_dict() for document in documents]
    mode = documents[0].mode

    # Numbered so the explanation agent's [n] citations line up with these.
    lines = [
        f"[{index}] {document.title} ({document.source}): {document.text}"
        for index, document in enumerate(documents, start=1)
    ]

    return {
        "retrieved_docs": retrieved,
        "explanation": state.explanation + (
            f"\n\n[Knowledge Retrieval ({mode})]\n" + "\n".join(lines)
        ),
        "messages": state.messages + [{
            "role": "assistant",
            "content": (
                f"[Knowledge Agent] Retrieved {len(documents)} document(s) "
                f"via {mode} search."
            ),
        }],
    }
