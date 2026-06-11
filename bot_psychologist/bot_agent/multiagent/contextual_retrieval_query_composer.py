"""Deterministic contextual retrieval query composer v1."""

from __future__ import annotations

import re
from typing import Any

from .contracts.retrieval_query_contract import (
    CONTEXTUAL_RETRIEVAL_QUERY_COMPOSER_VERSION,
    RetrievalQueryComposerPayload,
)


_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9_-]+")
_AFFIRM_MARKERS = {"да", "давай", "ага", "угу", "ок", "окей", "okay", "ok", "yes", "sure", "хорошо"}
_GREETING_MARKERS = ("привет", "здравствуй", "здравствуйте", "hello", "hi", "hey")
_CONTACT_MARKERS = ("давай знакомиться", "приятно познакомиться", "меня зовут", "my name is")
_CLOSE_MARKERS = ("спасибо", "благодарю", "thanks", "thank you", "пока", "до свидания")
_SUMMARY_MARKERS = ("подведи итог", "краткий итог", "резюме", "суммируй", "обобщи", "summary", "recap")
_KNOWLEDGE_MARKERS = (
    "что такое",
    "что значит",
    "объясни",
    "расскажи",
    "как работает",
    "в чем разница",
    "в чём разница",
)
_PRACTICE_MARKERS = ("какие практики", "практики есть", "дай практик", "упражнения", "practice")
_ONE_STEP_MARKERS = ("что сделать прямо сейчас", "один шаг", "первый шаг", "микрошаг", "microstep")
_FORMAT_ONLY_MARKERS = ("markdown", "таблиц", "список", "жирн", "заголов")
_GENERIC_QUERY_STOPWORDS = {
    "что",
    "такое",
    "значит",
    "объясни",
    "расскажи",
    "покажи",
    "дай",
    "как",
    "это",
    "есть",
    "мой",
    "моем",
    "моём",
    "примере",
    "какие",
    "practice",
    "summary",
    "recap",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower()).replace("ё", "е")


def _words(text: str) -> list[str]:
    return [part.lower().replace("ё", "е") for part in _WORD_RE.findall(str(text or ""))]


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _normalize(text)
    return any(marker.replace("ё", "е") in lowered for marker in markers)


def _is_short_affirmation(text: str) -> bool:
    parts = _words(text)
    return bool(parts) and len(parts) <= 4 and all(part in _AFFIRM_MARKERS for part in parts)


def _dedupe_terms(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        term = _normalize(item).strip(" .,:;!?-_")
        if not term or term in seen:
            continue
        seen.add(term)
        result.append(term)
    return result


def _extract_known_terms(*texts: str) -> list[str]:
    terms: list[str] = []
    for word in _words(" ".join(str(item or "") for item in texts)):
        normalized = _normalize(word)
        if len(normalized) < 3 or normalized in _GENERIC_QUERY_STOPWORDS:
            continue
        if normalized not in terms:
            terms.append(normalized)
    return _dedupe_terms(terms[:10])


def _compose_query(*sources: str, fallback_terms: list[str] | None = None, max_chars: int = 280) -> tuple[str, list[str]]:
    terms = _extract_known_terms(*sources)
    terms.extend(list(fallback_terms or []))
    terms = _dedupe_terms(terms)
    query = " ".join(terms).strip()
    if not query:
        query = " ".join(_words(" ".join(sources))[:12])
        terms = _dedupe_terms(_words(query))
    return query[:max_chars].strip(), terms


def _payload(
    *,
    retrieval_need: str,
    retrieval_action: str,
    query_source: str,
    composed_query: str = "",
    query_terms: list[str] | None = None,
    inherited_topic: str = "",
    inherited_offer_type: str = "",
    confidence: float = 0.0,
    writer_can_ignore_rag: bool = True,
    include_for_writer_if_found: bool = False,
    max_chunks_for_writer: int = 0,
    max_chars_per_chunk: int = 0,
    suppress_reason: str = "",
    reason: str = "",
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    return RetrievalQueryComposerPayload(
        retrieval_need=retrieval_need,
        retrieval_action=retrieval_action,
        query_source=query_source,
        composed_query=composed_query,
        query_terms=list(query_terms or []),
        inherited_topic=inherited_topic,
        inherited_offer_type=inherited_offer_type,
        confidence=confidence,
        writer_can_ignore_rag=writer_can_ignore_rag,
        include_for_writer_if_found=include_for_writer_if_found,
        max_chunks_for_writer=max_chunks_for_writer,
        max_chars_per_chunk=max_chars_per_chunk,
        suppress_reason=suppress_reason,
        reason=reason,
        evidence=list(evidence or []),
    ).to_dict()


def build_contextual_retrieval_query_composer_v1(
    *,
    user_message: str,
    recent_turns: list[dict[str, Any]] | None = None,
    last_assistant_offer: dict[str, Any] | None = None,
    dialogue_pragmatics: dict[str, Any] | None = None,
    dialogue_act_resolution: dict[str, Any] | None = None,
    answer_obligation_resolution: dict[str, Any] | None = None,
    final_answer_directive: dict[str, Any] | None = None,
    active_line: dict[str, Any] | None = None,
    response_planner: dict[str, Any] | None = None,
    diagnostic_card: dict[str, Any] | None = None,
    diagnostic_center_shadow: dict[str, Any] | None = None,
    knowledge_answer_guard: dict[str, Any] | None = None,
    retrieval_decision_previous: dict[str, Any] | None = None,
    memory_bundle_summary: dict[str, Any] | None = None,
    current_concept: str = "",
    thread_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create retrieval intent/query from dialogue context, not just the last utterance."""

    del recent_turns, final_answer_directive, active_line, diagnostic_card, diagnostic_center_shadow, retrieval_decision_previous
    text = str(user_message or "")
    lowered = _normalize(text)
    pragmatics = dict(dialogue_pragmatics or {})
    act = dict(dialogue_act_resolution or {})
    obligation = dict(answer_obligation_resolution or {})
    planner = dict(response_planner or {})
    guard = dict(knowledge_answer_guard or {})
    knowledge_answer = dict(guard.get("knowledge_answer", {})) if isinstance(guard.get("knowledge_answer"), dict) else {}
    last_offer = dict(last_assistant_offer or {})
    memory = dict(memory_bundle_summary or {})
    thread = dict(thread_state or {})

    dialogue_act = str(act.get("dialogue_act", "") or "")
    answer_obligation = str(obligation.get("answer_obligation", "") or "")
    offer_type = str(last_offer.get("offer_type", "") or pragmatics.get("previous_assistant_offer_type", "") or "")
    offer_summary = str(last_offer.get("offer_text_summary", "") or "")
    inherited_topic = str(
        pragmatics.get("inherited_topic", "")
        or knowledge_answer.get("concept", "")
        or current_concept
        or thread.get("active_concept", "")
        or ""
    ).strip()
    planner_next_move = str(planner.get("next_move", "") or "")
    planner_answer_shape = str(planner.get("answer_shape", "") or "")
    fresh_is_greeting = bool(memory.get("fresh_chat_is_greeting_or_contact", False))
    evidence: list[str] = []

    if dialogue_act == "summary_request" or answer_obligation == "summarize_current_conversation":
        if inherited_topic and any(term in lowered for term in ("свяжи", "через", "с точки зрения")):
            query, terms = _compose_query(text, inherited_topic, fallback_terms=["summary_context"])
            return _payload(
                retrieval_need="mixed",
                retrieval_action="query_kb",
                query_source="mixed_context",
                composed_query=query,
                query_terms=terms,
                inherited_topic=inherited_topic,
                inherited_offer_type=offer_type,
                confidence=0.72,
                writer_can_ignore_rag=True,
                include_for_writer_if_found=True,
                max_chunks_for_writer=2,
                max_chars_per_chunk=600,
                reason="summary request explicitly asks to connect current conversation with a topic",
                evidence=["summary_request", "explicit_topic_link"],
            )
        return _payload(
            retrieval_need="conversation_context",
            retrieval_action="use_current_context_only",
            query_source="summary_request",
            confidence=0.95,
            writer_can_ignore_rag=True,
            include_for_writer_if_found=False,
            suppress_reason="summary_request_current_conversation_only",
            reason="summary of current conversation should not introduce external KB",
            evidence=["summary_request", "no_external_kb_by_default"],
        )

    if (
        answer_obligation == "close_gently"
        or dialogue_act in {"greeting", "contact_open", "self_intro", "close_ack"}
        or fresh_is_greeting
        or _contains_any(lowered, _GREETING_MARKERS + _CONTACT_MARKERS + _CLOSE_MARKERS)
    ):
        return _payload(
            retrieval_need="none",
            retrieval_action="suppress_rag",
            query_source="current_user_message",
            confidence=0.90,
            suppress_reason="contact_or_close_turn_no_kb_needed",
            reason="greeting/contact/close should not retrieve KB without explicit knowledge need",
            evidence=["noise_suppression", "contact_or_close"],
        )

    if planner_next_move in {"give_short_support", "stabilize_safety"} or planner_answer_shape in {"short_support", "safety_grounding"}:
        return _payload(
            retrieval_need="none",
            retrieval_action="suppress_rag",
            query_source="answer_obligation",
            confidence=0.88,
            suppress_reason="support_or_safety_turn_no_kb_needed",
            reason="support/safety response should not be overloaded by KB",
            evidence=["noise_suppression", "planner_support_or_safety"],
        )

    if _contains_any(lowered, _FORMAT_ONLY_MARKERS):
        return _payload(
            retrieval_need="none",
            retrieval_action="suppress_rag",
            query_source="current_user_message",
            confidence=0.78,
            suppress_reason="formatting_only_request",
            reason="formatting-only request does not need retrieval",
            evidence=["noise_suppression", "formatting_only"],
        )

    if _contains_any(lowered, _ONE_STEP_MARKERS) or planner_answer_shape == "one_step":
        return _payload(
            retrieval_need="none",
            retrieval_action="suppress_rag",
            query_source="answer_obligation",
            confidence=0.76,
            suppress_reason="direct_one_step_no_kb_needed",
            reason="one-step direct response should not be overloaded by KB",
            evidence=["noise_suppression", "one_step"],
        )

    if _is_short_affirmation(text) and bool(last_offer.get("is_open", False) or offer_summary):
        if offer_type in {"short_support", "short_phrase", "one_step"}:
            return _payload(
                retrieval_need="none",
                retrieval_action="suppress_rag",
                query_source="last_assistant_offer",
                inherited_topic=inherited_topic,
                inherited_offer_type=offer_type,
                confidence=0.90,
                suppress_reason="accepted_short_support_offer_no_kb_needed",
                reason="short support or one-step offer can be fulfilled from dialogue context",
                evidence=["short_contextual_followup", "last_offer_inherited", "noise_suppression"],
            )
        if offer_type in {"explain_concept", "explanation", "example", "application", "practice_observation", "summary"} or inherited_topic:
            query, terms = _compose_query(offer_summary, inherited_topic, fallback_terms=["объяснение", "наблюдение"])
            return _payload(
                retrieval_need="knowledge_context",
                retrieval_action="query_kb",
                query_source="last_assistant_offer",
                composed_query=query,
                query_terms=terms,
                inherited_topic=inherited_topic or " ".join(terms[:2]),
                inherited_offer_type=offer_type,
                confidence=0.86,
                writer_can_ignore_rag=True,
                include_for_writer_if_found=True,
                max_chunks_for_writer=2,
                max_chars_per_chunk=650,
                reason="short acceptance inherits retrieval topic from previous assistant offer",
                evidence=["short_contextual_followup", "last_offer_inherited"],
            )
        return _payload(
            retrieval_need="none",
            retrieval_action="trace_only",
            query_source="last_assistant_offer",
            inherited_topic=inherited_topic,
            inherited_offer_type=offer_type,
            confidence=0.55,
            writer_can_ignore_rag=True,
            include_for_writer_if_found=False,
            suppress_reason="low_confidence_inherited_topic",
            reason="accepted previous offer but no reliable retrieval topic found",
            evidence=["short_contextual_followup", "low_confidence"],
        )

    if _contains_any(lowered, _PRACTICE_MARKERS) or str(knowledge_answer.get("answer_type", "")).lower() == "practice_overview":
        query, terms = _compose_query(text, inherited_topic, fallback_terms=["практики", "use_when", "avoid_when"])
        return _payload(
            retrieval_need="practice_context",
            retrieval_action="query_kb",
            query_source="current_user_message",
            composed_query=query,
            query_terms=terms,
            inherited_topic=inherited_topic,
            inherited_offer_type=offer_type,
            confidence=0.84,
            writer_can_ignore_rag=True,
            include_for_writer_if_found=True,
            max_chunks_for_writer=3,
            max_chars_per_chunk=650,
            reason="practice overview can use compact KB context",
            evidence=["practice_overview", "knowledge_context_useful"],
        )

    knowledge_needed = bool(knowledge_answer.get("needed", False))
    if knowledge_needed or dialogue_act == "knowledge_question" or _contains_any(lowered, _KNOWLEDGE_MARKERS):
        query, terms = _compose_query(text, inherited_topic, str(knowledge_answer.get("concept", "") or ""))
        return _payload(
            retrieval_need="knowledge_context",
            retrieval_action="query_kb",
            query_source="current_user_message",
            composed_query=query,
            query_terms=terms,
            inherited_topic=inherited_topic or str(knowledge_answer.get("concept", "") or ""),
            inherited_offer_type=offer_type,
            confidence=0.88,
            writer_can_ignore_rag=False,
            include_for_writer_if_found=True,
            max_chunks_for_writer=3,
            max_chars_per_chunk=700,
            reason="knowledge question needs compact KB support",
            evidence=["knowledge_question", "query_composed_from_current_message"],
        )

    if bool(pragmatics.get("is_contextual_followup", False)):
        return _payload(
            retrieval_need="memory_context",
            retrieval_action="trace_only",
            query_source="mixed_context",
            inherited_topic=inherited_topic,
            inherited_offer_type=offer_type,
            confidence=0.58,
            writer_can_ignore_rag=True,
            include_for_writer_if_found=False,
            suppress_reason="contextual_followup_without_knowledge_need",
            reason="recent dialogue context is preferred over noisy KB",
            evidence=["contextual_followup", "recent_context_preferred"],
        )

    return _payload(
        retrieval_need="none",
        retrieval_action="trace_only",
        query_source="current_user_message",
        composed_query="",
        confidence=0.45,
        writer_can_ignore_rag=True,
        include_for_writer_if_found=False,
        suppress_reason="no_clear_retrieval_need",
        reason="no reliable knowledge or memory retrieval need detected",
        evidence=evidence or ["fallback_trace_only"],
    )


def merge_composer_into_retrieval_decision_v1(
    *,
    retrieval_decision: dict[str, Any] | None,
    composer_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """Attach composer plan to existing retrieval gate and enforce suppress/include policy."""

    decision = dict(retrieval_decision or {})
    composer = dict(composer_payload or {})
    if not composer:
        return decision

    decision["composer"] = composer
    decision["contextual_retrieval_query_composer"] = composer
    decision["contextual_retrieval_query_composer_version"] = str(
        composer.get("version", CONTEXTUAL_RETRIEVAL_QUERY_COMPOSER_VERSION)
    )
    decision["retrieval_query_source"] = str(composer.get("query_source", "") or "")
    decision["composed_retrieval_query"] = str(composer.get("composed_query", "") or "")
    decision["retrieval_need"] = str(composer.get("retrieval_need", "") or "")
    decision["writer_can_ignore_rag"] = bool(composer.get("writer_can_ignore_rag", True))

    action = str(composer.get("retrieval_action", "") or "")
    if action in {"suppress_rag", "use_current_context_only", "trace_only"}:
        decision["retrieval_action"] = action
        decision["rag_included_for_writer"] = []
        decision["rag_included_count"] = 0
        reason = str(composer.get("suppress_reason", "") or composer.get("reason", "") or action)
        decision["rag_suppressed_reason"] = reason
        decision["rag_included_reason"] = ""
        decision["rag_relevance_to_current_turn"] = "low" if action == "suppress_rag" else "medium"
        return decision

    if action in {"query_kb", "query_memory", "query_kb_and_memory"}:
        decision["retrieval_action"] = action
        max_chunks = int(composer.get("max_chunks_for_writer", 2) or 2)
        max_chars = int(composer.get("max_chars_per_chunk", 650) or 650)
        if max_chunks < 0:
            max_chunks = 0
        if max_chars <= 0:
            max_chars = 650
        raw_items = [
            dict(item)
            for item in list(decision.get("rag_included_for_writer", []) or [])
            if isinstance(item, dict)
        ]
        compact_items = []
        for item in raw_items[:max_chunks]:
            compact = dict(item)
            compact["content"] = str(compact.get("content", "") or "")[: min(max_chars, 900)]
            compact_items.append(compact)
        decision["rag_included_for_writer"] = compact_items if bool(composer.get("include_for_writer_if_found", False)) else []
        decision["rag_included_count"] = len(decision["rag_included_for_writer"])
        decision["rag_included_reason"] = str(composer.get("reason", "") or decision.get("rag_included_reason", ""))
        if not decision["rag_included_for_writer"]:
            decision["rag_suppressed_reason"] = str(
                decision.get("rag_suppressed_reason", "")
                or "composer_query_had_no_writer_chunks"
            )
        return decision

    return decision


__all__ = [
    "CONTEXTUAL_RETRIEVAL_QUERY_COMPOSER_VERSION",
    "build_contextual_retrieval_query_composer_v1",
    "merge_composer_into_retrieval_decision_v1",
]
