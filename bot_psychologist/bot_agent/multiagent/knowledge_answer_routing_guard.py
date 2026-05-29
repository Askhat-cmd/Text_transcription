"""Deterministic Knowledge Answer Routing guard for known internal concepts."""

from __future__ import annotations

import re
from typing import Any

from .creator_live_behavior_guard import (
    REQUEST_TYPE_PRACTICE,
    REQUEST_TYPE_SAFETY,
    detect_request_type_v1,
)

KNOWLEDGE_ANSWER_ROUTING_VERSION = "knowledge_answer_routing_v1"
CONCEPT_ALIASES_VERSION = "concept_aliases_v1"

CONCEPT_ALIASES: dict[str, list[str]] = {
    "нейросталкинг": [
        "нейросталкинг",
        "нейро сталкинг",
        "нейро-сталкинг",
        "neurostalking",
    ],
    "неосталкинг": [
        "неосталкинг",
        "нео сталкинг",
        "нео-сталкинг",
        "neostalking",
    ],
    "самореализация": [
        "самореализация",
        "самореализоваться",
    ],
}

INTERNAL_CONCEPT_FALLBACK_SUMMARIES: dict[str, str] = {
    "нейросталкинг": (
        "Нейросталкинг — наблюдение за паттернами, триггерами и автоматическими реакциями "
        "во внутренней рамке."
    ),
    "неосталкинг": (
        "Неосталкинг — следующий уровень осознанного наблюдения за паттернами и выбором."
    ),
    "самореализация": (
        "Самореализация — раскрытие потенциала через осознанный выбор и авторство."
    ),
}

_CONCEPT_QUESTION_MARKERS = (
    "что такое",
    "что значит",
    "как связано",
    "как связана",
    "как связан",
    "как коррелирует",
    "ты понимаешь",
    "ты вообще понимаешь",
    "ты неправильно понял",
    "объясни",
)
_PRACTICE_OVERVIEW_MARKERS = (
    "какие практики",
    "какие способы",
    "какие варианты",
    "какие направления",
    "как это видеть",
)

_GREETING_MARKERS = (
    "привет",
    "здравствуй",
    "добрый день",
    "hello",
    "hi",
)


def _normalize_text(value: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("ё", "е")
    text = re.sub(r"\s+", " ", text)
    return text


def _contains_alias(text: str, alias: str) -> bool:
    norm_text = _normalize_text(text)
    norm_alias = _normalize_text(alias)
    if not norm_text or not norm_alias:
        return False
    exact_pattern = re.compile(rf"(?<!\w){re.escape(norm_alias)}(?!\w)", flags=re.IGNORECASE)
    if exact_pattern.search(norm_text):
        return True
    inflected_pattern = re.compile(
        rf"(?<!\w){re.escape(norm_alias)}[а-яa-z]{{1,4}}(?!\w)",
        flags=re.IGNORECASE,
    )
    return bool(inflected_pattern.search(norm_text))


def detect_concept_mentions(
    text: str,
    concept_aliases: dict[str, list[str]] | None = None,
) -> list[dict[str, str]]:
    aliases_map = concept_aliases or CONCEPT_ALIASES
    mentions: list[dict[str, str]] = []
    for concept, aliases in aliases_map.items():
        for alias in list(aliases or []):
            if _contains_alias(text, alias):
                mentions.append(
                    {
                        "concept": concept,
                        "alias": alias,
                        "match_type": "exact_or_near_exact",
                    }
                )
                break
    return mentions


def _is_greeting(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return any(normalized.startswith(marker) for marker in _GREETING_MARKERS)


def _looks_like_concept_question(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if any(marker in normalized for marker in _CONCEPT_QUESTION_MARKERS):
        return True
    return "?" in normalized


def _looks_like_practice_overview_request(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    return any(marker in normalized for marker in _PRACTICE_OVERVIEW_MARKERS)


def _safe_hit_content(raw_hit: Any) -> tuple[str, str, float]:
    if isinstance(raw_hit, dict):
        content = str(raw_hit.get("content", "") or "")
        source = str(raw_hit.get("source", "unknown") or "unknown")
        score = float(raw_hit.get("score", 0.0) or 0.0)
        return content, source, score
    content = str(getattr(raw_hit, "content", "") or "")
    source = str(getattr(raw_hit, "source", "unknown") or "unknown")
    score = float(getattr(raw_hit, "score", 0.0) or 0.0)
    return content, source, score


def select_lexical_override_hits(
    *,
    query: str,
    raw_hits: list[Any],
    max_hits: int = 2,
    concept_aliases: dict[str, list[str]] | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    mentions = detect_concept_mentions(query, concept_aliases)
    if not mentions:
        return [], {"reason": "no_known_concept_in_query", "matched_concepts": []}

    matched: list[tuple[float, Any]] = []
    matched_concepts = {item["concept"] for item in mentions}
    aliases_map = concept_aliases or CONCEPT_ALIASES

    for hit in list(raw_hits or []):
        content, _, score = _safe_hit_content(hit)
        for concept in matched_concepts:
            aliases = aliases_map.get(concept, [])
            if any(_contains_alias(content, alias) for alias in aliases):
                matched.append((score, hit))
                break

    matched.sort(key=lambda row: float(row[0]), reverse=True)
    selected = [row[1] for row in matched[: max(1, int(max_hits))]]
    trace = {
        "reason": "known_concept_lexical_override_applied" if selected else "no_lexical_hits_in_rag_content",
        "matched_concepts": sorted(matched_concepts),
        "matched_hits_count": len(selected),
    }
    return selected, trace


def build_knowledge_answer_routing_guard(
    *,
    user_message: str,
    rag_hits: list[Any],
    response_mode: str,
    concept_aliases: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    aliases_map = concept_aliases or CONCEPT_ALIASES
    mentions = detect_concept_mentions(user_message, aliases_map)
    concept = mentions[0]["concept"] if mentions else ""
    concept_set = {item["concept"] for item in mentions}

    kb_grounding_available = False
    grounding_sources: set[str] = set()
    max_score = 0.0

    for hit in list(rag_hits or []):
        content, source, score = _safe_hit_content(hit)
        max_score = max(max_score, score)
        for concept_item in concept_set:
            aliases = aliases_map.get(concept_item, [])
            if any(_contains_alias(content, alias) for alias in aliases):
                kb_grounding_available = True
                grounding_sources.add(source)
                break

    known_concept_question = bool(mentions) and _looks_like_concept_question(user_message)
    practice_overview_request = bool(mentions) and _looks_like_practice_overview_request(user_message)
    answer_type = "practice_overview" if practice_overview_request else "concept_explanation"
    knowledge_needed = bool(known_concept_question or practice_overview_request)
    fallback_concepts = sorted(
        concept_item
        for concept_item in concept_set
        if concept_item in INTERNAL_CONCEPT_FALLBACK_SUMMARIES
    )
    fallback_grounding_used = knowledge_needed and not kb_grounding_available and bool(fallback_concepts)
    if fallback_grounding_used:
        kb_grounding_available = True
        grounding_sources.add("internal_concept_fallback")

    should_answer_directly = knowledge_needed and kb_grounding_available
    should_ask_definition_first = False if should_answer_directly else not kb_grounding_available

    request_type = detect_request_type_v1(user_message)
    explicit_practice_request = request_type in {REQUEST_TYPE_PRACTICE, REQUEST_TYPE_SAFETY} or practice_overview_request
    greeting = _is_greeting(user_message)

    if practice_overview_request:
        practice_allowed = True
        practice_reason = "explicit_practice_overview_request"
    elif explicit_practice_request:
        practice_allowed = True
        practice_reason = "explicit_practice_request"
    elif knowledge_needed:
        practice_allowed = False
        practice_reason = "known_concept_answer_first"
    elif greeting:
        practice_allowed = False
        practice_reason = "greeting_no_practice_default"
    else:
        practice_allowed = True
        practice_reason = "no_guard_restriction"

    if should_answer_directly:
        base_instruction = (
            "knowledge_answer_first; answer from internal KB meaning first; "
            "do_not_ask_user_to_define_term_before_answering; "
            "do_not_switch_to_practice_before_answering; "
            "avoid_external_surveillance_interpretation_unless_user_explicitly_requests_it"
        )
        if fallback_grounding_used:
            base_instruction = (
                f"{base_instruction}; internal_concept_fallback_grounding={','.join(fallback_concepts)}"
            )
        writer_instruction = base_instruction
    else:
        writer_instruction = "follow_response_mode_with_normal_clarification_policy"

    preferred_response_mode = "inform" if should_answer_directly else str(response_mode or "")

    return {
        "schema_version": KNOWLEDGE_ANSWER_ROUTING_VERSION,
        "concept_aliases_version": CONCEPT_ALIASES_VERSION,
        "knowledge_answer": {
            "needed": knowledge_needed,
            "reason": (
                "known_internal_concept_question"
                if knowledge_needed
                else "no_known_concept_question"
            ),
            "concept": concept,
            "answer_type": answer_type,
            "concept_match_type": "exact_or_near_exact" if concept else "none",
            "matched_concepts": sorted(concept_set),
            "kb_grounding_available": kb_grounding_available,
            "kb_grounding_sources": sorted(grounding_sources),
            "kb_grounding_max_score": round(float(max_score), 6),
            "fallback_grounding_used": fallback_grounding_used,
            "fallback_grounding_concepts": fallback_concepts,
            "should_answer_directly": should_answer_directly,
            "should_ask_definition_first": should_ask_definition_first,
            "practice_overview_requested": practice_overview_request,
            "preferred_hit_tags": (
                ["chunk_type=practice", "lens_family=neurostalking", "allowed_use=practice_suggestion_or_writer_context"]
                if practice_overview_request
                else []
            ),
            "practice_allowed": practice_allowed,
            "preferred_response_mode": preferred_response_mode,
            "writer_instruction": writer_instruction,
        },
        "practice_gate": {
            "practice_allowed": practice_allowed,
            "reason": practice_reason,
            "explicit_practice_request": explicit_practice_request,
            "request_type": request_type,
            "is_greeting": greeting,
        },
    }


__all__ = [
    "KNOWLEDGE_ANSWER_ROUTING_VERSION",
    "CONCEPT_ALIASES_VERSION",
    "CONCEPT_ALIASES",
    "detect_concept_mentions",
    "select_lexical_override_hits",
    "build_knowledge_answer_routing_guard",
]
