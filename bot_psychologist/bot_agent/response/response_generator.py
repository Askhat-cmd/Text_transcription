"""Unified mode-aware response generation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

from ..config import config
from ..llm_answerer import LLMAnswerer
from .prompt_templates import build_mode_prompt

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generate LLM answers with shared mode and confidence directives."""

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

    def _load_sd_prompt(self, sd_level: str) -> str:
        """Загрузить SD-оверлей промта для уровня пользователя."""
        sd_file_map = {
            "BEIGE": "prompt_sd_purple.md",  # BEIGE -> используем PURPLE (ближайший)
            "PURPLE": "prompt_sd_purple.md",
            "RED": "prompt_sd_red.md",
            "BLUE": "prompt_sd_blue.md",
            "ORANGE": "prompt_sd_orange.md",
            "GREEN": "prompt_sd_green.md",
            "YELLOW": "prompt_sd_yellow.md",
            "TURQUOISE": "prompt_sd_yellow.md",  # TURQUOISE -> используем YELLOW (ближайший)
        }
        filename = sd_file_map.get((sd_level or "GREEN").upper(), "prompt_sd_green.md")
        prompt_path = Path(__file__).parent.parent / filename
        try:
            return prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning(f"[RESPONSE_GEN] SD prompt not found: {filename}, using empty")
            return ""

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
        sd_level: str = "GREEN",
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

        sd_overlay = self._load_sd_prompt(sd_level)
        if sd_overlay:
            base_system_prompt = f"{base_system_prompt}\n\n{sd_overlay}"

        mode_prompt = build_mode_prompt(mode, confidence_level, forbid or [])
        system_chunks = [base_system_prompt, f"MODE DIRECTIVE:\n{mode_prompt}"]
        if additional_system_context:
            system_chunks.append(additional_system_context.strip())
        final_system_prompt = "\n\n".join(chunk for chunk in system_chunks if chunk).strip()

        model_name = model or config.LLM_MODEL
        base_temp = temperature if temperature is not None else config.LLM_TEMPERATURE
        final_temperature = self._temperature_for_confidence(confidence_level, base_temp)
        final_max_tokens = max_tokens if max_tokens is not None else config.get_mode_max_tokens(mode)

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
                step_name="answer",
            )
        finally:
            self.answerer.build_system_prompt = original_build_prompt

        result["mode_prompt"] = mode_prompt
        result["mode"] = (mode or "PRESENCE").upper()
        return result
