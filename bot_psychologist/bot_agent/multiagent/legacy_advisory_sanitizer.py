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
    practice_gate = (
        dict(knowledge.get("practice_gate", {}))
        if isinstance(knowledge.get("practice_gate"), dict)
        else {}
    )

    lines: list[str] = []
    _append_line(lines, "Пользователь продолжает текущую линию разговора; ответ лучше держать живым, спокойным и по сути.")

    if _clean_text(active_line.get("active_line")):
        _append_line(lines, f"Текущий смысловой фокус: {_clean_text(active_line.get('active_line'))}.")
    elif _clean_text(active_line.get("user_intent")):
        _append_line(lines, f"Пользовательский вектор сейчас: {_clean_text(active_line.get('user_intent'))}.")

    if _clean_text(diagnostic.get("current_need")):
        _append_line(lines, f"Полезно ответить на актуальную потребность: {_clean_text(diagnostic.get('current_need'))}.")

    if _clean_text(diagnostic.get("suggested_writer_move")):
        _append_line(
            lines,
            f"Можно опереться на такой ход ответа: {_clean_text(diagnostic.get('suggested_writer_move'))}.",
        )
    elif _clean_text(writer_move.get("move")):
        _append_line(lines, f"Уместный ход ответа: {_clean_text(writer_move.get('move'))}.")

    if bool(knowledge_answer.get("should_answer_directly", False)):
        concept = _clean_text(knowledge_answer.get("concept"))
        if concept:
            _append_line(lines, f"Лучше отвечать прямо по известному понятию: {concept}.")
        else:
            _append_line(lines, "Лучше отвечать прямо и не уводить пользователя в лишние уточнения.")

    if _clean_text(response_planner.get("target_micro_shift")):
        _append_line(
            lines,
            f"Один полезный смысловой сдвиг: {_clean_text(response_planner.get('target_micro_shift'))}.",
        )

    if _clean_text(response_planner.get("answer_shape")):
        _append_line(
            lines,
            f"Формат можно держать таким: {_clean_text(response_planner.get('answer_shape'))}.",
        )

    if bool(active_line.get("should_continue_line", True)):
        _append_line(lines, "Лучше продолжать уже начатую тему, а не начинать новую ветку.")

    practice_suppressed = bool(active_line.get("practice_suppression_active", False)) or not bool(
        practice_gate.get("practice_allowed", True)
    )
    if practice_suppressed:
        practice_note = (
            "Если практика сейчас не запрошена или неуместна, не предлагай упражнение, технику или пошаговую практику. "
            "Вместо этого ответь нормально: объяснением, примером, отражением или продолжением мысли."
        )
        writer_visible_practice_instruction = "no_exercise_but_answer_normally"
    else:
        practice_note = "Если практика действительно помогает вопросу пользователя, её можно предлагать только уместно и без навязывания."
        writer_visible_practice_instruction = "practice_allowed_if_relevant"
    _append_line(lines, practice_note)

    writer_visible_summary = "\n".join(lines)
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

    directive_writer_payload = {
        "version": str(signals.get("final_answer_directive_version", "final_answer_directive_v1") or "final_answer_directive_v1"),
        "roles": {
            "diagnostic_center": str(signals.get("final_answer_diagnostic_center_role", "guided_legacy") or "guided_legacy"),
            "planner": str(signals.get("final_answer_planner_role", "guided_legacy") or "guided_legacy"),
            "active_line": str(signals.get("final_answer_active_line_role", "guided_legacy") or "guided_legacy"),
            "diagnostic_card": str(signals.get("final_answer_diagnostic_card_role", "guided_legacy") or "guided_legacy"),
        },
        "answer_obligation": _clean_text(signals.get("answer_obligation", "")) or "continue_line_with_focus",
        "must_answer": _clean_text(signals.get("must_answer", "")) or "answer_user_question_directly",
        "answer_shape": _clean_text(signals.get("answer_shape", "")) or "compact_direct",
        "depth": _clean_text(signals.get("depth", "")) or "medium",
        "style": _clean_text(signals.get("style", "")) or "human_conversational",
        "question_policy": _clean_text(signals.get("question_policy", "")) or "optional",
        "practice_instruction": writer_visible_practice_instruction,
        "writer_autonomy": _clean_text(signals.get("writer_autonomy", "")) or "guided",
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
