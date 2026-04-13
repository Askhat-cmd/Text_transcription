import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .auth import verify_api_key, is_dev_key
from .session_store import SessionStore, get_session_store
from bot_agent.config import config

router = APIRouter(prefix="/api/debug", tags=["debug"])
logger = logging.getLogger(__name__)


def _sanitize_trace_payload(raw_trace: Dict[str, Any]) -> Dict[str, Any]:
    trace = dict(raw_trace or {})
    for key in ("sd_level", "sd_classification", "sd_detail"):
        trace.pop(key, None)
    cfg = trace.get("config_snapshot")
    if isinstance(cfg, dict):
        cfg_clean = dict(cfg)
        cfg_clean.pop("sd_confidence_threshold", None)
        cfg_clean.pop("user_level", None)
        trace["config_snapshot"] = cfg_clean
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
