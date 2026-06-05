"""Deterministic Validator Agent for Writer drafts."""

from __future__ import annotations

import logging
from typing import Optional

from ..contracts.validation_result import ValidationResult
from ..contracts.writer_contract import WriterContract
from .validator_agent_config import (
    BOT_REVEAL_PATTERNS,
    DIAGNOSIS_PATTERNS,
    FORBIDDEN_STARTS,
    MAX_ANSWER_LENGTH,
    MEDICAL_ADVICE_PATTERNS,
    MIN_ANSWER_LENGTH,
    MODE_VIOLATION_PATTERNS,
    PROMISE_PATTERNS,
    SAFE_FALLBACKS,
    SELF_HARM_IN_ANSWER,
)


logger = logging.getLogger(__name__)


def _contains_any(text: str, patterns: list[str]) -> Optional[str]:
    """Return first matching pattern (case-insensitive) or None."""
    lowered = text.lower()
    for pattern in patterns:
        if pattern.lower() in lowered:
            return pattern
    return None


def _must_avoid_hit(text: str, must_avoid: list[str]) -> Optional[str]:
    """Find must_avoid hit with lightweight normalization."""
    lowered = text.lower().replace("ё", "е")
    for raw in must_avoid:
        item = (raw or "").strip().lower().replace("ё", "е")
        if not item:
            continue
        if item in lowered:
            return raw
        if len(item) >= 4 and item[-1] in "аеиоуыяьюй":
            stem = item[:-1]
            if stem and stem in lowered:
                return raw
    return None


def _safe_dict(value: object) -> dict:
    return dict(value) if isinstance(value, dict) else {}


class ValidatorAgent:
    """Rule-based validator: safety -> contract -> quality."""

    def validate(self, draft: str, contract: WriterContract) -> ValidationResult:
        """Validate writer draft synchronously and deterministically."""
        try:
            text = (draft or "").strip()

            safety_hit = self._check_safety(text)
            if safety_hit:
                logger.warning("[VALIDATOR] safety block: %s", safety_hit)
                return ValidationResult(
                    is_blocked=True,
                    block_reason=safety_hit,
                    block_category="safety",
                    safe_replacement=SAFE_FALLBACKS["safety"],
                )

            contract_hit = self._check_contract(text, contract)
            if contract_hit:
                logger.warning("[VALIDATOR] contract block: %s", contract_hit)
                return ValidationResult(
                    is_blocked=True,
                    block_reason=contract_hit,
                    block_category="contract",
                    safe_replacement=SAFE_FALLBACKS["contract"],
                )

            quality_flags = self._check_quality(text)
            return ValidationResult(is_blocked=False, quality_flags=quality_flags)
        except Exception as exc:
            logger.error("[VALIDATOR] validate failed: %s", exc, exc_info=True)
            return ValidationResult(is_blocked=False, quality_flags=["validator_error"])

    def _check_safety(self, text: str) -> Optional[str]:
        hit = _contains_any(text, SELF_HARM_IN_ANSWER)
        if hit:
            return f"self_harm_in_answer: {hit}"
        hit = _contains_any(text, MEDICAL_ADVICE_PATTERNS)
        if hit:
            return f"medical_advice: {hit}"
        hit = _contains_any(text, DIAGNOSIS_PATTERNS)
        if hit:
            return f"diagnosis: {hit}"
        hit = _contains_any(text, PROMISE_PATTERNS)
        if hit:
            return f"guarantee_promise: {hit}"
        hit = _contains_any(text, BOT_REVEAL_PATTERNS)
        if hit:
            return f"bot_reveal: {hit}"
        return None

    def _check_contract(self, text: str, contract: WriterContract) -> Optional[str]:
        must_avoid = contract.thread_state.must_avoid or []
        blocked = _must_avoid_hit(text, must_avoid)
        if blocked:
            return f"must_avoid_violated: {blocked}"

        mode = contract.thread_state.response_mode
        spec = MODE_VIOLATION_PATTERNS.get(mode)
        if spec:
            hit = _contains_any(text, list(spec.get("patterns", [])))
            if hit and not self._is_soft_format_violation(mode=mode, contract=contract):
                return str(spec.get("message", "mode_violation"))

        return None

    @staticmethod
    def _is_soft_format_violation(*, mode: str, contract: WriterContract) -> bool:
        if mode not in {"validate", "regulate"}:
            return False

        policy = _safe_dict(getattr(contract, "dialogue_policy", None))
        unified = _safe_dict(policy.get("unified_dialogue_profile"))
        directive = _safe_dict(getattr(contract, "final_answer_directive", None))
        obligation_payload = _safe_dict(policy.get("answer_obligation_resolution"))

        profile_preset = str(
            policy.get("profile_preset")
            or unified.get("profile_preset")
            or ""
        ).strip()
        if profile_preset != "free_dialogue_default":
            return False

        answer_obligation = str(
            obligation_payload.get("answer_obligation")
            or directive.get("answer_obligation")
            or ""
        ).strip()
        answer_shape = str(
            obligation_payload.get("answer_shape")
            or directive.get("answer_shape")
            or ""
        ).strip()

        if answer_obligation in {
            "acknowledge_style_preference_then_answer",
            "answer_direct_question",
            "answer_knowledge_question",
            "answer_concrete_situation",
            "repair_and_answer_last_question",
            "answer_last_offer",
        }:
            return True

        return answer_shape in {
            "structured_explanation",
            "contextual_explanation",
            "concept_explanation_full",
            "structured_summary",
        }

    @staticmethod
    def _check_quality(text: str) -> list[str]:
        flags: list[str] = []
        if len(text) < MIN_ANSWER_LENGTH:
            flags.append(f"too_short: {len(text)} chars")
        if len(text) > MAX_ANSWER_LENGTH:
            flags.append(f"too_long: {len(text)} chars")
        lowered = text.lower()
        for phrase in FORBIDDEN_STARTS:
            if lowered.startswith(phrase.lower()):
                flags.append(f"forbidden_start: {phrase}")
                break
        return flags


validator_agent = ValidatorAgent()
