"""Compact explicit latest-turn constraint extractor for current runtime."""

from __future__ import annotations

import re
from typing import Iterable


LATEST_TURN_CONSTRAINTS_VERSION = "latest_turn_constraints_v1"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _matches_any(text: str, patterns: Iterable[re.Pattern[str]]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


_NO_PRACTICE_PATTERNS = (
    re.compile(r"не\s+дава\w*\s+практик", re.IGNORECASE),
    re.compile(r"не\s+дава\w*(?:\s+\w+){0,3}\s+практик", re.IGNORECASE),
    re.compile(r"не\s+хоч\w*\s+практик", re.IGNORECASE),
    re.compile(r"не\s+хоч\w*(?:\s+\w+){0,3}\s+практик\w*", re.IGNORECASE),
    re.compile(r"не\s+хоч\w*(?:\s+\w+){0,3}\s+упражнен\w*", re.IGNORECASE),
    re.compile(r"без\s+практик", re.IGNORECASE),
    re.compile(r"не\s+предлаг\w*\s+(?:упражнен|практик)", re.IGNORECASE),
    re.compile(r"не\s+надо\s+(?:практик|упражнен)", re.IGNORECASE),
    re.compile(r"снова\s+су\w+\s+практик", re.IGNORECASE),
)
_NO_BREATHING_ONLY_PATTERNS = (
    re.compile(r"не\s+снова\s+дыхани", re.IGNORECASE),
    re.compile(r"не\s+только\s+дыхани", re.IGNORECASE),
    re.compile(r"кроме\s+дыхани", re.IGNORECASE),
    re.compile(r"нет\s+других\s+способ\w*\s+кроме\s+дыхани", re.IGNORECASE),
    re.compile(r"не\s+своди\w*\s+.*\s+к\s+дыхани", re.IGNORECASE),
    re.compile(r"не\s+своди\w*\s+к\s+дыхани", re.IGNORECASE),
)
_SIMPLIFY_PATTERNS = (
    re.compile(r"скажи\s+проще", re.IGNORECASE),
    re.compile(r"объясни\s+проще", re.IGNORECASE),
    re.compile(r"слишком\s+сложно", re.IGNORECASE),
    re.compile(r"простыми\s+словами", re.IGNORECASE),
    re.compile(r"без\s+лекци", re.IGNORECASE),
    re.compile(r"короче\s+и\s+проще", re.IGNORECASE),
)
_LONG_TERM_PATTERNS = (
    re.compile(r"долгосроч", re.IGNORECASE),
    re.compile(r"в\s+долгосрочн\w*\s+перспектив", re.IGNORECASE),
    re.compile(r"на\s+длинн\w*\s+дистанци", re.IGNORECASE),
    re.compile(r"в\s+долгую", re.IGNORECASE),
    re.compile(r"не\s+только\s+прямо\s+сейчас", re.IGNORECASE),
)
_NO_INTERNAL_DB_PATTERNS = (
    re.compile(r"не\s+опира\w*\s+на\s+внутренн\w*\s+бд", re.IGNORECASE),
    re.compile(r"без\s+внутренн\w*\s+бд", re.IGNORECASE),
    re.compile(r"не\s+использ\w*\s+внутренн\w*\s+бд", re.IGNORECASE),
    re.compile(r"без\s+внутренн\w*\s+баз", re.IGNORECASE),
    re.compile(r"internal db", re.IGNORECASE),
    re.compile(r"internal knowledge", re.IGNORECASE),
)


def active_latest_turn_constraint_names(payload: dict[str, object] | None) -> list[str]:
    constraints = dict(payload or {})
    active: list[str] = []
    for name in (
        "no_practice",
        "no_breathing_only",
        "simplify",
        "long_term_perspective",
        "no_internal_db",
    ):
        if bool(constraints.get(name, False)):
            active.append(name)
    return active


def build_latest_turn_constraints_v1(user_message: str) -> dict[str, object]:
    normalized = _normalize(user_message)
    payload: dict[str, object] = {
        "version": LATEST_TURN_CONSTRAINTS_VERSION,
        "no_practice": _matches_any(normalized, _NO_PRACTICE_PATTERNS),
        "no_breathing_only": _matches_any(normalized, _NO_BREATHING_ONLY_PATTERNS),
        "simplify": _matches_any(normalized, _SIMPLIFY_PATTERNS),
        "long_term_perspective": _matches_any(normalized, _LONG_TERM_PATTERNS),
        "no_internal_db": _matches_any(normalized, _NO_INTERNAL_DB_PATTERNS),
    }
    payload["active_constraints"] = active_latest_turn_constraint_names(payload)
    payload["source"] = (
        "latest_user_turn_explicit_text"
        if bool(payload["active_constraints"])
        else "none"
    )
    return payload


__all__ = [
    "LATEST_TURN_CONSTRAINTS_VERSION",
    "active_latest_turn_constraint_names",
    "build_latest_turn_constraints_v1",
]
