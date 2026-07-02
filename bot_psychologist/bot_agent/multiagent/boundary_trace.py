from __future__ import annotations

from typing import Any


BOUNDARY_TRACE_VERSION = "boundary_trace_v1"
_BOUNDARY_FLAG_NAMES = ("no_internal_db", "no_practice", "no_breathing_only", "simplify")
_INTERNAL_LANGUAGE_MARKERS = (
    "semantic card",
    "semantic cards",
    "writer kb payload",
    "runtime truth trace",
    "internal db",
    "chunk",
    "chunks",
    "trace",
)
_PRACTICE_LANGUAGE_MARKERS = (
    "practice",
    "exercise",
    "homework",
    "step 1",
    "step 2",
    "inhale",
    "exhale",
)


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _constraint_state(latest_turn_constraints: dict[str, Any] | None) -> dict[str, bool]:
    constraints = _safe_dict(latest_turn_constraints)
    return {name: bool(constraints.get(name, False)) for name in _BOUNDARY_FLAG_NAMES}


def _bool_source(source_hint: str, active: bool) -> str:
    if not active:
        return "not_detected"
    if source_hint == "latest_user_turn_explicit_text":
        return "latest_user_request"
    return "final_answer_directive"


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in markers)


def build_boundary_trace_v1(
    *,
    latest_turn_constraints: dict[str, Any] | None,
    writer_grounding_visibility: dict[str, Any] | None = None,
    writer_kb_payload_trace: dict[str, Any] | None = None,
    final_answer_directive: dict[str, Any] | None = None,
    runtime_truth_trace: dict[str, Any] | None = None,
    final_answer: str | None = None,
) -> dict[str, Any]:
    constraints = _constraint_state(latest_turn_constraints)
    raw_constraints = _safe_dict(latest_turn_constraints)
    grounding = _safe_dict(writer_grounding_visibility)
    payload_trace = _safe_dict(writer_kb_payload_trace)
    directive = _safe_dict(final_answer_directive)
    runtime_truth = _safe_dict(runtime_truth_trace)

    writer_payload_count = _safe_int(
        runtime_truth.get("writer_visible_payload_count"),
        _safe_int(payload_trace.get("payload_chunk_count"), 0),
    )
    semantic_cards_visible = bool(grounding.get("semantic_cards_visible_to_writer", False))
    kb_visible = bool(grounding.get("kb_visible_to_writer", False))
    grounding_reason = str(
        runtime_truth.get("grounding_visibility_reason")
        or grounding.get("reason", "")
        or ""
    )
    payload_reason = str(
        runtime_truth.get("payload_decision_reason")
        or payload_trace.get("status", "")
        or ""
    )
    practice_policy = str(directive.get("practice_policy", "") or "")

    suppression_reasons: list[str] = []
    for reason in (grounding_reason, payload_reason, practice_policy):
        if reason and reason not in suppression_reasons:
            suppression_reasons.append(reason)

    no_internal_db_suppressed = constraints["no_internal_db"] and not kb_visible and writer_payload_count == 0
    semantic_suppressed = constraints["no_internal_db"] and not semantic_cards_visible
    no_practice_hardened = constraints["no_practice"] and practice_policy.startswith("forbidden")

    public_violation_detected = False
    if isinstance(final_answer, str) and final_answer.strip():
        if constraints["no_internal_db"] and _contains_any(final_answer, _INTERNAL_LANGUAGE_MARKERS):
            public_violation_detected = True
        if constraints["no_practice"] and _contains_any(final_answer, _PRACTICE_LANGUAGE_MARKERS):
            public_violation_detected = True

    source_hint = str(raw_constraints.get("source", "") or "")
    boundary_flags = [name for name, active in constraints.items() if active]

    return {
        "version": BOUNDARY_TRACE_VERSION,
        "latest_turn_constraints": constraints,
        "boundary_flags": boundary_flags,
        "boundary_sources": {
            "no_internal_db": _bool_source(source_hint, constraints["no_internal_db"]),
            "no_practice": _bool_source(source_hint, constraints["no_practice"]),
        },
        "applied_suppressions": {
            "writer_kb_payload_suppressed": no_internal_db_suppressed,
            "semantic_cards_writer_visible_suppressed": semantic_suppressed,
            "practice_suggestion_suppressed": no_practice_hardened,
        },
        "suppression_reasons": suppression_reasons,
        "writer_directive_ack": {
            "no_internal_db": constraints["no_internal_db"] and grounding_reason == "latest_turn_no_internal_db",
            "no_practice": no_practice_hardened,
        },
        "writer_payload_count": writer_payload_count,
        "kb_visible_to_writer": kb_visible,
        "semantic_cards_visible_to_writer": semantic_cards_visible,
        "grounding_reason": grounding_reason,
        "practice_policy": practice_policy,
        "public_violation_detected": public_violation_detected,
    }


__all__ = [
    "BOUNDARY_TRACE_VERSION",
    "build_boundary_trace_v1",
]
