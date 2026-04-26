"""Writer Agent for NEO multi-agent runtime."""

from __future__ import annotations

import logging
from typing import Any, Optional

from ...config import config
from ...feature_flags import feature_flags
from ..contracts.writer_contract import WriterContract
from .writer_agent_prompts import WRITER_SYSTEM, WRITER_USER_TEMPLATE


logger = logging.getLogger(__name__)

WRITER_MODEL_DEFAULT = "gpt-5-mini"
WRITER_MAX_TOKENS_DEFAULT = 400
WRITER_TEMPERATURE_DEFAULT = 0.7

_SAFE_OVERRIDE_FALLBACKS = {
    "ru": "Я здесь. Ты не один. Сделай медленный вдох — я рядом.",
    "en": "I'm here. You're not alone. Take a slow breath — I'm with you.",
}
_DEFAULT_LANG = "ru"


def _to_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class WriterAgent:
    """Generates final user-facing response from WriterContract."""

    def __init__(self, client: Optional[Any] = None, model: Optional[str] = None):
        self._client = client
        self._model = model or feature_flags.value("WRITER_MODEL", WRITER_MODEL_DEFAULT)
        self._max_tokens = _to_int(
            feature_flags.value("WRITER_MAX_TOKENS", str(WRITER_MAX_TOKENS_DEFAULT)),
            WRITER_MAX_TOKENS_DEFAULT,
        )
        self._temperature = _to_float(
            feature_flags.value("WRITER_TEMPERATURE", str(WRITER_TEMPERATURE_DEFAULT)),
            WRITER_TEMPERATURE_DEFAULT,
        )

    async def write(self, contract: WriterContract) -> str:
        """Write one answer text with safe fallback behavior."""
        try:
            if contract.thread_state.safety_active:
                lang = contract.response_language or self._detect_language(contract.user_message)
                fallback = _SAFE_OVERRIDE_FALLBACKS.get(lang, _SAFE_OVERRIDE_FALLBACKS[_DEFAULT_LANG])
                try:
                    result = await self._call_llm(contract)
                    return result if result.strip() else fallback
                except Exception:
                    return fallback

            result = await self._call_llm(contract)
            return result if result.strip() else self._static_fallback(contract)
        except Exception as exc:
            logger.error("[WRITER] write failed: %s", exc, exc_info=True)
            return self._static_fallback(contract)

    async def _call_llm(self, contract: WriterContract) -> str:
        client = self._get_client()
        if client is None:
            raise RuntimeError("No LLM client available")

        ctx = contract.to_prompt_context()
        user_prompt = WRITER_USER_TEMPLATE.format(
            user_message=ctx["user_message"],
            response_mode=ctx["response_mode"],
            response_goal=ctx["response_goal"] or "нет",
            phase=ctx["phase"],
            nervous_state=ctx["nervous_state"],
            ok_position=ctx["ok_position"],
            openness=ctx["openness"],
            safety_active=ctx["safety_active"],
            open_loops=", ".join(ctx["open_loops"]) or "нет",
            must_avoid=", ".join(ctx["must_avoid"]) or "нет",
            conversation_context=(ctx["conversation_context"] or "нет")[:2000],
            user_profile_patterns=", ".join(ctx["user_profile_patterns"]) or "нет",
            user_profile_values=", ".join(ctx["user_profile_values"]) or "нет",
            semantic_hits=self._format_hits(ctx["semantic_hits"]),
        )

        response = await client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": WRITER_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        return (response.choices[0].message.content or "").strip()

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI

            api_key = getattr(config, "OPENAI_API_KEY", None)
            if not api_key:
                return None
            self._client = AsyncOpenAI(api_key=api_key)
            return self._client
        except Exception:
            return None

    @staticmethod
    def _detect_language(text: str) -> str:
        cyrillic = sum(1 for ch in text if ("а" <= ch.lower() <= "я") or ch.lower() == "ё")
        return "ru" if cyrillic > len(text) * 0.2 else "en"

    @staticmethod
    def _format_hits(hits: list[str]) -> str:
        if not hits:
            return "нет релевантных знаний"
        return "\n---\n".join(f"• {h[:300]}" for h in hits[:2])

    @staticmethod
    def _static_fallback(contract: WriterContract) -> str:
        mode = contract.thread_state.response_mode
        if mode == "safe_override":
            return "Я здесь. Ты не один."
        if mode == "validate":
            return "Я слышу тебя. Расскажи больше, если хочешь."
        if mode == "regulate":
            return "Сделай медленный вдох. Я рядом."
        return "Я слышу тебя."


writer_agent = WriterAgent()

