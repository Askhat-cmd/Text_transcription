"""Writer Agent for NEO multi-agent runtime."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

from ...config import config
from ...feature_flags import feature_flags
from ..contracts.writer_contract import WriterContract
from .writer_agent_prompts import WRITER_SYSTEM, WRITER_USER_TEMPLATE


logger = logging.getLogger(__name__)

WRITER_MODEL_DEFAULT = "gpt-5-mini"
WRITER_MAX_TOKENS_DEFAULT = 600
WRITER_TEMPERATURE_DEFAULT = 0.7
WRITER_TIMEOUT_DEFAULT = 30.0

_SAFE_OVERRIDE_FALLBACKS = {
    "ru": "Я здесь. Ты не один. Сделай медленный вдох — я рядом.",
    "en": "I'm here. You're not alone. Take a slow breath — I'm with you.",
}
_DEFAULT_LANG = "ru"

_COST_PER_1K_TOKENS = {
    "gpt-5-mini": {"input": 0.00025, "output": 0.00200},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    "default": {"input": 0.00125, "output": 0.01000},
}

_RU_NAME_PATTERNS = (
    re.compile(r"\bменя\s+зовут\s+([А-ЯЁA-Z][А-ЯЁа-яёA-Za-z\-]{1,30})", re.IGNORECASE),
    re.compile(r"\bмое\s+имя\s+([А-ЯЁA-Z][А-ЯЁа-яёA-Za-z\-]{1,30})", re.IGNORECASE),
)
_EN_NAME_PATTERNS = (
    re.compile(r"\bmy\s+name\s+is\s+([A-Z][A-Za-z\-]{1,30})", re.IGNORECASE),
    re.compile(r"\bi\s+am\s+([A-Z][A-Za-z\-]{1,30})", re.IGNORECASE),
)


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
        self._timeout = _to_float(
            feature_flags.value("MULTIAGENT_LLM_TIMEOUT", str(WRITER_TIMEOUT_DEFAULT)),
            WRITER_TIMEOUT_DEFAULT,
        )
        self._max_tokens = _to_int(
            feature_flags.value(
                "MULTIAGENT_MAX_TOKENS",
                feature_flags.value("WRITER_MAX_TOKENS", str(WRITER_MAX_TOKENS_DEFAULT)),
            ),
            WRITER_MAX_TOKENS_DEFAULT,
        )
        self._temperature = _to_float(
            feature_flags.value(
                "MULTIAGENT_TEMPERATURE",
                feature_flags.value("WRITER_TEMPERATURE", str(WRITER_TEMPERATURE_DEFAULT)),
            ),
            WRITER_TEMPERATURE_DEFAULT,
        )
        self.last_debug: dict[str, Any] = {}

    async def write(self, contract: WriterContract) -> str:
        """Write one answer text with safe fallback behavior."""
        self.last_debug = {
            "model": self._model,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "timeout": self._timeout,
            "system_prompt": WRITER_SYSTEM,
            "user_prompt": "",
            "llm_response": "",
            "tokens_prompt": None,
            "tokens_completion": None,
            "tokens_total": None,
            "estimated_cost_usd": None,
            "duration_ms": None,
            "error": None,
        }
        try:
            if contract.thread_state.safety_active:
                lang = contract.response_language or self._detect_language(contract.user_message)
                fallback = _SAFE_OVERRIDE_FALLBACKS.get(lang, _SAFE_OVERRIDE_FALLBACKS[_DEFAULT_LANG])
                try:
                    result = await self._call_llm(contract)
                    if not result.strip():
                        return fallback
                    return self._apply_name_continuity(result, contract)
                except Exception as exc:
                    self.last_debug["error"] = str(exc)
                    return fallback

            result = await self._call_llm(contract)
            if not result.strip():
                return self._static_fallback(contract)
            return self._apply_name_continuity(result, contract)
        except Exception as exc:
            logger.error("[WRITER] write failed: %s", exc, exc_info=True)
            self.last_debug["error"] = str(exc)
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
        self.last_debug["user_prompt"] = user_prompt

        start_ts = time.perf_counter()
        response = await client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": WRITER_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            timeout=self._timeout,
        )
        llm_response = (response.choices[0].message.content or "").strip()
        tokens_prompt, tokens_completion, tokens_total = self._extract_tokens(response)
        estimated_cost = self._estimate_cost(tokens_prompt=tokens_prompt, tokens_completion=tokens_completion)
        duration_ms = int((time.perf_counter() - start_ts) * 1000)
        self.last_debug.update(
            {
                "llm_response": llm_response,
                "tokens_prompt": tokens_prompt,
                "tokens_completion": tokens_completion,
                "tokens_total": tokens_total,
                "estimated_cost_usd": estimated_cost,
                "duration_ms": duration_ms,
                "error": None,
            }
        )
        return llm_response

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
    def _extract_tokens(response: Any) -> tuple[Optional[int], Optional[int], Optional[int]]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None, None, None
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        if total_tokens is None and isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
            total_tokens = prompt_tokens + completion_tokens
        try:
            prompt_value = int(prompt_tokens) if prompt_tokens is not None else None
        except (TypeError, ValueError):
            prompt_value = None
        try:
            completion_value = int(completion_tokens) if completion_tokens is not None else None
        except (TypeError, ValueError):
            completion_value = None
        try:
            total_value = int(total_tokens) if total_tokens is not None else None
        except (TypeError, ValueError):
            total_value = None
        return prompt_value, completion_value, total_value

    def _estimate_cost(self, *, tokens_prompt: Optional[int], tokens_completion: Optional[int]) -> Optional[float]:
        if tokens_prompt is None and tokens_completion is None:
            return None
        rates = _COST_PER_1K_TOKENS.get((self._model or "").lower(), _COST_PER_1K_TOKENS["default"])
        prompt = float(tokens_prompt or 0)
        completion = float(tokens_completion or 0)
        cost = (prompt / 1000.0) * float(rates["input"]) + (completion / 1000.0) * float(rates["output"])
        return round(cost, 6)

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


    def _apply_name_continuity(self, response_text: str, contract: WriterContract) -> str:
        """Добавляет обращение по имени, если имя явно есть в контексте и отсутствует в ответе."""
        name = self._extract_user_name(contract)
        if not name:
            return response_text
        if name.lower() in response_text.lower():
            return response_text
        return f"{name}, {response_text}"

    def _extract_user_name(self, contract: WriterContract) -> Optional[str]:
        memory_bundle = getattr(contract, "memory_bundle", None)
        conversation_context = ""
        if memory_bundle is not None:
            conversation_context = str(getattr(memory_bundle, "conversation_context", "") or "")
        context = " ".join(
            (
                str(contract.user_message or ""),
                conversation_context,
            )
        )
        if not context.strip():
            return None

        for pattern in _RU_NAME_PATTERNS:
            match = pattern.search(context)
            if match:
                return self._normalize_name(match.group(1))

        for pattern in _EN_NAME_PATTERNS:
            match = pattern.search(context)
            if match:
                return self._normalize_name(match.group(1))

        return None

    @staticmethod
    def _normalize_name(raw_name: str) -> Optional[str]:
        name = (raw_name or "").strip(" .,:;!?\"'()[]{}")
        if len(name) < 2 or len(name) > 31:
            return None
        return name[0].upper() + name[1:]


writer_agent = WriterAgent()
