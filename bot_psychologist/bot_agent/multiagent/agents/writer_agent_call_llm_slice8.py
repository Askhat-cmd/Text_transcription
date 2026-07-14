from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CallLLMSlice8ResponsePlannerAndDialoguePragmaticsInputs:
    response_planner_version: str
    response_planner_enabled: str
    response_planner_next_move: str
    response_planner_answer_shape: str
    response_planner_response_depth: str
    response_planner_target_micro_shift: str
    response_planner_should_answer_directly: str
    response_planner_question_policy: str
    response_planner_practice_policy: str
    response_planner_revoicing_policy: str
    response_planner_continuity_policy: str
    response_planner_safety_priority: str
    response_planner_must_include: str
    response_planner_must_avoid: str
    response_planner_confidence: float
    response_planner_rationale: str
    dialogue_profile: str
    dialogue_expansion_requested: str
    dialogue_repair_and_expand_requested: str
    dialogue_active_concept: str
    dialogue_pragmatics_version: str
    dialogue_pragmatics_short_utterance: str
    dialogue_pragmatics_short_type: str
    dialogue_pragmatics_is_contextual_followup: str
    dialogue_pragmatics_offer_type: str
    dialogue_pragmatics_inherited_intent: str
    dialogue_pragmatics_should_answer_directly: str
    dialogue_pragmatics_should_not_ask_confirmation_again: str
    dialogue_pragmatics_repair_user_dissatisfaction: str
    dialogue_pragmatics_reason: str


def _extract_call_llm_slice8_response_planner_and_dialogue_pragmatics(
    ctx: dict[str, Any],
) -> CallLLMSlice8ResponsePlannerAndDialoguePragmaticsInputs:
    return CallLLMSlice8ResponsePlannerAndDialoguePragmaticsInputs(
        response_planner_version=str(
            ctx.get("response_planner_version", "response_planner_v1")
        ),
        response_planner_enabled=str(
            bool(ctx.get("response_planner_enabled", False))
        ).lower(),
        response_planner_next_move=str(
            ctx.get("response_planner_next_move", "continue_active_line")
            or "continue_active_line"
        ),
        response_planner_answer_shape=str(
            ctx.get("response_planner_answer_shape", "compact_direct")
            or "compact_direct"
        ),
        response_planner_response_depth=str(
            ctx.get("response_planner_response_depth", "short") or "short"
        ),
        response_planner_target_micro_shift=str(
            ctx.get("response_planner_target_micro_shift", "") or ""
        ),
        response_planner_should_answer_directly=str(
            bool(ctx.get("response_planner_should_answer_directly", False))
        ).lower(),
        response_planner_question_policy=str(
            ctx.get("response_planner_question_policy", "none") or "none"
        ),
        response_planner_practice_policy=str(
            ctx.get("response_planner_practice_policy", "forbidden") or "forbidden"
        ),
        response_planner_revoicing_policy=str(
            ctx.get("response_planner_revoicing_policy", "suppressed") or "suppressed"
        ),
        response_planner_continuity_policy=str(
            ctx.get("response_planner_continuity_policy", "continue_active_line")
            or "continue_active_line"
        ),
        response_planner_safety_priority=str(
            bool(ctx.get("response_planner_safety_priority", False))
        ).lower(),
        response_planner_must_include=", ".join(
            [
                str(item)
                for item in list(ctx.get("response_planner_must_include", []) or [])
                if str(item).strip()
            ]
        )
        or "none",
        response_planner_must_avoid=", ".join(
            [
                str(item)
                for item in list(ctx.get("response_planner_must_avoid", []) or [])
                if str(item).strip()
            ]
        )
        or "none",
        response_planner_confidence=float(
            ctx.get("response_planner_confidence", 0.0) or 0.0
        ),
        response_planner_rationale=str(
            ctx.get("response_planner_rationale", "") or ""
        ),
        dialogue_profile=str(ctx.get("dialogue_profile", "safe_guided") or "safe_guided"),
        dialogue_expansion_requested=str(
            bool(ctx.get("dialogue_expansion_requested", False))
        ).lower(),
        dialogue_repair_and_expand_requested=str(
            bool(ctx.get("dialogue_repair_and_expand_requested", False))
        ).lower(),
        dialogue_active_concept=str(ctx.get("dialogue_active_concept", "") or ""),
        dialogue_pragmatics_version=str(
            ctx.get("dialogue_pragmatics_version", "dialogue_pragmatics_v1")
        ),
        dialogue_pragmatics_short_utterance=str(
            bool(ctx.get("dialogue_pragmatics_short_utterance", False))
        ).lower(),
        dialogue_pragmatics_short_type=str(
            ctx.get("dialogue_pragmatics_short_type", "not_short") or "not_short"
        ),
        dialogue_pragmatics_is_contextual_followup=str(
            bool(ctx.get("dialogue_pragmatics_is_contextual_followup", False))
        ).lower(),
        dialogue_pragmatics_offer_type=str(
            ctx.get("dialogue_pragmatics_offer_type", "unknown") or "unknown"
        ),
        dialogue_pragmatics_inherited_intent=str(
            ctx.get("dialogue_pragmatics_inherited_intent", "continue_previous_offer")
            or "continue_previous_offer"
        ),
        dialogue_pragmatics_should_answer_directly=str(
            bool(ctx.get("dialogue_pragmatics_should_answer_directly", False))
        ).lower(),
        dialogue_pragmatics_should_not_ask_confirmation_again=str(
            bool(ctx.get("dialogue_pragmatics_should_not_ask_confirmation_again", False))
        ).lower(),
        dialogue_pragmatics_repair_user_dissatisfaction=str(
            bool(ctx.get("dialogue_pragmatics_repair_user_dissatisfaction", False))
        ).lower(),
        dialogue_pragmatics_reason=str(
            ctx.get("dialogue_pragmatics_reason", "none") or "none"
        ),
    )
