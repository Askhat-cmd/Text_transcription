"""Async per-turn LLM summary service (PRD-045.6.3)."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from ..config import config
from .agents.agent_llm_client import create_agent_completion
from .contracts.turn_llm_summary import (
    TURN_LLM_SUMMARY_METHOD,
    TURN_LLM_SUMMARY_VERSION,
    TurnLLMSummary,
    utc_now_iso,
)


logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "turn_llm_summary_v1.md"
_PROMPT_CACHE: str | None = None


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def compute_turn_source_hash(user_input: str, assistant_response: str) -> str:
    normalized_user = _normalize_text(user_input)
    normalized_assistant = _normalize_text(assistant_response)
    payload = f"{normalized_user}\n---assistant---\n{normalized_assistant}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _clip(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    clean = _normalize_text(text)
    return clean[:max_chars].strip()


def _load_prompt() -> str:
    global _PROMPT_CACHE
    if _PROMPT_CACHE is not None:
        return _PROMPT_CACHE
    try:
        _PROMPT_CACHE = _PROMPT_PATH.read_text(encoding="utf-8").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[TURN_SUMMARY] failed to load prompt file: %s", exc)
        _PROMPT_CACHE = "Return ONLY JSON with fields summary, important_quote, open_loop, user_need, assistant_move, emotional_tone."
    return _PROMPT_CACHE


def build_pending_turn_summary_record(
    *,
    user_input: str,
    assistant_response: str,
    provider: str | None = None,
    model: str | None = None,
) -> TurnLLMSummary:
    return TurnLLMSummary(
        status="pending",
        summary="",
        important_quote=None,
        open_loop=None,
        user_need=None,
        assistant_move=None,
        emotional_tone=None,
        summary_version=TURN_LLM_SUMMARY_VERSION,
        summary_method=TURN_LLM_SUMMARY_METHOD,
        model=model or str(getattr(config, "TURN_LLM_SUMMARY_MODEL", "") or config.LLM_MODEL),
        provider=provider or str(getattr(config, "TURN_LLM_SUMMARY_PROVIDER", "disabled") or "disabled"),
        source_hash=compute_turn_source_hash(user_input, assistant_response),
        created_at=utc_now_iso(),
        error=None,
    )


def should_summarize_turn(user_input: str, assistant_response: str) -> bool:
    if not bool(getattr(config, "TURN_LLM_SUMMARY_ENABLED", False)):
        return False
    if not str(user_input or "").strip():
        return False
    if not str(assistant_response or "").strip():
        return False
    return True


def _safe_error(exc: Exception) -> str:
    preview_len = int(getattr(config, "TURN_LLM_SUMMARY_DEBUG_PREVIEW_CHARS", 160) or 160)
    text = f"{exc.__class__.__name__}: {exc}"
    return _clip(text, preview_len)


def _build_ready_record(
    *,
    user_input: str,
    assistant_response: str,
    payload: dict[str, Any],
    provider: str,
    model: str,
) -> TurnLLMSummary:
    max_summary_chars = int(getattr(config, "TURN_LLM_SUMMARY_MAX_SUMMARY_CHARS", 700) or 700)
    return TurnLLMSummary(
        status="ready",
        summary=_clip(str(payload.get("summary", "") or ""), max_summary_chars),
        important_quote=_clip(str(payload.get("important_quote", "") or ""), 160) or None,
        open_loop=_clip(str(payload.get("open_loop", "") or ""), 220) or None,
        user_need=_clip(str(payload.get("user_need", "") or ""), 220) or None,
        assistant_move=_clip(str(payload.get("assistant_move", "") or ""), 220) or None,
        emotional_tone=_clip(str(payload.get("emotional_tone", "") or ""), 120) or None,
        summary_version=TURN_LLM_SUMMARY_VERSION,
        summary_method=TURN_LLM_SUMMARY_METHOD,
        model=model,
        provider=provider,
        source_hash=compute_turn_source_hash(user_input, assistant_response),
        created_at=utc_now_iso(),
        error=None,
    )


def _build_failed_record(
    *,
    user_input: str,
    assistant_response: str,
    provider: str,
    model: str,
    error: str,
) -> TurnLLMSummary:
    return TurnLLMSummary(
        status="failed",
        summary="",
        important_quote=None,
        open_loop=None,
        user_need=None,
        assistant_move=None,
        emotional_tone=None,
        summary_version=TURN_LLM_SUMMARY_VERSION,
        summary_method=TURN_LLM_SUMMARY_METHOD,
        model=model,
        provider=provider,
        source_hash=compute_turn_source_hash(user_input, assistant_response),
        created_at=utc_now_iso(),
        error=error,
    )


def _mock_generate_payload(user_input: str, assistant_response: str) -> dict[str, str]:
    user_clean = _normalize_text(user_input)
    bot_clean = _normalize_text(assistant_response)
    summary = (
        f"Пользователь обозначил: {user_clean[:180]}. "
        f"Ассистент ответил: {bot_clean[:180]}."
    )
    return {
        "summary": summary,
        "important_quote": user_clean[:120],
        "open_loop": "",
        "user_need": user_clean[:140],
        "assistant_move": bot_clean[:140],
        "emotional_tone": "нейтрально-напряженный",
    }


async def generate_turn_llm_summary_v1(
    *,
    user_input: str,
    assistant_response: str,
    provider: str | None = None,
    model: str | None = None,
    client: Any | None = None,
) -> TurnLLMSummary:
    provider_name = str(provider or getattr(config, "TURN_LLM_SUMMARY_PROVIDER", "disabled") or "disabled").lower()
    model_name = str(model or getattr(config, "TURN_LLM_SUMMARY_MODEL", "") or config.LLM_MODEL)
    max_input_chars = int(getattr(config, "TURN_LLM_SUMMARY_MAX_INPUT_CHARS", 6000) or 6000)
    timeout_seconds = float(getattr(config, "TURN_LLM_SUMMARY_TIMEOUT_SECONDS", 20) or 20)
    retries = int(getattr(config, "TURN_LLM_SUMMARY_MAX_RETRIES", 1) or 1)

    user_in = _clip(user_input, max_input_chars)
    assistant_in = _clip(assistant_response, max_input_chars)

    if provider_name in {"disabled", ""}:
        return TurnLLMSummary(
            status="disabled",
            summary="",
            important_quote=None,
            open_loop=None,
            user_need=None,
            assistant_move=None,
            emotional_tone=None,
            summary_version=TURN_LLM_SUMMARY_VERSION,
            summary_method=TURN_LLM_SUMMARY_METHOD,
            model=model_name,
            provider="disabled",
            source_hash=compute_turn_source_hash(user_in, assistant_in),
            created_at=utc_now_iso(),
            error=None,
        )

    if provider_name == "mock":
        payload = _mock_generate_payload(user_in, assistant_in)
        return _build_ready_record(
            user_input=user_in,
            assistant_response=assistant_in,
            payload=payload,
            provider="mock",
            model=model_name,
        )

    if provider_name != "openai":
        return _build_failed_record(
            user_input=user_in,
            assistant_response=assistant_in,
            provider=provider_name,
            model=model_name,
            error=f"unsupported_provider:{provider_name}",
        )

    if client is None:
        try:
            from openai import AsyncOpenAI  # noqa: PLC0415

            api_key = getattr(config, "OPENAI_API_KEY", None)
            if not api_key:
                return _build_failed_record(
                    user_input=user_in,
                    assistant_response=assistant_in,
                    provider="openai",
                    model=model_name,
                    error="missing_openai_api_key",
                )
            client = AsyncOpenAI(api_key=api_key)
        except Exception as exc:  # noqa: BLE001
            return _build_failed_record(
                user_input=user_in,
                assistant_response=assistant_in,
                provider="openai",
                model=model_name,
                error=_safe_error(exc),
            )

    system_prompt = _load_prompt()
    user_prompt = (
        "Сформируй summary завершенного обмена.\n\n"
        f"USER:\n{user_in}\n\nASSISTANT:\n{assistant_in}"
    )

    attempts = max(1, retries + 1)
    last_error: str = "unknown_error"
    for _ in range(attempts):
        try:
            result = await create_agent_completion(
                client=client,
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=700,
                timeout=timeout_seconds,
                require_json=True,
            )
            raw_text = str(result.text or "").strip()
            parsed = json.loads(raw_text) if raw_text else {}
            if not isinstance(parsed, dict):
                raise ValueError("summary_payload_not_dict")
            ready = _build_ready_record(
                user_input=user_in,
                assistant_response=assistant_in,
                payload=parsed,
                provider="openai",
                model=model_name,
            )
            if not ready.summary:
                raise ValueError("summary_empty_after_normalization")
            return ready
        except Exception as exc:  # noqa: BLE001
            last_error = _safe_error(exc)

    return _build_failed_record(
        user_input=user_in,
        assistant_response=assistant_in,
        provider="openai",
        model=model_name,
        error=last_error,
    )

