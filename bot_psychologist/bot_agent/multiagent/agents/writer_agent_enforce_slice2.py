from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..concrete_answer_fit import evaluate_concrete_answer_fit
from .writer_agent_constants import _contains_any


@dataclass(frozen=True)
class EnforceSlice2SecondPreludeResult:
    last_debug_patch: dict[str, Any]
    close_gently_triggered: bool
    answer_obligation: str
    last_direct_question: str
    last_offer_summary: str
    offer_repair_context: str
    concept_question: bool
    has_unsolicited_practice: bool
    has_question: bool
    asks_define_known_term: bool
    has_external_surveillance_frame: bool
    user_requests_no_question: bool
    user_requests_no_practice: bool
    user_repair_signal: bool
    user_step_request: bool
    canned_step_disallowed: bool
    user_mechanism_request: Optional[bool] = None
    answer_fit: Optional[dict[str, Any]] = None


def _extract_enforce_slice2_second_prelude_and_close_gently(
    ctx: dict[str, Any],
    *,
    text: str,
    lowered_user: str,
    lowered_text: str,
    planner_question_policy: str,
    planner_practice_policy: str,
    planner_answer_shape: str,
    writer_contact_mode: str,
    direct_concrete_request: bool,
    application_request: bool,
    explicit_answer_need: bool,
    user_message: str,
    practice_markers: tuple[str, ...],
    known_concept_clarification_markers: tuple[str, ...],
    external_surveillance_markers: tuple[str, ...],
) -> EnforceSlice2SecondPreludeResult:
    last_debug_patch: dict[str, Any] = {}
    last_debug_patch["legacy_constraints_suppressed"] = [
        str(item)
        for item in list(ctx.get("legacy_constraints_suppressed", []) or [])
        if str(item).strip()
    ]
    last_debug_patch["question_forced"] = bool(
        planner_question_policy not in {"none", "optional_none"}
    )
    last_debug_patch["practice_forced"] = bool(
        planner_practice_policy in {"required", "one_step_required"}
    )
    last_debug_patch["microstep_forced"] = False
    answer_obligation = str(
        ctx.get("answer_obligation")
        or dict(ctx.get("final_answer_directive", {})).get("answer_obligation", "")
        or ""
    )
    last_direct_question = str(ctx.get("unanswered_question_summary", "") or "")
    last_offer_summary = str(ctx.get("last_assistant_offer_summary", "") or "")
    offer_repair_context = f"{last_offer_summary} {last_direct_question}".lower()
    concept_question = "нейросталкинг" in lowered_user

    has_unsolicited_practice = any(marker in lowered_text for marker in practice_markers)
    has_question = "?" in text
    asks_define_known_term = any(
        marker in lowered_text for marker in known_concept_clarification_markers
    )
    has_external_surveillance_frame = any(
        marker in lowered_text for marker in external_surveillance_markers
    )
    user_requests_no_question = _contains_any(
        lowered_user, ("без вопросов", "не задавай вопросов", "ответь без вопроса", "без вопроса")
    )
    user_requests_no_practice = _contains_any(
        lowered_user,
        (
            "без практик",
            "без перехода в практик",
            "не давай практик",
            "без упражн",
            "не хочу практик",
            "не хочу упражн",
        ),
    )
    user_repair_signal = _contains_any(
        lowered_user, ("ушел не туда", "вернись к сути", "снова предлагаешь практику", "я просил разбор механизма")
    )
    user_step_request = _contains_any(
        lowered_user, ("один шаг", "что сделать прямо сейчас", "что делать прямо сейчас", "дай шаг", "хочу действие")
    )
    last_debug_patch["microstep_forced"] = bool(
        planner_answer_shape == "one_step" and not user_step_request
    )
    canned_step_disallowed = bool(
        planner_practice_policy == "forbidden"
        or user_requests_no_practice
        or (writer_contact_mode == "free_writer_contact" and not user_step_request)
    )
    last_debug_patch["canned_step_disallowed"] = canned_step_disallowed
    if answer_obligation == "close_gently" and (
        has_question
        or has_unsolicited_practice
        or _contains_any(lowered_text, ("если хочешь", "если захочешь", "давай продолжим", "следующий шаг"))
    ):
        return EnforceSlice2SecondPreludeResult(
            last_debug_patch=last_debug_patch,
            close_gently_triggered=True,
            answer_obligation=answer_obligation,
            last_direct_question=last_direct_question,
            last_offer_summary=last_offer_summary,
            offer_repair_context=offer_repair_context,
            concept_question=concept_question,
            has_unsolicited_practice=has_unsolicited_practice,
            has_question=has_question,
            asks_define_known_term=asks_define_known_term,
            has_external_surveillance_frame=has_external_surveillance_frame,
            user_requests_no_question=user_requests_no_question,
            user_requests_no_practice=user_requests_no_practice,
            user_repair_signal=user_repair_signal,
            user_step_request=user_step_request,
            canned_step_disallowed=canned_step_disallowed,
        )
    user_mechanism_request = _contains_any(
        lowered_user, ("механизм", "почему застреваю", "как это работает", "разбор")
    )
    answer_fit = evaluate_concrete_answer_fit(
        user_message=user_message,
        answer_text=text,
        direct_concrete_request=direct_concrete_request,
        application_request=application_request,
        explicit_answer_need=explicit_answer_need,
    )
    last_debug_patch["answer_fit_evaluator"] = dict(answer_fit)
    return EnforceSlice2SecondPreludeResult(
        last_debug_patch=last_debug_patch,
        close_gently_triggered=False,
        answer_obligation=answer_obligation,
        last_direct_question=last_direct_question,
        last_offer_summary=last_offer_summary,
        offer_repair_context=offer_repair_context,
        concept_question=concept_question,
        has_unsolicited_practice=has_unsolicited_practice,
        has_question=has_question,
        asks_define_known_term=asks_define_known_term,
        has_external_surveillance_frame=has_external_surveillance_frame,
        user_requests_no_question=user_requests_no_question,
        user_requests_no_practice=user_requests_no_practice,
        user_repair_signal=user_repair_signal,
        user_step_request=user_step_request,
        canned_step_disallowed=canned_step_disallowed,
        user_mechanism_request=user_mechanism_request,
        answer_fit=answer_fit,
    )
