from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..prompt_constraint_section import format_prompt_constraint_section_v1


@dataclass(frozen=True)
class CallLLMSlice10PromptConstraintAndDebugBookkeepingResult:
    user_prompt: str
    last_debug_patch: dict[str, Any]


def _apply_call_llm_slice10_prompt_constraint_and_debug_bookkeeping(
    ctx: dict[str, Any],
    *,
    user_prompt: str,
    prompt_constraint_decision: dict[str, Any] | None,
    context_meta: dict[str, Any],
    human_like_answer_policy: dict[str, Any],
    explicit_answer_need: bool,
    repair_user_dissatisfaction: bool,
    sarcasm_or_negative_feedback: bool,
    overruled_constraints: list[str],
) -> CallLLMSlice10PromptConstraintAndDebugBookkeepingResult:
    prompt_section = (
        format_prompt_constraint_section_v1(prompt_constraint_decision)
        if prompt_constraint_decision is not None
        else ""
    )
    activation_mode = (
        str(prompt_constraint_decision.get("activation_mode", "disabled"))
        if isinstance(prompt_constraint_decision, dict)
        else "disabled"
    )
    blocked_reasons = (
        list(prompt_constraint_decision.get("blocked_reasons", []))
        if isinstance(prompt_constraint_decision, dict)
        and isinstance(prompt_constraint_decision.get("blocked_reasons", []), list)
        else []
    )
    if prompt_section:
        user_prompt = f"{user_prompt}\n\n{prompt_section}"
    last_debug_patch: dict[str, Any] = {
        "user_prompt": user_prompt,
        "prompt_constraint_pilot_activation_mode": activation_mode,
        "prompt_constraint_pilot_applied": bool(prompt_section),
        "prompt_constraint_pilot_blocked_reasons": blocked_reasons,
        "prompt_constraint_pilot_prompt_section_chars": len(prompt_section),
        "context_budget_chars": int(context_meta.get("context_budget_chars", 0) or 0),
        "context_truncated": bool(context_meta.get("context_truncated", False)),
        "preserved_recent_turns_count": int(
            context_meta.get("preserved_recent_turns_count", 0) or 0
        ),
        "older_context_omitted_chars": int(
            context_meta.get("older_context_omitted_chars", 0) or 0
        ),
        "human_like_answer_policy_enabled": bool(
            human_like_answer_policy.get("enabled", False)
        ),
        "explicit_answer_need": bool(explicit_answer_need),
        "repair_user_dissatisfaction": bool(repair_user_dissatisfaction),
        "sarcasm_or_negative_feedback": bool(sarcasm_or_negative_feedback),
        "overruled_constraints": overruled_constraints,
        "dialogue_pragmatics_contextual_followup": bool(
            ctx.get("dialogue_pragmatics_is_contextual_followup", False)
        ),
        "dialogue_pragmatics_offer_type": str(
            ctx.get("dialogue_pragmatics_offer_type", "unknown") or "unknown"
        ),
        "retrieval_action": str(ctx.get("retrieval_action", "none") or "none"),
        "retrieval_rag_included_count": int(
            ctx.get("retrieval_rag_included_count", 0) or 0
        ),
    }
    return CallLLMSlice10PromptConstraintAndDebugBookkeepingResult(
        user_prompt=user_prompt,
        last_debug_patch=last_debug_patch,
    )
