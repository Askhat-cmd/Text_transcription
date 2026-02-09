"""Signal extraction helpers for decision routing."""

from __future__ import annotations

from typing import Dict


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


def detect_routing_signals(query: str, retrieved_blocks, state_analysis=None) -> Dict[str, float]:
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

    return {
        "local_similarity": local_similarity,
        "voyage_confidence": local_similarity,  # placeholder until Voyage reranker integration
        "delta_top1_top2": delta,
        "state_match": max(0.0, min(1.0, state_confidence)),
        "question_clarity": 1.0 if len(query.split()) >= 4 else 0.5,
        "explicit_ask": explicit_ask,
        "ask_type": "action" if explicit_ask else "reflection",
        "emotion_load": emotion_load,
        "contradiction": False,
        "validation_needed": primary in {"confused", "overwhelmed"},
        "thinking_due": False,
        "intervention_cooldown_ok": True,
        "insight_signal": primary in {"breakthrough", "integrated"},
    }
