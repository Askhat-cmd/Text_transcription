from __future__ import annotations

from .admin_surface_bootstrap import *  # noqa: F401,F403
from .admin_runtime_compat import *  # noqa: F401,F403
from .admin_surface_helpers import *  # noqa: F401,F403

@admin_router.get(
    "/agents/status",
    summary="Статус агентов мультиагентного пайплайна",
)
async def admin_agents_status():
    pipeline_version = getattr(orchestrator, "pipeline_version", "multiagent_v1")
    compatibility_payload = _compatibility_runtime_payload()
    return {
        "pipeline_version": pipeline_version,
        "active_runtime": _compute_active_runtime(),
        "runtime_entrypoint": _runtime_entrypoint(),
        "pipeline_mode": compatibility_payload["pipeline_mode"],
        "pipeline_mode_read_only": compatibility_payload["pipeline_mode_read_only"],
        "legacy": _legacy_status_payload(),
        "agent_contract": _runtime_agents_contract_payload(),
        "agents": _compute_agent_metrics(),
    }


@admin_router.post(
    "/agents/{agent_id}/toggle",
    summary="Включить/выключить агента",
)
async def admin_agents_toggle(agent_id: str, body: dict):
    if agent_id not in _agent_metrics:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}. Valid: {sorted(_agent_metrics)}")
    with _agent_metrics_lock:
        _agent_metrics[agent_id]["enabled"] = bool(body.get("enabled", True))
        enabled = bool(_agent_metrics[agent_id]["enabled"])
    return {"agent_id": agent_id, "enabled": enabled, "status": "ok"}


@admin_router.post(
    "/agents/metrics/record",
    summary="Записать метрику прогона агента (internal)",
)
async def admin_agents_record_metric(body: dict):
    agent_id = str(body.get("agent_id", ""))
    if agent_id not in _agent_metrics:
        raise HTTPException(status_code=404, detail=f"Unknown agent_id: {agent_id}")
    with _agent_metrics_lock:
        metric = _agent_metrics[agent_id]
        metric["call_count"] += 1
        metric["total_ms"] += int(body.get("latency_ms", 0) or 0)
        if bool(body.get("error", False)):
            metric["error_count"] += 1
        metric["last_run"] = datetime.utcnow().isoformat() + "Z"
    return {"status": "ok"}


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# MULTIAGENT: ORCHESTRATOR CONFIG
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

@admin_router.get(
    "/orchestrator/config",
    summary="Конфигурация оркестратора",
)
async def admin_orchestrator_get_config():
    runtime_metrics = getattr(orchestrator, "_agent_metrics", None)
    source = runtime_metrics if isinstance(runtime_metrics, dict) and runtime_metrics else _agent_metrics
    with _agent_metrics_lock:
        agents_enabled = {agent_id: bool(metric.get("enabled", True)) for agent_id, metric in source.items()}
    env_flags = _env_flags_snapshot()
    runtime_warnings = _deprecated_runtime_warnings(env_flags)
    for warning in runtime_warnings:
        logger.warning("[PRD-040] %s", warning)
    compatibility_payload = _compatibility_runtime_payload()
    actual_mode = compatibility_payload["pipeline_mode"]
    return {
        "pipeline_mode": compatibility_payload["pipeline_mode"],
        "actual_pipeline_mode": actual_mode,
        "active_runtime": _compute_active_runtime(actual_mode),
        "runtime_entrypoint": _runtime_entrypoint(),
        "legacy": _legacy_status_payload(),
        "compatibility": compatibility_payload,
        "env_flags": env_flags,
        "runtime_warnings": runtime_warnings,
        "agents_enabled": agents_enabled,
        "pipeline_version": getattr(orchestrator, "pipeline_version", "multiagent_v1"),
    }


@admin_router.patch(
    "/orchestrator/config",
    summary="Изменить режим пайплайна",
)
async def admin_orchestrator_patch_config(body: dict):
    mode = str(body.get("pipeline_mode", ""))
    normalized_mode = mode.strip().lower()
    if normalized_mode in {"legacy_adaptive", "hybrid", "classic", "cascade"}:
        raise HTTPException(
            status_code=422,
            detail="Legacy runtime modes are disabled after PRD-036. Active runtime is multiagent.",
        )
    if normalized_mode not in {"multiagent_only", "full_multiagent"}:
        raise HTTPException(
            status_code=422,
            detail="Invalid pipeline_mode. Valid modes: ['multiagent_only', 'full_multiagent']",
        )
    _orchestrator_mode["pipeline_mode"] = "multiagent_only"
    compatibility_payload = _compatibility_runtime_payload()
    return {
        "pipeline_mode": compatibility_payload["pipeline_mode"],
        "pipeline_mode_alias_received": mode,
        "pipeline_mode_read_only": compatibility_payload["pipeline_mode_read_only"],
        "legacy_modes_selectable": compatibility_payload["legacy_modes_selectable"],
        "status": "ok",
    }


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# MULTIAGENT: AGENT TRACES
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

@admin_router.get(
    "/agents/traces",
    summary="Трассировки агентов по последним запросам",
)
async def admin_agents_traces(
    limit: int = Query(default=50, ge=1, le=200),
    agent_id: str | None = Query(default=None),
):
    runtime_traces = getattr(orchestrator, "_agent_traces", None)
    if isinstance(runtime_traces, list) and runtime_traces:
        traces = list(runtime_traces)
    else:
        with _agent_metrics_lock:
            traces = list(_agent_traces)
    if agent_id:
        traces = [trace for trace in traces if trace.get("agent_id") == agent_id]
    return {"traces": traces[-limit:][::-1], "total": len(traces)}


@admin_router.get(
    "/overview",
    summary="Обзор состояния multiagent runtime",
)
async def admin_overview():
    env_flags = _env_flags_snapshot()
    runtime_warnings = _deprecated_runtime_warnings(env_flags)
    compatibility_payload = _compatibility_runtime_payload()
    pipeline_mode = compatibility_payload["pipeline_mode"]
    agents = _compute_agent_metrics()
    traces = getattr(orchestrator, "_agent_traces", None)
    if isinstance(traces, list):
        recent_traces = traces[-5:][::-1]
    else:
        recent_traces = list(_agent_traces)[-5:][::-1]
    return {
        "pipeline_mode": pipeline_mode,
        "active_runtime": _compute_active_runtime(pipeline_mode),
        "runtime_entrypoint": _runtime_entrypoint(),
        "legacy": _legacy_status_payload(),
        "compatibility": compatibility_payload,
        "agent_contract": _runtime_agents_contract_payload(),
        "feature_flags": env_flags,
        "deprecated_runtime_flags": feature_flags.deprecated_runtime_flags(),
        "runtime_warnings": runtime_warnings,
        "agents": [
            {
                "agent_id": item.get("id"),
                "enabled": item.get("enabled", True),
                "calls": item.get("call_count", 0),
                "errors": item.get("error_count", 0),
                "avg_ms": item.get("avg_latency_ms", 0),
                "last_run": item.get("last_run"),
            }
            for item in agents
        ],
        "recent_traces": recent_traces,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "schema_version": ADMIN_SCHEMA_VERSION,
    }


@admin_router.post(
    "/agents/traces/record",
    summary="Записать трассировку агента (internal)",
)
async def admin_agents_traces_record(body: dict):
    trace = {
        "agent_id": str(body.get("agent_id", "unknown")),
        "request_id": str(body.get("request_id", "")),
        "user_id": str(body.get("user_id", "")),
        "input_preview": str(body.get("input_preview", ""))[:300],
        "output_preview": str(body.get("output_preview", ""))[:300],
        "latency_ms": int(body.get("latency_ms", 0) or 0),
        "error": body.get("error"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with _agent_metrics_lock:
        _agent_traces.append(trace)
    return {"status": "ok"}
