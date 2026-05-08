from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


@dataclass
class StructuredSection:
    heading_path: list[str]
    title: str
    level: int
    text: str
    start_line: int
    end_line: int
    section_role_hint: str
    boundary_confidence: float


_ROLE_ORDER = (
    "practice",
    "safety",
    "lens",
    "architecture",
    "case",
    "quote",
    "theory",
)

_ROLE_MARKERS: dict[str, tuple[str, ...]] = {
    "practice": (
        "практика",
        "упражнение",
        "техника",
        "цель:",
        "время:",
        "шаг 1",
        "шаг 2",
        "шаг 3",
    ),
    "safety": (
        "безопас",
        "кризис",
        "суицид",
        "самоповрежд",
        "не заменяет специалиста",
        "экстренная помощь",
        "протокол",
    ),
    "lens": (
        "паттерн",
        "программа",
        "избегани",
        "триггер",
        "слепая зона",
        "самоценност",
        "границ",
    ),
    "architecture": (
        "neo mindbot",
        "архитектур",
        "writer",
        "diagnostic center",
        "safety layer",
        "validator",
        "prompt",
    ),
    "case": (
        "кейс",
        "пример",
        "история",
    ),
    "quote": (
        "цитата",
    ),
}


def _normalize_line(text: str) -> str:
    return (text or "").strip()


def _line_token_count(text: str) -> int:
    return len([p for p in re.split(r"\s+", text.strip()) if p])


def _looks_like_upper_heading(line: str) -> bool:
    if len(line) < 8 or len(line) > 120:
        return False
    if _line_token_count(line) < 2:
        return False
    letters = [ch for ch in line if ch.isalpha()]
    if not letters:
        return False
    upper_letters = [ch for ch in letters if ch.upper() == ch]
    return len(upper_letters) / max(1, len(letters)) >= 0.85


def _match_heading(line: str) -> tuple[int, str, float] | None:
    text = _normalize_line(line)
    if not text:
        return None

    m = re.match(r"^(#{1,6})\s+(.+)$", text)
    if m:
        level = min(6, len(m.group(1)))
        return level, m.group(2).strip(), 0.96

    m = re.match(r"(?i)^(глава|chapter)\s+[\divxlcdm]+(?:[\s:.-].*)?$", text)
    if m:
        return 1, text, 0.88

    m = re.match(r"^\d+(?:\.\d+){0,3}[\).\s-]+.+$", text)
    if m and _line_token_count(text) >= 2:
        nested = re.match(r"^(\d+(?:\.\d+){0,3})", text)
        depth = 1
        if nested:
            depth = min(4, len(nested.group(1).split(".")))
        return min(6, depth + 1), text, 0.84

    marker_heading = re.match(
        r"(?i)^(практика|упражнение|техника|безопасность|важно|протокол|кейс|пример|цитата)\b.*$",
        text,
    )
    if marker_heading and len(text) <= 140:
        return 2, text, 0.8

    if _looks_like_upper_heading(text):
        return 1, text, 0.72

    return None


def _count_matches(text: str, markers: Iterable[str]) -> int:
    value = (text or "").lower()
    count = 0
    for marker in markers:
        if marker and marker in value:
            count += 1
    return count


def _detect_role(title: str, text: str) -> tuple[str, dict[str, int]]:
    title_lower = (title or "").lower()
    text_lower = (text or "").lower()

    role_counts: dict[str, int] = {role: 0 for role in _ROLE_ORDER}
    for role in _ROLE_ORDER:
        markers = _ROLE_MARKERS.get(role, ())
        score = 3 * _count_matches(title_lower, markers) + _count_matches(text_lower, markers)
        role_counts[role] = score

    quote_density = text.count("\"") + text.count("«") + text.count("»")
    if quote_density >= 6:
        role_counts["quote"] += 2

    best_role = "unknown"
    best_score = 0
    for role in _ROLE_ORDER:
        score = role_counts.get(role, 0)
        if score > best_score:
            best_score = score
            best_role = role

    if best_role == "unknown" or best_score <= 0:
        if len((text or "").strip()) > 0:
            return "theory", role_counts
        return "unknown", role_counts

    return best_role, role_counts


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))


def parse_markdown_like_sections_v1(text: str) -> list[StructuredSection]:
    lines = (text or "").splitlines()
    if not lines:
        return [
            StructuredSection(
                heading_path=["Document"],
                title="Document",
                level=1,
                text="",
                start_line=1,
                end_line=1,
                section_role_hint="unknown",
                boundary_confidence=0.2,
            )
        ]

    headings: list[tuple[int, str, int, float]] = []
    for idx, raw_line in enumerate(lines):
        matched = _match_heading(raw_line)
        if matched is None:
            continue
        level, title, confidence = matched
        headings.append((idx, title, level, confidence))

    if not headings:
        merged = "\n".join(lines).strip()
        role, _ = _detect_role("Document", merged)
        return [
            StructuredSection(
                heading_path=["Document"],
                title="Document",
                level=1,
                text=merged,
                start_line=1,
                end_line=max(1, len(lines)),
                section_role_hint=role if role != "theory" else "unknown",
                boundary_confidence=0.35,
            )
        ]

    sections: list[StructuredSection] = []
    stack: list[str] = []

    for i, (start_idx, title, level, heading_conf) in enumerate(headings):
        end_idx = headings[i + 1][0] - 1 if i + 1 < len(headings) else len(lines) - 1
        body_lines = lines[start_idx + 1 : end_idx + 1]
        body = "\n".join(body_lines).strip()

        stack = stack[: max(0, level - 1)]
        stack.append(title)
        heading_path = list(stack)

        role, role_counts = _detect_role(title, body)
        non_zero_roles = sum(1 for value in role_counts.values() if value > 0)
        confidence = heading_conf + (0.04 if role != "unknown" else 0.0) - (0.03 if non_zero_roles > 2 else 0.0)

        sections.append(
            StructuredSection(
                heading_path=heading_path,
                title=title,
                level=level,
                text=body,
                start_line=start_idx + 1,
                end_line=end_idx + 1,
                section_role_hint=role,
                boundary_confidence=_clamp_confidence(confidence),
            )
        )

    return sections
