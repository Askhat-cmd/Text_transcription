"""Writer-visible context packaging with strict RAG gating."""

from __future__ import annotations

from typing import Any

from ..feature_flags import feature_flags
from ..knowledge.semantic_card_payload_adapter import (
    build_semantic_cards_pilot_selection,
    get_semantic_cards_pilot_config,
)
from .contracts.context_package import ContextAssemblyPackage
from .contracts.memory_bundle import MemoryBundle
from .writer_kb_payload import (
    build_future_graduation_notes,
    build_writer_kb_payload,
    build_writer_kb_payload_trace,
    get_writer_kb_payload_config,
)


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
    user_message: str = "",
    memory_bundle: MemoryBundle,
    context_package: ContextAssemblyPackage | None,
    retrieval_decision: dict[str, Any] | None,
    fresh_chat_context_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    retrieval = dict(retrieval_decision or {})
    composer = (
        dict(retrieval.get("composer", {}))
        if isinstance(retrieval.get("composer"), dict)
        else (
            dict(retrieval.get("contextual_retrieval_query_composer", {}))
            if isinstance(retrieval.get("contextual_retrieval_query_composer"), dict)
            else {}
        )
    )
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
        chunking_quality = (
            dict(getattr(hit, "chunking_quality", {}) or {})
            if isinstance(getattr(hit, "chunking_quality", None), dict)
            else {}
        )
        rag_candidates_for_trace.append(
            {
                "chunk_id": chunk_id,
                "source": str(getattr(hit, "source", "unknown") or "unknown"),
                "score": float(getattr(hit, "score", 0.0) or 0.0),
                "content_preview": str(getattr(hit, "content", "") or "")[:240],
                "chunk_type": str(chunking_quality.get("chunk_type", "general_text") or "general_text"),
                "included_for_writer": chunk_id in included_chunk_ids,
                "reason_not_included": (
                    ""
                    if chunk_id in included_chunk_ids
                    else str(retrieval.get("rag_suppressed_reason", "") or "not_selected_for_writer")
                ),
            }
        )

    retrieval_context_chunks = []
    for item in rag_for_writer:
        if not isinstance(item, dict):
            continue
        chunking_quality = (
            dict(item.get("chunking_quality", {}))
            if isinstance(item.get("chunking_quality"), dict)
            else {}
        )
        retrieval_context_chunks.append(
            {
                "chunk_id": str(item.get("chunk_id", "") or ""),
                "chunk_type": str(chunking_quality.get("chunk_type", "general_text") or "general_text"),
                "summary": str(item.get("content", "") or "")[:160],
                "content_preview": str(item.get("content", "") or "")[:240],
                "allowed_use": ["writer_support"],
                "why_included": str(retrieval.get("rag_included_reason", "") or "selected_for_writer"),
            }
        )

    hybrid_plan = (
        dict(retrieval.get("hybrid_retrieval_plan", {}))
        if isinstance(retrieval.get("hybrid_retrieval_plan"), dict)
        else {}
    )
    semantic_cards_pilot = build_semantic_cards_pilot_selection(
        user_message=user_message,
        retrieval_decision=retrieval,
        config=get_semantic_cards_pilot_config(),
    )
    semantic_card_payload_items = [
        dict(item)
        for item in list(semantic_cards_pilot.get("payload_items", []) or [])
        if isinstance(item, dict)
    ]
    rag_for_writer_for_payload = list(rag_for_writer) + semantic_card_payload_items

    payload_config = get_writer_kb_payload_config()
    payload_resolution = feature_flags.resolve_bool("WRITER_KB_PAYLOAD_ENABLED")
    writer_kb_payload_failed = False
    writer_kb_payload_failure_reason = ""
    overlay_items = []
    overlay_shadow = retrieval.get("overlay_shadow")
    if isinstance(overlay_shadow, dict):
        overlay_items = [
            dict(item)
            for item in list(overlay_shadow.get("matched_candidates", []) or [])
            if isinstance(item, dict)
        ]
    try:
        writer_kb_payload = build_writer_kb_payload(
            semantic_hits=[
                dict(item)
                for item in list(memory_bundle.knowledge_rag_hits or [])
                if isinstance(item, dict)
            ]
            or [
                {
                    "chunk_id": str(getattr(hit, "chunk_id", "") or ""),
                    "source": str(getattr(hit, "source", "unknown") or "unknown"),
                    "score": float(getattr(hit, "score", 0.0) or 0.0),
                    "content": str(getattr(hit, "content", "") or ""),
                    "governance": (
                        dict(getattr(hit, "governance", {}) or {})
                        if isinstance(getattr(hit, "governance", None), dict)
                        else {}
                    ),
                    "chunking_quality": (
                        dict(getattr(hit, "chunking_quality", {}) or {})
                        if isinstance(getattr(hit, "chunking_quality", None), dict)
                        else {}
                    ),
                }
                for hit in list(memory_bundle.semantic_hits or [])
            ],
            rag_for_writer=rag_for_writer_for_payload,
            overlay_items=overlay_items,
            config=payload_config,
        )
    except Exception as exc:  # pragma: no cover - safe fallback branch
        writer_kb_payload_failed = True
        writer_kb_payload_failure_reason = str(exc)
        writer_kb_payload = {
            "schema_version": "writer_kb_payload_v1",
            "enabled": False,
            "chunk_count": 0,
            "total_sent_char_count": 0,
            "chunks": [],
            "warnings": ["writer_kb_payload_failed"],
            "blockers": [],
        }
    fallback_reason = ""
    if not bool(payload_resolution.get("effective_value", False)):
        fallback_reason = "disabled_by_config"
    elif writer_kb_payload_failed:
        fallback_reason = "builder_failure"
    elif int(writer_kb_payload.get("chunk_count", 0) or 0) <= 0:
        fallback_reason = "no_eligible_chunks"

    writer_kb_payload_trace = build_writer_kb_payload_trace(
        payload=writer_kb_payload,
        input_rag_for_writer_count=len(rag_for_writer),
        configured_enabled=bool(payload_resolution.get("effective_value", False)),
        configured_source=str(payload_resolution.get("source", "") or ""),
        fallback_reason=fallback_reason,
    )
    if writer_kb_payload_failed:
        writer_kb_payload_trace["warnings"] = list(
            dict.fromkeys(
                list(writer_kb_payload_trace.get("warnings", []) or [])
                + ["writer_kb_payload_failed"]
            )
        )
    future_graduation_notes = build_future_graduation_notes(
        payload=writer_kb_payload,
        trace=writer_kb_payload_trace,
        legacy_fallback_reason=fallback_reason or writer_kb_payload_failure_reason,
    )

    return {
        "version": WRITER_CONTEXT_PACKAGE_VERSION,
        "recent_turns_for_writer": recent_turns,
        "profile_for_writer": profile_for_writer,
        "rag_for_writer": rag_for_writer,
        "semantic_cards_pilot": {
            key: value
            for key, value in dict(semantic_cards_pilot).items()
            if key != "payload_items"
        },
        "semantic_card_payload_items": semantic_card_payload_items,
        "rag_candidates_for_trace": rag_candidates_for_trace,
        "rag_gate_decision": retrieval,
        "contextual_retrieval_query_composer": composer,
        "contextual_retrieval_query_composer_version": str(
            composer.get("version", "contextual_retrieval_query_composer_v1")
            or "contextual_retrieval_query_composer_v1"
        ),
        "hybrid_retrieval_plan": hybrid_plan,
        "hybrid_retrieval_planner_mode": str(
            retrieval.get("hybrid_retrieval_planner_mode", "shadow") or "shadow"
        ),
        "retrieval_query_source": str(composer.get("query_source", "") or ""),
        "composed_retrieval_query": str(composer.get("composed_query", "") or ""),
        "retrieval_need": str(composer.get("retrieval_need", "") or ""),
        "writer_can_ignore_rag": bool(composer.get("writer_can_ignore_rag", True)),
        "writer_kb_payload": writer_kb_payload,
        "writer_kb_payload_trace": writer_kb_payload_trace,
        "writer_kb_payload_future_graduation_notes": future_graduation_notes,
        "writer_kb_payload_enabled": bool(payload_resolution.get("effective_value", False)),
        "writer_kb_payload_failed": writer_kb_payload_failed,
        "writer_kb_payload_failure_reason": fallback_reason or writer_kb_payload_failure_reason,
        "retrieval_context": {
            "retrieval_action": str(
                hybrid_plan.get("retrieval_action", retrieval.get("retrieval_action", "trace_only"))
                or retrieval.get("retrieval_action", "trace_only")
            ),
            "composed_query": str(
                hybrid_plan.get("composed_query", retrieval.get("planned_composed_query", ""))
                or retrieval.get("planned_composed_query", "")
            ),
            "needed_chunk_types": [
                str(item)
                for item in list(hybrid_plan.get("needed_chunk_types", retrieval.get("needed_chunk_types", [])) or [])
                if str(item).strip()
            ],
            "mechanism_hints": [
                str(item)
                for item in list(hybrid_plan.get("mechanism_hints", retrieval.get("mechanism_hints", [])) or [])
                if str(item).strip()
            ],
            "depth_level_hint": int(hybrid_plan.get("depth_level_hint", 0) or 0),
            "writer_can_ignore_rag": bool(
                hybrid_plan.get("writer_can_ignore_rag", composer.get("writer_can_ignore_rag", True))
            ),
            "chunks": retrieval_context_chunks,
        },
    }


__all__ = ["WRITER_CONTEXT_PACKAGE_VERSION", "build_writer_context_package_v1"]
