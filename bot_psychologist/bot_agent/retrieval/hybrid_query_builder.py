"""Hybrid query builder where user question remains the anchor."""

from __future__ import annotations

from typing import Dict, Optional, Union

from ..working_state import WorkingState


class HybridQueryBuilder:
    """
    Build a retrieval query from multiple memory layers.

    Core rule: current user question must stay the anchor.
    """

    def __init__(
        self,
        max_chars: int = 2000,
        short_term_chars: int = 700,
        summary_chars: int = 500,
    ) -> None:
        self.max_chars = max_chars
        self.short_term_chars = short_term_chars
        self.summary_chars = summary_chars

    @staticmethod
    def _clean(text: str) -> str:
        return " ".join((text or "").strip().split())

    def _clip(self, text: str, limit: int) -> str:
        cleaned = self._clean(text)
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: max(0, limit - 3)] + "..."

    def _format_working_state(
        self,
        working_state: Optional[Union[WorkingState, Dict]],
    ) -> str:
        if working_state is None:
            return ""

        if isinstance(working_state, WorkingState):
            data = working_state.to_dict()
        else:
            data = dict(working_state)

        fields = [
            ("dominant_state", "состояние"),
            ("emotion", "эмоция"),
            ("defense", "защита"),
            ("phase", "фаза"),
            ("direction", "направление"),
            ("confidence_level", "уверенность"),
        ]
        parts = []
        for key, label in fields:
            value = data.get(key)
            if value:
                parts.append(f"{label}: {value}")
        return "; ".join(parts)

    def build_query(
        self,
        current_question: str,
        conversation_summary: str = "",
        working_state: Optional[Union[WorkingState, Dict]] = None,
        short_term_context: str = "",
    ) -> str:
        question = self._clean(current_question)
        if not question:
            raise ValueError("current_question must not be empty")

        summary = self._clip(conversation_summary, self.summary_chars)
        short_term = self._clip(short_term_context, self.short_term_chars)
        working_state_text = self._format_working_state(working_state)

        parts = [f"ВОПРОС-ЯКОРЬ: {question}"]

        if working_state_text:
            parts.append(f"РАБОЧЕЕ СОСТОЯНИЕ: {working_state_text}")
        if summary:
            parts.append(f"РЕЗЮМЕ ДИАЛОГА: {summary}")
        if short_term:
            parts.append(f"КОРОТКИЙ КОНТЕКСТ: {short_term}")

        # Repeat the question at the end to preserve anchor dominance.
        parts.append(f"СНОВА ВОПРОС-ЯКОРЬ: {question}")

        query = "\n".join(parts)
        if len(query) <= self.max_chars:
            return query

        # Clip middle while preserving anchor lines at top and bottom.
        head = parts[0]
        tail = parts[-1]
        middle = "\n".join(parts[1:-1])

        reserve = len(head) + len(tail) + 2
        allowed_middle = max(0, self.max_chars - reserve)
        middle = self._clip(middle, allowed_middle)

        if middle:
            return "\n".join([head, middle, tail])
        return "\n".join([head, tail])
