"""Compact top-level runtime trace summary for pilot inspection."""

from __future__ import annotations

from typing import Any

from .latest_turn_constraints import active_latest_turn_constraint_names


RUNTIME_TRACE_SUMMARY_VERSION = "runtime_trace_summary_v1"


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _directive_mode(
    *,
    final_answer_directive: dict[str, Any],
    latest_turn_constraints: dict[str, Any],
) -> str:
    active_constraints = set(active_latest_turn_constraint_names(latest_turn_constraints))
    if "no_practice" in active_constraints:
        return "answer_directly_without_practice"
    if "no_internal_db" in active_constraints:
        return "answer_without_internal_db_grounding"
    if "simplify" in active_constraints:
        return "simplified_direct_answer"
    if "long_term_perspective" in active_constraints:
        return "long_term_frame_first"
    if "no_breathing_only" in active_constraints:
        return "answer_with_non_breathing_alternatives"
    answer_shape = str(final_answer_directive.get("answer_shape", "") or "")
    answer_obligation = str(final_answer_directive.get("answer_obligation", "") or "")
    return answer_shape or answer_obligation or "standard_current_pipeline"


def build_runtime_trace_summary_v1(
    *,
    entrypoint: str,
    final_answer_directive: dict[str, Any] | None,
    writer_debug: dict[str, Any] | None,
    overlay_shadow: dict[str, Any] | None,
) -> dict[str, Any]:
    directive = _safe_dict(final_answer_directive)
    writer = _safe_dict(writer_debug)
    overlay = _safe_dict(overlay_shadow)
    latest_turn_constraints = _safe_dict(directive.get("latest_turn_constraints_v1"))
    active_constraints = active_latest_turn_constraint_names(latest_turn_constraints)
    writer_kb_payload_trace = _safe_dict(writer.get("writer_kb_payload_trace"))
    semantic_cards_pilot = _safe_dict(writer.get("semantic_cards_pilot"))
    writer_grounding_visibility = _safe_dict(writer.get("writer_grounding_visibility_v1"))
    if writer_grounding_visibility:
        kb_visible_to_writer = bool(writer_grounding_visibility.get("kb_visible_to_writer", False))
        semantic_cards_visible_to_writer = bool(
            writer_grounding_visibility.get("semantic_cards_visible_to_writer", False)
        )
    else:
        kb_visible_to_writer = int(writer_kb_payload_trace.get("payload_chunk_count", 0) or 0) > 0
        semantic_cards_visible_to_writer = bool(
            semantic_cards_pilot.get("writer_payload_enriched", False)
            or int(semantic_cards_pilot.get("selected_card_count", 0) or 0) > 0
        )
    overlay_apply_detected = bool(
        overlay.get("used_for_writer", False)
        or overlay.get("used_for_retrieval_execution", False)
        or overlay.get("used_for_final_answer", False)
    )
    warnings: list[str] = []
    if latest_turn_constraints.get("no_internal_db") and (
        kb_visible_to_writer or semantic_cards_visible_to_writer
    ):
        warnings.append("no_internal_db_visible_payload_leak")
    if writer_grounding_visibility and not bool(writer_grounding_visibility.get("kb_visible_to_writer", True)):
        if int(writer_kb_payload_trace.get("payload_chunk_count", 0) or 0) > 0:
            warnings.append("writer_grounding_visibility_payload_mismatch")
    if writer_grounding_visibility and not bool(
        writer_grounding_visibility.get("semantic_cards_visible_to_writer", True)
    ):
        if bool(semantic_cards_pilot.get("writer_payload_enriched", False)):
            warnings.append("writer_grounding_visibility_semantic_mismatch")
    if latest_turn_constraints.get("no_practice") and not str(
        directive.get("practice_policy", "")
    ).startswith("forbidden"):
        warnings.append("no_practice_constraint_not_hardened")
    if latest_turn_constraints.get("simplify") and str(directive.get("depth", "") or "") != "short":
        warnings.append("simplify_constraint_not_short")
    if overlay_apply_detected:
        warnings.append("overlay_apply_detected")
    explicit_practice_request = bool(
        writer_grounding_visibility.get("explicit_practice_request", False)
        or str(directive.get("answer_obligation", "") or "") == "provide_one_bounded_practice"
    )
    practice_request_runtime_note = ""
    if explicit_practice_request:
        practice_request_runtime_note = (
            "Detected explicit practice request. Forced contextual practice answer. "
            "KB remains optional/narrow."
            if str(writer_grounding_visibility.get("reason", "") or "") == "explicit_practice_request_narrow_grounding"
            else "Detected explicit practice request. Forced contextual practice answer."
        )

    return {
        "version": RUNTIME_TRACE_SUMMARY_VERSION,
        "entrypoint": str(entrypoint or "multiagent_adapter"),
        "latest_turn_constraints": active_constraints,
        "latest_turn_constraints_v1": latest_turn_constraints,
        "writer_grounding_visibility_v1": writer_grounding_visibility,
        "kb_visible_to_writer": kb_visible_to_writer,
        "semantic_cards_visible_to_writer": semantic_cards_visible_to_writer,
        "overlay_apply_detected": overlay_apply_detected,
        "final_directive_mode": _directive_mode(
            final_answer_directive=directive,
            latest_turn_constraints=latest_turn_constraints,
        ),
        "explicit_practice_request": explicit_practice_request,
        "practice_request_runtime_note": practice_request_runtime_note,
        "practice_blocked_by_user_request": bool(latest_turn_constraints.get("no_practice", False)),
        "warnings": warnings,
        "full_trace_available": True,
    }


__all__ = [
    "RUNTIME_TRACE_SUMMARY_VERSION",
    "build_runtime_trace_summary_v1",
]
