# bot_agent/answer_adaptive.py
"""Deprecated compatibility shim for adaptive answer entrypoint.

Active runtime is multiagent_adapter.
Legacy cascade was physically removed in PRD-041.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from .multiagent.runtime_adapter import run_multiagent_adaptive_sync

logger = logging.getLogger(__name__)


def _build_multiagent_shim_error_response(
    *,
    query: str,
    user_id: str,
    exc: Exception,
    debug: bool,
    started_at: float,
) -> Dict[str, Any]:
    elapsed = max(0.0, time.perf_counter() - started_at)
    pipeline_error = f"{exc.__class__.__name__}: {exc}"
    base_debug: Dict[str, Any] = {
        "multiagent_enabled": True,
        "runtime_entrypoint": "answer_adaptive_deprecated_shim",
        "legacy_fallback_used": False,
        "legacy_fallback_blocked": True,
        "pipeline_error": pipeline_error,
    }
    if debug:
        base_debug.update({"query": query, "user_id": user_id})
    return {
        "status": "error",
        "answer": "Temporary runtime issue. Please retry in a moment.",
        "state_analysis": {
            "primary_state": "unknown",
            "confidence": 0.0,
            "emotional_tone": "",
            "recommendations": [],
        },
        "path_recommendation": None,
        "feedback_prompt": "",
        "concepts": [],
        "sources": [],
        "conversation_context": "",
        "metadata": {
            "runtime": "multiagent",
            "runtime_entrypoint": "answer_adaptive_deprecated_shim",
            "legacy_fallback_used": False,
            "legacy_fallback_blocked": True,
            "pipeline_error": pipeline_error,
            "runtime_user_scope": user_id,
        },
        "debug": base_debug,
        "processing_time_seconds": elapsed,
    }


def _apply_deprecated_shim_markers(response: Dict[str, Any]) -> Dict[str, Any]:
    metadata = response.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        response["metadata"] = metadata

    metadata["runtime"] = metadata.get("runtime") or "multiagent"
    metadata["runtime_entrypoint"] = "answer_adaptive_deprecated_shim"
    metadata["legacy_fallback_used"] = False
    metadata["legacy_fallback_blocked"] = True

    debug_payload = response.get("debug")
    if not isinstance(debug_payload, dict):
        debug_payload = {}
        response["debug"] = debug_payload

    debug_payload["multiagent_enabled"] = True
    debug_payload["runtime_entrypoint"] = "answer_adaptive_deprecated_shim"
    debug_payload["legacy_fallback_used"] = False
    debug_payload["legacy_fallback_blocked"] = True
    return response


def answer_question_adaptive(
    query: str,
    user_id: str = "default",
    user_level: str = "beginner",
    include_path_recommendation: bool = False,
    include_feedback_prompt: bool = True,
    top_k: Optional[int] = None,
    debug: bool = False,
    session_store=None,
    schedule_summary_task: bool = True,
) -> Dict[str, Any]:
    """Deprecated compatibility shim.

    Runtime calls must stay on multiagent adapter only.
    """
    _ = (user_level, top_k, schedule_summary_task)
    logger.warning("[ADAPTIVE] deprecated shim used; routing to multiagent adapter")
    started_at = time.perf_counter()
    try:
        response = run_multiagent_adaptive_sync(
            query=query,
            user_id=user_id,
            debug=debug,
            session_store=session_store,
            include_path_recommendation=include_path_recommendation,
            include_feedback_prompt=include_feedback_prompt,
        )
    except Exception as exc:
        logger.error("[ADAPTIVE] multiagent adapter failed inside deprecated shim: %s", exc, exc_info=True)
        return _build_multiagent_shim_error_response(
            query=query,
            user_id=user_id,
            exc=exc,
            debug=debug,
            started_at=started_at,
        )

    if not isinstance(response, dict):
        return _build_multiagent_shim_error_response(
            query=query,
            user_id=user_id,
            exc=TypeError("multiagent adapter returned non-dict payload"),
            debug=debug,
            started_at=started_at,
        )

    return _apply_deprecated_shim_markers(response)
