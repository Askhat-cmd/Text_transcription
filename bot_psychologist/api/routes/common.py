"""Общие вспомогательные функции для API-роутов."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Добавляем путь к bot_agent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot_agent import answer_question_adaptive

from ..models import (
    AskQuestionRequest,
    AnswerResponse,
    ChunkTraceItem,
    SourceResponse,
)
from ..session_store import SessionStore

logger = logging.getLogger(__name__)

# Агрегированная статистика (в production хранится во внешнем хранилище)
_stats = {
    "total_users_approx": 0,
    "total_questions": 0,
    "total_processing_time": 0.0,
    "states_count": {},
    "interests_count": {},
}
_STATS_USER_LIMIT = 10_000
_seen_users: set[str] = set()

def _record_user(user_id: str) -> None:
    if user_id in _seen_users:
        return
    if len(_seen_users) >= _STATS_USER_LIMIT:
        _seen_users.clear()
    _seen_users.add(user_id)
    _stats["total_users_approx"] += 1

def _coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default

def _extract_token_triplet(trace_payload: Dict[str, Any]) -> tuple[int, int, int]:
    llm_calls = trace_payload.get("llm_calls") if isinstance(trace_payload.get("llm_calls"), list) else []
    prompt = trace_payload.get("tokens_prompt")
    completion = trace_payload.get("tokens_completion")
    total = trace_payload.get("tokens_total")

    if prompt is None and llm_calls:
        prompt = sum(_coerce_int(call.get("tokens_prompt")) for call in llm_calls if isinstance(call, dict))
    if completion is None and llm_calls:
        completion = sum(_coerce_int(call.get("tokens_completion")) for call in llm_calls if isinstance(call, dict))
    if total is None and llm_calls:
        total = sum(_coerce_int(call.get("tokens_total")) for call in llm_calls if isinstance(call, dict))

    prompt_value = _coerce_int(prompt, 0)
    completion_value = _coerce_int(completion, 0)
    total_value = _coerce_int(total, prompt_value + completion_value)
    return prompt_value, completion_value, total_value

def _build_turn_diff(previous_trace: Optional[Dict[str, Any]], current_trace: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(previous_trace, dict):
        return {
            "route_changed": False,
            "state_changed": False,
            "config_changed_keys": [],
            "memory_delta": {
                "turns_added": 0,
                "summary_changed": False,
                "semantic_hits_delta": 0,
            },
        }

    prev_config = previous_trace.get("config_snapshot") if isinstance(previous_trace.get("config_snapshot"), dict) else {}
    curr_config = current_trace.get("config_snapshot") if isinstance(current_trace.get("config_snapshot"), dict) else {}
    config_keys = sorted(set(prev_config.keys()) | set(curr_config.keys()))
    config_changed_keys = [
        key for key in config_keys if prev_config.get(key) != curr_config.get(key)
    ]

    prev_memory_turns = _coerce_int(previous_trace.get("memory_turns"), 0)
    curr_memory_turns = _coerce_int(current_trace.get("memory_turns"), 0)
    prev_semantic_hits = _coerce_int(previous_trace.get("semantic_hits"), 0)
    curr_semantic_hits = _coerce_int(current_trace.get("semantic_hits"), 0)

    summary_changed = (
        previous_trace.get("summary_text") != current_trace.get("summary_text")
        or previous_trace.get("summary_last_turn") != current_trace.get("summary_last_turn")
    )

    return {
        "route_changed": previous_trace.get("recommended_mode") != current_trace.get("recommended_mode"),
        "state_changed": previous_trace.get("user_state") != current_trace.get("user_state"),
        "config_changed_keys": config_changed_keys,
        "memory_delta": {
            "turns_added": curr_memory_turns - prev_memory_turns,
            "summary_changed": bool(summary_changed),
            "semantic_hits_delta": curr_semantic_hits - prev_semantic_hits,
        },
    }

def _enrich_trace_for_storage(
    *,
    previous_trace: Optional[Dict[str, Any]],
    trace_payload: Dict[str, Any],
) -> Dict[str, Any]:
    enriched = _strip_legacy_trace_fields(trace_payload)
    prompt, completion, total = _extract_token_triplet(enriched)
    if enriched.get("tokens_prompt") is None:
        enriched["tokens_prompt"] = prompt
    if enriched.get("tokens_completion") is None:
        enriched["tokens_completion"] = completion
    if enriched.get("tokens_total") is None:
        enriched["tokens_total"] = total
    enriched["turn_diff"] = _build_turn_diff(previous_trace, enriched)
    return enriched

def _append_trace_with_resolved_session(
    *,
    store: SessionStore,
    default_session_key: str,
    trace_payload: dict,
) -> dict:
    """
    Persist trace under runtime session id when available.

    In Neo runtime the effective session id can differ from request user_id.
    UI debug surfaces use trace.session_id, so we keep both keys for
    backward compatibility.
    """
    resolved_session_key = str(trace_payload.get("session_id") or "").strip() or default_session_key
    previous = store.get_session_traces(resolved_session_key)
    previous_trace = previous[-1] if previous else None
    trace_enriched = _enrich_trace_for_storage(previous_trace=previous_trace, trace_payload=trace_payload)

    store.append_trace(resolved_session_key, trace_enriched)
    if resolved_session_key != default_session_key:
        store.append_trace(default_session_key, trace_enriched)

    return trace_enriched

def _to_chunk_trace_item(raw_chunk: dict, passed_default: bool) -> ChunkTraceItem:
    score_initial = float(raw_chunk.get("score_initial", raw_chunk.get("score", 0.0) or 0.0))
    score_final = float(raw_chunk.get("score_final", raw_chunk.get("score", score_initial) or score_initial))
    passed_filter = bool(raw_chunk.get("passed_filter", passed_default))
    chunk_text = raw_chunk.get("text") or raw_chunk.get("full_text")
    preview = (
        raw_chunk.get("preview")
        or raw_chunk.get("content")
        or raw_chunk.get("summary")
        or ""
    )
    return ChunkTraceItem(
        block_id=str(raw_chunk.get("block_id", "")),
        title=str(raw_chunk.get("title", "")),
        emotional_tone=str(raw_chunk.get("emotional_tone") or ""),
        score_initial=score_initial,
        score_final=score_final,
        passed_filter=passed_filter,
        filter_reason=str(raw_chunk.get("filter_reason") or ""),
        preview=str(preview)[:120],
        text=str(chunk_text) if chunk_text is not None else None,
    )

def _strip_legacy_trace_fields(raw_trace: dict) -> dict:
    trace = dict(raw_trace or {})

    for key in (
        "sd_classification",
        "sd_detail",
        "sd_level",
        "sd_secondary",
        "sd_confidence",
        "sd_method",
        "sd_allowed_blocks",
        "user_level",
        "user_level_adapter_applied",
    ):
        trace.pop(key, None)

    config_snapshot = trace.get("config_snapshot")
    if isinstance(config_snapshot, dict):
        cleaned_snapshot = dict(config_snapshot)
        for key in ("user_level", "sd_confidence_threshold"):
            cleaned_snapshot.pop(key, None)
        trace["config_snapshot"] = cleaned_snapshot

    trace["trace_contract_version"] = "v2"

    return trace


def _normalize_semantic_hits_detail_for_debug_trace(raw_hits: Any) -> list[dict]:
    """
    Приводит semantic_hits_detail к контракту DebugTrace:
    - block_id
    - score
    - text_preview
    - source

    Поддерживает оба формата:
    - legacy/v2: block_id + text_preview
    - multiagent: chunk_id + content_preview/content_full
    """
    if not isinstance(raw_hits, list):
        return []

    normalized: list[dict] = []
    for item in raw_hits:
        if not isinstance(item, dict):
            continue

        block_id = str(item.get("block_id") or item.get("chunk_id") or "").strip()
        score_raw = item.get("score", 0.0)
        try:
            score = float(score_raw or 0.0)
        except (TypeError, ValueError):
            score = 0.0

        text_preview = str(
            item.get("text_preview")
            or item.get("content_preview")
            or item.get("content_full")
            or ""
        )
        source = item.get("source")
        normalized.append(
            {
                "block_id": block_id,
                "score": score,
                "text_preview": text_preview[:200],
                "source": str(source) if source is not None else None,
            }
        )

    return normalized

_LEGACY_RUNTIME_METADATA_KEYS = (
    "user_level",
    "user_level_adapter_applied",
    "sd_level",
    "sd_secondary",
    "sd_confidence",
    "sd_method",
    "sd_allowed_blocks",
    "decision_rule_id",
    "mode_reason",
    "confidence_level",
    "confidence_score",
)


def _strip_legacy_runtime_metadata(raw_metadata: dict) -> dict:
    metadata = dict(raw_metadata or {})
    for key in _LEGACY_RUNTIME_METADATA_KEYS:
        metadata.pop(key, None)
    return metadata

def _to_sources(raw_sources: list[dict]) -> list[SourceResponse]:
    return [
        SourceResponse(
            block_id=src.get("block_id", ""),
            title=src.get("title", ""),
            youtube_link=src.get("youtube_link", ""),
            start=src.get("start", 0),
            end=src.get("end", 0),
            block_type=src.get("block_type", "unknown"),
            complexity_score=src.get("complexity_score", 0.0),
        )
        for src in (raw_sources or [])
    ]

def _build_answer_response_from_adaptive(result: dict) -> AnswerResponse:
    metadata = _strip_legacy_runtime_metadata(result.get("metadata", {}) or {})
    return AnswerResponse(
        status=result.get("status", "success"),
        answer=result.get("answer", ""),
        concepts=result.get("concepts", []),
        sources=_to_sources(result.get("sources", [])),
        recommended_mode=metadata.get("recommended_mode"),
        decision_rule_id=metadata.get("decision_rule_id"),
        confidence_level=metadata.get("confidence_level"),
        confidence_score=metadata.get("confidence_score"),
        metadata=metadata,
        timestamp=datetime.now().isoformat(),
        processing_time_seconds=result.get("processing_time_seconds", 0),
    )

def _run_neo_compat_answer(
    *,
    request: AskQuestionRequest,
    session_store: SessionStore | None = None,
) -> dict:
    session_key = request.session_id or request.user_id
    return answer_question_adaptive(
        request.query,
        user_id=session_key,
        include_path_recommendation=False,
        include_feedback_prompt=False,
        debug=request.debug,
        session_store=session_store,
    )

def _session_title(item: dict) -> str:
    metadata = item.get("metadata") or {}
    raw_title = metadata.get("title")
    if isinstance(raw_title, str) and raw_title.strip():
        return raw_title.strip()

    last_user_input = (item.get("last_user_input") or "").strip()
    if not last_user_input:
        return "New chat"
    if len(last_user_input) <= 42:
        return last_user_input
    return f"{last_user_input[:42]}..."

