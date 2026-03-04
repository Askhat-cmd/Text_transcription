"""Shared formatter for mode-aware output constraints."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResponseFormatter:
    """Apply compact, mode-aware output shaping."""

    mode_char_limits: dict

    def __init__(self, mode_char_limits: dict | None = None) -> None:
        self.mode_char_limits = mode_char_limits or {
            "PRESENCE": 2000,
            "CLARIFICATION": 2000,
            "VALIDATION": 2400,
            "THINKING": 4000,
            "INTERVENTION": 3200,
            "INTEGRATION": 2400,
        }

    @staticmethod
    def _clip(text: str, max_chars: int) -> str:
        if max_chars <= 0 or len(text) <= max_chars:
            return text
        return text[: max(0, max_chars - 3)].rstrip() + "..."

    @staticmethod
    def _normalize(text: str) -> str:
        compact = (text or "").strip()
        while "\n\n\n" in compact:
            compact = compact.replace("\n\n\n", "\n\n")
        return compact

    def format_answer(
        self,
        answer: str,
        *,
        mode: str,
        confidence_level: str,
        max_chars: int | None = None,
    ) -> str:
        """Normalize answer and enforce light mode-driven limits."""
        text = self._normalize(answer)
        normalized_mode = (mode or "PRESENCE").upper()
        confidence = (confidence_level or "medium").lower()

        if normalized_mode == "CLARIFICATION" and "?" not in text:
            text = text.rstrip(".! ")
            text += ". Что в этом для вас сейчас главное?"

        if confidence == "low":
            normalized = text.lstrip()
            if not normalized.lower().startswith("могу ошибаться"):
                text = f"Могу ошибаться, {normalized}"

        char_limit = max_chars or self.mode_char_limits.get(normalized_mode, 900)
        return self._clip(text, char_limit)


def format_mode_aware_response(
    answer: str,
    *,
    mode: str,
    confidence_level: str,
    max_chars: int | None = None,
) -> str:
    """Convenience wrapper for one-off formatting."""
    formatter = ResponseFormatter()
    return formatter.format_answer(
        answer,
        mode=mode,
        confidence_level=confidence_level,
        max_chars=max_chars,
    )
