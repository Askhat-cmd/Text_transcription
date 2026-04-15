"""Mode/policy helper extraction for adaptive orchestration (Wave 4)."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ..feature_flags import feature_flags
from ..output_validator import output_validator

logger = logging.getLogger(__name__)

MODE_PROMPT_MAP: dict[str, str] = {
    "informational": "prompt_mode_informational",
}

_PRACTICE_START_RE = re.compile(
    r"\b(РєР°Рє РЅР°С‡Р°С‚СЊ|РєР°Рє РїСЂР°РєС‚РёРєРѕРІР°С‚СЊ|РєР°Рє РїСЂРёРјРµРЅРёС‚СЊ|С‡С‚Рѕ РґРµР»Р°С‚СЊ РґР°Р»СЊС€Рµ|РїСЂР°РєС‚РёРєРѕРІР°С‚СЊ|РІ Р¶РёР·РЅРё)\b",
    flags=re.IGNORECASE,
)
_PERSONAL_APPLICATION_RE = re.compile(
    r"\b(Сѓ СЃРµР±СЏ|РІ СЂРµР°Р»СЊРЅРѕР№ Р¶РёР·РЅРё|РІ РјРѕРµР№ Р¶РёР·РЅРё|РґР»СЏ РјРµРЅСЏ|РїСЂРѕ РјРµРЅСЏ|СЃРѕ РјРЅРѕР№|РЅР° РјРѕРµРј РїСЂРёРјРµСЂРµ)\b",
    flags=re.IGNORECASE,
)


NEO_PRESERVE_ROUTES = {"reflect", "inform", "presence", "intervention", "safe_override"}


def resolve_mode_prompt(user_state: str, cfg) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve mode prompt key and text by user state.
    Returns (None, None) if override is not defined.
    """
    prompt_key = MODE_PROMPT_MAP.get((user_state or "").strip().lower())
    if not prompt_key:
        return None, None
    try:
        prompt_payload = cfg.get_prompt(prompt_key)
        prompt_text = str((prompt_payload or {}).get("text") or "").strip()
        if not prompt_text:
            return None, None
        return prompt_key, prompt_text
    except Exception as exc:
        logger.warning("[MODE_PROMPT] failed to load '%s': %s", prompt_key, exc)
        return None, None


def _derive_informational_mode_hint(phase8_signals, query: str) -> bool:
    """Narrow informational hint to concept-first requests only."""
    if not _informational_branch_enabled() or phase8_signals is None:
        return False

    informational_intent = bool(getattr(phase8_signals, "informational_intent", False))
    personal_disclosure = bool(getattr(phase8_signals, "personal_disclosure", False))
    mixed_query = bool(getattr(phase8_signals, "mixed_query", False))
    if not informational_intent or personal_disclosure or mixed_query:
        return False

    text = (query or "").strip().lower()
    if not text:
        return False
    if _PERSONAL_APPLICATION_RE.search(text):
        return False
    if _PRACTICE_START_RE.search(text):
        return False
    return True


def _diagnostics_v1_enabled() -> bool:
    return feature_flags.enabled("USE_NEW_DIAGNOSTICS_V1")


def _deterministic_route_resolver_enabled() -> bool:
    return feature_flags.enabled("USE_DETERMINISTIC_ROUTE_RESOLVER")


def _prompt_stack_v2_enabled() -> bool:
    return feature_flags.enabled("USE_PROMPT_STACK_V2")


def _output_validation_enabled() -> bool:
    return feature_flags.enabled("USE_OUTPUT_VALIDATION")


def _informational_branch_enabled() -> bool:
    return feature_flags.enabled("INFORMATIONAL_BRANCH_ENABLED")


def _apply_output_validation_policy(
    *,
    answer: str,
    query: str = "",
    route: str,
    mode: str,
    validator=output_validator,
    force_enabled: Optional[bool] = None,
    generate_retry=None,
) -> Tuple[str, Dict[str, Any], Optional[Dict[str, Any]]]:
    """Validate output, optionally retry generation once, then fallback safely."""
    enabled = _output_validation_enabled() if force_enabled is None else bool(force_enabled)
    if not enabled:
        return answer, {"enabled": False}, None

    attempts: List[Dict[str, Any]] = []
    fallback_used = False
    retry_llm_result: Optional[Dict[str, Any]] = None
    normalized_route = (route or "").strip().lower()
    normalized_mode = (mode or "").strip().lower()
    safety_override = normalized_route == "safe_override"
    preserve_structure = (
        normalized_route in NEO_PRESERVE_ROUTES or normalized_mode in NEO_PRESERVE_ROUTES
    )

    first = validator.validate(
        answer,
        route=route,
        mode=mode,
        safety_override=safety_override,
        query=query or "",
        preserve_structure=preserve_structure,
    )
    attempts.append(first.as_dict())
    final_text = first.text
    final_valid = bool(first.valid)

    if first.needs_regeneration and callable(generate_retry):
        hint = validator.build_regeneration_hint(
            first.errors,
            route=route,
            mode=mode,
            query=query or "",
        )
        try:
            retry_llm_result = generate_retry(hint)
        except Exception as exc:
            logger.warning("[OUTPUT_VALIDATOR] retry generation failed: %s", exc)
            retry_llm_result = {"error": str(exc), "answer": ""}

        retry_answer = str((retry_llm_result or {}).get("answer") or "")
        second = validator.validate(
            retry_answer,
            route=route,
            mode=mode,
            safety_override=safety_override,
            query=query or "",
            preserve_structure=preserve_structure,
        )
        attempts.append(second.as_dict())
        final_text = second.text
        final_valid = bool(second.valid)
        if second.needs_regeneration:
            fallback_used = True
            final_valid = False
            final_text = validator.safe_fallback(route=route)
    elif first.needs_regeneration:
        fallback_used = True
        final_valid = False
        final_text = validator.safe_fallback(route=route)

    meta = {
        "enabled": True,
        "attempts": attempts,
        "fallback_used": fallback_used,
        "final_valid": final_valid,
    }
    return final_text, meta, retry_llm_result
