"""Deterministic dialogue pragmatics and contextual retrieval gating helpers."""

from __future__ import annotations

import re
from typing import Any

from .contracts.memory_bundle import SemanticHit

DIALOGUE_PRAGMATICS_VERSION = "dialogue_pragmatics_v1"
CONTEXTUAL_RETRIEVAL_GATING_VERSION = "contextual_retrieval_gating_v1"

_AFFIRM_SHORT_MARKERS = {
    "да",
    "давай",
    "конечно",
    "ок",
    "okay",
    "ok",
    "угу",
    "ага",
    "yes",
    "sure",
}
_CLOSE_ACK_MARKERS = {
    "спасибо",
    "благодарю",
    "понял",
    "поняла",
    "ясно",
    "ок",
    "окей",
    "thanks",
    "thank you",
}
_FOLLOWUP_IMPERATIVE_MARKERS = (
    "предложи",
    "покажи",
    "приведи",
    "объясни",
    "разверни",
    "дальше",
    "ответь",
    "разберем",
    "разберём",
    "continue",
    "show",
    "explain",
)
_REPAIR_DISSATISFACTION_MARKERS = (
    "ты снова не ответил",
    "ты опять не ответил",
    "ты не ответил мне на вопрос",
    "ты обещал предложить",
    "ты сам это предложил",
    "ты снова ушел не туда",
    "почему ты начал объяснять",
    "почему ты начал объяснять механизм",
    "я просто поздоровался",
    "я только поздоровался",
    "ответь на вопрос который я задавал ранее",
    "you did not answer",
    "you promised",
)
_OFFER_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    (
        "short_phrase",
        (
            "короткую фразу",
            "одну фразу",
            "короткую формулировку",
            "короткую реплику",
            "short phrase",
        ),
    ),
    ("example", ("на примере", "привести пример", "дай пример", "example")),
    ("one_step", ("один шаг", "один способ", "простой шаг", "one step")),
    ("explanation", ("объясню", "объяснить", "explain")),
    ("practice_observation", ("практик", "наблюдени", "practice", "observation")),
    ("summary", ("суммир", "итог", "summary")),
    ("application", ("примен", "в жизни", "apply")),
]
_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ]+")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _extract_words(text: str) -> list[str]:
    return [item.lower() for item in _WORD_RE.findall(str(text or ""))]


def _is_short_utterance(user_message: str) -> bool:
    words = _extract_words(user_message)
    if not words:
        return False
    compact = _normalize(user_message)
    return len(words) <= 10 and len(compact) <= 120


def _detect_short_utterance_type(user_message: str) -> str:
    lowered = _normalize(user_message)
    words = _extract_words(lowered)
    if any(marker in lowered for marker in _REPAIR_DISSATISFACTION_MARKERS):
        return "repair_feedback"
    has_followup_imperative = any(marker in lowered for marker in _FOLLOWUP_IMPERATIVE_MARKERS)
    is_pure_close_ack = bool(
        words and (" ".join(words) in _CLOSE_ACK_MARKERS or all(word in _CLOSE_ACK_MARKERS for word in words))
    )
    starts_with_close_marker = any(lowered.startswith(marker) for marker in _CLOSE_ACK_MARKERS)
    if not has_followup_imperative and (
        is_pure_close_ack or (starts_with_close_marker and _is_short_utterance(user_message))
    ):
        return "close_ack"
    if has_followup_imperative:
        if words and any(word in _AFFIRM_SHORT_MARKERS for word in words):
            return "affirmation_with_intent"
        return "imperative_followup"
    if words and all(word in _AFFIRM_SHORT_MARKERS for word in words):
        return "affirmation"
    if words and any(word in _AFFIRM_SHORT_MARKERS for word in words):
        return "affirmation_with_intent"
    return "short_unknown"


def _detect_offer_type(previous_assistant_message: str) -> str:
    lowered = _normalize(previous_assistant_message)
    if not lowered:
        return "unknown"
    for offer_type, markers in _OFFER_PATTERNS:
        if any(marker in lowered for marker in markers):
            return offer_type
    if "хочешь" in lowered or "могу" in lowered:
        return "unknown_offer"
    return "unknown"


def _extract_previous_assistant_from_context(conversation_context: str) -> str:
    text = str(conversation_context or "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.lower().startswith("assistant:"):
            return line.split(":", 1)[1].strip()
    blocks = re.split(r"\n-{3,}\n", text)
    for block in reversed(blocks):
        block_lines = [line.strip() for line in block.splitlines() if line.strip()]
        for line in reversed(block_lines):
            if line.lower().startswith("assistant:"):
                return line.split(":", 1)[1].strip()
    return ""


def _choose_inherited_intent(*, offer_type: str, short_type: str) -> str:
    if short_type == "repair_feedback":
        return "repair_direct_answer"
    if short_type == "close_ack":
        return "close_contact"
    mapping = {
        "short_phrase": "give_short_phrase",
        "example": "give_example",
        "one_step": "give_one_step",
        "explanation": "explain_concept",
        "practice_observation": "give_practice_observation",
        "summary": "give_summary",
        "application": "show_application",
    }
    return mapping.get(offer_type, "continue_previous_offer")


def _retrieve_topic(
    *,
    dialogue_policy: dict[str, Any] | None,
    active_frame: dict[str, Any] | None,
    thread_state: Any | None,
) -> str:
    policy = dict(dialogue_policy or {})
    if str(policy.get("active_concept", "") or "").strip():
        return str(policy.get("active_concept", "") or "").strip()
    frame = dict(active_frame or {})
    if str(frame.get("active_concept", "") or "").strip():
        return str(frame.get("active_concept", "") or "").strip()
    if thread_state is not None:
        raw_frame = getattr(thread_state, "active_frame", None)
        if isinstance(raw_frame, dict):
            if str(raw_frame.get("active_concept", "") or "").strip():
                return str(raw_frame.get("active_concept", "") or "").strip()
    return ""


def _retrieval_need_hint(*, offer_type: str, short_type: str, has_topic: bool, knowledge_needed: bool) -> str:
    if short_type == "close_ack":
        return "none"
    if offer_type in {"short_phrase", "one_step"} and not knowledge_needed:
        return "recent_context_only"
    if offer_type in {"example", "explanation", "application"}:
        return "example_or_concept_grounding" if (has_topic or knowledge_needed) else "contextual_optional"
    if offer_type == "practice_observation":
        return "practice_catalog" if (has_topic or knowledge_needed) else "contextual_optional"
    if knowledge_needed:
        return "kb_grounding_useful"
    return "contextual_optional"


def build_dialogue_pragmatics_v1(
    *,
    user_message: str,
    conversation_context: str,
    previous_assistant_message: str | None = None,
    thread_state: Any | None = None,
    active_frame: dict[str, Any] | None = None,
    dialogue_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lowered = _normalize(user_message)
    previous = str(previous_assistant_message or "").strip()
    if not previous:
        previous = _extract_previous_assistant_from_context(conversation_context)

    short_utterance = _is_short_utterance(user_message)
    short_type = _detect_short_utterance_type(user_message) if short_utterance else "not_short"
    offer_type = _detect_offer_type(previous)
    repair_dissatisfaction = any(marker in lowered for marker in _REPAIR_DISSATISFACTION_MARKERS)

    words = _extract_words(user_message)
    is_affirm_like = bool(words) and all(token in _AFFIRM_SHORT_MARKERS for token in words)
    contextual_followup = bool(
        short_utterance
        and previous
        and short_type != "close_ack"
        and (offer_type not in {"unknown", "unknown_offer"} or is_affirm_like or short_type in {"imperative_followup", "affirmation_with_intent"})
    )

    relation = "none"
    if repair_dissatisfaction:
        relation = "repair_after_failed_answer"
    elif short_type == "close_ack":
        relation = "close_acknowledgement"
    elif contextual_followup:
        relation = "accepts_previous_assistant_offer"

    inherited_topic = _retrieve_topic(
        dialogue_policy=dialogue_policy,
        active_frame=active_frame,
        thread_state=thread_state,
    )
    knowledge_answer = {}
    if isinstance(dialogue_policy, dict):
        knowledge_answer = dict(dialogue_policy.get("knowledge_answer", {}))
    knowledge_needed = bool(knowledge_answer.get("needed", False))
    retrieval_hint = _retrieval_need_hint(
        offer_type=offer_type,
        short_type=short_type,
        has_topic=bool(inherited_topic),
        knowledge_needed=knowledge_needed,
    )

    should_answer_directly = bool(
        repair_dissatisfaction
        or contextual_followup
        or short_type in {"imperative_followup", "affirmation_with_intent"}
    )
    allow_concrete_step_or_phrase = offer_type in {"short_phrase", "one_step", "practice_observation"}
    should_not_ask_confirmation_again = bool(contextual_followup or repair_dissatisfaction)

    reason = "none"
    if repair_dissatisfaction:
        reason = "user_reports_previous_non_answer"
    elif short_type == "close_ack":
        reason = "close_acknowledgement"
    elif contextual_followup:
        reason = "user_affirmed_previous_offer"
    elif short_utterance and not conversation_context.strip():
        reason = "short_utterance_without_context"

    return {
        "version": DIALOGUE_PRAGMATICS_VERSION,
        "is_short_utterance": bool(short_utterance),
        "short_utterance_type": short_type,
        "is_contextual_followup": bool(contextual_followup),
        "followup_relation": relation,
        "previous_assistant_offer_type": offer_type,
        "inherited_user_intent": _choose_inherited_intent(offer_type=offer_type, short_type=short_type),
        "inherited_topic": inherited_topic,
        "should_answer_directly": should_answer_directly,
        "should_not_ask_confirmation_again": should_not_ask_confirmation_again,
        "allow_concrete_step_or_phrase": bool(allow_concrete_step_or_phrase),
        "retrieval_need_hint": retrieval_hint,
        "repair_user_dissatisfaction": bool(repair_dissatisfaction),
        "should_apologize_briefly": bool(repair_dissatisfaction),
        "reason": reason,
    }


def build_contextual_retrieval_decision_v1(
    *,
    dialogue_pragmatics: dict[str, Any],
    knowledge_answer_guard: dict[str, Any] | None,
    semantic_hits: list[SemanticHit] | None,
    fresh_chat_context_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pragmatics = dict(dialogue_pragmatics or {})
    guard = dict(knowledge_answer_guard or {})
    fresh_policy = dict(fresh_chat_context_policy or {})
    knowledge_answer = (
        dict(guard.get("knowledge_answer", {}))
        if isinstance(guard.get("knowledge_answer"), dict)
        else {}
    )
    hits = [item for item in list(semantic_hits or []) if isinstance(item, SemanticHit)]
    candidates_count = len(hits)
    offer_type = str(pragmatics.get("previous_assistant_offer_type", "unknown") or "unknown")
    short_type = str(pragmatics.get("short_utterance_type", "not_short") or "not_short")
    inherited_intent = str(pragmatics.get("inherited_user_intent", "") or "")
    inherited_topic = str(
        pragmatics.get("inherited_topic") or knowledge_answer.get("concept") or ""
    ).strip()
    repair_mode = bool(pragmatics.get("repair_user_dissatisfaction", False))
    knowledge_needed = bool(knowledge_answer.get("needed", False))
    knowledge_answer_type = str(knowledge_answer.get("answer_type", "") or "").strip().lower()
    contextual_followup = bool(pragmatics.get("is_contextual_followup", False))
    fresh_greeting = bool(fresh_policy.get("is_greeting_or_contact", False))
    fresh_turn_index = int(fresh_policy.get("turn_index", 1) or 1)
    fresh_window_active = bool(fresh_policy.get("fresh_window_active", fresh_turn_index <= 2))
    explicit_question = bool(fresh_policy.get("explicit_question_or_knowledge_need", False))

    action = "none"
    included_reason = ""
    suppressed_reason = ""
    included_hits: list[SemanticHit] = []
    relevance = "unknown"
    memory_only_still_included_rag = ""

    if fresh_window_active and fresh_greeting and not knowledge_needed and not explicit_question:
        action = "none"
        suppressed_reason = "fresh_greeting_no_kb_needed"
        relevance = "low"
    elif short_type == "close_ack":
        action = "none"
        suppressed_reason = "close_ack_turn_no_kb_needed"
        relevance = "low"
    elif repair_mode and not knowledge_needed and not inherited_topic:
        action = "recent_context_only"
        suppressed_reason = "repair_turn_prefers_direct_contextual_answer"
        relevance = "low"
    elif contextual_followup and offer_type in {"short_phrase", "one_step"}:
        action = "recent_context_only"
        suppressed_reason = "local_followup_does_not_require_kb_grounding"
        relevance = "low"
    elif contextual_followup and offer_type in {"example", "application", "explanation"}:
        if candidates_count > 0:
            action = "example_grounding" if offer_type == "example" or inherited_intent == "give_example" else "kb_optional"
            included_hits = hits[:2]
            included_reason = "previous_offer_needs_example_or_concept_grounding"
            relevance = "high"
        else:
            action = "recent_context_only"
            suppressed_reason = "accepted_offer_but_no_relevant_kb_hits"
            relevance = "medium"
    elif knowledge_answer_type == "practice_overview":
        action = "practice_catalog"
        if candidates_count > 0:
            included_hits = hits[:3]
            included_reason = "practice_overview_with_kb_support"
            relevance = "high"
        else:
            suppressed_reason = "practice_overview_without_hits"
            relevance = "medium"
    elif knowledge_needed and candidates_count > 0:
        if knowledge_answer_type in {"known_concept", "concept", "term"} or inherited_topic:
            action = "concept_answer"
            included_reason = "knowledge_answer_guard_needed"
        else:
            action = "kb_grounding"
            included_reason = "knowledge_needed_with_relevant_hits"
        included_hits = hits[:2]
        relevance = "high"
    elif knowledge_needed:
        action = "memory_only"
        suppressed_reason = "knowledge_needed_without_kb_hits"
        relevance = "medium"
    elif candidates_count > 0:
        action = "memory_only"
        suppressed_reason = "candidate_available_but_current_turn_prefers_recent_context"
        relevance = "medium"
    else:
        action = "none"
        suppressed_reason = "no_candidates"
        relevance = "low"

    if action == "memory_only" and included_hits:
        memory_only_still_included_rag = "invalid_memory_only_configuration"

    if action == "memory_only":
        included_hits = []

    return {
        "version": CONTEXTUAL_RETRIEVAL_GATING_VERSION,
        "retrieval_decision_version": CONTEXTUAL_RETRIEVAL_GATING_VERSION,
        "retrieval_action": action,
        "rag_candidates_count": candidates_count,
        "rag_included_count": len(included_hits),
        "rag_included_reason": included_reason,
        "rag_suppressed_reason": suppressed_reason,
        "writer_can_ignore_rag": True,
        "rag_relevance_to_current_turn": relevance,
        "inherited_topic": inherited_topic,
        "inherited_offer_type": offer_type,
        "why_memory_only_still_included_rag": memory_only_still_included_rag,
        "fresh_chat_context_policy": fresh_policy,
        "rag_included_for_writer": [
            {
                "chunk_id": str(item.chunk_id or ""),
                "content": str(item.content or ""),
                "source": str(item.source or "unknown"),
                "score": float(item.score or 0.0),
            }
            for item in included_hits
        ],
    }


__all__ = [
    "CONTEXTUAL_RETRIEVAL_GATING_VERSION",
    "DIALOGUE_PRAGMATICS_VERSION",
    "build_contextual_retrieval_decision_v1",
    "build_dialogue_pragmatics_v1",
]
