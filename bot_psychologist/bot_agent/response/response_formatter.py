"""Shared formatter for mode-aware output constraints."""

from __future__ import annotations

from dataclasses import dataclass
import re


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
        self.mode_sentence_limits = {
            "VALIDATION": 2,
            "PRESENCE": 3,
            "CLARIFICATION": 3,
            "THINKING": 5,
            "INTERVENTION": 2,
            "INTEGRATION": 4,
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

    @staticmethod
    def _take_sentences(text: str, max_sentences: int) -> str:
        if max_sentences <= 0:
            return text
        chunks = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
        if len(chunks) <= max_sentences:
            return text
        trimmed = " ".join(chunks[:max_sentences]).rstrip()
        if not trimmed.endswith(("...", ".", "!", "?")):
            trimmed += "..."
        return trimmed

    def calculate_target_length(self, user_message: str, routing_mode: str, sd_level: str | None = None) -> dict:
        """
        Adaptive answer length based on user message size + routing mode.

        Returns:
            {"max_sentences": int, "mode": str}
        """
        mode = (routing_mode or "PRESENCE").upper()
        base = int(self.mode_sentence_limits.get(mode, 3))
        words = len((user_message or "").split())

        if words <= 5:
            max_sentences = min(base, 2)
        elif words <= 20:
            max_sentences = base
        else:
            max_sentences = base + 1

        # More direct/compact output for acute SD levels.
        sd = (sd_level or "").upper()
        if sd in {"BEIGE", "RED"} and max_sentences > 2:
            max_sentences -= 1

        return {"max_sentences": max(1, max_sentences), "mode": mode}

    def format_answer(
        self,
        answer: str,
        *,
        mode: str,
        confidence_level: str,
        max_chars: int | None = None,
        user_message: str | None = None,
        sd_level: str | None = None,
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

        target = self.calculate_target_length(
            user_message=user_message or "",
            routing_mode=normalized_mode,
            sd_level=sd_level,
        )
        text = self._take_sentences(text, int(target["max_sentences"]))

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
