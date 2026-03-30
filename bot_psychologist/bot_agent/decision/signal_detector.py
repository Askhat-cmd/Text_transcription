"""Signal extraction helpers for decision routing."""

from __future__ import annotations

import re
from typing import Dict

from ..contradiction_detector import detect_contradiction

_EMOTIONAL_PATTERNS = (
    r"\bстрашно\b",
    r"\bтревог",
    r"\bбольно\b",
    r"\bтяжело\b",
    r"\bне могу\b",
    r"\bвина\b",
    r"\bстыд\b",
)
_EMOTIONAL_RE = [re.compile(pattern, flags=re.IGNORECASE) for pattern in _EMOTIONAL_PATTERNS]

_POSITIVE_FEEDBACK_PATTERNS = (
    r"\bэто\s+именно\b",
    r"\bименно\s+то\b",
    r"\bспасибо.*помогло\b",
    r"\bда.*именно\b",
    r"\bв\s+точку\b",
)
_POSITIVE_FEEDBACK_RE = [
    re.compile(pattern, flags=re.IGNORECASE) for pattern in _POSITIVE_FEEDBACK_PATTERNS
]


def _extract_last_user_text(memory) -> str:
    if memory is None:
        return ""
    try:
        turns = getattr(memory, "turns", []) or []
        for turn in reversed(turns):
            content = getattr(turn, "user_input", "") or ""
            if content:
                return str(content)
    except Exception:
        return ""
    return ""


def _tokenize_topic(text: str) -> set[str]:
    tokens = re.findall(r"[а-яА-Яa-zA-Z]{4,}", (text or "").lower())
    return set(tokens)


def is_first_response_on_topic(query: str, memory) -> tuple[bool, int]:
    """
    Determine if query starts a new topic compared to last user turn.

    Returns:
        (is_first_response_on_topic, current_turn_in_topic)
    """
    prev = _extract_last_user_text(memory)
    if not prev:
        return True, 1

    current_tokens = _tokenize_topic(query)
    prev_tokens = _tokenize_topic(prev)
    if not current_tokens or not prev_tokens:
        return False, 2

    overlap = len(current_tokens & prev_tokens) / max(1, len(current_tokens))
    is_new_topic = overlap < 0.25
    return (is_new_topic, 1) if is_new_topic else (False, 2)


def has_emotional_signal(query: str, state_analysis=None) -> bool:
    text = (query or "").lower()
    if any(pattern.search(text) for pattern in _EMOTIONAL_RE):
        return True

    if state_analysis is None:
        return False

    tone = (getattr(state_analysis, "emotional_tone", "") or "").lower()
    primary = getattr(getattr(state_analysis, "primary_state", None), "value", "")
    return bool(
        any(token in tone for token in ("anxiety", "panic", "distress", "frustrat", "overwhelm"))
        or primary in {"overwhelmed", "confused", "resistant", "stagnant"}
    )


def has_positive_feedback_signal(query: str) -> bool:
    text = query or ""
    return any(pattern.search(text) for pattern in _POSITIVE_FEEDBACK_RE)


def resolve_user_stage(memory, state_analysis=None) -> str:
    """Resolve user stage from working_state first, then from state depth."""
    if getattr(memory, "working_state", None):
        try:
            return memory.working_state.get_user_stage()
        except Exception:
            pass

    depth = ""
    if state_analysis is not None:
        depth = (getattr(state_analysis, "depth", "") or "").lower()

    if "deep" in depth:
        return "exploration"
    if "medium" in depth:
        return "awareness"
    return "surface"


def detect_routing_signals(query: str, retrieved_blocks, state_analysis=None, memory=None) -> Dict[str, object]:
    """Prepare normalized signals for DecisionGate routing."""
    top_scores = [float(score) for _, score in (retrieved_blocks or [])[:2]]
    top1 = top_scores[0] if top_scores else 0.0
    top2 = top_scores[1] if len(top_scores) > 1 else 0.0
    delta = max(0.0, min(1.0, top1 - top2))
    local_similarity = max(0.0, min(1.0, top1))

    primary = ""
    emotional_tone = ""
    state_confidence = 0.0
    if state_analysis is not None:
        primary = getattr(state_analysis.primary_state, "value", "") or ""
        emotional_tone = (getattr(state_analysis, "emotional_tone", "") or "").lower()
        state_confidence = float(getattr(state_analysis, "confidence", 0.0) or 0.0)

    explicit_action_patterns = (
        "что делать",
        "как сделать",
        "с чего начать",
        "что мне делать",
    )
    lowered_query = query.lower()
    explicit_ask = any(pattern in lowered_query for pattern in explicit_action_patterns)

    emotion_load = "high" if any(
        token in emotional_tone for token in ("overwhelm", "panic", "anxiety", "distress")
    ) else "low"
    if primary in {"overwhelmed", "resistant", "stagnant"}:
        emotion_load = "high"

    topic_is_first, current_turn_in_topic = is_first_response_on_topic(query, memory)
    emotional_signal = has_emotional_signal(query, state_analysis=state_analysis)
    positive_feedback_signal = has_positive_feedback_signal(query)
    contradiction_info = detect_contradiction(query)
    contradiction_detected = bool(contradiction_info.get("has_contradiction", False))

    return {
        "local_similarity": local_similarity,
        "delta_top1_top2": delta,
        "state_match": max(0.0, min(1.0, state_confidence)),
        "question_clarity": 1.0 if len(query.split()) >= 4 else 0.5,
        "explicit_ask": explicit_ask,
        "ask_type": "action" if explicit_ask else "reflection",
        "emotion_load": emotion_load,
        # NOTE: keep routing contradiction disabled to avoid behavior regression.
        "contradiction": False,
        "contradiction_detected": contradiction_detected,
        "contradiction_declared": contradiction_info.get("declared"),
        "contradiction_actual_signal": contradiction_info.get("actual_signal"),
        "contradiction_suggestion": contradiction_info.get("suggestion", ""),
        "validation_needed": primary in {"confused", "overwhelmed"},
        "thinking_due": False,
        "intervention_cooldown_ok": True,
        "insight_signal": primary in {"breakthrough", "integrated"},
        "is_first_response_on_topic": topic_is_first,
        "current_turn_in_topic": current_turn_in_topic,
        "has_emotional_signal": emotional_signal,
        "positive_feedback_signal": positive_feedback_signal,
        "validation_first_enabled": True,
    }
