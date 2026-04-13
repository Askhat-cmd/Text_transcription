"""Low-risk utility helpers extracted from answer_adaptive orchestration."""

from __future__ import annotations

import asyncio
import concurrent.futures
import time
import uuid
from typing import Dict, List, Optional

from ..feature_flags import feature_flags


def _timed(name: str, label: str, fn, *args, **kwargs):
    """Wrapper to measure pipeline stage time."""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    ms = int((time.perf_counter() - t0) * 1000)
    return result, {"name": name, "label": label, "duration_ms": ms, "skipped": False}


def _build_config_snapshot(cfg) -> Dict[str, object]:
    """Build compact config snapshot for trace/debug card."""
    conditional_reranker = feature_flags.enabled("ENABLE_CONDITIONAL_RERANKER")
    snapshot: Dict[str, object] = {
        "conversation_history_depth": int(getattr(cfg, "CONVERSATION_HISTORY_DEPTH", 0) or 0),
        "max_context_size": int(getattr(cfg, "MAX_CONTEXT_SIZE", 0) or 0),
        "semantic_search_top_k": int(getattr(cfg, "SEMANTIC_SEARCH_TOP_K", 0) or 0),
        "fast_path_enabled": True,
        "rerank_enabled": bool(
            getattr(cfg, "VOYAGE_ENABLED", False)
            or (conditional_reranker and getattr(cfg, "RERANKER_ENABLED", False))
        ),
        "model_name": str(getattr(cfg, "LLM_MODEL", "")),
    }
    return snapshot


def _compute_anomalies(trace: Dict) -> List[Dict]:
    """
    Business anomaly logic for trace surface.
    Frontend should consume this output and not duplicate the logic.
    """
    flags: List[Dict] = []
    config_snapshot = trace.get("config_snapshot") or {}
    if trace.get("pipeline_error"):
        flags.append(
            {
                "code": "PIPELINE_EXCEPTION",
                "severity": "error",
                "message": "Pipeline завершился с ошибкой — см. Error View",
                "target": "error",
            }
        )

    if trace.get("blocks_after_cap") == 0 and not trace.get("fast_path"):
        flags.append(
            {
                "code": "NO_BLOCKS_TO_LLM",
                "severity": "error",
                "message": "LLM получил 0 блоков — ответ без контекста",
                "target": "chunks",
            }
        )

    if (trace.get("semantic_hits") == 0) and (trace.get("memory_turns") or 0) >= 3:
        flags.append(
            {
                "code": "SEMANTIC_NOT_TRIGGERED",
                "severity": "info",
                "message": "Семантический поиск вернул 0 результатов при памяти >= 3 turns",
                "target": "memory",
            }
        )

    if trace.get("fast_path"):
        query_len = len((trace.get("hybrid_query_preview") or "").split())
        if query_len > 15:
            flags.append(
                {
                    "code": "UNEXPECTED_FAST_PATH",
                    "severity": "warn",
                    "message": f"Fast path при длинном запросе ({query_len} слов) — проверь логику",
                    "target": "routing",
                }
            )

    pipeline_stages = trace.get("pipeline_stages") or []
    if pipeline_stages:
        total_ms = sum(int(stage.get("duration_ms") or 0) for stage in pipeline_stages) or 1
        for stage in pipeline_stages:
            duration_ms = int(stage.get("duration_ms") or 0)
            if duration_ms > total_ms * 0.5:
                flags.append(
                    {
                        "code": "SLOW_STAGE",
                        "severity": "warn",
                        "message": (
                            f"Этап '{stage.get('label')}' занял {duration_ms}ms "
                            f"({duration_ms / total_ms * 100:.0f}% общего времени)"
                        ),
                        "target": "timeline",
                    }
                )

    hybrid_preview = trace.get("hybrid_query_preview") or ""
    max_context_size = int(config_snapshot.get("max_context_size") or 0)
    if hybrid_preview and max_context_size and len(hybrid_preview) > max_context_size * 0.9:
        flags.append(
            {
                "code": "CONTEXT_BLOAT_RISK",
                "severity": "warn",
                "message": "Hybrid query близок к лимиту MAX_CONTEXT_SIZE",
                "target": "chunks",
            }
        )

    if (trace.get("memory_turns") == 0) and (trace.get("turn_number") or 0) > 3:
        flags.append(
            {
                "code": "EMPTY_MEMORY",
                "severity": "info",
                "message": "Память пуста после нескольких ходов — проверь storage",
                "target": "memory",
            }
        )

    return flags


def _build_state_trajectory(memory, depth: int = 10) -> List[Dict]:
    """Build compact state trajectory from memory.turns."""
    result: List[Dict] = []
    turns = memory.turns[-depth:] if hasattr(memory, "turns") else []
    for i, turn in enumerate(turns, start=1):
        state = getattr(turn, "user_state", None) or getattr(turn, "state", None)
        if state:
            result.append(
                {
                    "turn": i,
                    "state": str(state),
                    "confidence": getattr(turn, "state_confidence", None),
                }
            )
    return result


def _store_blob(session_store, session_id: str, content: str) -> Optional[str]:
    """Save heavy trace text and return blob_id."""
    if not session_store or not session_id or not content:
        return None
    blob_id = f"{session_id}:{uuid.uuid4().hex[:8]}"
    session_store.set_blob(blob_id, content, ttl_seconds=1800)
    return blob_id


def _run_coroutine_sync(coro):
    """
    Run coroutine from sync context.
    If an event loop is already running, run in a separate thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()
