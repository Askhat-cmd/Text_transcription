"""Static fallback/helper functions extracted from writer_agent.py."""

from __future__ import annotations

import re
from typing import Any

from ..contracts.writer_contract import WriterContract
from .writer_agent_constants import _contains_any


def _build_gentle_close_reply() -> str:
    return "Пожалуйста. Береги себя."


def _build_no_practice_fallback_text(user_message: str) -> str:
    lowered_user = str(user_message or "").lower()
    if _contains_any(lowered_user, ("почему", "объясни", "механизм", "как это работает", "разбор", "что со мной")):
        return (
            "Похоже, реакция включается автоматически: внутреннее напряжение поднимается быстрее, "
            "чем ты успеваешь это осмыслить, и система уводит тебя в привычный способ защиты. "
            "Это не про слабость, а про попытку быстро снизить перегруз."
        )
    return "Я рядом. Сейчас не нужно ничего делать через силу. Можно остаться в разговоре без практики и лишней нагрузки."


def _strip_optional_followup_invitation(text: str) -> str:
    return re.sub(
        r"(?:\n{2,}|[.!?]\s+)(?:Если хочется|Если захочешь|Если хочешь|Если хотите|Хочешь|Хотите|Могу дальше|Могу сразу|Если нужно).*$",
        "",
        text.strip(),
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()


def _detect_language(text: str) -> str:
    cyrillic = sum(1 for ch in text if ("а" <= ch.lower() <= "я") or ch.lower() == "ё")
    return "ru" if cyrillic > len(text) * 0.2 else "en"


def _format_hits(hits: list[str]) -> str:
    if not hits:
        return "нет релевантных знаний"
    return "\n---\n".join(f"- {h[:300]}" for h in hits[:2])


def _format_diagnostic_summary(summary: Any) -> str:
    if not isinstance(summary, dict) or not summary.get("present"):
        return "нет"
    return (
        f"situation_label={summary.get('situation_label')}; "
        f"current_need={summary.get('current_need')}; "
        f"suggested_writer_move={summary.get('suggested_writer_move')}; "
        f"confidence={summary.get('confidence')}"
    )


def _static_fallback(contract: WriterContract) -> str:
    response_planner = (
        dict(contract.response_planner) if isinstance(getattr(contract, "response_planner", None), dict) else {}
    )
    planner_next_move = str(response_planner.get("next_move", "") or "")
    planner_answer_shape = str(response_planner.get("answer_shape", "") or "")
    planner_question_policy = str(response_planner.get("question_policy", "") or "")
    planner_practice_policy = str(response_planner.get("practice_policy", "") or "")
    user_message = str(getattr(contract, "user_message", "") or "")
    lowered_user = user_message.lower()
    dialogue_policy = (
        dict(contract.dialogue_policy) if isinstance(getattr(contract, "dialogue_policy", None), dict) else {}
    )
    final_answer_directive = (
        dict(dialogue_policy.get("final_answer_directive", {}))
        if isinstance(dialogue_policy.get("final_answer_directive"), dict)
        else {}
    )
    writer_contact_mode = str(
        dialogue_policy.get("final_answer_writer_contact_mode")
        or final_answer_directive.get("writer_contact_mode", "")
        or ""
    )
    latest_turn_constraints = (
        dict(dialogue_policy.get("latest_turn_constraints_v1", {}))
        if isinstance(dialogue_policy.get("latest_turn_constraints_v1"), dict)
        else {}
    )
    user_requests_no_practice = _contains_any(
        lowered_user,
        (
            "без практик",
            "не давай практик",
            "не хочу практик",
            "без упражн",
            "просто объясни",
        ),
    )
    canned_step_disallowed = bool(
        planner_practice_policy == "forbidden"
        or bool(latest_turn_constraints.get("no_practice", False))
        or user_requests_no_practice
        or writer_contact_mode == "free_writer_contact"
    )

    if planner_next_move == "stabilize_safety" or planner_answer_shape == "safety_grounding":
        return "Я рядом. Сейчас важнее чуть стабилизироваться и снизить внутреннюю перегрузку. Без разбора, только опора здесь-и-сейчас."
    if planner_next_move == "give_short_support" or planner_answer_shape == "short_support":
        return "Я рядом. Сейчас не нужно ничего разбирать. Можно просто немного снизить внутреннее давление."
    if planner_next_move == "give_direct_step" or planner_answer_shape == "one_step":
        if canned_step_disallowed:
            return _build_no_practice_fallback_text(user_message)
        return "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."
    if planner_next_move == "close_gently" or planner_answer_shape == "gentle_close":
        return _build_gentle_close_reply()
    if planner_next_move == "clarify_one_point" or planner_answer_shape == "one_question":
        return "Если выбрать один узел прямо сейчас, что больше всего сжимает тебя в этой ситуации?"
    if planner_question_policy == "none":
        if planner_practice_policy == "forbidden":
            return "Я рядом. Давай продолжим спокойно, без лишней нагрузки."
        return "Я рядом. Продолжим спокойно."

    mode = contract.thread_state.response_mode
    if mode == "safe_override":
        return "Я здесь. Ты не один."
    if mode == "validate":
        return "Я слышу тебя. Я рядом."
    if mode == "regulate":
        return "Сделай медленный вдох. Я рядом."
    return "Я слышу тебя."


def _normalize_name(raw_name: str) -> str | None:
    name = (raw_name or "").strip(" .,:;!?\"'()[]{}")
    if len(name) < 2 or len(name) > 31:
        return None
    return name[0].upper() + name[1:]
