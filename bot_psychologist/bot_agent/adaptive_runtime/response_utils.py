"""Shared response helper builders extracted from answer_adaptive."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..state_classifier import StateAnalysis, UserState


def _get_feedback_prompt_for_state(state: UserState) -> str:
    """Return feedback follow-up prompt based on detected user state."""
    prompts = {
        UserState.UNAWARE: "Стало ли понятнее, о чём речь? Что осталось непонятным?",
        UserState.CURIOUS: "Хотите узнать что-то ещё по этой теме?",
        UserState.OVERWHELMED: "Не слишком ли много информации? Нужно ли упростить?",
        UserState.RESISTANT: "Есть ли что-то, с чем вы не согласны? Давайте обсудим.",
        UserState.CONFUSED: "Прояснилось ли объяснение? Если нет, какая часть всё ещё непонятна?",
        UserState.COMMITTED: "Готовы ли вы начать практику? Какая поддержка нужна?",
        UserState.PRACTICING: "Как идёт практика? Есть ли сложности?",
        UserState.STAGNANT: "Что, по-вашему, мешает продвижению? Попробуем найти новый подход?",
        UserState.BREAKTHROUGH: "Поздравляю с инсайтом! Как планируете применить это понимание?",
        UserState.INTEGRATED: "Как это знание проявляется в вашей жизни?",
    }
    return prompts.get(state, "Был ли этот ответ полезен? Оцените от 1 до 5.")


def _build_partial_response(
    message: str,
    state_analysis: StateAnalysis,
    memory,
    start_time: datetime,
    query: str,
) -> Dict:
    """Build partial response payload when no blocks are retrieved."""
    return {
        "status": "partial",
        "answer": message,
        "state_analysis": {
            "primary_state": state_analysis.primary_state.value,
            "confidence": state_analysis.confidence,
            "emotional_tone": state_analysis.emotional_tone,
            "recommendations": state_analysis.recommendations,
        }
        if state_analysis
        else None,
        "path_recommendation": None,
        "conversation_context": memory.get_adaptive_context_text(query) if memory else "",
        "feedback_prompt": "Попробуйте переформулировать вопрос.",
        "sources": [],
        "concepts": [],
        "metadata": {"conversation_turns": len(memory.turns) if memory else 0},
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
    }


def _build_error_response(
    message: str,
    state_analysis: StateAnalysis,
    start_time: datetime,
) -> Dict:
    """Build error response payload for safe failure mode."""
    return {
        "status": "error",
        "answer": message,
        "state_analysis": {
            "primary_state": state_analysis.primary_state.value if state_analysis else "unknown",
            "confidence": state_analysis.confidence if state_analysis else 0,
        }
        if state_analysis
        else None,
        "path_recommendation": None,
        "conversation_context": "",
        "feedback_prompt": "",
        "sources": [],
        "concepts": [],
        "metadata": {},
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
    }


def _serialize_state_analysis(state_analysis: Optional[StateAnalysis]) -> Optional[Dict[str, Any]]:
    if state_analysis is None:
        return None
    return {
        "primary_state": state_analysis.primary_state.value,
        "confidence": state_analysis.confidence,
        "secondary_states": [s.value for s in state_analysis.secondary_states],
        "emotional_tone": state_analysis.emotional_tone,
        "depth": state_analysis.depth,
        "recommendations": state_analysis.recommendations,
    }


def _build_success_response(
    *,
    answer: str,
    state_analysis: StateAnalysis,
    path_recommendation: Optional[Dict[str, Any]],
    conversation_context: str,
    feedback_prompt: str,
    sources: List[Dict[str, Any]],
    concepts: List[str],
    metadata: Dict[str, Any],
    elapsed_time: float,
) -> Dict[str, Any]:
    return {
        "status": "success",
        "answer": answer,
        "state_analysis": _serialize_state_analysis(state_analysis),
        "path_recommendation": path_recommendation,
        "conversation_context": conversation_context,
        "feedback_prompt": feedback_prompt,
        "sources": sources,
        "concepts": concepts,
        "metadata": metadata,
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": round(elapsed_time, 2),
    }
