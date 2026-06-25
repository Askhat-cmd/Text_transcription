"""Unified dialogue policy profile helpers for multiagent runtime."""

from __future__ import annotations

import re
from typing import Any


DIALOGUE_PROFILE_SAFE_GUIDED = "safe_guided"
DIALOGUE_PROFILE_MVP_FREE = "mvp_free_dialogue"
DIALOGUE_PROFILE_CUSTOM_DEV = "custom_dev"
ALLOWED_DIALOGUE_PROFILES = (
    DIALOGUE_PROFILE_SAFE_GUIDED,
    DIALOGUE_PROFILE_MVP_FREE,
    DIALOGUE_PROFILE_CUSTOM_DEV,
)
PROFILE_ALIAS_TO_PRESET = {
    DIALOGUE_PROFILE_SAFE_GUIDED: "safe_guided",
    DIALOGUE_PROFILE_MVP_FREE: "free_dialogue_default",
    DIALOGUE_PROFILE_CUSTOM_DEV: "custom_dev",
}
UNIFIED_DIALOGUE_POLICY_VERSION = "unified_dialogue_policy_v2"

SAFE_GUIDED_CONTEXT_BUDGET_CHARS = 3200
MVP_FREE_CONTEXT_BUDGET_CHARS = 7000
CUSTOM_DEV_CONTEXT_BUDGET_CHARS = 8500

_EXPANSION_MARKERS = (
    "развернуто",
    "развернут",
    "подробно",
    "подробнее",
    "полное объяснение",
    "объясни нормально",
    "я не понял",
    "не понимаю",
    "дай полный ответ",
    "обзор",
)
_REPAIR_AND_EXPAND_MARKERS = (
    "я не понял",
    "не понимаю",
    "это не ответ",
    "объясни нормально",
    "дай понятный полный ответ",
)
_SHORT_SUPPORT_MARKERS = (
    "коротко",
    "без анализа",
    "просто поддержи",
    "мне плохо",
    "не вывожу",
    "не справляюсь",
)
_PRACTICE_OVERVIEW_MARKERS = (
    "какие практики",
    "какие способы",
    "какие варианты",
    "какие направления",
    "как это видеть",
    "практики предлагаются",
)
_EXPLICIT_ONE_STEP_MARKERS = (
    "один шаг",
    "один конкретный шаг",
    "один микро-шаг",
    "дай шаг",
    "что сделать прямо сейчас",
    "что делать прямо сейчас",
)
_EXAMPLES_MARKERS = ("пример", "примеры", "на примере")
_NUMBERED_LIST_MARKERS = ("по пунктам", "списком", "по шагам")
_EXPLICIT_ANSWER_NEED_MARKERS = (
    "прямо ответь",
    "ответь на вопрос",
    "не уходи от вопроса",
    "скажи конкретно",
    "ответь мне на вопрос",
    "это не ответ",
)
_DIRECT_CONCRETE_MARKERS = (
    "назови конкретно",
    "какая конкретно",
    "что мне делать с",
    "что делать с",
    "конкретный ответ",
)
_SUMMARY_REQUEST_MARKERS = (
    "обобщи весь разговор",
    "суммируй весь разговор",
    "подведи итог",
    "сделай summary",
)
_SARCASM_OR_NEGATIVE_FEEDBACK_MARKERS = (
    "спасибо что ты не дал мне никаких ответов",
    "тебя что, заглючило",
    "ты не дал мне ответ",
    "это не ответ",
    "ты ушел от вопроса",
    "ты не ответил мне на вопрос",
    "ты не ответил",
)
_APPLICATION_REQUEST_MARKERS = (
    "как применять",
    "как применить",
    "в жизни",
    "как это использовать",
)


def normalize_dialogue_profile(value: Any) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in ALLOWED_DIALOGUE_PROFILES:
        return candidate
    return DIALOGUE_PROFILE_SAFE_GUIDED


def resolve_profile_preset(profile: Any) -> str:
    normalized = normalize_dialogue_profile(profile)
    return PROFILE_ALIAS_TO_PRESET.get(normalized, "safe_guided")


def detect_expansion_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _EXPANSION_MARKERS)


def detect_repair_and_expand_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _REPAIR_AND_EXPAND_MARKERS)


def detect_short_support_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _SHORT_SUPPORT_MARKERS)


def detect_practice_overview_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _PRACTICE_OVERVIEW_MARKERS)


def detect_explicit_one_step_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _EXPLICIT_ONE_STEP_MARKERS)


def detect_examples_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _EXAMPLES_MARKERS)


def detect_numbered_list_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _NUMBERED_LIST_MARKERS)


def detect_explicit_answer_need(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _EXPLICIT_ANSWER_NEED_MARKERS)


def detect_direct_concrete_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _DIRECT_CONCRETE_MARKERS)


def detect_summary_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _SUMMARY_REQUEST_MARKERS)


def detect_sarcasm_or_negative_feedback(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _SARCASM_OR_NEGATIVE_FEEDBACK_MARKERS)


def detect_application_request(user_message: str) -> bool:
    lowered = _normalize(user_message)
    return any(marker in lowered for marker in _APPLICATION_REQUEST_MARKERS)


def context_budget_for_profile(profile: str) -> int:
    normalized = normalize_dialogue_profile(profile)
    if normalized == DIALOGUE_PROFILE_MVP_FREE:
        return MVP_FREE_CONTEXT_BUDGET_CHARS
    if normalized == DIALOGUE_PROFILE_CUSTOM_DEV:
        return CUSTOM_DEV_CONTEXT_BUDGET_CHARS
    return SAFE_GUIDED_CONTEXT_BUDGET_CHARS


def build_effective_dialogue_policy(
    *,
    profile: str,
    user_message: str,
    state_snapshot: Any,
    thread_state: Any,
    knowledge_answer_guard: dict[str, Any],
) -> dict[str, Any]:
    normalized_profile = normalize_dialogue_profile(profile)
    profile_preset = resolve_profile_preset(normalized_profile)
    message = str(user_message or "")
    knowledge_answer = (
        dict(knowledge_answer_guard.get("knowledge_answer", {}))
        if isinstance(knowledge_answer_guard, dict)
        and isinstance(knowledge_answer_guard.get("knowledge_answer"), dict)
        else {}
    )

    safety_priority = _as_bool(_read_attr_or_key(state_snapshot, "safety_flag", False)) or _as_bool(
        _read_attr_or_key(thread_state, "safety_active", False)
    ) or str(_read_attr_or_key(thread_state, "response_mode", "") or "") == "safe_override"

    expansion_requested = detect_expansion_request(message)
    repair_and_expand_requested = detect_repair_and_expand_request(message)
    explicit_short_support_requested = detect_short_support_request(message)
    practice_overview_requested = detect_practice_overview_request(message)
    explicit_one_step_requested = detect_explicit_one_step_request(message)
    examples_requested = detect_examples_request(message)
    numbered_list_requested = detect_numbered_list_request(message)
    explicit_answer_need = detect_explicit_answer_need(message)
    direct_concrete_request = detect_direct_concrete_request(message)
    summary_request = detect_summary_request(message)
    sarcasm_or_negative_feedback = detect_sarcasm_or_negative_feedback(message)
    application_request = detect_application_request(message)

    knowledge_needed = bool(knowledge_answer.get("needed", False))
    active_concept = str(knowledge_answer.get("concept", "") or "").strip().lower()
    knowledge_answer_type = str(knowledge_answer.get("answer_type", "") or "").strip().lower()
    concept_or_practice_need = bool(
        knowledge_needed or practice_overview_requested or knowledge_answer_type == "practice_overview"
    )
    rich_answer_requested = bool(
        expansion_requested
        or repair_and_expand_requested
        or practice_overview_requested
        or examples_requested
        or numbered_list_requested
        or summary_request
        or direct_concrete_request
        or application_request
        or explicit_answer_need
        or sarcasm_or_negative_feedback
    )
    style_preference_priority = bool(
        expansion_requested or explicit_short_support_requested or repair_and_expand_requested
    )
    compact_support_answer = bool(
        not safety_priority
        and profile_preset != "safe_guided"
        and not rich_answer_requested
        and not concept_or_practice_need
        and not explicit_answer_need
        and not direct_concrete_request
        and not application_request
        and not summary_request
    )

    if safety_priority:
        answer_depth = "short"
    elif explicit_short_support_requested and not rich_answer_requested:
        answer_depth = "short"
    elif explicit_one_step_requested and not rich_answer_requested:
        answer_depth = "short"
    elif profile_preset == "safe_guided":
        answer_depth = "medium" if concept_or_practice_need or explicit_answer_need else "short"
    elif profile_preset == "custom_dev":
        answer_depth = "long"
    elif rich_answer_requested or concept_or_practice_need or explicit_answer_need:
        answer_depth = "long"
    else:
        answer_depth = "medium"

    allow_richer_format = bool(
        not safety_priority
        and profile_preset in {"free_dialogue_default", "custom_dev"}
        and not explicit_short_support_requested
        and (rich_answer_requested or concept_or_practice_need)
    )
    practice_catalog_allowed = bool(
        not safety_priority
        and profile_preset in {"free_dialogue_default", "custom_dev"}
        and practice_overview_requested
    )
    human_like_enabled = not safety_priority
    writer_autonomy = "high" if profile_preset in {"free_dialogue_default", "custom_dev"} else "medium"
    effective_safety_floor = "minimal_baseline"
    planner_advisory = True
    base_constraints = [
        "max_sentences=5",
        "do_not_over_explain",
        "do_not_offer_list",
        "do_not_expand_theory",
        "offer_only_one_next_step",
        "ask_at_most_one_question",
    ]
    allow_constraint_overrule = bool(
        human_like_enabled
        and (
            explicit_answer_need
            or rich_answer_requested
            or concept_or_practice_need
            or sarcasm_or_negative_feedback
            or summary_request
            or direct_concrete_request
            or application_request
        )
    )
    overrule_reason = "none"
    if allow_constraint_overrule:
        overrule_reason = "explicit_user_request_or_human_like_policy"
    if explicit_answer_need:
        overrule_reason = "direct_contextual_followup_to_previous_offer"

    hard_boundaries = [
        "safety",
        "crisis_routing",
        "no_diagnosis",
        "no_medical_legal_financial_directives",
        "no_spiritual_authority",
        "no_raw_kb_quote_dumping",
        "privacy_sanitized_trace_only",
    ]
    soft_guidance = [
        "state",
        "thread",
        "planner",
        "diagnostic_card",
        "knowledge_context",
        "style_preference",
        "target_micro_shift",
    ]

    return {
        "version": UNIFIED_DIALOGUE_POLICY_VERSION,
        "profile": normalized_profile,
        "active_profile_alias": normalized_profile,
        "profile_preset": profile_preset,
        "authority_order": [
            "minimal_safety_baseline",
            "explicit_user_request",
            "knowledge_or_concept_need",
            "writer_freedom",
            "planner_and_diagnostic_advisory",
        ],
        "minimal_safety_baseline": True,
        "effective_writer_autonomy": writer_autonomy,
        "writer_autonomy": writer_autonomy,
        "effective_safety_floor": effective_safety_floor,
        "planner_authority": "advisory",
        "diagnostic_card_authority": "advisory",
        "writer_move_authority": "advisory",
        "active_line_authority": "advisory",
        "knowledge_answer_priority": "high" if concept_or_practice_need else "normal",
        "user_explicit_request_priority": "highest_after_safety",
        "answer_depth": answer_depth,
        "allow_numbered_lists": allow_richer_format or numbered_list_requested,
        "allow_examples": allow_richer_format or examples_requested,
        "allow_practice_catalog": practice_catalog_allowed,
        "allow_multi_step_overview": practice_catalog_allowed,
        "human_like_answer_policy": {
            "enabled": human_like_enabled,
            "answer_style": "human_chatgpt_like" if human_like_enabled else "guided_compact",
            "default_depth": (
                "short_to_medium"
                if compact_support_answer or profile_preset == "safe_guided"
                else "medium_to_long"
            ),
            "allow_long_answers": bool(profile_preset != "safe_guided" and not compact_support_answer),
            "allow_lists": bool((profile_preset != "safe_guided") and (numbered_list_requested or rich_answer_requested)),
            "allow_examples": bool((profile_preset != "safe_guided") and (examples_requested or rich_answer_requested)),
            "allow_direct_answer": True,
            "allow_reflection_plus_explanation_plus_step": bool(profile_preset != "safe_guided" and not compact_support_answer),
            "allow_multiple_options": bool(profile_preset != "safe_guided" and not compact_support_answer),
            "question_is_optional": True,
            "micro_step_only_when_user_explicitly_requests_one_step": True,
            "do_not_force_question_at_end": True,
            "do_not_force_practice_frame": True,
            "do_not_force_max_sentences": profile_preset != "safe_guided",
            "respect_user_requested_format": True,
            "sarcasm_and_dissatisfaction_repair": True,
            "direct_answer_repair_when_user_complains": True,
            "support_answer_compactness": "ordinary_support_compact" if compact_support_answer else "adaptive",
            "preferred_shape": (
                "one_main_point_one_optional_next_step"
                if compact_support_answer
                else "adaptive"
            ),
            "target_length_chars": "450_1100" if compact_support_answer else "",
            "avoid_mechanism_heavy_default": compact_support_answer,
            "prefer_direct_answer_first": compact_support_answer,
            "prefer_single_main_mechanism": compact_support_answer,
            "max_list_items": 3 if compact_support_answer else 0,
        },
        "constraint_resolution": {
            "profile": normalized_profile,
            "planner_authority": "advisory",
            "overruled_constraints": base_constraints if allow_constraint_overrule else [],
            "overrule_reason": overrule_reason,
        },
        "must_not_force_one_step": bool(not explicit_one_step_requested and (practice_overview_requested or rich_answer_requested or concept_or_practice_need)),
        "context_budget_chars": context_budget_for_profile(normalized_profile),
        "semantic_hits_budget": {
            "max_hits": 4 if profile_preset != "safe_guided" else 2,
            "max_chars_per_hit": 900 if profile_preset != "safe_guided" else 300,
        },
        "expansion_requested": expansion_requested,
        "repair_and_expand_requested": repair_and_expand_requested,
        "explicit_short_support_requested": explicit_short_support_requested,
        "explicit_one_step_requested": explicit_one_step_requested,
        "practice_overview_requested": practice_overview_requested,
        "examples_requested": examples_requested,
        "numbered_list_requested": numbered_list_requested,
        "explicit_answer_need": explicit_answer_need,
        "direct_concrete_request": direct_concrete_request,
        "summary_request": summary_request,
        "sarcasm_or_negative_feedback": sarcasm_or_negative_feedback,
        "application_request": application_request,
        "style_preference_priority": style_preference_priority,
        "compact_support_answer": compact_support_answer,
        "active_concept": active_concept,
        "knowledge_answer_type": knowledge_answer_type,
        "planner_is_advisory": planner_advisory,
        "final_answer_directive_enabled": True,
        "final_answer_directive_role": "single_control_block",
        "writer_context_package_role": "single_context_package",
        "writer_first_prompt_assembly_enabled": True,
        "legacy_blocks_visible_to_writer": False,
        "legacy_blocks_source_signals_only": True,
        "legacy_prompt_blocks_mode": "source_signals_only",
        "diagnostic_center_role": "advisory_context_only",
        "planner_role": "advisory_context_only",
        "active_line_role": "advisory_context_only",
        "diagnostic_card_role": "advisory_context_only",
        "hard_boundaries": hard_boundaries,
        "soft_guidance": soft_guidance,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
        "mvp_overrides": {
            "explicit_user_request_wins": True,
            "old_max_sentence_constraints_softened": profile_preset != "safe_guided",
            "planner_advisory": True,
            "overview_questions_allow_lists": practice_catalog_allowed,
            "question_is_optional": True,
            "repair_user_dissatisfaction": True,
            "target_answer_depth": answer_depth,
        },
    }


def format_conversation_context_for_writer(
    conversation_context: str,
    profile: str,
    budget_chars: int,
) -> str:
    formatted, _ = format_conversation_context_for_writer_with_meta(
        conversation_context=conversation_context,
        profile=profile,
        budget_chars=budget_chars,
    )
    return formatted


def format_conversation_context_for_writer_with_meta(
    *,
    conversation_context: str,
    profile: str,
    budget_chars: int | None = None,
) -> tuple[str, dict[str, Any]]:
    raw_context = str(conversation_context or "").strip()
    if not raw_context:
        return "нет", {
            "context_budget_chars": 0,
            "context_truncated": False,
            "preserved_recent_turns_count": 0,
            "older_context_omitted_chars": 0,
        }

    normalized_profile = normalize_dialogue_profile(profile)
    limit = int(budget_chars or context_budget_for_profile(normalized_profile))
    if limit < 800:
        limit = 800

    if len(raw_context) <= limit:
        return raw_context, {
            "context_budget_chars": limit,
            "context_truncated": False,
            "preserved_recent_turns_count": _estimate_preserved_turns(raw_context),
            "older_context_omitted_chars": 0,
        }

    tail = raw_context[-limit:]
    split_match = re.search(
        r"(RECENT\s+(?:FULL|EXACT|SUMMARIZED)\s+TURNS:|USER#turn_|ASSISTANT#turn_)",
        tail,
        flags=re.IGNORECASE,
    )
    if split_match:
        start_idx = split_match.start()
        if start_idx > 0:
            tail = tail[start_idx:]

    omitted_chars = max(0, len(raw_context) - len(tail))
    formatted = f"[older context omitted: {omitted_chars} chars]\n{tail}"
    return formatted, {
        "context_budget_chars": limit,
        "context_truncated": True,
        "preserved_recent_turns_count": _estimate_preserved_turns(tail),
        "older_context_omitted_chars": omitted_chars,
    }


def extract_last_active_concept(active_frame: dict[str, Any] | None) -> str:
    if not isinstance(active_frame, dict):
        return ""
    return str(active_frame.get("active_concept", "") or "").strip().lower()


def apply_active_concept_continuation(
    *,
    user_message: str,
    dialogue_profile: str,
    knowledge_answer_guard: dict[str, Any],
    thread_active_frame: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    """Inject previous active concept on expansion follow-up in MVP profile."""
    guard = dict(knowledge_answer_guard or {})
    knowledge_answer = (
        dict(guard.get("knowledge_answer", {}))
        if isinstance(guard.get("knowledge_answer"), dict)
        else {}
    )
    concept = str(knowledge_answer.get("concept", "") or "").strip().lower()
    previous = extract_last_active_concept(thread_active_frame)
    profile = normalize_dialogue_profile(dialogue_profile)
    expansion_requested = detect_expansion_request(user_message)

    if concept:
        return guard, concept

    if profile == DIALOGUE_PROFILE_MVP_FREE and expansion_requested and previous:
        knowledge_answer["needed"] = True
        knowledge_answer["concept"] = previous
        knowledge_answer["should_answer_directly"] = True
        knowledge_answer["kb_grounding_available"] = bool(
            knowledge_answer.get("kb_grounding_available", True)
        )
        reason = str(knowledge_answer.get("reason", "no_known_concept_question") or "")
        knowledge_answer["reason"] = (
            "followup_expansion_inherits_active_concept"
            if reason == "no_known_concept_question"
            else reason
        )
        guard["knowledge_answer"] = knowledge_answer
        return guard, previous

    return guard, previous


def _estimate_preserved_turns(context: str) -> int:
    matches = re.findall(r"(?:USER|ASSISTANT)#turn_", context, flags=re.IGNORECASE)
    return len(matches)


def _read_attr_or_key(obj: Any, key: str, default: Any) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on"}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


__all__ = [
    "ALLOWED_DIALOGUE_PROFILES",
    "DIALOGUE_PROFILE_CUSTOM_DEV",
    "DIALOGUE_PROFILE_MVP_FREE",
    "DIALOGUE_PROFILE_SAFE_GUIDED",
    "MVP_FREE_CONTEXT_BUDGET_CHARS",
    "SAFE_GUIDED_CONTEXT_BUDGET_CHARS",
    "UNIFIED_DIALOGUE_POLICY_VERSION",
    "PROFILE_ALIAS_TO_PRESET",
    "apply_active_concept_continuation",
    "build_effective_dialogue_policy",
    "context_budget_for_profile",
    "detect_application_request",
    "detect_direct_concrete_request",
    "detect_examples_request",
    "detect_expansion_request",
    "detect_explicit_answer_need",
    "detect_explicit_one_step_request",
    "detect_numbered_list_request",
    "detect_practice_overview_request",
    "detect_repair_and_expand_request",
    "detect_sarcasm_or_negative_feedback",
    "detect_short_support_request",
    "detect_summary_request",
    "format_conversation_context_for_writer",
    "format_conversation_context_for_writer_with_meta",
    "normalize_dialogue_profile",
    "resolve_profile_preset",
]
