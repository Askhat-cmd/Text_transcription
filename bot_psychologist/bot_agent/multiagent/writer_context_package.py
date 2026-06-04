"""Writer-visible context packaging with strict RAG gating."""

from __future__ import annotations

from typing import Any

from .contracts.context_package import ContextAssemblyPackage
from .contracts.memory_bundle import MemoryBundle


WRITER_CONTEXT_PACKAGE_VERSION = "writer_context_package_v1"


def _writer_recent_turns_from_package(package: ContextAssemblyPackage | None) -> list[dict[str, str]]:
    if package is None:
        return []
    items: list[dict[str, str]] = []
    for turn in list(package.recent_turns_full or []):
        text = str(getattr(turn, "content", "") or "").strip()
        if text:
            items.append(
                {
                    "turn_id": str(getattr(turn, "turn_id", "") or ""),
                    "role": str(getattr(turn, "role", "") or ""),
                    "content": text,
                }
            )
    for turn in list(package.recent_turns_summarized or []):
        text = str(getattr(turn, "summary", "") or "").strip()
        if text:
            items.append(
                {
                    "turn_id": str(getattr(turn, "turn_id", "") or ""),
                    "role": str(getattr(turn, "role", "") or ""),
                    "content": text,
                }
            )
    return items


def _fallback_recent_turns(memory_bundle: MemoryBundle) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for idx, turn in enumerate(list(memory_bundle.recent_turns or []), start=1):
        if not isinstance(turn, dict):
            continue
        user_text = str(turn.get("user_input", "") or "").strip()
        bot_text = str(turn.get("bot_response", "") or "").strip()
        if user_text:
            items.append({"turn_id": f"turn_{idx}_user", "role": "user", "content": user_text})
        if bot_text:
            items.append({"turn_id": f"turn_{idx}_assistant", "role": "assistant", "content": bot_text})
    return items


def build_writer_context_package_v1(
    *,
    memory_bundle: MemoryBundle,
    context_package: ContextAssemblyPackage | None,
    retrieval_decision: dict[str, Any] | None,
    fresh_chat_context_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    retrieval = dict(retrieval_decision or {})
    fresh_policy = dict(fresh_chat_context_policy or {})
    recent_turns = _writer_recent_turns_from_package(context_package)
    if not recent_turns:
        recent_turns = _fallback_recent_turns(memory_bundle)

    profile_allowed = bool(fresh_policy.get("cross_session_memory_allowed", True))
    profile_for_writer = (
        {
            "patterns": list(memory_bundle.user_profile.patterns or []),
            "values": list(memory_bundle.user_profile.values or []),
            "progress_notes": list(memory_bundle.user_profile.progress_notes or []),
        }
        if profile_allowed
        else {}
    )

    explicit_retrieval_gate = "rag_included_count" in retrieval
    if explicit_retrieval_gate:
        rag_for_writer = [
            dict(item)
            for item in list(retrieval.get("rag_included_for_writer", []) or [])
            if isinstance(item, dict)
        ]
    elif context_package is not None and list(context_package.knowledge_rag_hits or []):
        rag_for_writer = [dict(item) for item in list(context_package.knowledge_rag_hits or []) if isinstance(item, dict)]
    else:
        rag_for_writer = [dict(item) for item in list(memory_bundle.knowledge_rag_hits or []) if isinstance(item, dict)]

    included_chunk_ids = {
        str(item.get("chunk_id", "") or "")
        for item in rag_for_writer
        if isinstance(item, dict)
    }
    rag_candidates_for_trace: list[dict[str, Any]] = []
    for hit in list(memory_bundle.semantic_hits or []):
        chunk_id = str(getattr(hit, "chunk_id", "") or "")
        rag_candidates_for_trace.append(
            {
                "chunk_id": chunk_id,
                "source": str(getattr(hit, "source", "unknown") or "unknown"),
                "score": float(getattr(hit, "score", 0.0) or 0.0),
                "content_preview": str(getattr(hit, "content", "") or "")[:240],
                "included_for_writer": chunk_id in included_chunk_ids,
                "reason_not_included": (
                    ""
                    if chunk_id in included_chunk_ids
                    else str(retrieval.get("rag_suppressed_reason", "") or "not_selected_for_writer")
                ),
            }
        )

    return {
        "version": WRITER_CONTEXT_PACKAGE_VERSION,
        "recent_turns_for_writer": recent_turns,
        "profile_for_writer": profile_for_writer,
        "rag_for_writer": rag_for_writer,
        "rag_candidates_for_trace": rag_candidates_for_trace,
        "rag_gate_decision": retrieval,
    }


__all__ = ["WRITER_CONTEXT_PACKAGE_VERSION", "build_writer_context_package_v1"]
