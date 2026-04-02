"""Unified mode-aware response generation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import AsyncGenerator, Iterable, Optional

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
        sd_name_map = {
            "BEIGE": "prompt_sd_purple",  # BEIGE -> используем PURPLE (ближайший)
            "PURPLE": "prompt_sd_purple",
            "RED": "prompt_sd_red",
            "BLUE": "prompt_sd_blue",
            "ORANGE": "prompt_sd_orange",
            "GREEN": "prompt_sd_green",
            "YELLOW": "prompt_sd_yellow",
            "TURQUOISE": "prompt_sd_yellow",  # TURQUOISE -> используем YELLOW (ближайший)
        }
        prompt_name = sd_name_map.get((sd_level or "GREEN").upper(), "prompt_sd_green")
        try:
            # Используем config.get_prompt() для горячей замены (admin-panel)
            return config.get_prompt(prompt_name)["text"]
        except (FileNotFoundError, ValueError):
            logger.warning(f"[RESPONSE_GEN] SD prompt not found: {prompt_name}, using empty")
            return ""

    @staticmethod
    def _conflicts_with_mode(level_text: str, mode: str) -> bool:
        """Detect restrictive level directives that conflict with expanding modes."""
        expanding_modes = {"THINKING", "INTEGRATION", "VALIDATION"}
        restricting_keywords = ("кратко", "упрощай", "не перегружай", "один точный вопрос")
        if (mode or "").upper() not in expanding_modes:
            return False
        text = (level_text or "").lower()
        return any(keyword in text for keyword in restricting_keywords)

    @staticmethod
    def _strip_restricting_lines(text: str) -> str:
        """Remove explicitly restrictive lines from composed prompt."""
        restricting_keywords = ("кратко", "упрощай", "не перегружай", "один точный вопрос")
        kept_lines = []
        for line in (text or "").splitlines():
            low = line.lower()
            if any(keyword in low for keyword in restricting_keywords):
                continue
            kept_lines.append(line)
        return "\n".join(kept_lines).strip()

    def _build_free_mode_prompt(
        self,
        base_prompt: str,
        sd_level: str,
        blocks,
    ) -> str:
        """Compose non-restrictive system prompt for FREE conversation mode."""
        normalized_base = self._strip_restricting_lines(base_prompt)
        sd_context = f"SD_LEVEL={sd_level or 'GREEN'}"
        context_parts = []
        for idx, block in enumerate(blocks[:5], start=1):
            title = getattr(block, "title", "") or getattr(block, "document_title", "")
            summary = getattr(block, "summary", "")
            content = (getattr(block, "content", "") or "")[:240]
            preview = summary or content
            if preview:
                context_parts.append(f"[{idx}] {title}: {preview}")
        knowledge = "\n".join(context_parts) if context_parts else "Нет дополнительных блоков."
        return (
            f"{normalized_base}\n\n"
            f"## Контекст SD (для понимания, не для ограничения):\n{sd_context}\n\n"
            f"## Контекст знаний:\n{knowledge}\n\n"
            "Отвечай полно, развёрнуто и по делу. Не ограничивай длину искусственно, "
            "если запрос требует деталей."
        )

    def _compose_system_prompt(
        self,
        base_prompt: str,
        sd_overlay: str,
        mode_prompt: str,
        additional_system_context: str,
        mode: str,
    ) -> str:
        """Compose final prompt with configurable priority order."""
        base = base_prompt.strip()
        sd = (sd_overlay or "").strip()
        mode_prompt_clean = (mode_prompt or "").strip()
        mode_directive = f"MODE DIRECTIVE:\n{mode_prompt_clean}" if mode_prompt_clean else ""

        if config.PROMPT_SD_OVERRIDES_BASE:
            chunks = [base, sd]
        else:
            chunks = [sd, base]

        if config.PROMPT_MODE_OVERRIDES_SD:
            chunks.append(mode_directive)
        else:
            chunks.insert(1, mode_directive)

        if additional_system_context:
            chunks.append(additional_system_context.strip())

        final_prompt = "\n\n".join(chunk for chunk in chunks if chunk).strip()
        if self._conflicts_with_mode(final_prompt, mode):
            final_prompt = self._strip_restricting_lines(final_prompt)
        return final_prompt

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
        system_prompt_blob_id: Optional[str] = None,
        user_prompt_blob_id: Optional[str] = None,
        session_store=None,
        session_id: Optional[str] = None,
        mode_prompt_override: Optional[str] = None,
        mode_overrides_sd: bool = False,
        system_prompt_override: Optional[str] = None,
    ) -> dict:
        """Generate a response using shared mode-aware prompt composition."""
        mode_prompt = build_mode_prompt(mode, confidence_level, forbid or [])
        if system_prompt_override:
            final_system_prompt = str(system_prompt_override).strip()
        else:
            base_system_prompt = self.answerer.build_system_prompt()
            if user_level_adapter is not None:
                try:
                    base_system_prompt = user_level_adapter.adapt_system_prompt(base_system_prompt)
                except Exception:
                    # Keep base prompt when adapter is unavailable or incompatible.
                    pass

            sd_overlay = self._load_sd_prompt(sd_level)
            if mode_prompt_override:
                if mode_overrides_sd:
                    sd_overlay = mode_prompt_override
                    mode_prompt = ""
                else:
                    mode_prompt = mode_prompt_override
            if config.FREE_CONVERSATION_MODE:
                final_system_prompt = self._build_free_mode_prompt(
                    base_prompt=base_system_prompt,
                    sd_level=sd_level,
                    blocks=blocks,
                )
            else:
                final_system_prompt = self._compose_system_prompt(
                    base_prompt=base_system_prompt,
                    sd_overlay=sd_overlay,
                    mode_prompt=mode_prompt,
                    additional_system_context=additional_system_context,
                    mode=mode,
                )

        model_name = model or config.LLM_MODEL
        base_temp = temperature if temperature is not None else config.LLM_TEMPERATURE
        final_temperature = self._temperature_for_confidence(confidence_level, base_temp)
        final_max_tokens = max_tokens if max_tokens is not None else config.get_mode_max_tokens(mode)
        if config.FREE_CONVERSATION_MODE:
            final_max_tokens = None

        original_build_prompt = self.answerer.build_system_prompt
        self.answerer.build_system_prompt = lambda: final_system_prompt
        try:
            try:
                result = self.answerer.generate_answer(
                    query,
                    blocks,
                    conversation_history=conversation_context,
                    model=model_name,
                    temperature=final_temperature,
                    max_tokens=final_max_tokens,
                    step_name="answer",
                    system_prompt_blob_id=system_prompt_blob_id,
                    user_prompt_blob_id=user_prompt_blob_id,
                    session_store=session_store,
                    session_id=session_id,
                )
            except TypeError as exc:
                if "step_name" not in str(exc):
                    raise
                result = self.answerer.generate_answer(
                    query,
                    blocks,
                    conversation_history=conversation_context,
                    model=model_name,
                    temperature=final_temperature,
                    max_tokens=final_max_tokens,
                    system_prompt_blob_id=system_prompt_blob_id,
                    user_prompt_blob_id=user_prompt_blob_id,
                    session_store=session_store,
                    session_id=session_id,
                )
        finally:
            self.answerer.build_system_prompt = original_build_prompt

        result["mode_prompt"] = mode_prompt
        result["mode"] = (mode or "PRESENCE").upper()
        return result

    async def generate_stream(
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
        system_prompt_override: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a response using shared mode-aware prompt composition."""
        if system_prompt_override:
            final_system_prompt = str(system_prompt_override).strip()
        else:
            base_system_prompt = self.answerer.build_system_prompt()
            if user_level_adapter is not None:
                try:
                    base_system_prompt = user_level_adapter.adapt_system_prompt(base_system_prompt)
                except Exception:
                    pass

            sd_overlay = self._load_sd_prompt(sd_level)
            mode_prompt = build_mode_prompt(mode, confidence_level, forbid or [])
            if config.FREE_CONVERSATION_MODE:
                final_system_prompt = self._build_free_mode_prompt(
                    base_prompt=base_system_prompt,
                    sd_level=sd_level,
                    blocks=blocks,
                )
            else:
                final_system_prompt = self._compose_system_prompt(
                    base_prompt=base_system_prompt,
                    sd_overlay=sd_overlay,
                    mode_prompt=mode_prompt,
                    additional_system_context=additional_system_context,
                    mode=mode,
                )

        model_name = model or config.LLM_MODEL
        base_temp = temperature if temperature is not None else config.LLM_TEMPERATURE
        final_temperature = self._temperature_for_confidence(confidence_level, base_temp)
        final_max_tokens = max_tokens if max_tokens is not None else config.get_mode_max_tokens(mode)
        if config.FREE_CONVERSATION_MODE:
            final_max_tokens = None

        async for token in self.answerer.answer_stream(
            query,
            blocks,
            conversation_history=conversation_context,
            model=model_name,
            temperature=final_temperature,
            max_tokens=final_max_tokens,
            system_prompt_override=final_system_prompt,
        ):
            yield token
