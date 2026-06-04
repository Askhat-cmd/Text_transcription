"""Concrete answer-fit heuristics for writer-side repair decisions."""

from __future__ import annotations

import re
from typing import Any

_CONCRETE_NEED_MARKERS = (
    "по моей ситуации",
    "по моему случаю",
    "объясни по",
    "разбери по",
    "в этой ситуации",
    "в такой ситуации",
    "в моем случае",
    "в моём случае",
    "на моем примере",
    "на моём примере",
    "на примере",
    "по моему примеру",
    "по моему случаю",
    "по ситуации",
    "разбери ситуацию",
    "разбери мой случай",
    "применить к",
    "как это выглядит",
    "как это применить",
    "что делать когда",
    "что происходит когда",
    "когда ",
    "если ",
)

_FORMULAIC_OPENINGS = (
    "сейчас полезнее не упражнение",
    "сейчас полезнее прямое объяснение",
    "сейчас лучше продолжить смысловую линию",
    "здесь важно сначала увидеть триггер",
    "ключевой механизм застревания в том",
    "исправляю прошлую заготовку и отвечаю прямо",
)

_ANCHOR_PATTERNS = (
    re.compile(r"\b(в разговоре с [^,.!?\n]+)", re.IGNORECASE),
    re.compile(r"\b(когда [^,.!?\n]+)", re.IGNORECASE),
    re.compile(r"\b(если [^,.!?\n]+)", re.IGNORECASE),
    re.compile(r"\b(на работе[^,.!?\n]*)", re.IGNORECASE),
    re.compile(r"\b(с начальник[^,.!?\n]*)", re.IGNORECASE),
    re.compile(r"\b(в отношени[^,.!?\n]*)", re.IGNORECASE),
    re.compile(r"\b(в переписк[^,.!?\n]*)", re.IGNORECASE),
)


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def _contains_any(text: str, items: tuple[str, ...]) -> bool:
    return any(item in text for item in items)


def extract_context_anchor(user_message: str) -> str:
    message = str(user_message or "").strip()
    for pattern in _ANCHOR_PATTERNS:
        match = pattern.search(message)
        if match:
            return match.group(1).strip(" .,!?")
    return ""


def evaluate_concrete_answer_fit(
    *,
    user_message: str,
    answer_text: str,
    direct_concrete_request: bool = False,
    application_request: bool = False,
    explicit_answer_need: bool = False,
) -> dict[str, Any]:
    normalized_user = _normalize(user_message)
    normalized_answer = _normalize(answer_text)
    context_anchor = extract_context_anchor(user_message)
    concrete_need = bool(
        direct_concrete_request
        or application_request
        or (
            context_anchor
            and (
                "объясни" in normalized_user
                or "разбери" in normalized_user
                or "по моей ситуации" in normalized_user
                or "по моему случаю" in normalized_user
            )
        )
        or (
            explicit_answer_need
            and _contains_any(normalized_user, _CONCRETE_NEED_MARKERS)
        )
    )
    formulaic = _contains_any(normalized_answer, _FORMULAIC_OPENINGS)
    anchor_used = bool(context_anchor and _normalize(context_anchor) in normalized_answer)
    structured_answer = bool(re.search(r"(^|\n)\s*(?:[-*•]|\d+[.)])\s+", answer_text))
    answer_long_enough = len(str(answer_text or "").strip()) >= 180
    needs_repair = bool(concrete_need and formulaic and not anchor_used)
    fit_status = "pass"
    if concrete_need and not answer_long_enough and not structured_answer:
        fit_status = "warning"
    if needs_repair:
        fit_status = "fail"
    return {
        "version": "concrete_answer_fit_v1",
        "concrete_need": concrete_need,
        "formulaic_opening_detected": formulaic,
        "context_anchor": context_anchor,
        "answer_mentions_context_anchor": anchor_used,
        "structured_answer": structured_answer,
        "answer_long_enough": answer_long_enough,
        "fit_status": fit_status,
        "needs_repair": needs_repair,
    }


def build_contextual_no_practice_answer(*, user_message: str, concept: str = "") -> str:
    anchor = extract_context_anchor(user_message)
    anchor_phrase = anchor if anchor else "в той ситуации, о которой ты говоришь"
    concept_prefix = ""
    if str(concept or "").strip().lower() == "нейросталкинг":
        concept_prefix = "Если смотреть на это через нейросталкинг, "
    return (
        f"{concept_prefix}ключевой узел {anchor_phrase} не в упражнении, а в том, как внутри быстро собирается "
        "автоматическая реакция.\n\n"
        "1. Триггер. Есть момент, после которого тело и мысль мгновенно уходят в знакомый сценарий.\n"
        "2. Автопаттерн. Внутри появляется готовая интерпретация вроде защиты, контроля или избегания, и она сужает выбор.\n"
        "3. Что важно увидеть. Проблема не в самом факте ситуации, а в том, что реакция успевает стать единственным вариантом ответа.\n\n"
        "Поэтому полезный разбор здесь такой: что именно запускает сжатие, какой внутренний сценарий включается первым, "
        "и какой более точный ответ по факту ты хотел бы выбрать вместо автоматизма."
    )


__all__ = [
    "build_contextual_no_practice_answer",
    "evaluate_concrete_answer_fit",
    "extract_context_anchor",
]
