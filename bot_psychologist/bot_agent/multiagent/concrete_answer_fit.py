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
    "по ситуации",
    "разбери ситуацию",
    "разбери мой случай",
    "применить к",
    "как это выглядит",
    "как это применить",
    "что делать когда",
    "что происходит когда",
    "как распутать",
    "узел убеждений",
    "в семье",
    "на работе",
    "сокращение",
    "невостребованность",
    "ступор",
)

_FORMULAIC_OPENINGS = (
    "сейчас полезнее не упражнение",
    "сейчас полезнее прямое объяснение",
    "сейчас лучше продолжить смысловую линию",
    "здесь важно сначала увидеть триггер",
    "ключевой механизм застревания в том",
    "ключевой узел в том",
    "ключевой узел на работе",
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

_USER_ANCHOR_LABELS = (
    ("50", ("50", "пятьдесят")),
    ("семья", ("семь", "семьи", "семье")),
    ("сокращение на работе", ("сокращ",)),
    ("работа", ("работ",)),
    ("ступор", ("ступор",)),
    ("невостребованность", ("невостреб",)),
    ("голос 'я бесполезен'", ("бесполез",)),
    ("ощущение, что время упущено", ("упущ", "время")),
    ("узел убеждений", ("убежден", "убеждён", "узел")),
)


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower().replace("ё", "е")


def _contains_any(text: str, items: tuple[str, ...]) -> bool:
    return any(item in text for item in items)


def extract_context_anchor(user_message: str) -> str:
    message = str(user_message or "").strip()
    for pattern in _ANCHOR_PATTERNS:
        match = pattern.search(message)
        if match:
            return match.group(1).strip(" .,!?")
    anchors = extract_user_anchor_labels(user_message)
    return ", ".join(anchors[:4])


def extract_user_anchor_labels(user_message: str) -> list[str]:
    normalized = _normalize(user_message)
    labels: list[str] = []
    for label, markers in _USER_ANCHOR_LABELS:
        if any(marker in normalized for marker in markers):
            labels.append(label)
    return labels


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
    user_anchor_labels = extract_user_anchor_labels(user_message)
    concrete_need = bool(
        direct_concrete_request
        or application_request
        or len(user_anchor_labels) >= 2
        or (
            context_anchor
            and (
                "объясни" in normalized_user
                or "разбери" in normalized_user
                or "по моей ситуации" in normalized_user
                or "по моему случаю" in normalized_user
                or "как распутать" in normalized_user
            )
        )
        or (
            explicit_answer_need
            and _contains_any(normalized_user, _CONCRETE_NEED_MARKERS)
        )
    )
    formulaic = _contains_any(normalized_answer, _FORMULAIC_OPENINGS)
    anchor_hits = [label for label in user_anchor_labels if _normalize(label).strip("'") in normalized_answer]
    anchor_used = bool(context_anchor and _normalize(context_anchor) in normalized_answer) or len(anchor_hits) >= 2
    structured_answer = bool(re.search(r"(^|\n)\s*(?:[-*•]|\d+[.)])\s+", answer_text))
    answer_long_enough = len(str(answer_text or "").strip()) >= 180
    needs_repair = bool(concrete_need and (formulaic or not anchor_used))
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
        "user_anchor_labels": user_anchor_labels,
        "answer_anchor_hits": anchor_hits,
        "answer_mentions_context_anchor": anchor_used,
        "structured_answer": structured_answer,
        "answer_long_enough": answer_long_enough,
        "fit_status": fit_status,
        "needs_repair": needs_repair,
    }


__all__ = [
    "evaluate_concrete_answer_fit",
    "extract_context_anchor",
    "extract_user_anchor_labels",
]
