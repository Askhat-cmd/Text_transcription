from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..dialogue_policy import (
    context_budget_for_profile,
    format_conversation_context_for_writer_with_meta,
    normalize_dialogue_profile,
)


@dataclass(frozen=True)
class CallLLMSlice1Inputs:
    knowledge_answer: dict[str, Any]
    knowledge_answer_first: bool
    do_not_ask_definition: bool
    practice_allowed: bool
    practice_ban_instruction: str
    known_concept_clarification_ban: str
    external_surveillance_frame_ban: str
    philosophy_kernel: dict[str, Any]
    writer_freedom_contract: dict[str, Any]
    selected_lenses: list[str]
    freedom_hard_boundaries: list[str]
    dialogue_policy_payload: dict[str, Any]
    human_like_answer_policy: dict[str, Any]
    constraint_resolution: dict[str, Any]
    user_message: str
    dialogue_profile: str
    context_budget_chars: int
    formatted_context: str
    context_meta: dict[str, Any]


def _extract_call_llm_slice1_inputs(ctx: dict[str, Any]) -> CallLLMSlice1Inputs:
    knowledge_answer = (
        dict(ctx.get("knowledge_answer", {}))
        if isinstance(ctx.get("knowledge_answer"), dict)
        else {}
    )
    practice_gate = (
        dict(ctx.get("practice_gate", {}))
        if isinstance(ctx.get("practice_gate"), dict)
        else {}
    )
    knowledge_answer_first = bool(knowledge_answer.get("should_answer_directly", False))
    do_not_ask_definition = bool(knowledge_answer.get("should_answer_directly", False))
    practice_allowed = bool(practice_gate.get("practice_allowed", True))
    practice_ban_instruction = (
        str(ctx.get("writer_visible_practice_instruction", "") or "no_exercise_but_answer_normally")
        if not practice_allowed
        else "false"
    )
    known_concept_clarification_ban = (
        "true: do_not_ask_user_to_define_or_choose_known_concept_variant"
        if do_not_ask_definition
        else "false"
    )
    external_surveillance_frame_ban = (
        "true: avoid_external_surveillance_biofeedback_eeg_frame_for_internal_concept_answer"
        if knowledge_answer_first
        else "false"
    )
    philosophy_kernel = (
        dict(ctx.get("philosophy_kernel", {}))
        if isinstance(ctx.get("philosophy_kernel"), dict)
        else {}
    )
    writer_freedom_contract = (
        dict(ctx.get("writer_freedom_contract", {}))
        if isinstance(ctx.get("writer_freedom_contract"), dict)
        else {}
    )
    selected_lenses = [
        str(item)
        for item in list(ctx.get("philosophy_kernel_selected_lenses", []) or [])
        if str(item).strip()
    ]
    freedom_hard_boundaries = [
        str(item)
        for item in list(ctx.get("writer_freedom_hard_boundaries", []) or [])
        if str(item).strip()
    ]

    dialogue_policy_payload = (
        dict(ctx.get("dialogue_policy", {}))
        if isinstance(ctx.get("dialogue_policy"), dict)
        else {}
    )
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
    user_message = str(ctx.get("user_message", "") or "")
    dialogue_profile = normalize_dialogue_profile(
        dialogue_policy_payload.get("profile", ctx.get("dialogue_profile", "safe_guided"))
    )
    context_budget_chars = int(
        dialogue_policy_payload.get("context_budget_chars", context_budget_for_profile(dialogue_profile))
        or context_budget_for_profile(dialogue_profile)
    )
    formatted_context, context_meta = format_conversation_context_for_writer_with_meta(
        conversation_context=str(ctx.get("conversation_context", "") or ""),
        profile=dialogue_profile,
        budget_chars=context_budget_chars,
    )

    return CallLLMSlice1Inputs(
        knowledge_answer=knowledge_answer,
        knowledge_answer_first=knowledge_answer_first,
        do_not_ask_definition=do_not_ask_definition,
        practice_allowed=practice_allowed,
        practice_ban_instruction=practice_ban_instruction,
        known_concept_clarification_ban=known_concept_clarification_ban,
        external_surveillance_frame_ban=external_surveillance_frame_ban,
        philosophy_kernel=philosophy_kernel,
        writer_freedom_contract=writer_freedom_contract,
        selected_lenses=selected_lenses,
        freedom_hard_boundaries=freedom_hard_boundaries,
        dialogue_policy_payload=dialogue_policy_payload,
        human_like_answer_policy=human_like_answer_policy,
        constraint_resolution=constraint_resolution,
        user_message=user_message,
        dialogue_profile=dialogue_profile,
        context_budget_chars=context_budget_chars,
        formatted_context=formatted_context,
        context_meta=context_meta,
    )
