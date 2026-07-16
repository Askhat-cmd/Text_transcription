from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..contracts.writer_contract import WriterContract
from ..dialogue_policy import (
    detect_application_request,
    detect_direct_concrete_request,
    detect_expansion_request,
    detect_explicit_answer_need,
    detect_repair_and_expand_request,
    detect_sarcasm_or_negative_feedback,
    detect_summary_request,
    normalize_dialogue_profile,
)
from .writer_agent_constants import _extract_literal_markdown_echo_request


@dataclass(frozen=True)
class EnforceSlice1PreludeResult:
    ctx: dict[str, Any]
    user_message: str
    lowered_user: str
    literal_markdown_echo: str
    dialogue_profile: str
    expansion_requested: bool
    repair_and_expand_requested: bool
    knowledge_answer: dict[str, Any]
    practice_gate: dict[str, Any]
    practice_allowed: bool
    should_answer_directly: bool
    is_greeting: bool
    concept: str
    active_line: dict[str, Any]
    active_line_intent: str
    active_line_repair_mode: str
    active_line_revoicing_allowed: bool
    active_line_should_offer_practice: bool
    active_line_practice_suppression: bool
    response_planner: dict[str, Any]
    planner_next_move: str
    planner_answer_shape: str
    planner_question_policy: str
    planner_practice_policy: str
    planner_safety_priority: bool
    dialogue_policy_payload: dict[str, Any]
    dialogue_pragmatics_payload: dict[str, Any]
    explicit_answer_need: bool
    direct_concrete_request: bool
    summary_request: bool
    sarcasm_or_negative_feedback: bool
    application_request: bool
    human_like_answer_policy: dict[str, Any]
    constraint_resolution: dict[str, Any]
    practice_overview_requested: bool
    pragmatics_contextual_followup: bool
    pragmatics_offer_type: str
    pragmatics_should_not_reconfirm: bool
    pragmatics_repair_dissatisfaction: bool
    lowered_text: str
    final_answer_directive: dict[str, Any]
    writer_contact_mode: str
    gate_feedback: dict[str, Any]
    gate_failed_checks: set[str]
    last_debug_patch: dict[str, Any]


def _extract_enforce_slice1_prelude(
    contract: WriterContract,
    *,
    text: str,
) -> EnforceSlice1PreludeResult:
    ctx = contract.to_prompt_context()
    user_message = str(ctx.get("user_message", "") or "")
    lowered_user = user_message.lower()
    literal_markdown_echo = _extract_literal_markdown_echo_request(user_message)
    dialogue_profile = normalize_dialogue_profile(ctx.get("dialogue_profile", "safe_guided"))
    expansion_requested = bool(ctx.get("dialogue_expansion_requested", False)) or detect_expansion_request(user_message)
    repair_and_expand_requested = bool(
        ctx.get("dialogue_repair_and_expand_requested", False)
    ) or detect_repair_and_expand_request(user_message)
    knowledge_answer = dict(ctx.get("knowledge_answer", {})) if isinstance(ctx.get("knowledge_answer"), dict) else {}
    practice_gate = dict(ctx.get("practice_gate", {})) if isinstance(ctx.get("practice_gate"), dict) else {}
    practice_allowed = bool(practice_gate.get("practice_allowed", True))
    should_answer_directly = bool(knowledge_answer.get("should_answer_directly", False))
    is_greeting = bool(practice_gate.get("is_greeting", False))
    concept = str(knowledge_answer.get("concept", "") or "").strip().lower()
    active_line = dict(ctx.get("active_line", {})) if isinstance(ctx.get("active_line"), dict) else {}
    active_line_intent = str(active_line.get("user_intent", "unknown") or "unknown")
    active_line_repair_mode = str(active_line.get("repair_mode", "") or "")
    active_line_revoicing_allowed = bool(active_line.get("revoicing_allowed", True))
    active_line_should_offer_practice = bool(active_line.get("should_offer_practice", practice_allowed))
    active_line_practice_suppression = bool(active_line.get("practice_suppression_active", False))
    response_planner = dict(ctx.get("response_planner", {})) if isinstance(ctx.get("response_planner"), dict) else {}
    planner_next_move = str(response_planner.get("next_move", "continue_active_line") or "continue_active_line")
    planner_answer_shape = str(response_planner.get("answer_shape", "compact_direct") or "compact_direct")
    planner_question_policy = str(response_planner.get("question_policy", "none") or "none")
    planner_practice_policy = str(response_planner.get("practice_policy", "forbidden") or "forbidden")
    planner_safety_priority = bool(response_planner.get("safety_priority", False))
    dialogue_policy_payload = dict(ctx.get("dialogue_policy", {})) if isinstance(ctx.get("dialogue_policy"), dict) else {}
    dialogue_pragmatics_payload = (
        dict(ctx.get("dialogue_pragmatics", {}))
        if isinstance(ctx.get("dialogue_pragmatics"), dict)
        else {}
    )
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
    human_like_answer_policy = (
        dict(dialogue_policy_payload.get("human_like_answer_policy", {}))
        if isinstance(dialogue_policy_payload.get("human_like_answer_policy"), dict)
        else {}
    )
    constraint_resolution = (
        dict(dialogue_policy_payload.get("constraint_resolution", {}))
        if isinstance(dialogue_policy_payload.get("constraint_resolution"), dict)
        else {}
    )
    practice_overview_requested = bool(
        dialogue_policy_payload.get("practice_overview_requested", False)
        or planner_next_move == "answer_practice_overview"
        or planner_answer_shape == "practice_catalog_explanation"
    )
    pragmatics_contextual_followup = bool(
        dialogue_pragmatics_payload.get("is_contextual_followup", False)
    )
    pragmatics_offer_type = str(
        dialogue_pragmatics_payload.get("previous_assistant_offer_type", "unknown") or "unknown"
    )
    pragmatics_should_not_reconfirm = bool(
        dialogue_pragmatics_payload.get("should_not_ask_confirmation_again", False)
    )
    pragmatics_repair_dissatisfaction = bool(
        dialogue_pragmatics_payload.get("repair_user_dissatisfaction", False)
    )
    lowered_text = text.lower()
    last_debug_patch: dict[str, Any] = {}
    last_debug_patch["compliance_planner_next_move"] = planner_next_move
    last_debug_patch["compliance_planner_answer_shape"] = planner_answer_shape
    last_debug_patch["compliance_planner_question_policy"] = planner_question_policy
    last_debug_patch["compliance_response_planner_present"] = bool(response_planner)
    last_debug_patch["human_like_answer_policy_enabled"] = bool(
        human_like_answer_policy.get("enabled", False)
    )
    last_debug_patch["explicit_answer_need"] = bool(explicit_answer_need)
    last_debug_patch["repair_user_dissatisfaction"] = bool(
        sarcasm_or_negative_feedback
        or bool(
            dict(dialogue_policy_payload.get("mvp_overrides", {})).get(
                "repair_user_dissatisfaction",
                False,
            )
        )
    )
    last_debug_patch["sarcasm_or_negative_feedback"] = bool(sarcasm_or_negative_feedback)
    last_debug_patch["overruled_constraints"] = [
        str(item)
        for item in list(constraint_resolution.get("overruled_constraints", []) or [])
        if str(item).strip()
    ]
    final_answer_directive = (
        dict(ctx.get("final_answer_directive", {}))
        if isinstance(ctx.get("final_answer_directive"), dict)
        else {}
    )
    writer_contact_mode = str(
        ctx.get("final_answer_writer_contact_mode")
        or final_answer_directive.get("writer_contact_mode", "")
        or ""
    )
    last_debug_patch["final_answer_directive"] = final_answer_directive
    gate_feedback = (
        dict(final_answer_directive.get("acceptance_gate_feedback", {}))
        if isinstance(final_answer_directive.get("acceptance_gate_feedback"), dict)
        else {}
    )
    gate_failed_checks = {
        str(item)
        for item in list(gate_feedback.get("failed_checks", []) or [])
        if str(item).strip()
    }
    return EnforceSlice1PreludeResult(
        ctx=ctx,
        user_message=user_message,
        lowered_user=lowered_user,
        literal_markdown_echo=literal_markdown_echo,
        dialogue_profile=dialogue_profile,
        expansion_requested=expansion_requested,
        repair_and_expand_requested=repair_and_expand_requested,
        knowledge_answer=knowledge_answer,
        practice_gate=practice_gate,
        practice_allowed=practice_allowed,
        should_answer_directly=should_answer_directly,
        is_greeting=is_greeting,
        concept=concept,
        active_line=active_line,
        active_line_intent=active_line_intent,
        active_line_repair_mode=active_line_repair_mode,
        active_line_revoicing_allowed=active_line_revoicing_allowed,
        active_line_should_offer_practice=active_line_should_offer_practice,
        active_line_practice_suppression=active_line_practice_suppression,
        response_planner=response_planner,
        planner_next_move=planner_next_move,
        planner_answer_shape=planner_answer_shape,
        planner_question_policy=planner_question_policy,
        planner_practice_policy=planner_practice_policy,
        planner_safety_priority=planner_safety_priority,
        dialogue_policy_payload=dialogue_policy_payload,
        dialogue_pragmatics_payload=dialogue_pragmatics_payload,
        explicit_answer_need=explicit_answer_need,
        direct_concrete_request=direct_concrete_request,
        summary_request=summary_request,
        sarcasm_or_negative_feedback=sarcasm_or_negative_feedback,
        application_request=application_request,
        human_like_answer_policy=human_like_answer_policy,
        constraint_resolution=constraint_resolution,
        practice_overview_requested=practice_overview_requested,
        pragmatics_contextual_followup=pragmatics_contextual_followup,
        pragmatics_offer_type=pragmatics_offer_type,
        pragmatics_should_not_reconfirm=pragmatics_should_not_reconfirm,
        pragmatics_repair_dissatisfaction=pragmatics_repair_dissatisfaction,
        lowered_text=lowered_text,
        final_answer_directive=final_answer_directive,
        writer_contact_mode=writer_contact_mode,
        gate_feedback=gate_feedback,
        gate_failed_checks=gate_failed_checks,
        last_debug_patch=last_debug_patch,
    )
