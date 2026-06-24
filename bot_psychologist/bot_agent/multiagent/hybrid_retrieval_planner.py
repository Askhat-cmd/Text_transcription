"""Hybrid Retrieval Planner for PRD-047.15-HF2-R1."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from ..feature_flags import feature_flags
from .agents.agent_llm_client import create_agent_completion
from .agents.agent_llm_config import get_model_for_agent
from .contracts.hybrid_retrieval_planner_contract import (
    ALLOWED_CHUNK_TYPES,
    ALLOWED_PLANNER_MODES,
    ALLOWED_RETRIEVAL_ACTIONS,
    HYBRID_RETRIEVAL_PLANNER_VERSION,
    HybridRetrievalPlan,
    normalize_chunk_type,
)


logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9][a-zA-Zа-яА-ЯёЁ0-9_-]{1,}")
_GREETING_MARKERS = ("привет", "здравствуй", "здравствуйте", "hello", "hi", "hey")
_THANKS_MARKERS = ("спасибо", "благодарю", "thanks", "thank you", "пока", "до свидания", "bye")
_REJECT_MARKERS = ("нет", "не хочу", "не надо", "не нужно", "stop", "no")
_SUMMARY_MARKERS = ("подведи итог", "краткий итог", "резюме", "summary", "recap")
_FORMAT_MARKERS = ("короче", "списком", "без воды", "в двух словах", "markdown", "bullet", "список")
_SHORT_SUPPORT_MARKERS = ("просто поддержи", "без советов", "пару спокойных слов", "just support", "just stay")
_NO_THEORY_MARKERS = ("без теории", "без практик", "не нужно практик", "без упражнений")
_KB_ASK_MARKERS = ("что такое", "что значит", "объясни", "расскажи", "как работает", "в чем разница", "в чём разница")
_MECHANISM_MARKERS = {
    "контрол": "control_as_safety",
    "паник": "panic_regulation",
    "стыд": "shame_loop",
    "тревог": "anxiety_cycle",
    "вина": "guilt_loop",
    "злость": "anger_protection",
}
_SAFETY_MARKERS = (
    "умру",
    "умереть",
    "себя убить",
    "убить себя",
    "суицид",
    "паника",
    "паническая атака",
    "не могу дышать",
    "если перестану контролировать",
)
_FOLLOWUP_COMPLEX_MARKERS = ("на моем примере", "на моём примере", "как это связано", "но без теории", "но с примером")
_ADVICE_LIKE_QUERY_MARKERS = ("скажи пользователю", "ответь пользователю", "you should tell the user")
_ALLOWED_USE_HINTS = {"writer_support", "diagnostic_hint", "practice_suggestion"}
_PLANNER_SYSTEM = """Ты Hybrid Retrieval Planner для психологического диалогового бота.
Ты НЕ отвечаешь пользователю.
Ты НЕ пишешь финальный ответ.
Ты НЕ даёшь совет.
Ты НЕ ставишь диагноз.
Ты НЕ являешься терапевтом.

Твоя задача — вернуть только JSON retrieval_plan:
- нужен ли retrieval;
- какой retrieval_action выбрать;
- какой composed_query выполнить до RAG;
- какие chunk types желательны;
- какие mechanism hints могут помочь поиску;
- какая глубина допустима;
- какие ограничения передать Writer'у как metadata.

Writer остаётся единственным автором ответа и может игнорировать retrieval.
Верни только JSON. Никакого markdown, никаких пояснений вне JSON."""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _normalize(text)
    return any(marker in lowered for marker in markers)


def _extract_terms(*texts: str, max_terms: int = 8) -> list[str]:
    joined = " ".join(str(item or "") for item in texts)
    seen: set[str] = set()
    result: list[str] = []
    for token in _WORD_RE.findall(joined):
        normalized = token.lower().replace("ё", "е").strip(" -_")
        if len(normalized) < 3:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
        if len(result) >= max_terms:
            break
    return result


def _clean_literal_kb_query(text: str) -> str:
    lowered = _normalize(text)
    cleaned = lowered
    for marker in _KB_ASK_MARKERS:
        cleaned = cleaned.replace(marker, " ")
    cleaned = re.sub(r"[?!.:,;]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = lowered
    return " ".join(_extract_terms(cleaned, max_terms=8))[:280].strip()


def _build_generic_query(*texts: str, max_chars: int = 280) -> str:
    return " ".join(_extract_terms(*texts, max_terms=10))[:max_chars].strip()


def _mechanism_hints_from_text(text: str) -> list[str]:
    lowered = _normalize(text)
    result: list[str] = []
    for marker, hint in _MECHANISM_MARKERS.items():
        if marker in lowered and hint not in result:
            result.append(hint)
    if (
        "loss_of_control_as_threat" not in result
        and (
            "если перестану контролировать" in lowered
            or (
                "контрол" in lowered
                and any(marker in lowered for marker in ("умр", "умереть", "смерт"))
            )
        )
    ):
        result.append("loss_of_control_as_threat")
    return result


def _constraints_from_text(text: str) -> list[str]:
    lowered = _normalize(text)
    constraints: list[str] = []
    if "без теории" in lowered:
        constraints.append("no_theory")
    if "без практик" in lowered or "без упражнений" in lowered:
        constraints.append("no_practice")
    if "короче" in lowered or "в двух словах" in lowered:
        constraints.append("keep_brief")
    if "списком" in lowered:
        constraints.append("list_ok")
    return constraints


def _build_plan_dict(plan: HybridRetrievalPlan) -> dict[str, Any]:
    payload = plan.to_dict()
    if not payload["needed_chunk_types"]:
        payload["needed_chunk_types"] = ["general_text"]
    return payload


def _owner_status_fields(
    *,
    mode: str,
    planner_status: str,
    fallback_used: bool,
    owner_severity: str = "info",
) -> dict[str, Any]:
    shadow_only = mode == "shadow" and bool(fallback_used)
    return {
        "planner_status": planner_status,
        "owner_severity": owner_severity,
        "fallback_scope": "shadow_only" if shadow_only else "none",
        "production_query_source": "current_turn_focus_v1",
        "production_answer_affected": False,
    }


def _validate_plan_payload(raw_plan: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(raw_plan, dict):
        return None, "plan_not_dict"
    if raw_plan.get("no_user_facing_text_created") is not True:
        return None, "no_user_facing_text_created_must_be_true"
    action = str(raw_plan.get("retrieval_action", "") or "")
    if action not in ALLOWED_RETRIEVAL_ACTIONS:
        return None, "unknown_retrieval_action"
    confidence = raw_plan.get("confidence", 0.0)
    try:
        confidence_value = float(confidence)
    except (TypeError, ValueError):
        return None, "confidence_not_numeric"
    if not 0.0 <= confidence_value <= 1.0:
        return None, "confidence_out_of_range"
    composed_query = str(raw_plan.get("composed_query", "") or "").strip()
    if any(marker in composed_query.lower() for marker in _ADVICE_LIKE_QUERY_MARKERS):
        return None, "advice_like_composed_query"
    needed_chunk_types = raw_plan.get("needed_chunk_types", [])
    avoided_chunk_types = raw_plan.get("avoided_chunk_types", [])
    allowed_use_filter_hint = raw_plan.get("allowed_use_filter_hint", [])
    normalized = HybridRetrievalPlan(
        retrieval_needed=bool(raw_plan.get("retrieval_needed", False)),
        retrieval_action=action,
        composed_query=composed_query[:280],
        needed_chunk_types=[normalize_chunk_type(item) for item in list(needed_chunk_types or [])],
        avoided_chunk_types=[normalize_chunk_type(item) for item in list(avoided_chunk_types or [])],
        mechanism_hints=[str(item) for item in list(raw_plan.get("mechanism_hints", []) or []) if str(item).strip()],
        depth_level_hint=int(raw_plan.get("depth_level_hint", 0) or 0),
        safety_layer_required=bool(raw_plan.get("safety_layer_required", False)),
        allowed_use_filter_hint=[
            str(item) for item in list(allowed_use_filter_hint or []) if str(item).strip() and str(item) in _ALLOWED_USE_HINTS
        ] or ["writer_support"],
        diagnostic_hints_used=bool(raw_plan.get("diagnostic_hints_used", False)),
        writer_can_ignore_rag=bool(raw_plan.get("writer_can_ignore_rag", True)),
        retrieval_gap_reason=str(raw_plan.get("retrieval_gap_reason", "") or ""),
        no_user_facing_text_created=True,
        fallback_if_invalid=str(raw_plan.get("fallback_if_invalid", "legacy_query") or "legacy_query"),
        constraints_for_writer=[str(item) for item in list(raw_plan.get("constraints_for_writer", []) or []) if str(item).strip()],
        confidence=confidence_value,
    ).to_dict()
    return normalized, None


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        parsed = json.loads(cleaned[start : end + 1])
    return dict(parsed)


def get_hybrid_retrieval_planner_mode() -> str:
    mode = str(feature_flags.value("HYBRID_RETRIEVAL_PLANNER_MODE", "shadow") or "shadow").strip().lower()
    return mode if mode in ALLOWED_PLANNER_MODES else "shadow"


def get_hybrid_retrieval_planner_settings() -> dict[str, Any]:
    return {
        "enabled": get_hybrid_retrieval_planner_mode() != "off",
        "mode": get_hybrid_retrieval_planner_mode(),
        "version": HYBRID_RETRIEVAL_PLANNER_VERSION,
        "model": str(feature_flags.value("HYBRID_RETRIEVAL_PLANNER_MODEL", get_model_for_agent("state_analyzer"))),
        "max_tokens": int(feature_flags.value("HYBRID_RETRIEVAL_PLANNER_MAX_TOKENS", "320") or "320"),
    }


def _universal_gate_plan(
    *,
    user_message: str,
    last_assistant_offer: dict[str, Any] | None,
    dialogue_pragmatics: dict[str, Any] | None,
    state_snapshot_compact: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str]:
    text = str(user_message or "")
    lowered = _normalize(text)
    last_offer = dict(last_assistant_offer or {})
    pragmatics = dict(dialogue_pragmatics or {})
    state = dict(state_snapshot_compact or {})
    constraints = _constraints_from_text(text)

    if bool(state.get("safety_active")) or _contains_any(lowered, _SAFETY_MARKERS):
        return (
            _build_plan_dict(
                HybridRetrievalPlan(
                    retrieval_needed=True,
                    retrieval_action="query_kb",
                    composed_query=_build_generic_query(text, "safety regulation mechanism"),
                    needed_chunk_types=["safety", "mechanism", "dialogue_move"],
                    mechanism_hints=_mechanism_hints_from_text(text),
                    depth_level_hint=1,
                    safety_layer_required=True,
                    allowed_use_filter_hint=["writer_support", "diagnostic_hint"],
                    writer_can_ignore_rag=True,
                    constraints_for_writer=constraints,
                    confidence=0.9,
                )
            ),
            "safety_signal",
        )
    if _contains_any(lowered, _GREETING_MARKERS):
        return _build_plan_dict(HybridRetrievalPlan(retrieval_action="suppress_rag", confidence=0.98)), "greeting"
    if _contains_any(lowered, _THANKS_MARKERS):
        return _build_plan_dict(HybridRetrievalPlan(retrieval_action="suppress_rag", confidence=0.97)), "thanks_or_farewell"
    if _contains_any(lowered, _SUMMARY_MARKERS):
        return (
            _build_plan_dict(
                HybridRetrievalPlan(
                    retrieval_action="use_current_context_only",
                    writer_can_ignore_rag=True,
                    constraints_for_writer=constraints,
                    confidence=0.95,
                )
            ),
            "summary_request",
        )
    if _contains_any(lowered, _FORMAT_MARKERS):
        return (
            _build_plan_dict(
                HybridRetrievalPlan(
                    retrieval_action="use_current_context_only",
                    writer_can_ignore_rag=True,
                    constraints_for_writer=constraints,
                    confidence=0.92,
                )
            ),
            "formatting_request",
        )
    if lowered in {"нет", "не хочу", "не надо", "no"} or _contains_any(lowered, _REJECT_MARKERS):
        return (
            _build_plan_dict(
                HybridRetrievalPlan(
                    retrieval_action="use_current_context_only",
                    writer_can_ignore_rag=True,
                    constraints_for_writer=constraints,
                    confidence=0.86,
                )
            ),
            "explicit_reject",
        )
    if _contains_any(lowered, _SHORT_SUPPORT_MARKERS):
        return (
            _build_plan_dict(
                HybridRetrievalPlan(
                    retrieval_action="suppress_rag",
                    writer_can_ignore_rag=True,
                    constraints_for_writer=constraints,
                    confidence=0.88,
                )
            ),
            "short_support",
        )
    if any(marker in lowered for marker in _FOLLOWUP_COMPLEX_MARKERS):
        return None, "complex_or_low_confidence"
    if any(marker in lowered for marker in _KB_ASK_MARKERS) and len(_extract_terms(text, max_terms=10)) >= 1:
        return (
            _build_plan_dict(
                HybridRetrievalPlan(
                    retrieval_needed=True,
                    retrieval_action="query_kb",
                    composed_query=_clean_literal_kb_query(text),
                    needed_chunk_types=["concept", "source_fragment"],
                    mechanism_hints=_mechanism_hints_from_text(text),
                    depth_level_hint=1,
                    writer_can_ignore_rag=False,
                    constraints_for_writer=constraints,
                    confidence=0.84,
                )
            ),
            "clear_kb_ask",
        )
    if lowered in {"да", "давай", "ок", "хорошо"} and bool(last_offer.get("is_open", False)):
        offer_type = str(last_offer.get("offer_type", "") or "")
        if offer_type in {"short_support", "short_phrase", "one_step"}:
            return (
                _build_plan_dict(
                    HybridRetrievalPlan(
                        retrieval_action="use_current_context_only",
                        writer_can_ignore_rag=True,
                        constraints_for_writer=constraints,
                        confidence=0.81,
                    )
                ),
                "short_accept_followup",
            )
    if bool(pragmatics.get("is_contextual_followup", False)) and not _contains_any(lowered, _KB_ASK_MARKERS):
        return (
            _build_plan_dict(
                HybridRetrievalPlan(
                    retrieval_action="use_current_context_only",
                    writer_can_ignore_rag=True,
                    constraints_for_writer=constraints,
                    confidence=0.72,
                )
            ),
            "contextual_followup",
        )
    return None, "complex_or_low_confidence"


def _planner_input_payload(
    *,
    user_message: str,
    recent_turns_compact: list[dict[str, Any]] | None,
    last_assistant_offer: dict[str, Any] | None,
    thread_state_compact: dict[str, Any] | None,
    state_snapshot_compact: dict[str, Any] | None,
    dialogue_pragmatics: dict[str, Any] | None,
    fresh_chat_policy: dict[str, Any] | None,
    constraints: list[str] | None,
) -> dict[str, Any]:
    return {
        "user_message": str(user_message or "")[:1200],
        "recent_turns_compact": list(recent_turns_compact or [])[:4],
        "last_assistant_offer": dict(last_assistant_offer or {}),
        "thread_state_compact": dict(thread_state_compact or {}),
        "state_snapshot_compact": dict(state_snapshot_compact or {}),
        "dialogue_pragmatics": dict(dialogue_pragmatics or {}),
        "fresh_chat_policy": dict(fresh_chat_policy or {}),
        "constraints": [str(item) for item in list(constraints or []) if str(item).strip()],
        "available_chunk_type_vocab": sorted(ALLOWED_CHUNK_TYPES),
    }


async def build_hybrid_retrieval_plan_v1(
    *,
    user_message: str,
    recent_turns_compact: list[dict[str, Any]] | None = None,
    last_assistant_offer: dict[str, Any] | None = None,
    thread_state_compact: dict[str, Any] | None = None,
    state_snapshot_compact: dict[str, Any] | None = None,
    dialogue_pragmatics: dict[str, Any] | None = None,
    fresh_chat_policy: dict[str, Any] | None = None,
    constraints: list[str] | None = None,
    planner_mode: str | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    mode = str(planner_mode or get_hybrid_retrieval_planner_mode() or "shadow").strip().lower()
    if mode not in ALLOWED_PLANNER_MODES:
        mode = "shadow"

    universal_plan, universal_gate = _universal_gate_plan(
        user_message=user_message,
        last_assistant_offer=last_assistant_offer,
        dialogue_pragmatics=dialogue_pragmatics,
        state_snapshot_compact=state_snapshot_compact,
    )
    if universal_plan is not None:
        return {
            "version": HYBRID_RETRIEVAL_PLANNER_VERSION,
            "mode": mode,
            "plan": universal_plan,
            "valid": True,
            "error": None,
            "universal_gate": universal_gate,
            "llm_called": False,
            "llm_reason": "universal_gate_resolved",
            "fallback_used": False,
            **_owner_status_fields(
                mode=mode,
                planner_status="valid",
                fallback_used=False,
            ),
        }

    base_constraints = _constraints_from_text(user_message)
    if constraints:
        base_constraints.extend(str(item) for item in constraints if str(item).strip())
    base_constraints = list(dict.fromkeys(base_constraints))
    llm_reason = "complex_or_low_confidence"
    if client is None or mode == "off":
        fallback_plan = _build_plan_dict(
            HybridRetrievalPlan(
                retrieval_needed=False,
                retrieval_action="trace_only",
                composed_query="",
                mechanism_hints=_mechanism_hints_from_text(user_message),
                constraints_for_writer=base_constraints,
                confidence=0.0,
            )
        )
        return {
            "version": HYBRID_RETRIEVAL_PLANNER_VERSION,
            "mode": mode,
            "plan": fallback_plan,
            "valid": True,
            "error": None,
            "universal_gate": universal_gate,
            "llm_called": False,
            "llm_reason": "planner_client_unavailable" if client is None else "planner_mode_off",
            "fallback_used": True,
            **_owner_status_fields(
                mode=mode,
                planner_status="shadow_client_unavailable" if mode == "shadow" else "planner_unavailable",
                fallback_used=True,
            ),
        }

    prompt_payload = _planner_input_payload(
        user_message=user_message,
        recent_turns_compact=recent_turns_compact,
        last_assistant_offer=last_assistant_offer,
        thread_state_compact=thread_state_compact,
        state_snapshot_compact=state_snapshot_compact,
        dialogue_pragmatics=dialogue_pragmatics,
        fresh_chat_policy=fresh_chat_policy,
        constraints=base_constraints,
    )
    try:
        model = str(feature_flags.value("HYBRID_RETRIEVAL_PLANNER_MODEL", get_model_for_agent("state_analyzer")))
        result = await create_agent_completion(
            client=client,
            model=model,
            messages=[
                {"role": "system", "content": _PLANNER_SYSTEM},
                {"role": "user", "content": json.dumps(prompt_payload, ensure_ascii=False)},
            ],
            temperature=0.0,
            max_tokens=int(feature_flags.value("HYBRID_RETRIEVAL_PLANNER_MAX_TOKENS", "320") or "320"),
            response_format={"type": "json_object"},
            require_json=True,
        )
        parsed = _parse_json_object(result.text or "{}")
        validated, error = _validate_plan_payload(parsed)
        if validated is None:
            fallback_plan = _build_plan_dict(
                HybridRetrievalPlan(
                    retrieval_action="trace_only",
                    mechanism_hints=_mechanism_hints_from_text(user_message),
                    constraints_for_writer=base_constraints,
                    retrieval_gap_reason="legacy_fallback_used",
                    confidence=0.0,
                )
            )
            return {
                "version": HYBRID_RETRIEVAL_PLANNER_VERSION,
                "mode": mode,
                "plan": fallback_plan,
                "valid": False,
                "error": error,
                "universal_gate": universal_gate,
                "llm_called": True,
                "llm_reason": llm_reason,
                "fallback_used": True,
                **_owner_status_fields(
                    mode=mode,
                    planner_status="shadow_invalid_plan" if mode == "shadow" else "invalid_plan",
                    fallback_used=True,
                ),
                "llm_tokens_prompt": result.tokens_prompt,
                "llm_tokens_completion": result.tokens_completion,
                "llm_tokens_total": result.tokens_total,
            }
        return {
            "version": HYBRID_RETRIEVAL_PLANNER_VERSION,
            "mode": mode,
            "plan": validated,
            "valid": True,
            "error": None,
            "universal_gate": universal_gate,
            "llm_called": True,
            "llm_reason": llm_reason,
            "fallback_used": False,
            **_owner_status_fields(
                mode=mode,
                planner_status="valid",
                fallback_used=False,
            ),
            "llm_tokens_prompt": result.tokens_prompt,
            "llm_tokens_completion": result.tokens_completion,
            "llm_tokens_total": result.tokens_total,
        }
    except Exception as exc:  # noqa: BLE001
        logger.debug("[HYBRID_RETRIEVAL] planner fallback used in %s mode: %s", mode, exc.__class__.__name__)
        fallback_plan = _build_plan_dict(
            HybridRetrievalPlan(
                retrieval_action="trace_only",
                mechanism_hints=_mechanism_hints_from_text(user_message),
                constraints_for_writer=base_constraints,
                retrieval_gap_reason="legacy_fallback_used",
                confidence=0.0,
            )
        )
        invalid_json = isinstance(exc, json.JSONDecodeError)
        compact_error = "JSONDecodeError:invalid_json" if invalid_json else f"{exc.__class__.__name__}:planner_error"
        return {
            "version": HYBRID_RETRIEVAL_PLANNER_VERSION,
            "mode": mode,
            "plan": fallback_plan,
            "valid": False,
            "error": compact_error,
            "universal_gate": universal_gate,
            "llm_called": True,
            "llm_reason": llm_reason,
            "fallback_used": True,
            **_owner_status_fields(
                mode=mode,
                planner_status=(
                    "shadow_invalid_json"
                    if mode == "shadow" and invalid_json
                    else "shadow_error"
                    if mode == "shadow"
                    else "invalid_json"
                    if invalid_json
                    else "planner_error"
                ),
                fallback_used=True,
            ),
        }


__all__ = [
    "ALLOWED_CHUNK_TYPES",
    "HYBRID_RETRIEVAL_PLANNER_VERSION",
    "build_hybrid_retrieval_plan_v1",
    "get_hybrid_retrieval_planner_mode",
    "get_hybrid_retrieval_planner_settings",
]
