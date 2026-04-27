import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .auth import verify_api_key, is_dev_key
from .models import (
    AnomalyItem,
    MemoryContextTrace,
    MemoryRetrievalTrace,
    MultiAgentPipelineTrace,
    MultiAgentTraceResponse,
    SemanticHitTrace,
    SessionDashboard,
    StateAnalyzerTrace,
    ThreadManagerTrace,
    TurnDiffTrace,
    ValidatorTrace,
    WriterLLMTrace,
    WriterTrace,
)
from .session_store import SessionStore, get_session_store
from bot_agent.config import config

router = APIRouter(prefix="/api/debug", tags=["debug"])
logger = logging.getLogger(__name__)


def _sanitize_trace_payload(raw_trace: Dict[str, Any]) -> Dict[str, Any]:
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
        sanitized_snapshot = dict(config_snapshot)
        for key in ("user_level", "sd_confidence_threshold"):
            sanitized_snapshot.pop(key, None)
        trace["config_snapshot"] = sanitized_snapshot

    trace["trace_contract_version"] = "v2"
    return trace


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _derive_turn_tokens(trace: Dict[str, Any]) -> tuple[int, int, int]:
    llm_calls = trace.get("llm_calls") if isinstance(trace.get("llm_calls"), list) else []

    prompt = _safe_int(trace.get("tokens_prompt"))
    completion = _safe_int(trace.get("tokens_completion"))
    total = _safe_int(trace.get("tokens_total"))

    if prompt is None and llm_calls:
        prompt = sum(_safe_int(call.get("tokens_prompt")) or 0 for call in llm_calls if isinstance(call, dict))
    if completion is None and llm_calls:
        completion = sum(_safe_int(call.get("tokens_completion")) or 0 for call in llm_calls if isinstance(call, dict))
    if total is None and llm_calls:
        total = sum(_safe_int(call.get("tokens_total")) or 0 for call in llm_calls if isinstance(call, dict))

    prompt_value = prompt or 0
    completion_value = completion or 0
    if total is None:
        total_value = prompt_value + completion_value
    else:
        total_value = total

    return prompt_value, completion_value, total_value


def _build_turn_diff(
    *,
    current: Dict[str, Any],
    previous: Optional[Dict[str, Any]],
) -> Optional[TurnDiffTrace]:
    if not isinstance(previous, dict):
        return None

    prev_state = str(previous.get("nervous_state") or "").strip() or None
    curr_state = str(current.get("nervous_state") or "").strip()
    prev_phase = str(previous.get("phase") or "").strip() or None
    curr_phase = str(current.get("phase") or "").strip()
    relation = str(current.get("relation_to_thread") or "").strip()

    curr_turns = _safe_int(current.get("context_turns")) or 0
    prev_turns = _safe_int(previous.get("context_turns")) or 0
    curr_hits = _safe_int(current.get("semantic_hits_count")) or 0
    prev_hits = _safe_int(previous.get("semantic_hits_count")) or 0

    state_changed = prev_state != curr_state
    phase_changed = prev_phase != curr_phase
    memory_delta = curr_turns - prev_turns
    hits_delta = curr_hits - prev_hits

    if not (state_changed or phase_changed or memory_delta != 0 or hits_delta != 0):
        return None

    return TurnDiffTrace(
        nervous_state_prev=prev_state,
        nervous_state_curr=curr_state,
        phase_prev=prev_phase,
        phase_curr=curr_phase,
        relation_to_thread=relation,
        memory_turns_delta=memory_delta,
        semantic_hits_delta=hits_delta,
    )


def _build_anomalies(debug: Dict[str, Any]) -> List[AnomalyItem]:
    anomalies: List[AnomalyItem] = []
    timings = debug.get("timings") if isinstance(debug.get("timings"), dict) else {}
    total_ms = max(_safe_int(debug.get("total_latency_ms")) or 0, 1)
    writer_ms = max(_safe_int(timings.get("writer_ms")) or 0, 0)

    if writer_ms > 0 and (writer_ms / total_ms) > 0.6:
        anomalies.append(
            AnomalyItem(
                code="SLOW_WRITER",
                severity="WARN",
                message=f"Writer занял {writer_ms}ms ({round(writer_ms / total_ms * 100)}% общего времени)",
            )
        )
    if bool(debug.get("safety_flag")):
        anomalies.append(
            AnomalyItem(
                code="SAFETY_FLAG",
                severity="WARN",
                message="State Analyzer обнаружил признак кризисного состояния",
            )
        )
    if bool(debug.get("validator_blocked")):
        anomalies.append(
            AnomalyItem(
                code="VALIDATOR_BLOCKED",
                severity="ERROR",
                message=f"Ответ заблокирован: {debug.get('validator_block_reason', 'неизвестная причина')}",
            )
        )
    return anomalies


def _compact_trace_payload(raw_trace: Dict[str, Any]) -> Dict[str, Any]:
    trace = dict(raw_trace or {})

    for key in (
        "memory_turns_content",
        "summary_text",
        "semantic_hits_detail",
        "hybrid_query_text",
        "context_written",
    ):
        trace.pop(key, None)

    llm_calls = trace.get("llm_calls") if isinstance(trace.get("llm_calls"), list) else []
    compact_calls: List[Dict[str, Any]] = []
    for call in llm_calls:
        if not isinstance(call, dict):
            continue
        compact_calls.append(
            {
                "step": call.get("step"),
                "model": call.get("model"),
                "duration_ms": call.get("duration_ms"),
                "tokens_prompt": call.get("tokens_prompt"),
                "tokens_completion": call.get("tokens_completion"),
                "tokens_total": call.get("tokens_total"),
                "blob_error": call.get("blob_error"),
            }
        )
    trace["llm_calls"] = compact_calls

    stages = trace.get("pipeline_stages")
    if isinstance(stages, list):
        trace["pipeline_stages"] = [
            stage for stage in stages
            if isinstance(stage, dict) and not bool(stage.get("skipped"))
        ]

    return trace


@router.get("/blob/{blob_id}")
async def get_blob(
    blob_id: str,
    api_key: str = Depends(verify_api_key),
    store: SessionStore = Depends(get_session_store),
):
    if not is_dev_key(api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debug access denied")
    content = store.get_blob(blob_id)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blob not found or expired")
    content = _sanitize_pii(content)
    return {"blob_id": blob_id, "content": content}


@router.get("/session/{session_id}/metrics")
async def get_session_metrics(
    session_id: str,
    api_key: str = Depends(verify_api_key),
    store: SessionStore = Depends(get_session_store),
):
    if not is_dev_key(api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debug access denied")
    traces = store.get_session_traces(session_id)
    if not traces:
        return {
            "total_turns": 0,
            "fast_path_pct": 0,
            "avg_llm_time_ms": 0,
            "max_llm_time_ms": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "turns_with_anomalies": 0,
            "anomaly_turns_indices": [],
        }
    sanitized = [_sanitize_trace_payload(t) for t in traces if isinstance(t, dict)]
    return _aggregate_session_metrics(sanitized)


@router.get("/session/{session_id}/traces")
async def get_session_traces(
    session_id: str,
    format: str = Query(default="full"),
    api_key: str = Depends(verify_api_key),
    store: SessionStore = Depends(get_session_store),
):
    if not is_dev_key(api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debug access denied")
    traces = store.get_session_traces(session_id)
    sanitized = [_sanitize_trace_payload(t) for t in traces if isinstance(t, dict)]
    format_value = (format or "full").strip().lower()
    if format_value not in {"full", "compact"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported format")
    if format_value == "compact":
        sanitized = [_compact_trace_payload(trace) for trace in sanitized]
    return {"session_id": session_id, "format": format_value, "traces": sanitized}


@router.get(
    "/session/{session_id}/multiagent-trace",
    response_model=MultiAgentTraceResponse,
)
async def get_multiagent_trace(
    session_id: str,
    turn_index: Optional[int] = Query(default=None),
    api_key: str = Depends(verify_api_key),
    store: SessionStore = Depends(get_session_store),
):
    if not is_dev_key(api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debug access denied")

    if turn_index is None:
        debug = store.get_latest_multiagent_debug(session_id)
    else:
        debug = store.get_multiagent_debug(session_id, turn_index)

    if not debug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Multiagent trace not found for this session",
        )

    if not bool(debug.get("multiagent_enabled")):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session was processed by legacy pipeline",
        )

    timings = debug.get("timings") if isinstance(debug.get("timings"), dict) else {}
    tokens_used = debug.get("tokens_used")
    if tokens_used is None:
        tokens_used = debug.get("tokens_total")

    model_used = debug.get("model_used") or debug.get("primary_model")
    resolved_turn_index = _safe_int(debug.get("turn_index"))
    previous_debug = None
    if isinstance(resolved_turn_index, int) and resolved_turn_index > 1:
        previous_debug = store.get_multiagent_debug(session_id, resolved_turn_index - 1)

    raw_hits = debug.get("semantic_hits_detail")
    semantic_hits: List[SemanticHitTrace] = []
    if isinstance(raw_hits, list):
        for item in raw_hits:
            if not isinstance(item, dict):
                continue
            semantic_hits.append(
                SemanticHitTrace(
                    chunk_id=str(item.get("chunk_id", "")),
                    source=str(item.get("source", "unknown")),
                    score=float(item.get("score", 0.0) or 0.0),
                    content_preview=str(item.get("content_preview", "")),
                    content_full=str(item.get("content_full", "")),
                )
            )

    profile = debug.get("user_profile") if isinstance(debug.get("user_profile"), dict) else {}
    memory_written = debug.get("memory_written")
    if isinstance(memory_written, dict):
        memory_written_preview = (
            f"user: {str(memory_written.get('user_input', '') or '')}\n"
            f"assistant: {str(memory_written.get('bot_response', '') or '')}\n"
            f"thread_id: {str(memory_written.get('thread_id', '') or '')} | "
            f"phase: {str(memory_written.get('phase', '') or '')}"
        ).strip()
    else:
        memory_written_preview = str(memory_written or "")

    memory_context = MemoryContextTrace(
        conversation_context=str(debug.get("conversation_context", "") or ""),
        rag_query=str(debug.get("rag_query", "") or ""),
        semantic_hits=semantic_hits,
        user_profile_patterns=[str(v) for v in (profile.get("patterns") or [])],
        user_profile_values=[str(v) for v in (profile.get("values") or [])],
        memory_written_preview=memory_written_preview,
    )

    writer_llm = WriterLLMTrace(
        system_prompt=str(debug.get("writer_system_prompt", "") or ""),
        user_prompt=str(debug.get("writer_user_prompt", "") or ""),
        llm_response_raw=str(debug.get("writer_llm_response_raw", "") or ""),
        model=str(model_used or ""),
        temperature=float(debug.get("model_temperature") or 0.7),
        max_tokens=_safe_int(debug.get("model_max_tokens")) or 600,
        tokens_prompt=_safe_int(debug.get("tokens_prompt")),
        tokens_completion=_safe_int(debug.get("tokens_completion")),
        tokens_total=_safe_int(debug.get("tokens_total")),
        estimated_cost_usd=(
            float(debug.get("estimated_cost_usd"))
            if isinstance(debug.get("estimated_cost_usd"), (int, float))
            else None
        ),
    )

    anomalies = _build_anomalies(debug)
    turn_diff = _build_turn_diff(current=debug, previous=previous_debug)

    stats = store.get_session_stats(session_id)
    total_turns = int(stats.get("total_turns", 0) or 0)
    avg_latency = (
        round((int(stats.get("total_latency_ms", 0) or 0) / max(total_turns, 1)))
        if total_turns > 0
        else 0
    )
    session_dashboard = SessionDashboard(
        total_turns=total_turns,
        avg_latency_ms=int(avg_latency),
        total_cost_usd=float(stats.get("total_cost_usd", 0.0) or 0.0),
        state_trajectory=[str(v) for v in (stats.get("state_trajectory") or [])],
        thread_switches=int(stats.get("thread_switches", 0) or 0),
        safety_events=int(stats.get("safety_events", 0) or 0),
        validator_blocks=int(stats.get("validator_blocks", 0) or 0),
    )

    return MultiAgentTraceResponse(
        session_id=session_id,
        turn_index=resolved_turn_index,
        pipeline_version=str(debug.get("pipeline_version") or "multiagent_v1"),
        total_latency_ms=_safe_int(debug.get("total_latency_ms")) or 0,
        agents=MultiAgentPipelineTrace(
            state_analyzer=StateAnalyzerTrace(
                latency_ms=_safe_int(timings.get("state_analyzer_ms")) or 0,
                nervous_state=str(debug.get("nervous_state") or "neutral"),
                intent=str(debug.get("intent") or ""),
                safety_flag=bool(debug.get("safety_flag", False)),
                confidence=float(debug.get("confidence") or 0.0),
            ),
            thread_manager=ThreadManagerTrace(
                latency_ms=_safe_int(timings.get("thread_manager_ms")) or 0,
                thread_id=str(debug.get("thread_id") or ""),
                phase=str(debug.get("phase") or "exploring"),
                relation_to_thread=str(debug.get("relation_to_thread") or "continue"),
                continuity_score=float(debug.get("continuity_score") or 0.0),
            ),
            memory_retrieval=MemoryRetrievalTrace(
                latency_ms=_safe_int(timings.get("memory_retrieval_ms")) or 0,
                context_turns=_safe_int(debug.get("context_turns")) or 0,
                semantic_hits_count=_safe_int(debug.get("semantic_hits_count")) or 0,
                has_relevant_knowledge=bool(debug.get("has_relevant_knowledge", False)),
            ),
            writer=WriterTrace(
                latency_ms=_safe_int(timings.get("writer_ms")) or 0,
                response_mode=str(debug.get("response_mode") or ""),
                tokens_used=_safe_int(tokens_used),
                model_used=str(model_used) if model_used is not None else None,
            ),
            validator=ValidatorTrace(
                latency_ms=_safe_int(timings.get("validator_ms")) or 0,
                is_blocked=bool(debug.get("validator_blocked", False)),
                block_reason=str(debug.get("validator_block_reason"))
                if debug.get("validator_block_reason") is not None
                else None,
                quality_flags=[str(item) for item in (debug.get("validator_quality_flags") or [])],
            ),
        ),
        memory_context=memory_context,
        writer_llm=writer_llm,
        turn_diff=turn_diff,
        anomalies=anomalies,
        session_dashboard=session_dashboard,
    )


@router.get("/session/{session_id}/llm-payload")
async def get_session_llm_payload(
    session_id: str,
    format: str = Query(default="structured"),
    api_key: str = Depends(verify_api_key),
    store: SessionStore = Depends(get_session_store),
):
    if not is_dev_key(api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debug access denied")

    traces = store.get_session_traces(session_id)
    if not traces:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session trace not found")

    trace = _sanitize_trace_payload(traces[-1])
    llm_calls = trace.get("llm_calls") or []
    if not llm_calls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No LLM payload for this session")

    flat_payload = _build_flat_payload(
        session_id=session_id,
        trace=trace,
        llm_calls=llm_calls,
        store=store,
    )
    if (format or "").strip().lower() == "flat":
        return flat_payload
    return _build_structured_payload(trace=trace, flat_payload=flat_payload)


def _sanitize_pii(text: str) -> str:
    import re

    text = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w]{2,}\b", "[email]", text)
    text = re.sub(r"\b\+?[\d\s\-()]{10,15}\b", "[phone]", text)
    return text


def _estimate_tokens(text: str) -> int:
    return max(0, len(text or "") // 4)


def _clip_for_payload(text: str) -> str:
    value = _sanitize_pii(text or "")
    if bool(getattr(config, "LLM_PAYLOAD_INCLUDE_FULL_CONTENT", True)):
        return value
    return value[:1200]


def _extract_section(text: str, start_marker: str, *end_markers: str) -> str:
    source = str(text or "")
    if not source:
        return ""
    start_idx = source.find(start_marker)
    if start_idx < 0:
        return ""
    start_idx += len(start_marker)
    end_candidates = []
    for marker in end_markers:
        idx = source.find(marker, start_idx)
        if idx >= 0:
            end_candidates.append(idx)
    end_idx = min(end_candidates) if end_candidates else len(source)
    return source[start_idx:end_idx].strip()


def _extract_section_by_markers(
    text: str,
    start_markers: List[str],
    end_markers: List[str],
) -> str:
    for marker in start_markers:
        value = _extract_section(text, marker, *end_markers)
        if value:
            return value
    return ""


def _section_payload(name: str, content: str, **extra: Any) -> Dict[str, Any]:
    text = _clip_for_payload(content)
    payload: Dict[str, Any] = {
        "name": name,
        "chars": len(text),
        "tokens_est": _estimate_tokens(text),
        "content": text,
    }
    payload.update(extra)
    return payload


def _build_flat_payload(
    *,
    session_id: str,
    trace: Dict[str, Any],
    llm_calls: List[Dict[str, Any]],
    store: SessionStore,
) -> Dict[str, Any]:
    payload_calls = []
    for call in llm_calls:
        system_blob_id = call.get("system_prompt_blob_id") or trace.get("system_prompt_blob_id")
        user_blob_id = call.get("user_prompt_blob_id") or trace.get("user_prompt_blob_id")
        payload_calls.append(
            {
                "step": call.get("step"),
                "model": call.get("model"),
                "duration_ms": call.get("duration_ms"),
                "tokens_prompt": call.get("tokens_prompt"),
                "tokens_completion": call.get("tokens_completion"),
                "tokens_total": call.get("tokens_total"),
                "system_prompt": _clip_for_payload(
                    store.get_blob(system_blob_id) or call.get("system_prompt_preview") or ""
                ),
                "user_prompt": _clip_for_payload(
                    store.get_blob(user_blob_id) or call.get("user_prompt_preview") or ""
                ),
                "response_preview": _clip_for_payload(call.get("response_preview") or ""),
                "blob_error": call.get("blob_error"),
            }
        )

    memory_blob_id = trace.get("memory_snapshot_blob_id")
    memory_snapshot = _clip_for_payload(store.get_blob(memory_blob_id) or "") if memory_blob_id else ""
    payload = {
        "session_id": session_id,
        "turn_number": trace.get("turn_number"),
        "recommended_mode": trace.get("recommended_mode"),
        "user_state": trace.get("user_state"),
        "hybrid_query_preview": trace.get("hybrid_query_preview"),
        "chunks_count": len(trace.get("chunks_after_filter") or trace.get("chunks_retrieved") or []),
        "llm_calls": payload_calls,
        "memory_snapshot": memory_snapshot,
    }
    return payload


def _build_retrieval_blocks(trace: Dict[str, Any]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    blocks = trace.get("chunks_after_filter") or trace.get("chunks_retrieved") or []
    for item in blocks:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "block_id": item.get("block_id"),
                "title": item.get("title"),
                "score": item.get("score_final") or item.get("score"),
            }
        )
    return result


def _build_structured_payload(*, trace: Dict[str, Any], flat_payload: Dict[str, Any]) -> Dict[str, Any]:
    calls = flat_payload.get("llm_calls") or []
    preferred = next((c for c in calls if str(c.get("step") or "").lower() == "answer"), calls[0] if calls else {})
    system_prompt = str(preferred.get("system_prompt") or "")
    user_prompt = str(preferred.get("user_prompt") or "")

    summary_in_prompt = _extract_section_by_markers(
        user_prompt,
        start_markers=[
            "[СВОДКА ДИАЛОГА / CONVERSATION SUMMARY]",
            "[CONVERSATION SUMMARY]",
            "[СВОДКА ДИАЛОГА]",
        ],
        end_markers=[
            "[ПОСЛЕДНИЙ ДИАЛОГ / RECENT DIALOG]",
            "[RECENT DIALOG]",
            "[ПОСЛЕДНИЙ ДИАЛОГ]",
            "МАТЕРИАЛ ИЗ ЛЕКЦИЙ:",
        ],
    )
    summary_content = summary_in_prompt or str(trace.get("summary_text") or "")

    recent_content = _extract_section_by_markers(
        user_prompt,
        start_markers=[
            "[ПОСЛЕДНИЙ ДИАЛОГ / RECENT DIALOG]",
            "[RECENT DIALOG]",
            "[ПОСЛЕДНИЙ ДИАЛОГ]",
        ],
        end_markers=[
            "МАТЕРИАЛ ИЗ ЛЕКЦИЙ:",
        ],
    )
    knowledge_content = _extract_section_by_markers(
        user_prompt,
        start_markers=["МАТЕРИАЛ ИЗ ЛЕКЦИЙ:"],
        end_markers=[
            "ВОПРОС ПОЛЬЗОВАТЕЛЯ:",
            "ЗАПРОС ПОЛЬЗОВАТЕЛЯ:",
        ],
    )
    task_content = _extract_section_by_markers(
        user_prompt,
        start_markers=[
            "ВОПРОС ПОЛЬЗОВАТЕЛЯ:",
            "ЗАПРОС ПОЛЬЗОВАТЕЛЯ:",
        ],
        end_markers=[],
    )

    recent_turns_count = recent_content.count("- user:")
    knowledge_blocks_count = knowledge_content.count("---")
    summary_present = bool(summary_in_prompt.strip())
    turn_index = trace.get("turn_number")
    summary_pending_turn = trace.get("summary_pending_turn")
    summary_lag = bool(
        summary_pending_turn
        and turn_index
        and int(summary_pending_turn) == int(turn_index)
        and not summary_present
    )
    if summary_lag:
        logger.warning(
            "[LLM_PAYLOAD] summary_lag=true session=%s turn=%s",
            flat_payload.get("session_id"),
            turn_index,
        )

    hybridquery_text = str(trace.get("hybrid_query_text") or trace.get("hybrid_query_preview") or "")
    hybridquery_text = _clip_for_payload(hybridquery_text)
    hybridquery_len = trace.get("hybrid_query_len")
    if hybridquery_len is None:
        hybridquery_len = len(hybridquery_text)
    try:
        hybridquery_len_value = int(hybridquery_len)
    except (TypeError, ValueError):
        hybridquery_len_value = len(hybridquery_text)

    sections = [
        _section_payload("CORE_IDENTITY", system_prompt),
        _section_payload(
            "CONVERSATION_SUMMARY",
            summary_content,
            present=summary_present,
        ),
        _section_payload(
            "RECENT_DIALOG",
            recent_content,
            turns_count=recent_turns_count,
        ),
        _section_payload(
            "KNOWLEDGE_CONTEXT",
            knowledge_content,
            blocks_count=knowledge_blocks_count,
        ),
        _section_payload("TASK_INSTRUCTION", task_content),
    ]

    total_chars = sum(int(item.get("chars") or 0) for item in sections)
    total_tokens_est = sum(int(item.get("tokens_est") or 0) for item in sections)
    context_mode = str(
        trace.get("context_mode")
        or ("summary" if bool(trace.get("summary_used")) else "full")
    )

    return {
        "session_id": flat_payload.get("session_id"),
        "turn_index": turn_index,
        "context_mode": context_mode,
        "total_chars": total_chars,
        "total_tokens_est": total_tokens_est,
        "sections": sections,
        "retrieval_blocks": _build_retrieval_blocks(trace),
        "diagnostics": {
            "summary_present": summary_present,
            "summary_lag": summary_lag,
            "recent_dialog_turns": recent_turns_count,
            "hybridquery_len": hybridquery_len_value,
            "hybridquery_text": hybridquery_text,
        },
    }


def _aggregate_session_metrics(traces: list) -> dict:
    total = len(traces)
    fast_path_count = sum(1 for t in traces if t.get("fast_path"))
    llm_times = [(_safe_int(t.get("total_duration_ms")) or 0) for t in traces]
    costs = [t.get("estimated_cost_usd", 0) or 0 for t in traces]
    anomaly_counts = [len(t.get("anomalies", [])) for t in traces]
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    for trace in traces:
        prompt, completion, tokens_total = _derive_turn_tokens(trace)
        total_prompt_tokens += prompt
        total_completion_tokens += completion
        total_tokens += tokens_total

    return {
        "total_turns": total,
        "fast_path_pct": round(fast_path_count / total * 100, 1) if total else 0,
        "avg_llm_time_ms": round(sum(llm_times) / total) if total else 0,
        "max_llm_time_ms": max(llm_times) if llm_times else 0,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "total_cost_usd": round(sum(costs), 6),
        "turns_with_anomalies": sum(1 for c in anomaly_counts if c > 0),
        "anomaly_turns_indices": [i for i, c in enumerate(anomaly_counts) if c > 0],
    }
