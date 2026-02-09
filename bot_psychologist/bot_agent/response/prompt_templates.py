"""Mode-specific prompt directives."""

from __future__ import annotations

from typing import Iterable, List


MODE_BASE_DIRECTIVES = {
    "PRESENCE": "Будь рядом и стабилизируй контакт. Коротко отзеркаль суть без анализа.",
    "CLARIFICATION": "Уточни запрос пользователя. Задай 1 точный проясняющий вопрос.",
    "VALIDATION": "Признай переживание и нормализуй реакцию. Не давай жёстких указаний.",
    "THINKING": "Замедли темп и помоги структурировать мысль шаг за шагом.",
    "INTERVENTION": "Дай один практичный следующий шаг без перегруза вариантами.",
    "INTEGRATION": "Закрепи инсайт и не углубляй дальше.",
}


def _confidence_behavior(confidence_level: str) -> str:
    level = (confidence_level or "medium").lower()
    if level == "low":
        return "Уверенность низкая: не утверждай категорично, уточняй и предлагай мягко."
    if level == "high":
        return "Уверенность высокая: можно дать конкретный и ясный фокус."
    return "Уверенность средняя: сохраняй баланс между ясностью и осторожностью."


def _format_forbid(forbid: Iterable[str] | None) -> str:
    items: List[str] = [str(x).strip() for x in (forbid or []) if str(x).strip()]
    if not items:
        return ""
    return "Запрещено: " + ", ".join(items) + "."


def build_mode_prompt(mode: str, confidence_level: str, forbid: Iterable[str] | None = None) -> str:
    """Build compact mode directive for LLM system prompt."""
    normalized_mode = (mode or "PRESENCE").upper()
    base = MODE_BASE_DIRECTIVES.get(normalized_mode, MODE_BASE_DIRECTIVES["PRESENCE"])
    confidence = _confidence_behavior(confidence_level)
    forbid_line = _format_forbid(forbid)

    lines = [
        f"РЕЖИМ: {normalized_mode}",
        base,
        confidence,
    ]
    if forbid_line:
        lines.append(forbid_line)
    lines.append("Ответ держи в простом языке и без избыточной длины.")
    return "\n".join(lines)
