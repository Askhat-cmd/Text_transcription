"""Writer-visible context packaging with strict RAG gating."""

from __future__ import annotations

import re
from typing import Any

from ..feature_flags import feature_flags
from ..knowledge.semantic_card_payload_adapter import (
    build_semantic_cards_pilot_selection,
    get_semantic_cards_pilot_config,
)
from .creator_live_behavior_guard import REQUEST_TYPE_PRACTICE, detect_request_type_v1
from .contracts.context_package import ContextAssemblyPackage
from .contracts.memory_bundle import MemoryBundle
from .writer_kb_payload import (
    build_future_graduation_notes,
    build_writer_kb_payload,
    build_writer_kb_payload_trace,
    get_writer_kb_payload_config,
)


WRITER_CONTEXT_PACKAGE_VERSION = "writer_context_package_v1"
WRITER_GROUNDING_VISIBILITY_VERSION = "writer_grounding_visibility_v1"
RUNTIME_TRUTH_TRACE_VERSION = "runtime_truth_trace_v1"
NARROW_PRACTICE_GROUNDING_TYPES = frozenset({"practice", "dialogue_move", "anti_pattern", "safety"})

_KNOWLEDGE_MARKERS = (
    "что такое",
    "что значит",
    "объясни",
    "объясните",
    "расскажи",
    "расскажи",
    "как работает",
    "в чем разница",
    "в чём разница",
    "механизм",
    "концепт",
    "термин",
)
_DIRECT_SOURCE_MARKERS = (
    "в базе",
    "из базы",
    "из внутренней базы",
    "во внутренней базе",
    "внутренней базе",
    "что в базе говорится",
    "что во внутренней базе говорится",
    "что база говорит",
    "источник",
    "источники",
)
_EMOTIONAL_SUPPORT_MARKERS = (
    "мне тяжело",
    "мне плохо",
    "мне больно",
    "я запутал",
    "я запуталась",
    "я злюсь",
    "меня бесит",
    "я устал",
    "я устала",
    "поддержи",
    "побудь со мной",
    "просто поддержи",
)
_REPAIR_MARKERS = (
    "ты слишком сложно",
    "скажи проще",
    "это не ответ",
    "ты не ответил",
    "объясни нормально",
    "просто объясни",
)
_GREETING_MARKERS = ("привет", "здравствуйте", "добрый день", "добрый вечер")
_CLOSE_MARKERS = ("спасибо", "благодарю", "пока", "до свидания")
_SAFETY_GROUNDING_MARKERS = (
    "сжало груд",
    "сердц",
    "паник",
    "не могу дыш",
    "задыха",
    "суиц",
    "убить себя",
)
_WORD_RE = re.compile(r"[a-zа-я0-9_]{3,}", re.IGNORECASE)


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


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower()).replace("ё", "е")


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _normalize(text)
    return any(marker in lowered for marker in markers)


def _tokens(text: str) -> list[str]:
    return [part.lower() for part in _WORD_RE.findall(_normalize(text))]


def _looks_like_greeting_or_close(user_message: str) -> bool:
    lowered = _normalize(user_message).strip(" !?.")
    token_count = len(_tokens(lowered))
    return (
        any(lowered.startswith(marker) for marker in _GREETING_MARKERS)
        or (any(marker in lowered for marker in _CLOSE_MARKERS) and token_count <= 8)
    )


def _looks_like_repair_turn(user_message: str) -> bool:
    return _contains_any(user_message, _REPAIR_MARKERS)


def _looks_like_emotional_support_turn(user_message: str) -> bool:
    return _contains_any(user_message, _EMOTIONAL_SUPPORT_MARKERS)


def _looks_like_direct_source_request(user_message: str) -> bool:
    return _contains_any(user_message, _DIRECT_SOURCE_MARKERS)


def _looks_like_explicit_knowledge_request(user_message: str) -> bool:
    return _contains_any(user_message, _KNOWLEDGE_MARKERS)


def _looks_like_safety_grounding_need(user_message: str) -> bool:
    return _contains_any(user_message, _SAFETY_GROUNDING_MARKERS)


def _normalize_chunk_type(value: Any) -> str:
    return str(value or "").strip().lower()


def _extract_chunk_type(item: dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return ""
    chunking_quality = (
        dict(item.get("chunking_quality", {}))
        if isinstance(item.get("chunking_quality"), dict)
        else {}
    )
    governance = (
        dict(item.get("governance", {}))
        if isinstance(item.get("governance"), dict)
        else {}
    )
    for candidate in (
        item.get("chunk_type"),
        chunking_quality.get("chunk_type"),
        governance.get("chunk_type"),
    ):
        chunk_type = _normalize_chunk_type(candidate)
        if chunk_type:
            return chunk_type
    return ""


def _collect_candidate_chunk_types(items: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in list(items or []):
        chunk_type = _extract_chunk_type(item)
        if chunk_type and chunk_type not in seen:
            seen.add(chunk_type)
            ordered.append(chunk_type)
    return ordered


def _filter_items_by_chunk_types(
    items: list[dict[str, Any]],
    allowed_chunk_types: set[str],
) -> list[dict[str, Any]]:
    if not allowed_chunk_types:
        return [
            dict(item)
            for item in list(items or [])
            if isinstance(item, dict)
        ]
    return [
        dict(item)
        for item in list(items or [])
        if isinstance(item, dict) and _extract_chunk_type(item) in allowed_chunk_types
    ]


def build_writer_grounding_visibility_v1(
    *,
    user_message: str,
    retrieval_decision: dict[str, Any] | None,
    latest_turn_constraints: dict[str, Any] | None,
    has_grounding_candidates: bool,
    candidate_chunk_types: list[str] | None = None,
) -> dict[str, Any]:
    retrieval = dict(retrieval_decision or {})
    constraints = dict(latest_turn_constraints or {})
    no_internal_db = bool(constraints.get("no_internal_db", False))
    retrieval_action = str(retrieval.get("retrieval_action", "trace_only") or "trace_only")
    retrieval_need = str(retrieval.get("retrieval_need", "") or "")
    request_type = detect_request_type_v1(user_message)
    explicit_practice_request = request_type == REQUEST_TYPE_PRACTICE
    direct_source_request = _looks_like_direct_source_request(user_message)
    explicit_knowledge_request = _looks_like_explicit_knowledge_request(user_message)
    safety_grounding_allowed = _looks_like_safety_grounding_need(user_message)
    normalized_candidate_chunk_types = [
        chunk_type
        for chunk_type in (
            _normalize_chunk_type(item)
            for item in list(candidate_chunk_types or [])
        )
        if chunk_type
    ]
    narrow_practice_chunk_types = sorted(
        {
            chunk_type
            for chunk_type in normalized_candidate_chunk_types
            if chunk_type in NARROW_PRACTICE_GROUNDING_TYPES
        }
    )
    direct_kb_question = bool(
        direct_source_request
        or (
            retrieval_action in {"query_kb", "query_kb_and_memory", "knowledge_grounding", "contextual_grounding", "include_relevant_rag"}
            and retrieval_need in {"knowledge_context", "practice_context"}
        )
        or (
            explicit_knowledge_request
            and (
                retrieval_need in {"knowledge_context", "practice_context"}
                or has_grounding_candidates
            )
        )
    )
    narrow_practice_grounding_available = bool(
        explicit_practice_request and narrow_practice_chunk_types
    )

    if no_internal_db:
        kb_visible_to_writer = False
        semantic_cards_visible_to_writer = False
        reason = "latest_turn_no_internal_db"
    elif direct_source_request:
        kb_visible_to_writer = True
        semantic_cards_visible_to_writer = True
        reason = "direct_source_request"
    elif safety_grounding_allowed:
        kb_visible_to_writer = True
        semantic_cards_visible_to_writer = True
        reason = "safety_grounding_allowed"
    elif _looks_like_greeting_or_close(user_message):
        kb_visible_to_writer = False
        semantic_cards_visible_to_writer = False
        reason = "greeting_or_contact"
    elif _looks_like_repair_turn(user_message):
        kb_visible_to_writer = False
        semantic_cards_visible_to_writer = False
        reason = "repair_turn"
    elif bool(constraints.get("simplify", False)):
        kb_visible_to_writer = False
        semantic_cards_visible_to_writer = False
        reason = "simplify_turn_trace_only"
    elif bool(constraints.get("no_practice", False)) or bool(constraints.get("no_breathing_only", False)):
        kb_visible_to_writer = False
        semantic_cards_visible_to_writer = False
        reason = "support_or_pushback_turn_trace_only"
    elif narrow_practice_grounding_available:
        kb_visible_to_writer = True
        semantic_cards_visible_to_writer = True
        reason = "explicit_practice_request_narrow_grounding"
    elif direct_kb_question:
        kb_visible_to_writer = True
        semantic_cards_visible_to_writer = True
        reason = "direct_knowledge_question"
    elif _looks_like_emotional_support_turn(user_message):
        kb_visible_to_writer = False
        semantic_cards_visible_to_writer = False
        reason = "non_kb_emotional_support_turn"
    elif retrieval_action in {"suppress_rag", "use_current_context_only", "trace_only"}:
        kb_visible_to_writer = False
        semantic_cards_visible_to_writer = False
        reason = str(retrieval.get("rag_suppressed_reason", "") or "grounding_not_needed_for_current_turn")
    else:
        kb_visible_to_writer = False
        semantic_cards_visible_to_writer = False
        reason = "grounding_not_needed_for_current_turn"

    return {
        "version": WRITER_GROUNDING_VISIBILITY_VERSION,
        "kb_visible_to_writer": kb_visible_to_writer,
        "semantic_cards_visible_to_writer": semantic_cards_visible_to_writer,
        "reason": reason,
        "direct_kb_question": direct_kb_question,
        "direct_source_request": direct_source_request,
        "explicit_knowledge_request": explicit_knowledge_request,
        "explicit_practice_request": explicit_practice_request,
        "candidate_chunk_types": normalized_candidate_chunk_types,
        "allowed_grounding_types": narrow_practice_chunk_types if narrow_practice_grounding_available else [],
        "narrow_practice_grounding_available": narrow_practice_grounding_available,
        "safety_grounding_allowed": safety_grounding_allowed,
        "no_internal_db": no_internal_db,
        "trace_only_grounding_available": bool(has_grounding_candidates),
        "writer_may_ignore_grounding": True,
        "retrieval_action": retrieval_action,
        "retrieval_need": retrieval_need,
    }


def build_writer_grounding_authority_note_v1() -> str:
    return (
        "Safety and the explicit latest user request are mandatory. Conversation context supports continuity. "
        "KB, semantic cards, retrieval notes, and diagnostic hints are optional grounding: use them only if they help "
        "the current answer, never let them change the user's request, and do not sound like internal recitation."
    )


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _candidate_id(item: dict[str, Any]) -> str:
    for key in ("chunk_id", "item_id", "semantic_card_id", "source_id", "source"):
        value = str(item.get(key, "") or "").strip()
        if value:
            return value
    return "unknown"


def _source_doc(item: dict[str, Any]) -> str:
    for key in ("source_doc", "source_document", "doc_title", "title", "source"):
        value = str(item.get(key, "") or "").strip()
        if value:
            return value
    return "unknown"


def _candidate_origin(item: dict[str, Any], default: str) -> str:
    return str(
        item.get("origin")
        or item.get("payload_item_origin")
        or ("semantic_card" if str(item.get("semantic_card_id", "") or "").strip() else default)
    )


def _filtered_reason(
    *,
    item: dict[str, Any],
    writer_grounding_visibility: dict[str, Any],
    no_internal_db: bool,
    sent_to_writer: bool,
    narrow_practice_grounding_active: bool,
    actual_writer_payload_ids: set[str],
) -> str:
    if sent_to_writer:
        return ""
    if no_internal_db:
        return "latest_turn_no_internal_db"
    chunk_type = _extract_chunk_type(item)
    allowed_types = {
        _normalize_chunk_type(value)
        for value in list(writer_grounding_visibility.get("allowed_grounding_types", []) or [])
        if _normalize_chunk_type(value)
    }
    if narrow_practice_grounding_active and chunk_type and chunk_type not in allowed_types:
        return "filtered_by_narrow_practice_grounding"
    if _candidate_id(item) in actual_writer_payload_ids:
        return ""
    return str(writer_grounding_visibility.get("reason", "") or "not_selected_for_writer")


def _build_runtime_truth_trace_v1(
    *,
    rag_candidates_for_trace: list[dict[str, Any]],
    base_rag_for_writer: list[dict[str, Any]],
    semantic_card_candidate_payload_items: list[dict[str, Any]],
    writer_kb_payload: dict[str, Any],
    writer_kb_payload_trace: dict[str, Any],
    writer_grounding_visibility: dict[str, Any],
    retrieval: dict[str, Any],
    no_internal_db: bool,
    narrow_practice_grounding_active: bool,
    fallback_reason: str,
) -> dict[str, Any]:
    payload_chunks = [
        dict(item)
        for item in list(writer_kb_payload.get("chunks", []) or [])
        if isinstance(item, dict)
    ]
    writer_visible_payload_items: list[dict[str, Any]] = []
    actual_writer_payload_ids: set[str] = set()
    for item in payload_chunks:
        item_id = _candidate_id(item)
        actual_writer_payload_ids.add(item_id)
        writer_visible_payload_items.append(
            {
                "item_id": item_id,
                "origin": _candidate_origin(item, "retrieval"),
                "chunk_type": _extract_chunk_type(item),
                "source_doc": _source_doc(item),
                "allowed_use": _string_list(item.get("allowed_use")),
                "quote_policy": str(item.get("quote_policy", "") or "paraphrase_only"),
                "sent_to_writer": True,
                "writer_can_ignore": bool(item.get("writer_can_ignore", True)),
                "applied_as_authority": bool(item.get("applied_as_authority", False)),
                "inclusion_reason": str(item.get("inclusion_reason", "") or "selected_for_writer_payload"),
            }
        )

    candidate_pool: list[dict[str, Any]] = []
    seen_candidates: set[str] = set()
    for origin, items in (
        ("retrieval_candidate", base_rag_for_writer),
        ("semantic_card_candidate", semantic_card_candidate_payload_items),
        ("memory_semantic_hit", rag_candidates_for_trace),
    ):
        for raw in list(items or []):
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            item_id = _candidate_id(item)
            dedupe_key = f"{origin}:{item_id}"
            if dedupe_key in seen_candidates:
                continue
            seen_candidates.add(dedupe_key)
            item["_runtime_origin"] = origin
            candidate_pool.append(item)

    filtered_out: list[dict[str, Any]] = []
    trace_only: list[dict[str, Any]] = []
    for item in candidate_pool:
        item_id = _candidate_id(item)
        sent_to_writer = item_id in actual_writer_payload_ids
        reason = _filtered_reason(
            item=item,
            writer_grounding_visibility=writer_grounding_visibility,
            no_internal_db=no_internal_db,
            sent_to_writer=sent_to_writer,
            narrow_practice_grounding_active=narrow_practice_grounding_active,
            actual_writer_payload_ids=actual_writer_payload_ids,
        )
        if not sent_to_writer:
            entry = {
                "item_id": item_id,
                "origin": _candidate_origin(item, str(item.get("_runtime_origin", "trace"))),
                "chunk_type": _extract_chunk_type(item),
                "source_doc": _source_doc(item),
                "sent_to_writer": False,
                "filter_reason": reason,
            }
            filtered_out.append(entry)
            trace_only.append(entry)

    writer_visible_payload_types = [
        str(item.get("chunk_type", "") or "")
        for item in writer_visible_payload_items
        if str(item.get("chunk_type", "") or "").strip()
    ]
    grounding_reason = str(writer_grounding_visibility.get("reason", "") or "")
    retrieval_query_build_trace = (
        dict(retrieval.get("retrieval_query_build_trace", {}))
        if isinstance(retrieval.get("retrieval_query_build_trace"), dict)
        else {}
    )
    retrieval_query_source = str(
        retrieval.get("retrieval_query_source")
        or retrieval_query_build_trace.get("primary_path", "")
        or "current_turn_focus_v1"
    )
    payload_decision_reason = (
        str(fallback_reason or "")
        or str(writer_kb_payload_trace.get("status", "") or "")
        or grounding_reason
    )
    return {
        "trace_version": RUNTIME_TRUTH_TRACE_VERSION,
        "retrieved_candidates_count": len(candidate_pool),
        "trace_only_candidates_count": len(trace_only),
        "filtered_out_for_writer_count": len(filtered_out),
        "writer_visible_payload_count": len(writer_visible_payload_items),
        "actual_writer_payload_count": len(writer_visible_payload_items),
        "writer_visible_payload_ids": [
            str(item.get("item_id", "") or "")
            for item in writer_visible_payload_items
            if str(item.get("item_id", "") or "").strip()
        ],
        "writer_visible_payload_types": writer_visible_payload_types,
        "payload_decision_reason": payload_decision_reason,
        "grounding_visibility_reason": grounding_reason,
        "writer_can_ignore_grounding": bool(writer_grounding_visibility.get("writer_may_ignore_grounding", True)),
        "broad_kb_visible": bool(
            writer_grounding_visibility.get("kb_visible_to_writer", False)
            and grounding_reason != "explicit_practice_request_narrow_grounding"
        ),
        "narrow_grounding_visible": bool(grounding_reason == "explicit_practice_request_narrow_grounding"),
        "writer_visible_payload_items": writer_visible_payload_items,
        "filtered_out_for_writer": filtered_out,
        "trace_only_grounding": trace_only,
        "retrieval_query_source": retrieval_query_source,
        "legacy_fallback_scope": str(writer_kb_payload_trace.get("fallback_scope", "none") or "none"),
        "writer_kb_payload_status": str(writer_kb_payload_trace.get("status", "") or ""),
        "writer_kb_payload_primary_path": str(writer_kb_payload_trace.get("primary_path", "") or ""),
    }


def build_writer_context_package_v1(
    *,
    user_message: str = "",
    memory_bundle: MemoryBundle,
    context_package: ContextAssemblyPackage | None,
    retrieval_decision: dict[str, Any] | None,
    fresh_chat_context_policy: dict[str, Any] | None,
    latest_turn_constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    retrieval = dict(retrieval_decision or {})
    constraints = dict(latest_turn_constraints or {})
    no_internal_db = bool(constraints.get("no_internal_db", False))
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
    if no_internal_db:
        base_rag_for_writer = []
    elif explicit_retrieval_gate:
        base_rag_for_writer = [
            dict(item)
            for item in list(retrieval.get("rag_included_for_writer", []) or [])
            if isinstance(item, dict)
        ]
    elif context_package is not None and list(context_package.knowledge_rag_hits or []):
        base_rag_for_writer = [dict(item) for item in list(context_package.knowledge_rag_hits or []) if isinstance(item, dict)]
    else:
        base_rag_for_writer = [dict(item) for item in list(memory_bundle.knowledge_rag_hits or []) if isinstance(item, dict)]

    semantic_cards_pilot = build_semantic_cards_pilot_selection(
        user_message=user_message,
        retrieval_decision=retrieval,
        config=get_semantic_cards_pilot_config(),
    )
    semantic_card_candidate_payload_items = [
        dict(item)
        for item in list(semantic_cards_pilot.get("payload_items", []) or [])
        if isinstance(item, dict)
    ]
    candidate_chunk_types = _collect_candidate_chunk_types(base_rag_for_writer)
    candidate_chunk_types.extend(
        chunk_type
        for chunk_type in _collect_candidate_chunk_types(semantic_card_candidate_payload_items)
        if chunk_type not in candidate_chunk_types
    )
    writer_grounding_visibility = build_writer_grounding_visibility_v1(
        user_message=user_message,
        retrieval_decision=retrieval,
        latest_turn_constraints=constraints,
        has_grounding_candidates=bool(base_rag_for_writer) or bool(semantic_card_candidate_payload_items),
        candidate_chunk_types=candidate_chunk_types,
    )
    allowed_grounding_types = {
        _normalize_chunk_type(item)
        for item in list(writer_grounding_visibility.get("allowed_grounding_types", []) or [])
        if _normalize_chunk_type(item)
    }
    narrow_practice_grounding_active = bool(
        writer_grounding_visibility.get("reason") == "explicit_practice_request_narrow_grounding"
        and allowed_grounding_types
    )
    rag_for_writer = (
        _filter_items_by_chunk_types(base_rag_for_writer, allowed_grounding_types)
        if narrow_practice_grounding_active
        else list(base_rag_for_writer)
        if bool(writer_grounding_visibility.get("kb_visible_to_writer", False))
        else []
    )

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
                    else (
                        "latest_turn_no_internal_db"
                        if no_internal_db
                        else str(
                            writer_grounding_visibility.get("reason", "")
                            or retrieval.get("rag_suppressed_reason", "")
                            or "not_selected_for_writer"
                        )
                    )
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
    if no_internal_db:
        semantic_cards_pilot = dict(semantic_cards_pilot)
        semantic_cards_pilot["status"] = "suppressed"
        semantic_cards_pilot["suppressed_reason"] = "latest_turn_no_internal_db"
        semantic_cards_pilot["writer_payload_enriched"] = False
        semantic_cards_pilot["selected_card_count"] = 0
        semantic_cards_pilot["selected_card_ids"] = []
        semantic_cards_pilot["payload_items"] = []
    elif not bool(writer_grounding_visibility.get("semantic_cards_visible_to_writer", False)):
        semantic_cards_pilot = dict(semantic_cards_pilot)
        semantic_cards_pilot["status"] = "trace_only"
        semantic_cards_pilot["suppressed_reason"] = str(
            writer_grounding_visibility.get("reason", "") or "grounding_hidden_for_current_turn"
        )
        semantic_cards_pilot["writer_payload_enriched"] = False
        semantic_cards_pilot["payload_items"] = []
    semantic_card_payload_items = (
        _filter_items_by_chunk_types(
            [
                dict(item)
                for item in list(semantic_cards_pilot.get("payload_items", []) or [])
                if isinstance(item, dict)
            ],
            allowed_grounding_types,
        )
        if narrow_practice_grounding_active
        else [
            dict(item)
            for item in list(semantic_cards_pilot.get("payload_items", []) or [])
            if isinstance(item, dict)
        ]
    )
    if narrow_practice_grounding_active:
        semantic_cards_pilot = dict(semantic_cards_pilot)
        semantic_cards_pilot["writer_payload_enriched"] = bool(semantic_card_payload_items)
        semantic_cards_pilot["payload_items"] = list(semantic_card_payload_items)
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
            semantic_hits=(
                []
                if (no_internal_db or not bool(writer_grounding_visibility.get("kb_visible_to_writer", False)))
                else (
                    [
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
                    ]
                )
            ),
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
    elif no_internal_db:
        fallback_reason = "latest_turn_no_internal_db"
    elif not bool(writer_grounding_visibility.get("kb_visible_to_writer", False)):
        fallback_reason = str(
            writer_grounding_visibility.get("reason", "") or "grounding_hidden_for_current_turn"
        )
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
    runtime_truth_trace = _build_runtime_truth_trace_v1(
        rag_candidates_for_trace=rag_candidates_for_trace,
        base_rag_for_writer=base_rag_for_writer,
        semantic_card_candidate_payload_items=semantic_card_candidate_payload_items,
        writer_kb_payload=writer_kb_payload,
        writer_kb_payload_trace=writer_kb_payload_trace,
        writer_grounding_visibility=writer_grounding_visibility,
        retrieval=retrieval,
        no_internal_db=no_internal_db,
        narrow_practice_grounding_active=narrow_practice_grounding_active,
        fallback_reason=fallback_reason,
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
        "runtime_truth_trace_v1": runtime_truth_trace,
        "writer_kb_payload_future_graduation_notes": future_graduation_notes,
        "writer_kb_payload_enabled": bool(payload_resolution.get("effective_value", False)),
        "writer_kb_payload_failed": writer_kb_payload_failed,
        "writer_kb_payload_failure_reason": fallback_reason or writer_kb_payload_failure_reason,
        "writer_grounding_visibility_v1": writer_grounding_visibility,
        "writer_grounding_authority_note": build_writer_grounding_authority_note_v1(),
        "latest_turn_constraints_v1": constraints,
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


__all__ = [
    "WRITER_CONTEXT_PACKAGE_VERSION",
    "WRITER_GROUNDING_VISIBILITY_VERSION",
    "RUNTIME_TRUTH_TRACE_VERSION",
    "build_writer_context_package_v1",
    "build_writer_grounding_authority_note_v1",
    "build_writer_grounding_visibility_v1",
]
