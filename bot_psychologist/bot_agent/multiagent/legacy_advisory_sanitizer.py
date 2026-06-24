from __future__ import annotations

import json
from typing import Any


LEGACY_ADVISORY_SANITIZER_VERSION = "legacy_advisory_sanitizer_v1"
_SUPPRESSED_COMMAND_TERMS = [
    "MUST DO",
    "MUST NOT",
    "ask_one_specific_question",
    "max_sentences",
    "max_questions",
    "practice_suppression_active",
    "practice_policy=forbidden",
    "response_planner.must_include",
    "response_planner.must_avoid",
    "active_line.next_meaningful_move",
]


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def _append_line(lines: list[str], text: str) -> None:
    cleaned = _clean_text(text)
    if cleaned and cleaned not in lines:
        lines.append(cleaned)


def _safe_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def sanitize_legacy_advisory_for_writer(source_signals: dict) -> dict[str, Any]:
    signals = dict(source_signals or {})
    diagnostic = dict(signals.get("diagnostic_card_summary", {}))
    writer_move = dict(signals.get("writer_move_instructions", {}))
    active_line = dict(signals.get("active_line", {}))
    response_planner = dict(signals.get("response_planner", {}))
    knowledge = dict(signals.get("knowledge_answer_guard", {}))
    knowledge_answer = (
        dict(knowledge.get("knowledge_answer", {}))
        if isinstance(knowledge.get("knowledge_answer"), dict)
        else {}
    )
    latest_turn_constraints = (
        dict(signals.get("latest_turn_constraints_v1", {}))
        if isinstance(signals.get("latest_turn_constraints_v1"), dict)
        else {}
    )
    writer_grounding_visibility = (
        dict(signals.get("writer_grounding_visibility_v1", {}))
        if isinstance(signals.get("writer_grounding_visibility_v1"), dict)
        else {}
    )
    practice_gate = (
        dict(knowledge.get("practice_gate", {}))
        if isinstance(knowledge.get("practice_gate"), dict)
        else {}
    )

    lines: list[str] = []
    _append_line(lines, "Answer the user's latest request first, in a direct and human tone.")

    if _clean_text(active_line.get("active_line")):
        _append_line(lines, f"Current line: {_clean_text(active_line.get('active_line'))}.")
    elif _clean_text(active_line.get("user_intent")):
        _append_line(lines, f"Current user vector: {_clean_text(active_line.get('user_intent'))}.")

    if _clean_text(diagnostic.get("current_need")):
        _append_line(lines, f"Primary need to cover: {_clean_text(diagnostic.get('current_need'))}.")

    if bool(knowledge_answer.get("should_answer_directly", False)):
        concept = _clean_text(knowledge_answer.get("concept"))
        if concept:
            _append_line(lines, f"Answer the known concept directly: {concept}.")
        else:
            _append_line(lines, "Answer directly; do not bounce the user back into clarifying a known term.")

    if _clean_text(response_planner.get("target_micro_shift")):
        _append_line(lines, f"Useful meaning shift: {_clean_text(response_planner.get('target_micro_shift'))}.")
    elif _clean_text(diagnostic.get("suggested_writer_move")):
        _append_line(lines, f"Helpful move: {_clean_text(diagnostic.get('suggested_writer_move'))}.")
    elif _clean_text(writer_move.get("move")):
        _append_line(lines, f"Helpful move: {_clean_text(writer_move.get('move'))}.")

    if bool(active_line.get("should_continue_line", True)):
        _append_line(lines, "Keep the same conversation line; do not open a noisy side branch.")

    if writer_grounding_visibility:
        if bool(writer_grounding_visibility.get("kb_visible_to_writer", False)):
            _append_line(lines, "Grounding is optional support here: use it only if it helps, without sounding like an internal recital.")
        else:
            _append_line(lines, "Grounding is not needed in the visible answer here: answer in your own words and do not dump internal material.")

    writer_visible_summary = "\n".join(lines[:5])
    lower_summary = writer_visible_summary.lower()
    forbidden_tokens = (
        "must",
        "forbidden",
        "do_not",
        "ask_one_specific_question",
        "practice_suppression_active",
        "max_questions",
        "max_sentences",
    )
    for token in forbidden_tokens:
        if token in lower_summary:
            raise ValueError(f"sanitized advisory summary leaked forbidden token: {token}")

    practice_suppressed = (
        bool(latest_turn_constraints.get("no_practice", False))
        or bool(active_line.get("practice_suppression_active", False))
        or not bool(practice_gate.get("practice_allowed", True))
    )
    if practice_suppressed:
        practice_note = (
            "Do not offer an exercise, drill, breathing routine, or homework here. "
            "Answer normally with explanation, reflection, example, or continuation of the thought."
        )
        writer_visible_practice_instruction = "no_exercise_but_answer_normally"
    else:
        practice_note = (
            "Practice is optional and should appear only if it clearly helps the current user request."
        )
        writer_visible_practice_instruction = "practice_allowed_if_relevant"

    directive_writer_payload = {
        "version": str(
            signals.get("final_answer_directive_version", "final_answer_directive_v1")
            or "final_answer_directive_v1"
        ),
        "roles": {
            "diagnostic_center": str(
                signals.get("final_answer_diagnostic_center_role", "guided_legacy")
                or "guided_legacy"
            ),
            "planner": str(
                signals.get("final_answer_planner_role", "guided_legacy")
                or "guided_legacy"
            ),
            "active_line": str(
                signals.get("final_answer_active_line_role", "guided_legacy")
                or "guided_legacy"
            ),
            "diagnostic_card": str(
                signals.get("final_answer_diagnostic_card_role", "guided_legacy")
                or "guided_legacy"
            ),
        },
        "answer_obligation": _clean_text(signals.get("answer_obligation", "")) or "continue_line_with_focus",
        "must_answer": _clean_text(signals.get("must_answer", "")) or "answer_user_question_directly",
        "answer_shape": _clean_text(signals.get("answer_shape", "")) or "compact_direct",
        "depth": _clean_text(signals.get("depth", "")) or "medium",
        "style": _clean_text(signals.get("style", "")) or "human_conversational",
        "question_policy": _clean_text(signals.get("question_policy", "")) or "optional",
        "practice_instruction": writer_visible_practice_instruction,
        "writer_autonomy": _clean_text(signals.get("writer_autonomy", "")) or "guided",
        "latest_turn_constraints": {
            "no_practice": bool(latest_turn_constraints.get("no_practice", False)),
            "no_breathing_only": bool(latest_turn_constraints.get("no_breathing_only", False)),
            "simplify": bool(latest_turn_constraints.get("simplify", False)),
            "long_term_perspective": bool(latest_turn_constraints.get("long_term_perspective", False)),
            "no_internal_db": bool(latest_turn_constraints.get("no_internal_db", False)),
        },
        "grounding_authority": {
            "safety_and_latest_user_request": "mandatory",
            "conversation_context": "supportive",
            "kb_semantic_cards_diagnostic_hints": "optional_grounding",
            "never_change_user_request": True,
            "do_not_sound_like_internal_recital": True,
        },
        "grounding_visibility": {
            "kb_visible_to_writer": bool(writer_grounding_visibility.get("kb_visible_to_writer", False)),
            "semantic_cards_visible_to_writer": bool(
                writer_grounding_visibility.get("semantic_cards_visible_to_writer", False)
            ),
            "reason": _clean_text(writer_grounding_visibility.get("reason", "")) or "unknown",
            "direct_kb_question": bool(writer_grounding_visibility.get("direct_kb_question", False)),
            "safety_grounding_allowed": bool(
                writer_grounding_visibility.get("safety_grounding_allowed", False)
            ),
            "no_internal_db": bool(writer_grounding_visibility.get("no_internal_db", False)),
            "trace_only_grounding_available": bool(
                writer_grounding_visibility.get("trace_only_grounding_available", False)
            ),
        },
    }
    gate_feedback = signals.get("acceptance_gate_feedback")
    if isinstance(gate_feedback, dict) and gate_feedback:
        directive_writer_payload["acceptance_gate_feedback"] = {
            "version": _clean_text(gate_feedback.get("version", "")) or "final_answer_acceptance_gate_v1",
            "failed_checks": [
                _clean_text(item)
                for item in list(gate_feedback.get("failed_checks", []) or [])
                if _clean_text(item)
            ][:8],
            "instruction": _clean_text(
                gate_feedback.get(
                    "instruction",
                    "Rewrite the answer so it directly addresses the user's current question and avoids stale generic phrasing.",
                )
            ),
        }

    return {
        "version": LEGACY_ADVISORY_SANITIZER_VERSION,
        "writer_visible_summary": writer_visible_summary,
        "writer_visible_practice_instruction": writer_visible_practice_instruction,
        "writer_visible_practice_note": practice_note,
        "suppressed_command_terms": list(_SUPPRESSED_COMMAND_TERMS),
        "raw_legacy_visible_to_writer": False,
        "practice_rewrite_applied": practice_suppressed,
        "writer_visible_final_answer_directive_json": _safe_json(directive_writer_payload),
    }


__all__ = [
    "LEGACY_ADVISORY_SANITIZER_VERSION",
    "sanitize_legacy_advisory_for_writer",
]
