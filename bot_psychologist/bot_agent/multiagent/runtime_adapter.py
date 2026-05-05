"""Multiagent runtime adapter for API/transport cutover."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Dict

from .orchestrator import orchestrator


def _run_orchestrator_from_sync(*, query: str, user_id: str) -> Dict[str, Any]:
    """Run async orchestrator from sync context, including active event loop cases."""
    try:
        asyncio.get_running_loop()
        loop_is_running = True
    except RuntimeError:
        loop_is_running = False

    if not loop_is_running:
        return orchestrator.run_sync(query=query, user_id=user_id)

    result_holder: Dict[str, Any] = {}
    error_holder: Dict[str, Exception] = {}

    def _runner() -> None:
        try:
            result_holder["result"] = orchestrator.run_sync(query=query, user_id=user_id)
        except Exception as exc:  # pragma: no cover - defensive thread bridge
            error_holder["error"] = exc

    thread = threading.Thread(target=_runner, name="multiagent-runtime-adapter", daemon=True)
    thread.start()
    thread.join()

    if "error" in error_holder:
        raise error_holder["error"]

    result = result_holder.get("result")
    if isinstance(result, dict):
        return result
    return {}


def normalize_multiagent_result(
    *,
    result: dict,
    query: str,
    user_id: str,
    debug: bool,
    started_at: float,
    include_feedback_prompt: bool = True,
) -> dict:
    """Normalize raw orchestrator payload into current API-compatible adaptive schema."""
    debug_payload = result.get("debug") if isinstance(result.get("debug"), dict) else {}
    debug_payload = dict(debug_payload)
    debug_payload.setdefault("multiagent_enabled", True)
    debug_payload.setdefault("pipeline_version", "multiagent_v1")

    confidence_raw = debug_payload.get("confidence")
    try:
        confidence = float(confidence_raw) if confidence_raw is not None else 0.0
    except (TypeError, ValueError):
        confidence = 0.0

    total_seconds = max(time.perf_counter() - started_at, 0.0)

    normalized = {
        "status": result.get("status", "ok"),
        "answer": str(result.get("answer", "") or ""),
        "state_analysis": {
            "primary_state": str(debug_payload.get("nervous_state", "unknown") or "unknown"),
            "confidence": confidence,
            "emotional_tone": "",
            "recommendations": [],
        },
        "path_recommendation": None,
        "feedback_prompt": "" if include_feedback_prompt else "",
        "concepts": [],
        "sources": [],
        "conversation_context": str(debug_payload.get("conversation_context", "") or ""),
        "metadata": {
            "runtime": "multiagent",
            "pipeline_version": str(debug_payload.get("pipeline_version", "multiagent_v1")),
            "thread_id": result.get("thread_id"),
            "phase": result.get("phase"),
            "response_mode": result.get("response_mode"),
            "relation_to_thread": result.get("relation_to_thread"),
            "continuity_score": result.get("continuity_score"),
            "recommended_mode": result.get("response_mode"),
            "confidence_score": debug_payload.get("confidence"),
            "tokens_prompt": debug_payload.get("tokens_prompt"),
            "tokens_completion": debug_payload.get("tokens_completion"),
            "tokens_total": debug_payload.get("tokens_total"),
            "estimated_cost_usd": debug_payload.get("estimated_cost_usd"),
            "model_used": debug_payload.get("model_used"),
            "writer_api_mode": debug_payload.get("writer_api_mode"),
            "state_analyzer_api_mode": debug_payload.get("state_analyzer_api_mode"),
            "runtime_user_scope": user_id,
            "query_length": len(query or ""),
        },
        "debug": debug_payload if debug else debug_payload,
        "processing_time_seconds": float(total_seconds),
    }
    return normalized


async def run_multiagent_adaptive_async(
    *,
    query: str,
    user_id: str,
    debug: bool = False,
    session_store: Any | None = None,
    include_path_recommendation: bool = False,
    include_feedback_prompt: bool = True,
) -> Dict[str, Any]:
    _ = (session_store, include_path_recommendation)
    started_at = time.perf_counter()
    raw_result = await orchestrator.run(query=query, user_id=user_id)
    return normalize_multiagent_result(
        result=raw_result,
        query=query,
        user_id=user_id,
        debug=debug,
        started_at=started_at,
        include_feedback_prompt=include_feedback_prompt,
    )


def run_multiagent_adaptive_sync(
    *,
    query: str,
    user_id: str,
    debug: bool = False,
    session_store: Any | None = None,
    include_path_recommendation: bool = False,
    include_feedback_prompt: bool = True,
) -> Dict[str, Any]:
    _ = (session_store, include_path_recommendation)
    started_at = time.perf_counter()
    raw_result = _run_orchestrator_from_sync(query=query, user_id=user_id)
    return normalize_multiagent_result(
        result=raw_result,
        query=query,
        user_id=user_id,
        debug=debug,
        started_at=started_at,
        include_feedback_prompt=include_feedback_prompt,
    )
