"""Detect mismatch between declared positive state and anxiety markers."""

from __future__ import annotations

import re
from typing import Dict, Optional


POSITIVE_DECLARATIONS = [
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        r"\bвсё\s+(хорошо|нормально|ок)\b",
        r"\bя\s+(справляюсь|в\s+порядке)\b",
        r"\bне\s+жалуюсь\b",
        r"\bвсё\s+под\s+контролем\b",
    )
]

ANXIETY_MARKERS = [
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        r"\b(устал|выматывает|тяжело|напряжени[ея]|не\s+высыпаюсь)\b",
        r"\b(раздражает|бесит|злит|достало)\b",
        r"\b(не\s+знаю\s+(как|что)|запутал[сяась]|не\s+понимаю)\b",
    )
]


def _first_match(patterns: list[re.Pattern[str]], text: str) -> Optional[str]:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def detect_contradiction(text: str) -> Dict[str, object]:
    """
    Detect contradiction signal in a single user message.

    The signal is informational and should not change routing directly.
    """
    lowered = (text or "").strip().lower()
    if not lowered:
        return {
            "has_contradiction": False,
            "declared": None,
            "actual_signal": None,
            "suggestion": "",
        }

    declared = _first_match(POSITIVE_DECLARATIONS, lowered)
    anxiety = _first_match(ANXIETY_MARKERS, lowered)
    has_contradiction = bool(declared and anxiety)

    if not has_contradiction:
        return {
            "has_contradiction": False,
            "declared": None,
            "actual_signal": None,
            "suggestion": "",
        }

    return {
        "has_contradiction": True,
        "declared": declared,
        "actual_signal": anxiety,
        "suggestion": (
            "Пользователь декларирует, что всё в порядке, но в тексте есть маркеры "
            "напряжения. Мягко отрази это расхождение и предложи уточнить переживание."
        ),
    }

