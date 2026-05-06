"""Deterministic quality trace builder for multiagent runtime."""

from __future__ import annotations

import re
from typing import Any

from .contracts.validation_result import ValidationResult
from .contracts.writer_contract import WriterContract

QUALITY_TRACE_VERSION = "quality_trace_v1"
TOO_SHORT_CHARS = 40
TOO_LONG_CHARS = 1400
TOO_MANY_QUESTIONS = 3

_GENERIC_PHRASE_MARKERS = (
    "я понимаю",
    "это нормально",
    "важно помнить",
    "дай себе время",
    "всё индивидуально",
    "тебе стоит",
    "просто",
)

_PRACTICE_STEP_MARKERS = (
    "шаг",
    "сделай",
    "попробуй",
    "начни",
    "сегодня",
    "таймер",
    "в течение",
)


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[A-Za-zА-Яа-яЁё0-9]{2,}", text.lower())}


def _count_sentences(text: str) -> int:
    chunks = re.findall(r"[^.!?]+[.!?]?", text)
    meaningful = [chunk for chunk in chunks if chunk.strip()]
    return len(meaningful)


def _count_questions(text: str) -> int:
    return text.count("?")


def _contains_numbered_list(text: str) -> bool:
    return bool(re.search(r"(?m)^\s*\d+[\.)]\s+", text))


def _confidence_bucket(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value < 0.6:
        return "low"
    if value < 0.8:
        return "medium"
    return "high"


def _continuity_bucket(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value < 0.25:
        return "low"
    if value < 0.65:
        return "medium"
    return "high"


def _build_answer_quality(*, final_answer: str) -> dict[str, Any]:
    normalized = final_answer.strip()
    lowered = normalized.lower()
    questions = _count_questions(normalized)
    generic_markers_count = sum(lowered.count(marker) for marker in _GENERIC_PHRASE_MARKERS)

    return {
        "chars": len(normalized),
        "sentences": _count_sentences(normalized),
        "questions": questions,
        "too_short": len(normalized) < TOO_SHORT_CHARS,
        "too_long": len(normalized) > TOO_LONG_CHARS,
        "too_many_questions": questions > TOO_MANY_QUESTIONS,
        "contains_numbered_list": _contains_numbered_list(normalized),
        "generic_phrase_risk": generic_markers_count > 0,
        "generic_markers_count": generic_markers_count,
    }


def _build_state_quality(*, writer_contract: WriterContract) -> dict[str, Any]:
    thread_state = writer_contract.thread_state
    confidence = getattr(thread_state, "confidence", None)
    if isinstance(confidence, (int, float)):
        confidence_value: float | None = float(confidence)
    else:
        confidence_value = None

    return {
        "nervous_state": _to_text(getattr(thread_state, "nervous_state", "")),
        "intent": _to_text(getattr(thread_state, "intent", "")),
        "openness": _to_text(getattr(thread_state, "openness", "")),
        "ok_position": _to_text(getattr(thread_state, "ok_position", "")),
        "safety_flag": bool(getattr(thread_state, "safety_active", False)),
        "confidence": confidence_value,
        "confidence_bucket": _confidence_bucket(confidence_value),
    }


def _build_thread_quality(*, writer_contract: WriterContract) -> dict[str, Any]:
    thread_state = writer_contract.thread_state
    continuity_raw = getattr(thread_state, "continuity_score", None)
    continuity_score = float(continuity_raw) if isinstance(continuity_raw, (int, float)) else None
    open_loops = list(getattr(thread_state, "open_loops", []) or [])
    closed_loops = list(getattr(thread_state, "closed_loops", []) or [])

    return {
        "thread_id_present": bool(_to_text(getattr(thread_state, "thread_id", "")).strip()),
        "phase": _to_text(getattr(thread_state, "phase", "")),
        "relation_to_thread": _to_text(getattr(thread_state, "relation_to_thread", "")),
        "continuity_score": continuity_score,
        "continuity_bucket": _continuity_bucket(continuity_score),
        "open_loops_count": len(open_loops),
        "closed_loops_count": len(closed_loops),
        "has_open_loops": bool(open_loops),
        "has_closed_loops": bool(closed_loops),
        "turns_in_phase": int(getattr(thread_state, "turns_in_phase", 0) or 0),
    }


def _build_memory_quality(*, writer_contract: WriterContract) -> dict[str, Any]:
    memory = writer_contract.memory_bundle
    semantic_hits_count = len(list(getattr(memory, "semantic_hits", []) or []))
    rag_query_present = bool(_to_text(getattr(memory, "rag_query", "")).strip())
    conversation_context_present = bool(_to_text(getattr(memory, "conversation_context", "")).strip())

    user_profile = getattr(memory, "user_profile", None)
    user_profile_non_empty = False
    if user_profile is not None:
        user_profile_non_empty = any(
            bool(list(getattr(user_profile, key, []) or []))
            for key in ("patterns", "triggers", "values", "progress_notes")
        )

    if semantic_hits_count > 0:
        retrieval_status = "has_hits"
    elif rag_query_present:
        retrieval_status = "no_hits"
    elif not conversation_context_present and semantic_hits_count == 0:
        retrieval_status = "no_context"
    else:
        retrieval_status = "unknown"

    return {
        "context_turns": int(getattr(memory, "context_turns", 0) or 0),
        "semantic_hits_count": semantic_hits_count,
        "has_relevant_knowledge": bool(getattr(memory, "has_relevant_knowledge", False)),
        "rag_query_present": rag_query_present,
        "conversation_context_present": conversation_context_present,
        "user_profile_non_empty": user_profile_non_empty,
        "retrieval_status": retrieval_status,
    }


def _build_continuity_quality(*, final_answer: str, writer_contract: WriterContract) -> dict[str, Any]:
    answer_tokens = _tokenize(final_answer)
    memory = writer_contract.memory_bundle
    thread_state = writer_contract.thread_state

    context_tokens = _tokenize(_to_text(getattr(memory, "conversation_context", "")))
    open_loop_tokens = _tokenize(" ".join(str(item) for item in (getattr(thread_state, "open_loops", []) or [])))
    closed_loop_tokens = _tokenize(" ".join(str(item) for item in (getattr(thread_state, "closed_loops", []) or [])))

    context_overlap = len(answer_tokens.intersection(context_tokens))
    open_loop_overlap = len(answer_tokens.intersection(open_loop_tokens))
    closed_loop_overlap = len(answer_tokens.intersection(closed_loop_tokens))

    return {
        "answer_mentions_recent_context": context_overlap > 0,
        "answer_mentions_open_loop": open_loop_overlap > 0,
        "possible_closed_loop_repetition": closed_loop_overlap > 0,
        "context_overlap_terms_count": context_overlap,
        "open_loop_overlap_terms_count": open_loop_overlap,
        "closed_loop_overlap_terms_count": closed_loop_overlap,
    }


def _build_response_mode_quality(*, final_answer: str, writer_contract: WriterContract, answer_quality: dict[str, Any]) -> dict[str, Any]:
    thread_state = writer_contract.thread_state
    mode = _to_text(getattr(thread_state, "response_mode", ""))
    response_goal = _to_text(getattr(thread_state, "response_goal", ""))
    answer_lower = final_answer.lower()
    practice_step_present = any(marker in answer_lower for marker in _PRACTICE_STEP_MARKERS)

    mode_risk_flags: list[str] = []
    if mode == "practice" and not practice_step_present:
        mode_risk_flags.append("practice_without_step")
    if mode == "regulate" and bool(answer_quality.get("too_long")):
        mode_risk_flags.append("regulate_too_long")
    if mode == "validate" and bool(answer_quality.get("too_many_questions")):
        mode_risk_flags.append("validate_too_many_questions")
    if mode == "safe_override" and bool(answer_quality.get("too_long")):
        mode_risk_flags.append("safe_override_too_long")
    if mode == "explore" and int(answer_quality.get("questions", 0) or 0) == 0:
        mode_risk_flags.append("explore_no_question")

    return {
        "mode": mode,
        "goal_present": bool(response_goal.strip()),
        "practice_step_present": practice_step_present,
        "mode_risk_flags": mode_risk_flags,
    }


def _build_validator_quality(*, validation_result: ValidationResult) -> dict[str, Any]:
    quality_flags = [str(flag) for flag in (validation_result.quality_flags or [])]
    return {
        "blocked": bool(validation_result.is_blocked),
        "block_reason_present": bool(_to_text(validation_result.block_reason).strip()),
        "quality_flags_count": len(quality_flags),
        "quality_flags": quality_flags,
    }


def _build_summary_flags(
    *,
    answer_quality: dict[str, Any],
    thread_quality: dict[str, Any],
    memory_quality: dict[str, Any],
    response_mode_quality: dict[str, Any],
    validator_quality: dict[str, Any],
) -> list[str]:
    flags: list[str] = []

    if answer_quality.get("too_short"):
        flags.append("too_short")
    if answer_quality.get("too_long"):
        flags.append("too_long")
    if answer_quality.get("too_many_questions"):
        flags.append("too_many_questions")
    if answer_quality.get("generic_phrase_risk"):
        flags.append("generic_phrase_risk")

    if thread_quality.get("continuity_bucket") == "low":
        flags.append("low_continuity")

    retrieval_status = _to_text(memory_quality.get("retrieval_status"))
    if retrieval_status == "no_hits":
        flags.append("retrieval_no_hits")
    if retrieval_status == "no_context":
        flags.append("retrieval_no_context")

    for risk_flag in response_mode_quality.get("mode_risk_flags", []) or []:
        flags.append(str(risk_flag))

    if validator_quality.get("blocked"):
        flags.append("validator_blocked")

    return flags


def build_quality_trace(
    *,
    final_answer: str,
    writer_contract: WriterContract,
    validation_result: ValidationResult,
) -> dict[str, Any]:
    answer = _build_answer_quality(final_answer=final_answer)
    state = _build_state_quality(writer_contract=writer_contract)
    thread = _build_thread_quality(writer_contract=writer_contract)
    memory = _build_memory_quality(writer_contract=writer_contract)
    continuity = _build_continuity_quality(final_answer=final_answer, writer_contract=writer_contract)
    response_mode = _build_response_mode_quality(
        final_answer=final_answer,
        writer_contract=writer_contract,
        answer_quality=answer,
    )
    validator = _build_validator_quality(validation_result=validation_result)
    summary_flags = _build_summary_flags(
        answer_quality=answer,
        thread_quality=thread,
        memory_quality=memory,
        response_mode_quality=response_mode,
        validator_quality=validator,
    )

    return {
        "version": QUALITY_TRACE_VERSION,
        "answer": answer,
        "state": state,
        "thread": thread,
        "memory": memory,
        "continuity": continuity,
        "response_mode": response_mode,
        "validator": validator,
        "summary_flags": summary_flags,
    }
