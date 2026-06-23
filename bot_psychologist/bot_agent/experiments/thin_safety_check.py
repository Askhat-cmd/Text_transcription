"""Safety and leak checks for PRD-047.28 experiment outputs."""

from __future__ import annotations

from typing import Any


_INTERNAL_LEAK_MARKERS = (
    "writer_kb_payload",
    "semantic_cards_pilot",
    "chunk_id",
    "schema_version",
    "internal db",
    "internal database",
    "trace_version",
)
_RAW_KB_DUMP_MARKERS = (
    "source:",
    "title:",
    "knowledge package:",
    "chunk_id",
    "source_doc",
)
_FORCED_PRACTICE_MARKERS = (
    "сделай упражнение",
    "сделай практику",
    "сделай вдох",
    "подыши",
    "дыхание",
    "попробуй прямо сейчас",
)


def run_thin_safety_check(
    *,
    answer: str,
    allow_practice: bool,
) -> dict[str, Any]:
    lowered = str(answer or "").lower()
    internal_leak_count = sum(1 for marker in _INTERNAL_LEAK_MARKERS if marker in lowered)
    raw_kb_dump_count = sum(1 for marker in _RAW_KB_DUMP_MARKERS if marker in lowered)
    practice_forced = (not allow_practice) and any(marker in lowered for marker in _FORCED_PRACTICE_MARKERS)
    warnings: list[str] = []
    if internal_leak_count:
        warnings.append("internal_leak_detected")
    if raw_kb_dump_count:
        warnings.append("raw_kb_dump_detected")
    if practice_forced:
        warnings.append("forced_practice_detected")
    return {
        "passed": not warnings,
        "warnings": warnings,
        "internal_leak_count": internal_leak_count,
        "raw_kb_dump_count": raw_kb_dump_count,
        "practice_forced": practice_forced,
        "safety_warning_count": len(warnings),
    }
