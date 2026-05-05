"""Общие вспомогательные функции для API-роутов."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Добавляем путь к bot_agent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot_agent.multiagent.runtime_adapter import run_multiagent_adaptive_sync

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
    enriched = _build_multiagent_trace_storage_payload(trace_payload)
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

def _normalize_semantic_hits_detail_for_debug_trace_compat(raw_hits: Any) -> list[dict]:
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


_FORBIDDEN_LEGACY_TRACE_KEYS = {
    "sd_classification",
    "sd_detail",
    "sd_level",
    "sd_secondary",
    "sd_confidence",
    "sd_method",
    "sd_allowed_blocks",
    "user_level",
    "user_level_adapter_applied",
    "decision_rule_id",
    "mode_reason",
    "confidence_level",
    "informational_mode",
    "applied_mode_prompt",
}

_FORBIDDEN_LEGACY_METADATA_KEYS = {
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
}

_COMPAT_ONLY_METADATA_KEYS = (
    "decision_rule_id",
    "mode_reason",
    "confidence_level",
    "confidence_score",
)

_MULTIAGENT_METADATA_KEYS = {
    "runtime",
    "runtime_entrypoint",
    "pipeline_version",
    "legacy_fallback_used",
    "legacy_fallback_blocked",
    "direct_multiagent_cutover",
    "thread_id",
    "phase",
    "response_mode",
    "relation_to_thread",
    "continuity_score",
    "recommended_mode",
    "runtime_user_scope",
    "session_id",
    "model_used",
    "writer_api_mode",
    "state_analyzer_api_mode",
    "tokens_prompt",
    "tokens_completion",
    "tokens_total",
    "estimated_cost_usd",
    "session_tokens_prompt",
    "session_tokens_completion",
    "session_tokens_total",
    "session_cost_usd",
    "session_turns",
    "memory_turns",
    "summary_length",
    "summary_last_turn",
    "summary_pending_turn",
    "summary_used",
    "semantic_hits",
    "context_mode",
    "hybrid_query_len",
}


def _build_debug_trace_compat_payload(raw_trace: dict) -> dict:
    trace = dict(raw_trace or {})
    for key in _FORBIDDEN_LEGACY_TRACE_KEYS:
        trace.pop(key, None)

    config_snapshot = trace.get("config_snapshot")
    if isinstance(config_snapshot, dict):
        cleaned_snapshot = dict(config_snapshot)
        for key in ("user_level", "sd_confidence_threshold"):
            cleaned_snapshot.pop(key, None)
        trace["config_snapshot"] = cleaned_snapshot

    trace["trace_contract_version"] = "multiagent_compat_v2"
    return trace


def _build_multiagent_trace_storage_payload(raw_trace: dict) -> dict:
    trace = _build_debug_trace_compat_payload(raw_trace)
    trace["trace_contract_version"] = "multiagent_v1"
    return trace


def _build_multiagent_metadata(
    raw_metadata: dict | None,
    debug_payload: dict | None = None,
) -> dict:
    metadata = dict(raw_metadata or {})
    debug = debug_payload if isinstance(debug_payload, dict) else {}
    cleaned: dict[str, Any] = {}

    for key in _MULTIAGENT_METADATA_KEYS:
        value = metadata.get(key)
        if value is not None:
            cleaned[key] = value

    fallback_map = {
        "runtime_entrypoint": "runtime_entrypoint",
        "pipeline_version": "pipeline_version",
        "legacy_fallback_used": "legacy_fallback_used",
        "legacy_fallback_blocked": "legacy_fallback_blocked",
        "direct_multiagent_cutover": "direct_multiagent_cutover",
        "thread_id": "thread_id",
        "phase": "phase",
        "response_mode": "response_mode",
        "relation_to_thread": "relation_to_thread",
        "continuity_score": "continuity_score",
        "recommended_mode": "recommended_mode",
        "model_used": "model_used",
        "writer_api_mode": "writer_api_mode",
        "state_analyzer_api_mode": "state_analyzer_api_mode",
        "tokens_prompt": "tokens_prompt",
        "tokens_completion": "tokens_completion",
        "tokens_total": "tokens_total",
        "estimated_cost_usd": "estimated_cost_usd",
    }
    for target_key, source_key in fallback_map.items():
        if cleaned.get(target_key) is None and debug.get(source_key) is not None:
            cleaned[target_key] = debug.get(source_key)

    cleaned["runtime"] = "multiagent"
    cleaned["runtime_entrypoint"] = str(cleaned.get("runtime_entrypoint") or "multiagent_adapter")
    cleaned["pipeline_version"] = str(cleaned.get("pipeline_version") or "multiagent_v1")
    cleaned["legacy_fallback_used"] = bool(cleaned.get("legacy_fallback_used", False))
    cleaned["direct_multiagent_cutover"] = bool(cleaned.get("direct_multiagent_cutover", True))

    if cleaned.get("response_mode") is None and cleaned.get("recommended_mode") is not None:
        cleaned["response_mode"] = cleaned.get("recommended_mode")
    if cleaned.get("recommended_mode") is None and cleaned.get("response_mode") is not None:
        cleaned["recommended_mode"] = cleaned.get("response_mode")

    for key in _FORBIDDEN_LEGACY_METADATA_KEYS:
        cleaned.pop(key, None)

    return cleaned


# Backward-compatible aliases for staged migration.
def _strip_legacy_trace_fields(raw_trace: dict) -> dict:
    return _build_debug_trace_compat_payload(raw_trace)


def _strip_legacy_runtime_metadata(raw_metadata: dict) -> dict:
    return _build_multiagent_metadata(raw_metadata, None)


# Compat alias used by existing tests/callers.
_normalize_semantic_hits_detail_for_debug_trace = _normalize_semantic_hits_detail_for_debug_trace_compat


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
    metadata = _build_multiagent_metadata(
        result.get("metadata", {}) or {},
        result.get("debug", {}) or {},
    )
    confidence_score = metadata.get("continuity_score")
    if confidence_score is None:
        confidence_score = metadata.get("confidence_score")
    return AnswerResponse(
        status=result.get("status", "success"),
        answer=result.get("answer", ""),
        concepts=result.get("concepts", []),
        sources=_to_sources(result.get("sources", [])),
        recommended_mode=metadata.get("response_mode") or metadata.get("recommended_mode"),
        decision_rule_id=None,
        confidence_level=None,
        confidence_score=confidence_score,
        metadata=metadata,
        timestamp=datetime.now().isoformat(),
        processing_time_seconds=result.get("processing_time_seconds", 0),
    )

def _run_multiagent_compat_answer(
    *,
    request: AskQuestionRequest,
    session_store: SessionStore | None = None,
) -> dict:
    session_key = request.session_id or request.user_id
    return run_multiagent_adaptive_sync(
        query=request.query,
        user_id=session_key,
        include_path_recommendation=False,
        include_feedback_prompt=False,
        debug=request.debug,
        session_store=session_store,
    )


# Backward-compatible alias for existing imports/tests.
_run_neo_compat_answer = _run_multiagent_compat_answer

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

