"""Formatting for prompt-constraint pilot section in Writer user prompt."""

from __future__ import annotations

from typing import Any

from .contracts.prompt_constraint_pilot_runtime_v1 import PromptConstraintPilotRuntimeDecision


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _join(values: list[str], default: str = "none") -> str:
    if not values:
        return default
    return "; ".join(values)


def format_prompt_constraint_section_v1(
    decision: PromptConstraintPilotRuntimeDecision | dict[str, Any],
) -> str:
    payload = decision.to_dict() if isinstance(decision, PromptConstraintPilotRuntimeDecision) else _safe_dict(decision)
    if str(payload.get("activation_mode", "disabled")) != "test_apply":
        return ""
    if not bool(payload.get("apply_to_writer_prompt", False)):
        return ""

    constraints = _safe_dict(payload.get("candidate_constraints"))
    must_do = _safe_list(constraints.get("must_do"))[:8]
    must_not_do = _safe_list(constraints.get("must_not_do"))[:12]

    kb_mode = str(constraints.get("kb_usage_mode", "none") or "none")
    if kb_mode not in {"none", "internal_lens_only", "practice_candidate_only"}:
        kb_mode = "none"

    return (
        "PILOT PROMPT CONSTRAINTS:\n"
        f"- depth_limit: {str(constraints.get('depth_limit', 'none') or 'none')}\n"
        f"- max_questions: {int(constraints.get('max_questions', 0) or 0)}\n"
        f"- max_concepts: {int(constraints.get('max_concepts', 1) or 1)}\n"
        f"- must_do: {_join(must_do)}\n"
        f"- must_not_do: {_join(must_not_do)}\n"
        f"- kb_usage_mode: {kb_mode}\n"
        f"- must_not_quote_source: {'true' if bool(constraints.get('must_not_quote_source', True)) else 'false'}"
    )
