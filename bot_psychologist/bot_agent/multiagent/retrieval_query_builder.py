"""Deterministic current-turn-focused retrieval query builder."""

from __future__ import annotations

import re
from typing import Any


RETRIEVAL_QUERY_BUILD_VERSION = "retrieval_query_build_trace_v1"
CURRENT_TURN_QUERY_BUILDER_PATH = "current_turn_focus_v1"

_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+(?:[-_][A-Za-zА-Яа-яЁё0-9]+)*")
_QUOTE_RE = re.compile(r"[\"«](.+?)[\"»]")
_QUESTION_WORDS = {
    "что",
    "как",
    "зачем",
    "почему",
    "какой",
    "какая",
    "какие",
    "какое",
    "где",
    "когда",
}
_ELLIPTICAL_MARKERS = {
    "да",
    "ага",
    "угу",
    "ок",
    "окей",
    "хорошо",
    "подробнее",
    "дальше",
    "пример",
    "разверни",
    "объясни",
}
_EXPLICIT_REFERENCE_MARKERS = (
    "это",
    "этим",
    "этого",
    "этот",
    "второй",
    "уровень",
    "подробнее",
    "дальше",
    "связано",
)
_STOPWORDS = {
    "а",
    "и",
    "или",
    "но",
    "же",
    "ли",
    "что",
    "как",
    "это",
    "этим",
    "этого",
    "этот",
    "такое",
    "какие",
    "какая",
    "какой",
    "какое",
    "расскажи",
    "объясни",
    "подробно",
    "подробнее",
    "скажи",
    "мне",
    "про",
    "прошу",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _normalized_words(text: str) -> list[str]:
    return [token.lower().replace("ё", "е") for token in _WORD_RE.findall(str(text or ""))]


def _compact_topic_text(value: str) -> str:
    normalized = _normalize(value).strip(" .,:;!?")
    if not normalized:
        return ""
    return normalized[:120].strip()


def _dedupe_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for term in terms:
        normalized = _normalize(term).strip(" .,:;!?-_").lower().replace("ё", "е")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(_normalize(term).strip(" .,:;!?-_"))
    return result


def _extract_quoted_phrases(text: str) -> list[str]:
    phrases: list[str] = []
    for raw in _QUOTE_RE.findall(str(text or "")):
        value = _compact_topic_text(raw)
        if value:
            phrases.append(value)
    return _dedupe_terms(phrases)


def _extract_focus_terms(text: str, *, max_terms: int = 12) -> list[str]:
    focus_terms: list[str] = []
    for token in _normalized_words(text):
        if len(token) < 2 or token in _STOPWORDS:
            continue
        normalized_existing = [item.lower().replace("ё", "е") for item in focus_terms]
        if token not in normalized_existing:
            focus_terms.append(token)
        if len(focus_terms) >= max_terms:
            break
    return focus_terms


def _has_question_shape(text: str) -> bool:
    normalized = _normalize(text).lower()
    if "?" in normalized:
        return True
    words = _normalized_words(normalized)
    return bool(words and words[0] in _QUESTION_WORDS)


def _is_short_elliptical(text: str) -> bool:
    normalized = _normalize(text).lower().replace("ё", "е")
    words = _normalized_words(normalized)
    if not normalized:
        return False
    if len(words) <= 2 and normalized in _ELLIPTICAL_MARKERS:
        return True
    if len(words) <= 6 and any(marker in normalized for marker in _EXPLICIT_REFERENCE_MARKERS):
        return True
    return False


def _looks_like_standalone_knowledge_question(text: str) -> bool:
    words = _normalized_words(text)
    return bool(words) and (len(words) >= 4 or _has_question_shape(text) or bool(_extract_quoted_phrases(text)))


def _collapse_duplicate_halves(text: str) -> tuple[str, int]:
    normalized = _normalize(text)
    if not normalized:
        return "", 0
    words = normalized.split()
    for window in range(min(24, len(words) // 2), 4, -1):
        probe = " ".join(words[:window])
        tail = " ".join(words[window:])
        if probe and probe in tail:
            cleaned = normalized.replace(f" {probe}", "", 1)
            return _normalize(cleaned), 1
    return normalized, 0


def _safe_truncate(text: str, *, max_chars: int) -> tuple[str, bool, str]:
    normalized = _normalize(text)
    if len(normalized) <= max_chars:
        return normalized, False, "none"
    cut = normalized[:max_chars]
    if " " in cut:
        truncated = cut.rsplit(" ", 1)[0].rstrip(" ,.;:!?")
        if truncated:
            return truncated, True, "word_boundary"
    return cut.rstrip(" ,.;:!?"), True, "hard_boundary"


def _query_has_mid_word_cut(text: str) -> bool:
    stripped = _normalize(text).rstrip()
    if not stripped:
        return False
    if re.search(r"[.!?:;…»”)\]]$", stripped):
        return False
    return bool(re.search(r"[A-Za-zА-Яа-яЁё0-9]$", stripped))


def _sanitize_planner_query(planner_query: str, *, max_chars: int) -> str:
    trimmed, _, _ = _safe_truncate(planner_query, max_chars=max_chars)
    return trimmed


def _planner_query_is_current(planner_query: str, *, user_message: str) -> bool:
    planner_words = set(_extract_focus_terms(planner_query, max_terms=16))
    current_words = set(_extract_focus_terms(user_message, max_terms=16))
    quoted = set(_extract_quoted_phrases(user_message))
    if not planner_words:
        return False
    if not current_words and len(_normalize(user_message)) <= 4:
        return True
    if quoted and any(phrase.lower().replace("ё", "е") in planner_query.lower().replace("ё", "е") for phrase in quoted):
        return True
    overlap = len(planner_words.intersection(current_words))
    return overlap >= 1 and overlap >= min(len(planner_words), max(1, len(current_words) // 3))


def build_retrieval_query(
    *,
    user_message: str,
    previous_user_message: str | None = None,
    thread_state: dict[str, Any] | None = None,
    dialogue_act: dict[str, Any] | None = None,
    planner_query: str | None = None,
    inherited_topic: str | None = None,
    last_assistant_offer_summary: str | None = None,
    max_chars: int,
    mode: str = CURRENT_TURN_QUERY_BUILDER_PATH,
) -> dict[str, Any]:
    raw_user_query = _normalize(user_message)
    previous_user_query = _normalize(previous_user_message or "")
    thread = dict(thread_state or {})
    dialogue = dict(dialogue_act or {})
    inherited = _compact_topic_text(
        inherited_topic
        or str(thread.get("active_concept", "") or "")
        or str(thread.get("core_direction", "") or "")
    )
    offer_summary = _compact_topic_text(last_assistant_offer_summary or "")
    planned_query = _sanitize_planner_query(str(planner_query or ""), max_chars=max_chars)

    is_elliptical = _is_short_elliptical(raw_user_query)
    standalone = _looks_like_standalone_knowledge_question(raw_user_query) and not is_elliptical
    explicit_reference = any(marker in raw_user_query.lower().replace("ё", "е") for marker in _EXPLICIT_REFERENCE_MARKERS)

    previous_user_query_included = False
    previous_user_query_inclusion_reason = "not_used"
    inherited_topic_used = False
    inherited_topic_reason = "none"
    planner_query_used = False
    fallback_used = False
    fallback_reason = ""
    current_turn_focus_status = "clean"

    focus_terms = _extract_focus_terms(raw_user_query)
    quoted_phrases = _extract_quoted_phrases(raw_user_query)
    canonical_parts: list[str] = quoted_phrases + focus_terms
    raw_duplicate_fragment_count = _collapse_duplicate_halves(raw_user_query)[1]

    if is_elliptical and inherited:
        inherited_topic_used = True
        inherited_topic_reason = "elliptical_followup_inherited_topic"
        current_turn_focus_status = "elliptical_contextualized"
        canonical_parts = _dedupe_terms(quoted_phrases + [inherited] + focus_terms)
    elif is_elliptical and offer_summary:
        inherited_topic_used = True
        inherited_topic_reason = "elliptical_followup_last_offer_summary"
        current_turn_focus_status = "elliptical_contextualized"
        canonical_parts = _dedupe_terms(quoted_phrases + _extract_focus_terms(offer_summary, max_terms=8) + focus_terms)
    elif standalone:
        previous_user_query_inclusion_reason = "standalone_current_knowledge_question"
        current_turn_focus_status = "clean"
    elif explicit_reference and inherited:
        inherited_topic_used = True
        inherited_topic_reason = "explicit_reference_inherited_topic"
        current_turn_focus_status = "elliptical_contextualized"
        canonical_parts = _dedupe_terms(quoted_phrases + [inherited] + focus_terms)

    canonical_query = _normalize(" ".join(_dedupe_terms(canonical_parts)))
    if not canonical_query:
        canonical_query = raw_user_query

    if planned_query and _planner_query_is_current(planned_query, user_message=raw_user_query):
        planner_query_used = True
        if quoted_phrases:
            canonical_query = _normalize(" ".join(_dedupe_terms(quoted_phrases + _extract_focus_terms(planned_query, max_terms=12))))
        else:
            canonical_query = planned_query
    elif planned_query:
        current_turn_focus_status = "polluted_blocked" if standalone else current_turn_focus_status

    deduped_query, duplicate_fragment_count = _collapse_duplicate_halves(canonical_query)
    duplicate_fragment_count = max(raw_duplicate_fragment_count, duplicate_fragment_count)
    dedupe_applied = duplicate_fragment_count > 0
    executed_query, truncation_applied, truncation_strategy = _safe_truncate(deduped_query, max_chars=max_chars)
    query_truncated_mid_word = _query_has_mid_word_cut(executed_query) if truncation_applied else False
    if truncation_strategy == "word_boundary":
        query_truncated_mid_word = False

    if query_truncated_mid_word:
        executed_query = executed_query.rsplit(" ", 1)[0].rstrip(" ,.;:!?")
        truncation_applied = True
        truncation_strategy = "word_boundary"
        query_truncated_mid_word = False

    if not executed_query and planned_query:
        fallback_used = True
        fallback_reason = "empty_canonical_query_used_planner"
        executed_query = planned_query
    elif not executed_query and previous_user_query:
        fallback_used = True
        fallback_reason = "empty_canonical_query_used_previous"
        previous_user_query_included = True
        previous_user_query_inclusion_reason = "explicit_previous_query_fallback"
        executed_query = _safe_truncate(previous_user_query, max_chars=max_chars)[0]
    elif not executed_query:
        fallback_used = True
        fallback_reason = "empty_canonical_query_used_raw"
        executed_query = _safe_truncate(raw_user_query, max_chars=max_chars)[0]

    if fallback_used and current_turn_focus_status == "clean":
        current_turn_focus_status = "fallback"

    return {
        "schema_version": RETRIEVAL_QUERY_BUILD_VERSION,
        "enabled": True,
        "primary_path": mode,
        "raw_user_query": raw_user_query,
        "previous_user_query": previous_user_query,
        "canonical_query": canonical_query,
        "executed_query": executed_query,
        "planned_query": planned_query,
        "planner_query_used": planner_query_used,
        "previous_user_query_included": previous_user_query_included,
        "previous_user_query_inclusion_reason": previous_user_query_inclusion_reason,
        "inherited_topic_used": inherited_topic_used,
        "inherited_topic_reason": inherited_topic_reason,
        "inherited_topic": inherited if inherited_topic_used else "",
        "dialogue_act_hint": str(dialogue.get("dialogue_act", "") or ""),
        "dedupe_applied": dedupe_applied,
        "duplicate_fragment_count": duplicate_fragment_count,
        "truncation_applied": truncation_applied,
        "truncation_strategy": truncation_strategy,
        "query_truncated_mid_word": query_truncated_mid_word,
        "current_turn_focus_status": current_turn_focus_status,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "legacy_query_builder_fallback": fallback_used,
        "query_builder_primary_path": mode,
    }


__all__ = [
    "CURRENT_TURN_QUERY_BUILDER_PATH",
    "RETRIEVAL_QUERY_BUILD_VERSION",
    "build_retrieval_query",
]
