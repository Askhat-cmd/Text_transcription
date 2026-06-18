"""Final answer acceptance gate for live dialogue truth checks."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from .stale_stub_detector import detect_stale_stub
from .template_family_guard import detect_template_family_leakage


FINAL_ANSWER_ACCEPTANCE_GATE_VERSION = "final_answer_acceptance_gate_v1"

_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+")
_MECHANISM_LECTURE_MARKERS = (
    "механизм",
    "автоматический контроль",
    "автопилот",
    "паттерн",
    "внутренняя перегруз",
    "прогнозирование",
    "ресурс уходит",
)
_GENERIC_MARKERS = (
    "важно помнить",
    "это нормально",
    "дай себе время",
    "можно просто",
    "попробуй заметить",
    "ключевой механизм",
    "ключевой узел",
    "сейчас полезнее",
)
_CLOSE_MARKERS = ("спасибо", "благодарю", "до свидания", "прощай", "глупый бот", "тупой бот")
_MARKDOWN_REQUEST_MARKERS = (
    "markdown",
    "маркдаун",
    "жирн",
    "список",
    "пункт",
    "заголов",
    "таблиц",
)
_QUESTION_ACTS = {
    "direct_question",
    "knowledge_question",
    "concrete_situation_question",
    "practice_request",
    "clarification_request",
}
_CONCRETE_USER_ANCHORS = (
    "семья",
    "работ",
    "сокращ",
    "50",
    "пятьдесят",
    "невостреб",
    "ступор",
    "слом",
    "пропуст",
    "время",
    "бесполез",
    "убежден",
    "начальник",
    "несправедлив",
    "молч",
    "сжим",
    "конфликт",
)
_SUMMARY_RECONFIRM_MARKERS = (
    "хочешь чтобы я подвел итог",
    "хочешь, чтобы я подвел итог",
    "хочешь чтобы я подвёл итог",
    "хочешь, чтобы я подвёл итог",
    "хотите чтобы я подвел итог",
    "хотите, чтобы я подвел итог",
    "хотите чтобы я подвёл итог",
    "хотите, чтобы я подвёл итог",
    "могу подвести итог",
    "могу сделать резюме",
    "подвести итог?",
    "сделать резюме?",
    "do you want me to summarize",
    "would you like a summary",
)
_SUMMARY_LAST_OFFER_MARKERS = (
    "могу так сделать",
    "после подтверждения",
    "подтверди",
    "выбери формат",
    "скажи что выбрать",
    "да, могу",
    "начнем после",
    "начнём после",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower()).replace("ё", "е")


def _words(text: str) -> list[str]:
    return [part.lower().replace("ё", "е") for part in _WORD_RE.findall(str(text or ""))]


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _normalize(text)
    return any(marker in lowered for marker in markers)


def _content_words(text: str) -> set[str]:
    stop = {
        "что",
        "как",
        "это",
        "мне",
        "тебе",
        "меня",
        "тебя",
        "если",
        "где",
        "там",
        "здесь",
        "сейчас",
        "почему",
        "можно",
        "нужно",
        "мой",
        "моя",
        "мое",
        "моё",
        "про",
        "для",
        "без",
        "или",
        "оно",
        "она",
        "они",
        "все",
        "всё",
    }
    return {word for word in _words(text) if len(word) >= 4 and word not in stop}


def _overlap_ratio(source: str, answer: str) -> float:
    source_words = _content_words(source)
    if not source_words:
        return 0.0
    answer_words = _content_words(answer)
    return len(source_words & answer_words) / max(1, len(source_words))


def _concrete_anchor_hits(user_message: str, final_answer: str) -> list[str]:
    user_lower = _normalize(user_message)
    answer_lower = _normalize(final_answer)
    return [
        marker
        for marker in _CONCRETE_USER_ANCHORS
        if marker in user_lower and marker in answer_lower
    ]


def _looks_like_concrete_situation(
    *,
    user_message: str,
    dialogue_act_resolution: dict[str, Any],
    answer_obligation_resolution: dict[str, Any],
) -> bool:
    act = str(dialogue_act_resolution.get("dialogue_act", "") or "")
    obligation = str(answer_obligation_resolution.get("answer_obligation", "") or "")
    if act == "concrete_situation_question" or obligation == "answer_concrete_situation":
        return True
    lowered = _normalize(user_message)
    return (
        any(marker in lowered for marker in _CONCRETE_USER_ANCHORS)
        and any(marker in lowered for marker in ("что", "как", "почему", "?"))
    )


def _similarity(left: str, right: str) -> float:
    left_norm = _normalize(left)
    right_norm = _normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def _markdown_requested(user_message: str) -> bool:
    return _contains_any(user_message, _MARKDOWN_REQUEST_MARKERS)


def _bold_markdown_requested(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return "**" in str(user_message or "") or "жирн" in lowered or "заголов" in lowered


def _looks_like_greeting(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in ("здравств", "привет", "добрый день", "добрый вечер", "мой дорогой бот"))


def _answer_has_markdown(final_answer: str) -> bool:
    text = str(final_answer or "")
    return bool(
        re.search(r"(?m)^\s*(?:[-*]|\d+[.)])\s+\S", text)
        or re.search(r"\*\*[^*]+\*\*", text)
        or re.search(r"(?m)^#{1,3}\s+\S", text)
    )


def _count_list_items(text: str) -> int:
    return len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+\S", str(text or "")))


def _is_explicit_one_practice_request(text: str) -> bool:
    lowered = _normalize(text)
    return (
        any(marker in lowered for marker in ("практик", "упражн", "микропракти", "шаг"))
        and any(marker in lowered for marker in ("одну", "один", "коротк", "микро"))
    )


def _looks_like_practice_step(text: str) -> bool:
    lowered = _normalize(text)
    return any(marker in lowered for marker in ("сделай", "заметь", "отметь", "поймай", "назови", "остановись", "выдох"))


def _practice_request_anchor_hits(user_message: str, final_answer: str) -> list[str]:
    lowered_user = _normalize(user_message)
    lowered_answer = _normalize(final_answer)
    anchors = ("будь сильным", "сильн", "драйвер", "напряж", "сдерж")
    return [anchor for anchor in anchors if anchor in lowered_user and anchor in lowered_answer]


def _is_panic_control_support_question(text: str) -> bool:
    lowered = _normalize(text)
    return "паник" in lowered and "контрол" in lowered and "почему" in lowered


def build_final_answer_acceptance_gate_v1(
    *,
    user_message: str,
    final_answer: str,
    dialogue_act_resolution: dict[str, Any] | None,
    answer_obligation_resolution: dict[str, Any] | None,
    unanswered_question_state_before: dict[str, Any] | None,
    last_assistant_offer_before: dict[str, Any] | None,
    dialogue_style_state: dict[str, Any] | None,
    final_answer_directive: dict[str, Any] | None,
    writer_debug: dict[str, Any] | None,
    validator_result: Any | None,
    previous_assistant_message: str = "",
) -> dict[str, Any]:
    """Evaluate the final answer before it becomes accepted dialogue state."""

    act = dict(dialogue_act_resolution or {})
    obligation = dict(answer_obligation_resolution or {})
    unanswered = dict(unanswered_question_state_before or {})
    last_offer = dict(last_assistant_offer_before or {})
    style = dict(dialogue_style_state or {})
    directive = dict(final_answer_directive or {})
    writer = dict(writer_debug or {})
    answer = str(final_answer or "").strip()
    user = str(user_message or "").strip()
    failed_checks: list[str] = []
    warnings: list[str] = []

    stale = detect_stale_stub(answer)
    if bool(stale.get("detected", False)):
        failed_checks.append("stale_stub_detected")
    template_family_guard = detect_template_family_leakage(answer)
    if bool(template_family_guard.get("leak_detected", False)):
        failed_checks.append("template_family_leakage_detected")

    validator_blocked = bool(getattr(validator_result, "is_blocked", False))
    if not answer or bool(writer.get("error")) or validator_blocked:
        failed_checks.append("writer_error_or_empty_answer")
    no_stub_signal = (
        dict(writer.get("no_stub_repair_signal", {}))
        if isinstance(writer.get("no_stub_repair_signal"), dict)
        else {}
    )
    if no_stub_signal:
        failed_checks.append("no_stub_repair_signal")

    concrete_need = _looks_like_concrete_situation(
        user_message=user,
        dialogue_act_resolution=act,
        answer_obligation_resolution=obligation,
    )
    anchor_hits = _concrete_anchor_hits(user, answer)
    overlap = _overlap_ratio(user, answer)
    generic = _contains_any(answer, _GENERIC_MARKERS)
    if concrete_need and (len(anchor_hits) < 3 or overlap < 0.16 or generic) and len(answer) < 900:
        failed_checks.append("answer_too_generic_for_concrete_situation")

    dialogue_act = str(act.get("dialogue_act", "") or "")
    answer_obligation = str(obligation.get("answer_obligation", "") or "")
    direct_question = bool(
        dialogue_act in _QUESTION_ACTS
        or answer_obligation.startswith("answer_")
        or bool(unanswered.get("answer_required", False))
    )
    must_answer = str(
        unanswered.get("last_direct_user_question")
        or directive.get("must_answer")
        or user
    ).strip()
    if direct_question:
        question_overlap = _overlap_ratio(must_answer or user, answer)
        has_specific_concept = any(
            concept in _normalize(must_answer)
            and concept in _normalize(answer)
            for concept in ("нейросталкинг", "самореализац", "красн", "оранж", "зелен")
        )
        if question_overlap < 0.10 and not has_specific_concept and len(answer) < 700:
            failed_checks.append("answer_does_not_address_direct_question")

    if _is_explicit_one_practice_request(user):
        practice_anchor_hits = _practice_request_anchor_hits(user, answer)
        if (
            not _looks_like_practice_step(answer)
            or _count_list_items(answer) > 1
            or "?" in answer
            or len(answer) > 900
            or not practice_anchor_hits
        ):
            failed_checks.append("explicit_one_practice_request_not_fulfilled")

    lowered_answer = _normalize(answer)
    support_like_question = _is_panic_control_support_question(user) or (
        dialogue_act == "concrete_situation_question"
        and "почему" in _normalize(must_answer or user)
        and any(marker in lowered_answer for marker in ("паник", "контрол"))
    )
    if support_like_question:
        support_anchor_count = sum(
            1 for marker in ("паник", "контрол", "тел", "угроз", "безопас") if marker in lowered_answer
        )
        support_has_why = any(marker in lowered_answer for marker in ("потому что", "поэтому", "из-за"))
        support_textbook = any(
            marker in lowered_answer for marker in ("симпатоадренал", "префронтал", "автономн", "адреналин", "нижние этажи", "верхний этаж")
        )
        inline_numbered_lecture = all(marker in answer for marker in ("1.", "2.", "3."))
        if (
            not support_has_why
            or support_anchor_count < 3
            or ((support_textbook or inline_numbered_lecture) and (_count_list_items(answer) >= 2 or len(answer) > 180))
        ):
            failed_checks.append("support_direct_question_answer_too_textbook")
        elif "answer_too_generic_for_concrete_situation" in failed_checks:
            failed_checks = [
                check for check in failed_checks if check != "answer_too_generic_for_concrete_situation"
            ]

    previous_text = previous_assistant_message or str(last_offer.get("offer_text_summary", "") or "")
    previous_stale = detect_stale_stub(previous_text)
    if previous_text and (
        _similarity(previous_text, answer) >= 0.82
        or (bool(previous_stale.get("detected", False)) and _similarity(previous_text, answer) >= 0.45)
    ):
        failed_checks.append("answer_repeats_previous_bad_answer")

    if dialogue_act == "repair_complaint" or answer_obligation == "repair_and_answer_last_question":
        target = str(unanswered.get("last_direct_user_question", "") or directive.get("must_answer", "") or "")
        target_overlap = _overlap_ratio(target, answer)
        if target and target_overlap < 0.10 and "нейросталкинг" not in _normalize(answer):
            failed_checks.append("repair_failed_to_answer_recovered_question")

    summary_request = bool(
        dialogue_act == "summary_request"
        or answer_obligation == "summarize_current_conversation"
        or directive.get("summary_request", False)
    )
    if summary_request:
        if "?" in answer and _contains_any(answer, _SUMMARY_RECONFIRM_MARKERS):
            failed_checks.append("summary_request_reconfirmed_instead_of_answered")
        if _contains_any(answer, _SUMMARY_LAST_OFFER_MARKERS):
            failed_checks.append("summary_answered_last_offer_instead")
        summary_anchors = [
            str(item).strip()
            for item in list(directive.get("summary_context_anchors", []) or [])
            if str(item).strip()
        ]
        if summary_anchors:
            summary_overlap = max((_overlap_ratio(anchor, answer) for anchor in summary_anchors), default=0.0)
            if summary_overlap < 0.06 and len(answer) < 700:
                failed_checks.append("summary_answer_lacks_conversation_context")

    user_close = _contains_any(user, _CLOSE_MARKERS)
    answer_continues = _contains_any(answer, ("продолж", "механизм", "разбер", "практик", "шаг"))
    if user_close and answer_continues and dialogue_act in {"close_ack", "repair_complaint", "unknown"}:
        failed_checks.append("negative_goodbye_not_closed")

    if (dialogue_act in {"greeting", "contact_open"} or _looks_like_greeting(user)) and _contains_any(answer, _MECHANISM_LECTURE_MARKERS):
        failed_checks.append("greeting_answered_with_mechanism_explanation")

    if dialogue_act == "self_intro" and (
        _contains_any(answer, _MECHANISM_LECTURE_MARKERS) or len(answer) > 520
    ):
        failed_checks.append("self_intro_answered_with_lecture")

    if _markdown_requested(user) and (
        not _answer_has_markdown(answer)
        or (_bold_markdown_requested(user) and "**" not in answer and not re.search(r"(?m)^#{1,3}\s+\S", answer))
    ):
        failed_checks.append("markdown_requested_but_plain_text_only")

    if _contains_any(answer, ("как специалист", "я ии", "я искусственный интеллект")):
        warnings.append("user_facing_role_leak_risk")

    failed_checks = sorted(set(failed_checks))
    warnings = sorted(set(warnings))
    blocker_checks = {
        "stale_stub_detected",
        "template_family_leakage_detected",
        "writer_error_or_empty_answer",
        "no_stub_repair_signal",
        "answer_too_generic_for_concrete_situation",
        "answer_does_not_address_direct_question",
        "repair_failed_to_answer_recovered_question",
        "summary_request_reconfirmed_instead_of_answered",
        "summary_answered_last_offer_instead",
        "summary_answer_lacks_conversation_context",
        "negative_goodbye_not_closed",
        "greeting_answered_with_mechanism_explanation",
        "self_intro_answered_with_lecture",
    }
    high = any(check in blocker_checks for check in failed_checks)
    status = "failed" if failed_checks else ("warning" if warnings else "passed")
    severity = "blocker" if high else ("medium" if failed_checks else ("low" if warnings else "none"))
    can_accept = status == "passed"
    can_save_last_assistant_offer = bool(can_accept and not summary_request)

    return {
        "version": FINAL_ANSWER_ACCEPTANCE_GATE_VERSION,
        "status": status,
        "severity": severity,
        "failed_checks": failed_checks,
        "warnings": warnings,
        "stale_stub_detected": bool(stale.get("detected", False)),
        "stale_stub_detail": stale,
        "answer_considered_real": bool(can_accept),
        "can_mark_question_answered": bool(can_accept),
        "can_save_as_healthy_context": bool(can_accept),
        "can_use_as_summary_source": bool(can_accept),
        "can_save_last_assistant_offer": can_save_last_assistant_offer,
        "must_quarantine_answer": not bool(can_accept),
        "retry_recommended": bool(status == "failed"),
        "template_family_guard": {
            **template_family_guard,
            "contamination_quarantined": bool(
                template_family_guard.get("leak_detected", False)
                and not can_accept
            ),
        },
        "no_stub_repair_signal": {
            **no_stub_signal,
            "user_facing_replacement_created": bool(
                no_stub_signal.get("user_facing_replacement_created", False)
            ),
        },
        "input_summary": {
            "dialogue_act": dialogue_act,
            "answer_obligation": answer_obligation,
            "unanswered_answer_required": bool(unanswered.get("answer_required", False)),
            "last_offer_open": bool(last_offer.get("is_open", False)),
            "style_length_preference": str(style.get("length_preference", "") or ""),
        },
        "quality_signals": {
            "concrete_need": bool(concrete_need),
            "concrete_anchor_hits": anchor_hits,
            "user_answer_overlap_ratio": round(float(overlap), 3),
            "previous_answer_similarity": round(float(_similarity(previous_text, answer)), 3),
            "markdown_requested": bool(_markdown_requested(user)),
            "markdown_detected": bool(_answer_has_markdown(answer)),
            "summary_request": bool(summary_request),
        },
        "quarantine_reason": ", ".join(failed_checks),
    }


__all__ = [
    "FINAL_ANSWER_ACCEPTANCE_GATE_VERSION",
    "build_final_answer_acceptance_gate_v1",
]
