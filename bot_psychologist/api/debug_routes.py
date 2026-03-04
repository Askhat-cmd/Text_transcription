from fastapi import APIRouter, Depends, HTTPException, status

from .auth import verify_api_key, is_dev_key
from .session_store import SessionStore, get_session_store

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
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
