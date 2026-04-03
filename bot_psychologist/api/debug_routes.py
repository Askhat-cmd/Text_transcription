from fastapi import APIRouter, Depends, HTTPException, status

from .auth import verify_api_key, is_dev_key
from .session_store import SessionStore, get_session_store
from bot_agent.feature_flags import feature_flags

router = APIRouter(prefix="/api/debug", tags=["debug"])


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
            "sd_distribution": {
                "GREEN": 0,
                "YELLOW": 0,
                "RED": 0,
            },
            "avg_llm_time_ms": 0,
            "max_llm_time_ms": 0,
            "total_cost_usd": 0.0,
            "turns_with_anomalies": 0,
            "anomaly_turns_indices": [],
        }
    return _aggregate_session_metrics(traces)


@router.get("/session/{session_id}/traces")
async def get_session_traces(
    session_id: str,
    api_key: str = Depends(verify_api_key),
    store: SessionStore = Depends(get_session_store),
):
    if not is_dev_key(api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debug access denied")
    traces = store.get_session_traces(session_id)
    return {"session_id": session_id, "traces": traces}


@router.get("/session/{session_id}/llm-payload")
async def get_session_llm_payload(
    session_id: str,
    api_key: str = Depends(verify_api_key),
    store: SessionStore = Depends(get_session_store),
):
    if not is_dev_key(api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debug access denied")

    traces = store.get_session_traces(session_id)
    if not traces:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session trace not found")

    trace = traces[-1]
    llm_calls = trace.get("llm_calls") or []
    if not llm_calls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No LLM payload for this session")

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
                "system_prompt": _sanitize_pii(store.get_blob(system_blob_id) or call.get("system_prompt_preview") or ""),
                "user_prompt": _sanitize_pii(store.get_blob(user_blob_id) or call.get("user_prompt_preview") or ""),
                "response_preview": _sanitize_pii(call.get("response_preview") or ""),
                "blob_error": call.get("blob_error"),
            }
        )

    memory_blob_id = trace.get("memory_snapshot_blob_id")
    memory_snapshot = _sanitize_pii(store.get_blob(memory_blob_id) or "") if memory_blob_id else ""

    sd_runtime_disabled = feature_flags.enabled("DISABLE_SD_RUNTIME")
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
    if not sd_runtime_disabled:
        payload["sd_level"] = trace.get("sd_level")
    return payload


def _sanitize_pii(text: str) -> str:
    import re

    text = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w]{2,}\b", "[email]", text)
    text = re.sub(r"\b\+?[\d\s\-()]{10,15}\b", "[phone]", text)
    return text


def _aggregate_session_metrics(traces: list) -> dict:
    total = len(traces)
    fast_path_count = sum(1 for t in traces if t.get("fast_path"))
    sd_levels = [t.get("sd_level", "unknown") for t in traces]
    llm_times = [t.get("total_duration_ms", 0) for t in traces]
    costs = [t.get("estimated_cost_usd", 0) or 0 for t in traces]
    anomaly_counts = [len(t.get("anomalies", [])) for t in traces]

    return {
        "total_turns": total,
        "fast_path_pct": round(fast_path_count / total * 100, 1) if total else 0,
        "sd_distribution": {
            "GREEN": sd_levels.count("GREEN"),
            "YELLOW": sd_levels.count("YELLOW"),
            "RED": sd_levels.count("RED"),
        },
        "avg_llm_time_ms": round(sum(llm_times) / total) if total else 0,
        "max_llm_time_ms": max(llm_times) if llm_times else 0,
        "total_cost_usd": round(sum(costs), 6),
        "turns_with_anomalies": sum(1 for c in anomaly_counts if c > 0),
        "anomaly_turns_indices": [i for i, c in enumerate(anomaly_counts) if c > 0],
    }
