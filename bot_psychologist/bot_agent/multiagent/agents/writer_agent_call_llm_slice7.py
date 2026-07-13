from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CallLLMSlice7FreshChatAndActiveLineInputs:
    fresh_chat_context_policy_version: str
    fresh_chat_is_new_chat: str
    fresh_chat_turn_index: int
    fresh_chat_is_greeting_or_contact: str
    fresh_chat_cross_session_memory_allowed: str
    fresh_chat_cross_session_memory_reason: str
    fresh_chat_active_context_source: str
    writer_context_package_version: str
    writer_context_recent_turns_count: int
    writer_context_profile_present: str
    writer_context_rag_candidates_count: int
    writer_context_rag_for_writer_count: int
    practice_rewrite_applied: str
    active_line_version: str
    active_line_text: str
    active_line_user_intent: str
    active_line_continuity_mode: str
    active_line_next_meaningful_move: str
    active_line_should_continue_line: str
    active_line_should_ask_question: str
    active_line_should_offer_practice: str
    active_line_revoicing_allowed: str
    active_line_revoicing_style: str
    active_line_repair_mode: str
    active_line_practice_suppression_active: str


def _extract_call_llm_slice7_fresh_chat_and_active_line(
    ctx: dict[str, Any],
) -> CallLLMSlice7FreshChatAndActiveLineInputs:
    return CallLLMSlice7FreshChatAndActiveLineInputs(
        fresh_chat_context_policy_version=str(
            ctx.get("fresh_chat_context_policy_version", "fresh_chat_context_policy_v1")
            or "fresh_chat_context_policy_v1"
        ),
        fresh_chat_is_new_chat=str(bool(ctx.get("fresh_chat_is_new_chat", False))).lower(),
        fresh_chat_turn_index=int(ctx.get("fresh_chat_turn_index", 1) or 1),
        fresh_chat_is_greeting_or_contact=str(
            bool(ctx.get("fresh_chat_is_greeting_or_contact", False))
        ).lower(),
        fresh_chat_cross_session_memory_allowed=str(
            bool(ctx.get("fresh_chat_cross_session_memory_allowed", True))
        ).lower(),
        fresh_chat_cross_session_memory_reason=str(
            ctx.get("fresh_chat_cross_session_memory_reason", "") or ""
        ),
        fresh_chat_active_context_source=str(
            ctx.get("fresh_chat_active_context_source", "current_chat_only")
            or "current_chat_only"
        ),
        writer_context_package_version=str(
            ctx.get("writer_context_package_version", "writer_context_package_v1")
            or "writer_context_package_v1"
        ),
        writer_context_recent_turns_count=int(
            ctx.get("writer_context_recent_turns_count", 0) or 0
        ),
        writer_context_profile_present=str(
            bool(ctx.get("writer_context_profile_present", False))
        ).lower(),
        writer_context_rag_candidates_count=int(
            ctx.get("writer_context_rag_candidates_count", 0) or 0
        ),
        writer_context_rag_for_writer_count=int(
            ctx.get("writer_context_rag_for_writer_count", 0) or 0
        ),
        practice_rewrite_applied=str(bool(ctx.get("practice_rewrite_applied", False))).lower(),
        active_line_version=str(ctx.get("active_line_version", "active_line_v1")),
        active_line_text=str(ctx.get("active_line_text", "") or ""),
        active_line_user_intent=str(ctx.get("active_line_user_intent", "unknown") or "unknown"),
        active_line_continuity_mode=str(
            ctx.get("active_line_continuity_mode", "continue_existing_line")
        ),
        active_line_next_meaningful_move=str(
            ctx.get("active_line_next_meaningful_move", "") or ""
        ),
        active_line_should_continue_line=str(
            bool(ctx.get("active_line_should_continue_line", True))
        ).lower(),
        active_line_should_ask_question=str(
            bool(ctx.get("active_line_should_ask_question", False))
        ).lower(),
        active_line_should_offer_practice=str(
            bool(ctx.get("active_line_should_offer_practice", False))
        ).lower(),
        active_line_revoicing_allowed=str(
            bool(ctx.get("active_line_revoicing_allowed", False))
        ).lower(),
        active_line_revoicing_style=str(
            ctx.get("active_line_revoicing_style", "suppressed") or "suppressed"
        ),
        active_line_repair_mode=str(ctx.get("active_line_repair_mode", "") or ""),
        active_line_practice_suppression_active=str(
            bool(ctx.get("active_line_practice_suppression_active", False))
        ).lower(),
    )
