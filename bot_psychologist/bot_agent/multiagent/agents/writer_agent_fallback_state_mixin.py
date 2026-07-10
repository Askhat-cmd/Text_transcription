"""Stateful fallback/name-continuity helpers extracted from writer_agent.py."""

from __future__ import annotations

import re
from typing import Any, Optional

from ...config import config
from ..contracts.writer_contract import WriterContract
from .writer_agent_constants import _contains_any


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


class WriterAgentFallbackStateMixin:
    def _repair_greeting_without_mechanism_lecture(self, *, user_message: str) -> str:
        lowered_user = str(user_message or "").lower()
        self._set_final_answer_shape_debug("contact_brief")
        if "?" in user_message or _contains_any(lowered_user, ("как", "почему", "можешь", "что делать")):
            return (
                "Привет. Такое обычно повторяется, когда в похожих ситуациях снова включается "
                "один и тот же автоматический способ справляться, даже если он уже не помогает. "
                "Это не про слабость, а про привычную защитную реакцию."
            )
        return "Привет. Я рядом. Можем спокойно начать без спешки и лишней нагрузки."

    def _resolve_one_step_or_no_practice_fallback(
        self,
        *,
        text: str,
        user_message: str,
        lowered_user: str,
        canned_step_disallowed: bool,
    ) -> str:
        if not canned_step_disallowed:
            self._set_final_answer_shape_debug("one_step")
            return "Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."

        sanitized = self._strip_optional_followup_invitation(text) or text
        lowered_sanitized = sanitized.lower()
        if (
            len(sanitized.strip()) >= 90
            and "?" not in sanitized
            and not _contains_any(lowered_sanitized, self._PRACTICE_MARKERS)
        ):
            self._set_final_answer_shape_debug("sanitized_direct_no_forced_practice")
            return sanitized

        self._set_final_answer_shape_debug("sanitized_direct_no_forced_practice")
        return self._build_no_practice_fallback_text(user_message if user_message.strip() else lowered_user)

    def _set_final_answer_shape_debug(self, shape: str) -> None:
        self.last_debug["final_answer_shape"] = str(shape or "compact_direct")

    def _defer_no_stub_repair(self, *, signal: str, text: str, must_answer: str = "") -> str:
        """Signal the existing acceptance gate/retry path instead of writing a canned answer."""

        shape = str(signal or "no_stub_repair").strip() or "no_stub_repair"
        self._set_final_answer_shape_debug(f"{shape}_deferred_to_gate")
        failed_checks = [
            str(item)
            for item in list(self.last_debug.get("compliance_failed_checks", []) or [])
            if str(item).strip()
        ]
        if "no_stub_repair_signal" not in failed_checks:
            failed_checks.append("no_stub_repair_signal")
        payload = {
            "version": "no_stub_repair_signal_v1",
            "reason": shape,
            "recommended_action": "writer_retry",
            "must_answer": str(must_answer or "").strip(),
            "user_facing_replacement_created": False,
        }
        self.last_debug["compliance_failed_checks"] = failed_checks
        self.last_debug["no_stub_repair_signal"] = payload
        self.last_debug["retry_recommended"] = True
        return self._strip_optional_followup_invitation(text) or text

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

    def _estimate_cost(self, *, tokens_prompt: Optional[int], tokens_completion: Optional[int]) -> Optional[float]:
        if tokens_prompt is None and tokens_completion is None:
            return None
        model = str(self.last_debug.get("model") or self._resolve_model()).lower()
        rates = _COST_PER_1K_TOKENS.get(model, _COST_PER_1K_TOKENS["default"])
        prompt = float(tokens_prompt or 0)
        completion = float(tokens_completion or 0)
        cost = (prompt / 1000.0) * float(rates["input"]) + (completion / 1000.0) * float(rates["output"])
        return round(cost, 6)

    def _apply_name_continuity(self, response_text: str, contract: WriterContract) -> str:
        """Добавляет обращение по имени, если имя найдено в контексте и отсутствует в ответе."""
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
