from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .writer_agent_fallback_helpers import _format_diagnostic_summary


@dataclass(frozen=True)
class CallLLMSlice4PolicyAndDialogueStateInputs:
    unified_dialogue_policy_version: str
    unified_active_profile_alias: str
    profile_preset: str
    unified_effective_writer_autonomy: str
    unified_effective_safety_floor: str
    unified_legacy_blocks_visible_to_writer: str
    unified_legacy_blocks_source_signals_only: str
    unified_hard_boundaries_csv: str
    unified_soft_guidance_csv: str
    dialogue_act: str
    dialogue_act_confidence: float
    dialogue_act_evidence: str
    last_assistant_offer_open: str
    last_assistant_offer_type: str
    last_assistant_offer_summary: str
    unanswered_question_answer_required: str
    unanswered_question_status: str
    unanswered_question_summary: str
    dialogue_style_tone: str
    dialogue_style_length_preference: str
    dialogue_style_complexity_preference: str
    dialogue_style_avoid_csv: str
    answer_obligation: str
    answer_obligation_shape: str
    answer_obligation_depth: str
    answer_obligation_question_policy: str
    answer_obligation_source: str
    diagnostic_card_summary: str
    diagnostic_card_avoid: str
    diagnostic_card_risk_flags: str
    writer_move_instruction_summary: Any
    writer_move_must_do: str
    writer_move_must_not_do: str
    context_budget_chars: int
    context_truncated: str
    preserved_recent_turns_count: int
    older_context_omitted_chars: int
    user_profile_patterns: str
    user_profile_values: str


def _extract_call_llm_slice4_policy_and_dialogue_state(
    ctx: dict[str, Any],
    context_meta: dict[str, Any],
    dialogue_profile: str,
) -> CallLLMSlice4PolicyAndDialogueStateInputs:
    return CallLLMSlice4PolicyAndDialogueStateInputs(
        unified_dialogue_policy_version=str(
            ctx.get("unified_dialogue_policy_version", "unified_dialogue_policy_v2")
        ),
        unified_active_profile_alias=str(
            ctx.get("unified_active_profile_alias", dialogue_profile)
        ),
        profile_preset=str(ctx.get("profile_preset", "safe_guided")),
        unified_effective_writer_autonomy=str(
            ctx.get("unified_effective_writer_autonomy", "medium")
        ),
        unified_effective_safety_floor=str(
            ctx.get("unified_effective_safety_floor", "minimal_baseline")
        ),
        unified_legacy_blocks_visible_to_writer=str(
            bool(ctx.get("unified_legacy_blocks_visible_to_writer", False))
        ).lower(),
        unified_legacy_blocks_source_signals_only=str(
            bool(ctx.get("unified_legacy_blocks_source_signals_only", True))
        ).lower(),
        unified_hard_boundaries_csv=str(
            ctx.get("unified_hard_boundaries_csv", "none") or "none"
        ),
        unified_soft_guidance_csv=str(
            ctx.get("unified_soft_guidance_csv", "none") or "none"
        ),
        dialogue_act=str(ctx.get("dialogue_act", "unknown") or "unknown"),
        dialogue_act_confidence=float(ctx.get("dialogue_act_confidence", 0.0) or 0.0),
        dialogue_act_evidence=str(ctx.get("dialogue_act_evidence", "none") or "none"),
        last_assistant_offer_open=str(
            bool(ctx.get("last_assistant_offer_open", False))
        ).lower(),
        last_assistant_offer_type=str(
            ctx.get("last_assistant_offer_type", "none") or "none"
        ),
        last_assistant_offer_summary=str(
            ctx.get("last_assistant_offer_summary", "none") or "none"
        ),
        unanswered_question_answer_required=str(
            bool(ctx.get("unanswered_question_answer_required", False))
        ).lower(),
        unanswered_question_status=str(
            ctx.get("unanswered_question_status", "answered") or "answered"
        ),
        unanswered_question_summary=str(
            ctx.get("unanswered_question_summary", "none") or "none"
        ),
        dialogue_style_tone=str(ctx.get("dialogue_style_tone", "neutral") or "neutral"),
        dialogue_style_length_preference=str(
            ctx.get("dialogue_style_length_preference", "adaptive") or "adaptive"
        ),
        dialogue_style_complexity_preference=str(
            ctx.get("dialogue_style_complexity_preference", "normal") or "normal"
        ),
        dialogue_style_avoid_csv=str(
            ctx.get("dialogue_style_avoid_csv", "none") or "none"
        ),
        answer_obligation=str(
            ctx.get("answer_obligation", "continue_thread") or "continue_thread"
        ),
        answer_obligation_shape=str(
            ctx.get("answer_obligation_shape", "structured_explanation")
            or "structured_explanation"
        ),
        answer_obligation_depth=str(ctx.get("answer_obligation_depth", "medium") or "medium"),
        answer_obligation_question_policy=str(
            ctx.get("answer_obligation_question_policy", "optional_none")
            or "optional_none"
        ),
        answer_obligation_source=str(ctx.get("answer_obligation_source", "none") or "none"),
        diagnostic_card_summary=_format_diagnostic_summary(ctx.get("diagnostic_card_summary")),
        diagnostic_card_avoid=", ".join(ctx.get("diagnostic_card_avoid_list", []) or []) or "нет",
        diagnostic_card_risk_flags=", ".join(ctx.get("diagnostic_card_risk_flags", []) or [])
        or "нет",
        writer_move_instruction_summary=ctx.get("writer_move_instruction_summary") or "нет",
        writer_move_must_do=", ".join(ctx.get("writer_move_must_do", []) or []) or "нет",
        writer_move_must_not_do=", ".join(ctx.get("writer_move_must_not_do", []) or [])
        or "нет",
        context_budget_chars=int(context_meta.get("context_budget_chars", 0) or 0),
        context_truncated=str(bool(context_meta.get("context_truncated", False))).lower(),
        preserved_recent_turns_count=int(
            context_meta.get("preserved_recent_turns_count", 0) or 0
        ),
        older_context_omitted_chars=int(
            context_meta.get("older_context_omitted_chars", 0) or 0
        ),
        user_profile_patterns=", ".join(ctx["user_profile_patterns"]) or "нет",
        user_profile_values=", ".join(ctx["user_profile_values"]) or "нет",
    )
