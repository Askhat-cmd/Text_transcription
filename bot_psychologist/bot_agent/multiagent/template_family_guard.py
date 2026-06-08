"""Template-family leakage detector for final-answer quarantine."""

from __future__ import annotations

import re
from typing import Any


TEMPLATE_FAMILY_GUARD_VERSION = "template_family_guard_v1"

TEMPLATE_EXACT_MARKERS = {
    "single_mechanism_reduction": "в твоем описании важно не свести все к одному общему механизму",
    "facts_vs_conclusion": "сначала отдели факты от вывода",
    "central_belief": "затем найди центральное убеждение",
    "belief_check": "после этого проверь",
    "unraveling_practical_sense": "практический смысл распутывания",
}

_FUZZY_MARKER_SETS = {
    "numbered_belief_skeleton": (
        "факты",
        "вывод",
        "центральное убеждение",
        "проверь",
        "практический смысл",
    ),
    "single_mechanism_skeleton": (
        "не свести",
        "одному общему механизму",
        "клубок убеждений",
        "распутывается",
    ),
}

_NUMBERED_LINE_RE = re.compile(r"(?m)^\s*(?:[1-4][.)])\s+\S")


def _normalize(text: str) -> str:
    lowered = str(text or "").lower().replace("ё", "е")
    return re.sub(r"\s+", " ", lowered).strip()


def detect_template_family_leakage(text: str) -> dict[str, Any]:
    """Return a compact guard payload; marker constants are detector-only."""

    normalized = _normalize(text)
    markers: list[str] = []
    if normalized:
        for marker_id, phrase in TEMPLATE_EXACT_MARKERS.items():
            if _normalize(phrase) in normalized:
                markers.append(marker_id)
        for marker_id, tokens in _FUZZY_MARKER_SETS.items():
            if all(token in normalized for token in tokens):
                markers.append(marker_id)

    numbered_skeleton = bool(_NUMBERED_LINE_RE.search(str(text or "")))
    if numbered_skeleton and {"facts_vs_conclusion", "central_belief"} & set(markers):
        markers.append("numbered_answer_skeleton")

    unique_markers = sorted(set(markers))
    leak_detected = bool(unique_markers)
    return {
        "version": TEMPLATE_FAMILY_GUARD_VERSION,
        "checked": True,
        "leak_detected": leak_detected,
        "markers": unique_markers,
        "action": "retry_or_quarantine" if leak_detected else "passed",
        "contamination_quarantined": leak_detected,
        "user_facing_replacement_created": False,
    }


def build_memory_contamination_guard_result(
    *, final_answer_acceptance_gate: dict[str, Any] | None
) -> dict[str, Any]:
    gate = dict(final_answer_acceptance_gate or {})
    template_guard = dict(gate.get("template_family_guard") or {})
    contaminated = bool(
        gate.get("must_quarantine_answer", False)
        or template_guard.get("leak_detected", False)
    )
    return {
        "version": "memory_contamination_guard_v1",
        "contaminated": contaminated,
        "healthy_memory_allowed": bool(gate.get("can_save_as_healthy_context", False)) and not contaminated,
        "summary_source_allowed": bool(gate.get("can_use_as_summary_source", False)) and not contaminated,
        "last_assistant_offer_allowed": bool(gate.get("can_save_last_assistant_offer", False)) and not contaminated,
        "quarantine_reason": str(gate.get("quarantine_reason", "") or ""),
        "template_family_guard": template_guard,
    }


__all__ = [
    "TEMPLATE_FAMILY_GUARD_VERSION",
    "TEMPLATE_EXACT_MARKERS",
    "build_memory_contamination_guard_result",
    "detect_template_family_leakage",
]
