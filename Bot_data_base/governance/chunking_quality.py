from __future__ import annotations

from models.universal_block import UniversalBlock

_PRACTICE_MARKERS = (
    "практика",
    "упражнение",
    "техника",
    "шаг",
    "цель:",
    "время:",
)

_SAFETY_MARKERS = (
    "безопас",
    "кризис",
    "суицид",
    "самоповрежд",
    "не заменяет специалиста",
)

_LENS_MARKERS = (
    "паттерн",
    "избегани",
    "триггер",
    "границ",
    "слепая зона",
)

_ARCHITECTURE_MARKERS = (
    "neo mindbot",
    "архитектур",
    "writer",
    "diagnostic center",
    "prompt",
)


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in text)


def build_chunking_quality_v1(block: UniversalBlock) -> dict:
    text = (block.text or "").strip()
    title = (block.title or "").strip()
    char_count = len(text)
    approx_token_count = max(1, char_count // 4) if text else 0

    too_short = approx_token_count < 80
    too_long = approx_token_count > 1800
    has_heading = bool(title)
    has_summary = bool((block.summary or "").strip())

    heading_path_present = bool(block.heading_path)
    section_role_hint = (block.section_role_hint or "").strip().lower() or "unknown"
    boundary_confidence = float(block.boundary_confidence or 0.0)
    split_reason = (block.split_reason or "").strip()

    lowered = f"{' > '.join(block.heading_path or [])}\n{title}\n{text}".lower()
    role_marker_counts = {
        "practice": _count_markers(lowered, _PRACTICE_MARKERS),
        "safety": _count_markers(lowered, _SAFETY_MARKERS),
        "lens": _count_markers(lowered, _LENS_MARKERS),
        "architecture": _count_markers(lowered, _ARCHITECTURE_MARKERS),
    }
    mixed_intent_risk = sum(1 for value in role_marker_counts.values() if value > 0) >= 2

    possible_practice_split = (
        block.governance.get("chunk_type") == "practice"
        and not any(marker in lowered for marker in ("шаг 2", "шаг 3", "время:", "цель:"))
    )
    possible_context_fragment = char_count < 240 and text.endswith(":")
    practice_steps_preserved = split_reason in {"practice_preserved", "practice_step_split"}

    quality_notes: list[str] = []
    if too_short:
        quality_notes.append("too_short")
    if too_long:
        quality_notes.append("too_long")
    if not has_summary:
        quality_notes.append("missing_summary")
    if possible_practice_split:
        quality_notes.append("possible_practice_split")
    if possible_context_fragment:
        quality_notes.append("possible_context_fragment")
    if not heading_path_present:
        quality_notes.append("missing_heading_path")
    if section_role_hint in {"", "unknown"}:
        quality_notes.append("role_hint_unknown")
    if mixed_intent_risk:
        quality_notes.append("mixed_intent_risk")
    if boundary_confidence < 0.55:
        quality_notes.append("low_boundary_confidence")
    if block.governance.get("chunk_type") == "practice" and not practice_steps_preserved:
        quality_notes.append("practice_steps_maybe_split")

    return {
        "schema_version": "chunking_quality_v1",
        "char_count": int(char_count),
        "approx_token_count": int(approx_token_count),
        "has_heading": has_heading,
        "has_summary": has_summary,
        "possible_practice_split": possible_practice_split,
        "possible_context_fragment": possible_context_fragment,
        "too_short": too_short,
        "too_long": too_long,
        "heading_path_present": heading_path_present,
        "section_role_hint": section_role_hint,
        "boundary_confidence": boundary_confidence,
        "split_reason": split_reason,
        "mixed_intent_risk": mixed_intent_risk,
        "practice_steps_preserved": practice_steps_preserved,
        "role_marker_counts": role_marker_counts,
        "quality_notes": quality_notes,
    }
