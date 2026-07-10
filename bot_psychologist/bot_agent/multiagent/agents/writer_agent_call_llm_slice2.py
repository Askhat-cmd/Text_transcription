from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..dialogue_policy import (
    DIALOGUE_PROFILE_MVP_FREE,
    detect_application_request,
    detect_direct_concrete_request,
    detect_examples_request,
    detect_expansion_request,
    detect_explicit_answer_need,
    detect_numbered_list_request,
    detect_practice_overview_request,
    detect_sarcasm_or_negative_feedback,
    detect_summary_request,
)


@dataclass(frozen=True)
class CallLLMSlice2Inputs:
    explicit_answer_need: bool
    sarcasm_or_negative_feedback: bool
    repair_user_dissatisfaction: bool
    overruled_constraints: list[str]
    mvp_override_block: str


def _extract_call_llm_slice2_request_detectors(
    *,
    dialogue_policy_payload: dict[str, Any],
    user_message: str,
    constraint_resolution: dict[str, Any],
    dialogue_profile: str,
) -> CallLLMSlice2Inputs:
    mvp_overrides_payload = (
        dict(dialogue_policy_payload.get("mvp_overrides", {}))
        if isinstance(dialogue_policy_payload.get("mvp_overrides"), dict)
        else {}
    )
    practice_overview_requested = bool(
        dialogue_policy_payload.get("practice_overview_requested", False)
    ) or detect_practice_overview_request(user_message)
    examples_requested = bool(
        dialogue_policy_payload.get("examples_requested", False)
    ) or detect_examples_request(user_message)
    numbered_list_requested = bool(
        dialogue_policy_payload.get("numbered_list_requested", False)
    ) or detect_numbered_list_request(user_message)
    expansion_requested = bool(
        dialogue_policy_payload.get("expansion_requested", False)
    ) or detect_expansion_request(user_message)
    explicit_answer_need = bool(
        dialogue_policy_payload.get("explicit_answer_need", False)
    ) or detect_explicit_answer_need(user_message)
    direct_concrete_request = bool(
        dialogue_policy_payload.get("direct_concrete_request", False)
    ) or detect_direct_concrete_request(user_message)
    summary_request = bool(
        dialogue_policy_payload.get("summary_request", False)
    ) or detect_summary_request(user_message)
    sarcasm_or_negative_feedback = bool(
        dialogue_policy_payload.get("sarcasm_or_negative_feedback", False)
    ) or detect_sarcasm_or_negative_feedback(user_message)
    application_request = bool(
        dialogue_policy_payload.get("application_request", False)
    ) or detect_application_request(user_message)
    repair_user_dissatisfaction = bool(
        dict(dialogue_policy_payload.get("mvp_overrides", {})).get(
            "repair_user_dissatisfaction",
            False,
        )
        or sarcasm_or_negative_feedback
    )
    overruled_constraints = [
        str(item)
        for item in list(constraint_resolution.get("overruled_constraints", []) or [])
        if str(item).strip()
    ]
    rich_user_request = (
        practice_overview_requested
        or examples_requested
        or numbered_list_requested
        or expansion_requested
        or explicit_answer_need
        or direct_concrete_request
        or summary_request
        or sarcasm_or_negative_feedback
        or application_request
        or bool(dialogue_policy_payload.get("repair_and_expand_requested", False))
    )
    mvp_override_block = "not_applicable_for_safe_guided_profile"
    if dialogue_profile == DIALOGUE_PROFILE_MVP_FREE:
        mvp_override_block = "\n".join(
            [
                "MVP FREE DIALOGUE OVERRIDES:",
                f"- explicit_user_request_wins={str(bool(mvp_overrides_payload.get('explicit_user_request_wins', True))).lower()}",
                f"- old_max_sentence_constraints_softened={str(bool(mvp_overrides_payload.get('old_max_sentence_constraints_softened', True))).lower()}",
                f"- planner_advisory={str(bool(mvp_overrides_payload.get('planner_advisory', True))).lower()}",
                f"- overview_questions_allow_lists={str(bool(mvp_overrides_payload.get('overview_questions_allow_lists', practice_overview_requested))).lower()}",
                f"- target_answer_depth={str(mvp_overrides_payload.get('target_answer_depth', dialogue_policy_payload.get('answer_depth', 'medium')) or 'medium')}",
                f"- rich_user_request_detected={str(bool(rich_user_request)).lower()}",
                f"- explicit_answer_need={str(bool(explicit_answer_need)).lower()}",
                f"- direct_concrete_request={str(bool(direct_concrete_request)).lower()}",
                f"- summary_request={str(bool(summary_request)).lower()}",
                f"- sarcasm_or_negative_feedback={str(bool(sarcasm_or_negative_feedback)).lower()}",
            ]
        )

    return CallLLMSlice2Inputs(
        explicit_answer_need=explicit_answer_need,
        sarcasm_or_negative_feedback=sarcasm_or_negative_feedback,
        repair_user_dissatisfaction=repair_user_dissatisfaction,
        overruled_constraints=overruled_constraints,
        mvp_override_block=mvp_override_block,
    )
