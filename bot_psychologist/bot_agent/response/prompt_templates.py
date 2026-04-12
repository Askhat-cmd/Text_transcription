"""Mode-specific prompt directives."""

from __future__ import annotations

from typing import Iterable, List


MODE_BASE_DIRECTIVES = {
    "PRESENCE": (
        "Сначала отрази состояние пользователя, затем раскрой контекст и смысл. "
        "Дай полноценный ответ минимум в 3-5 предложениях; вопрос в конце только если он реально помогает."
    ),
    "CLARIFICATION": (
        "Уточни запрос, но не подменяй ответ одним вопросом. "
        "Сначала дай ясное объяснение, затем при необходимости задай один проясняющий вопрос."
    ),
    "VALIDATION": (
        "Признай переживание и нормализуй реакцию. "
        "Добавь короткое объяснение механизма и один посильный следующий шаг."
    ),
    "THINKING": (
        "Помоги структурировать мысль глубоко и последовательно. "
        "Раскрывай причинно-следственные связи, а не ограничивайся общими фразами."
    ),
    "INTERVENTION": (
        "Дай конкретный следующий шаг с понятным фокусом выполнения. "
        "Объясни зачем этот шаг и как понять, что он сработал."
    ),
    "INTEGRATION": (
        "Закрепи инсайт и переведи его в устойчивое действие. "
        "Сохрани практическую опору без искусственного сжатия."
    ),
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
    lines.append("Ответ держи в простом языке и с полной смысловой достаточностью; не сокращай искусственно.")
    return "\n".join(lines)
