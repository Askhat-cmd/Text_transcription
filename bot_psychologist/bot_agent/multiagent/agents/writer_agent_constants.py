"""Small pure helper functions extracted from writer_agent.py."""

from __future__ import annotations

import re


_LITERAL_MARKDOWN_ECHO_PATTERNS = (
    re.compile(
        r"(?:верни\s+без\s+объяснений\s+и\s+без\s+изменений\s+следующий\s+markdown(?:-блок)?\s*:)(.+)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"(?:return\s+the\s+following\s+markdown\s+block\s+without\s+changes\s*:)(.+)",
        re.IGNORECASE | re.DOTALL,
    ),
)


def _extract_literal_markdown_echo_request(user_message: str) -> str:
    text = str(user_message or "").strip()
    if not text:
        return ""
    for pattern in _LITERAL_MARKDOWN_ECHO_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        candidate = str(match.group(1) or "").strip()
        if not candidate:
            return ""
        if any(marker in candidate for marker in ("**", "- ", "* ", "1.", "##", "```")):
            return candidate
    return ""


def _to_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in markers)
