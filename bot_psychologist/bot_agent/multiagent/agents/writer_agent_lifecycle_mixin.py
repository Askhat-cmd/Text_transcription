"""Lifecycle mixin for WriterAgent runtime settings and write path."""

from __future__ import annotations

import logging
from typing import Any

from ...feature_flags import feature_flags
from ..contracts.writer_contract import WriterContract
from ..dialogue_policy import DIALOGUE_PROFILE_MVP_FREE, normalize_dialogue_profile
from .writer_agent_constants import _to_float, _to_int
from .writer_agent_prompts import WRITER_SYSTEM, WRITER_SYSTEM_MVP_FREE_DIALOGUE


logger = logging.getLogger(__name__)

WRITER_MAX_TOKENS_DEFAULT = 600
WRITER_TIMEOUT_DEFAULT = 30.0

_SAFE_OVERRIDE_FALLBACKS = {
    "ru": "Я здесь. Ты не один. Сделай медленный вдох — я рядом.",
    "en": "I'm here. You're not alone. Take a slow breath - I'm with you.",
}
_DEFAULT_LANG = "ru"


class WriterAgentLifecycleMixin:
    def _resolve_runtime_settings(self, dialogue_profile: str = "safe_guided") -> dict[str, Any]:
        model = self._resolve_model()
        profile = normalize_dialogue_profile(dialogue_profile)
        configured_max_tokens = _to_int(
            feature_flags.value(
                "MULTIAGENT_MAX_TOKENS",
                feature_flags.value("WRITER_MAX_TOKENS", str(WRITER_MAX_TOKENS_DEFAULT)),
            ),
            WRITER_MAX_TOKENS_DEFAULT,
        )
        max_tokens = configured_max_tokens
        if profile == DIALOGUE_PROFILE_MVP_FREE:
            max_tokens = max(configured_max_tokens, 2500)
        return {
            "model": model,
            "timeout": _to_float(
                feature_flags.value("MULTIAGENT_LLM_TIMEOUT", str(WRITER_TIMEOUT_DEFAULT)),
                WRITER_TIMEOUT_DEFAULT,
            ),
            "max_tokens": max_tokens,
            "temperature": self._get_temperature_for_agent("writer"),
        }

    async def write(
        self,
        contract: WriterContract,
        *,
        prompt_constraint_decision: dict[str, Any] | None = None,
    ) -> str:
        """Write one answer text with safe fallback behavior."""
        dialogue_profile = normalize_dialogue_profile(
            getattr(contract, "dialogue_policy", {}).get("profile", "safe_guided")
            if isinstance(getattr(contract, "dialogue_policy", None), dict)
            else "safe_guided"
        )
        runtime_settings = self._resolve_runtime_settings(dialogue_profile=dialogue_profile)
        system_prompt = (
            WRITER_SYSTEM_MVP_FREE_DIALOGUE
            if dialogue_profile == DIALOGUE_PROFILE_MVP_FREE
            else WRITER_SYSTEM
        )
        self.last_debug = {
            "model": runtime_settings["model"],
            "api_mode": None,
            "temperature": runtime_settings["temperature"],
            "max_tokens": runtime_settings["max_tokens"],
            "timeout": runtime_settings["timeout"],
            "dialogue_profile": dialogue_profile,
            "system_prompt": system_prompt,
            "user_prompt": "",
            "llm_response": "",
            "tokens_prompt": None,
            "tokens_completion": None,
            "tokens_total": None,
            "estimated_cost_usd": None,
            "duration_ms": None,
            "error": None,
            "fallback_used": False,
            "prompt_constraint_pilot_activation_mode": "disabled",
            "prompt_constraint_pilot_applied": False,
            "prompt_constraint_pilot_blocked_reasons": [],
            "prompt_constraint_pilot_prompt_section_chars": 0,
            "context_budget_chars": None,
            "context_truncated": None,
            "preserved_recent_turns_count": None,
            "older_context_omitted_chars": None,
            "writer_kb_payload_trace": {},
            "writer_kb_payload_future_graduation_notes": {},
            "semantic_cards_pilot": {},
            "writer_grounding_visibility_v1": {},
            "writer_kb_payload_enabled": None,
            "writer_kb_payload_failed": None,
            "human_like_answer_policy_enabled": None,
            "explicit_answer_need": None,
            "repair_user_dissatisfaction": None,
            "sarcasm_or_negative_feedback": None,
            "overruled_constraints": [],
            "final_answer_shape": None,
            "question_forced": None,
            "practice_forced": None,
            "microstep_forced": None,
        }
        try:
            if contract.thread_state.safety_active:
                lang = contract.response_language or self._detect_language(contract.user_message)
                fallback = _SAFE_OVERRIDE_FALLBACKS.get(lang, _SAFE_OVERRIDE_FALLBACKS[_DEFAULT_LANG])
                try:
                    result = await self._call_llm(
                        contract,
                        prompt_constraint_decision=prompt_constraint_decision,
                    )
                    result = self._enforce_answer_compliance(result, contract)
                    if not result.strip():
                        self.last_debug["fallback_used"] = True
                        return fallback
                    return self._apply_name_continuity(result, contract)
                except Exception as exc:
                    self.last_debug["error"] = str(exc)
                    self.last_debug["fallback_used"] = True
                    return fallback

            result = await self._call_llm(
                contract,
                prompt_constraint_decision=prompt_constraint_decision,
            )
            result = self._enforce_answer_compliance(result, contract)
            if not result.strip():
                self.last_debug["fallback_used"] = True
                return self._static_fallback(contract)
            return self._apply_name_continuity(result, contract)
        except Exception as exc:
            logger.error("[WRITER] write failed: %s", exc, exc_info=True)
            self.last_debug["error"] = str(exc)
            self.last_debug["fallback_used"] = True
            return self._static_fallback(contract)
