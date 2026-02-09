"""Unified mode-aware response generation."""

from __future__ import annotations

from typing import Iterable, Optional

from ..config import config
from ..llm_answerer import LLMAnswerer
from .prompt_templates import build_mode_prompt


class ResponseGenerator:
    """Generate LLM answers with shared mode and confidence directives."""

    MODE_TOKEN_LIMITS = {
        "PRESENCE": 420,
        "CLARIFICATION": 450,
        "VALIDATION": 500,
        "THINKING": 900,
        "INTERVENTION": 700,
        "INTEGRATION": 520,
    }

    def __init__(self, answerer: Optional[LLMAnswerer] = None) -> None:
        self.answerer = answerer or LLMAnswerer()

    @staticmethod
    def _temperature_for_confidence(confidence_level: str, default: float) -> float:
        level = (confidence_level or "medium").lower()
        if level == "low":
            return max(0.1, default - 0.15)
        if level == "high":
            return min(1.0, default + 0.05)
        return default

    def _max_tokens_for_mode(self, mode: str, default: int) -> int:
        mode_cap = self.MODE_TOKEN_LIMITS.get((mode or "PRESENCE").upper(), default)
        return min(default, mode_cap)

    def generate(
        self,
        query: str,
        blocks,
        *,
        conversation_context: str = "",
        mode: str = "PRESENCE",
        confidence_level: str = "medium",
        forbid: Optional[Iterable[str]] = None,
        user_level_adapter=None,
        additional_system_context: str = "",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """Generate a response using shared mode-aware prompt composition."""
        base_system_prompt = self.answerer.build_system_prompt()
        if user_level_adapter is not None:
            try:
                base_system_prompt = user_level_adapter.adapt_system_prompt(base_system_prompt)
            except Exception:
                # Keep base prompt when adapter is unavailable or incompatible.
                pass

        mode_prompt = build_mode_prompt(mode, confidence_level, forbid or [])
        system_chunks = [base_system_prompt, f"MODE DIRECTIVE:\n{mode_prompt}"]
        if additional_system_context:
            system_chunks.append(additional_system_context.strip())
        final_system_prompt = "\n\n".join(chunk for chunk in system_chunks if chunk).strip()

        model_name = model or config.LLM_MODEL
        base_temp = temperature if temperature is not None else config.LLM_TEMPERATURE
        final_temperature = self._temperature_for_confidence(confidence_level, base_temp)
        token_budget = max_tokens or config.LLM_MAX_TOKENS
        final_max_tokens = self._max_tokens_for_mode(mode, token_budget)

        original_build_prompt = self.answerer.build_system_prompt
        self.answerer.build_system_prompt = lambda: final_system_prompt
        try:
            result = self.answerer.generate_answer(
                query,
                blocks,
                conversation_history=conversation_context,
                model=model_name,
                temperature=final_temperature,
                max_tokens=final_max_tokens,
            )
        finally:
            self.answerer.build_system_prompt = original_build_prompt

        result["mode_prompt"] = mode_prompt
        result["mode"] = (mode or "PRESENCE").upper()
        return result

