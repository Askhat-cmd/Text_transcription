from __future__ import annotations

from .admin_surface_bootstrap import *  # noqa: F401,F403

def _filter_operational_flags(snapshot: dict[str, bool]) -> dict[str, bool]:
    return {
        key: value
        for key, value in (snapshot or {}).items()
        if not key.startswith("DISABLE_SD_")
    }


def _status_snapshot() -> dict[str, Any]:
    stats = data_loader.get_stats()
    flags_snapshot = _filter_operational_flags(feature_flags.snapshot())
    return {
        "degraded_mode": bool(stats.get("degraded_mode", False)),
        "data_source": stats.get("data_source", "unknown"),
        "blocks_loaded": int(stats.get("total_blocks", 0)),
        "version": "0.7.0",
        "feature_flags": flags_snapshot,
    }


def _prompt_stack_v2_sections_baseline() -> dict[str, str]:
    build = prompt_registry_v2.build(
        query="baseline",
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route="inform",
        mode="CLARIFICATION",
        diagnostics={
            "interaction_mode": "informational",
            "nervous_system_state": "window",
            "request_function": "understand",
            "core_theme": "baseline",
        },
    )
    return dict(build.sections)


def _prompt_history_metadata(prompt_name: str | None) -> dict[str, Any]:
    if not prompt_name:
        return {"version": "v2.0.0", "updated_at": None}
    history = list(config.get_history() or [])
    related = [entry for entry in history if entry.get("key") == prompt_name and str(entry.get("type", "")).startswith("prompt")]
    if not related:
        return {"version": "v2.0.0", "updated_at": None}
    latest = related[-1]
    return {
        "version": f"v2.0.{len(related)}",
        "updated_at": latest.get("timestamp"),
    }


def _build_prompt_stack_v2_meta() -> list[dict[str, Any]]:
    baseline_sections = _prompt_stack_v2_sections_baseline()
    result: list[dict[str, Any]] = []
    for section in PROMPT_STACK_ORDER:
        editable_prompt_name = PROMPT_STACK_V2_EDITABLE_MAP.get(section)
        editable = editable_prompt_name is not None
        if editable:
            prompt_payload = config.get_prompt(editable_prompt_name)
            active_text = prompt_payload.get("text", "")
            is_overridden = bool(prompt_payload.get("is_overridden", False))
        else:
            active_text = baseline_sections.get(section, "")
            is_overridden = False
        history_meta = _prompt_history_metadata(editable_prompt_name)
        result.append(
            {
                "name": section,
                "label": section,
                "preview": str(active_text).replace("\n", " ")[:150],
                "is_overridden": is_overridden,
                "char_count": len(str(active_text)),
                "editable": editable,
                "is_legacy": False,
                "source": "config_prompt" if editable else "runtime_derived",
                "stack_version": PROMPT_STACK_VERSION,
                "variants": list(PROMPT_STACK_V2_VARIANTS),
                "version": history_meta["version"],
                "updated_at": history_meta["updated_at"],
                "legacy_prompt_name": editable_prompt_name,
                "derived_from": editable_prompt_name if editable else "prompt_registry_v2",
                "read_only_reason": None if editable else "runtime_derived_section_not_editable_via_admin",
                "usage_markers": {"used_in_last_turn": False},
            }
        )
    return result


def _build_prompt_stack_v2_detail(section_name: str) -> dict[str, Any]:
    sections = _prompt_stack_v2_sections_baseline()
    if section_name not in PROMPT_STACK_ORDER:
        raise HTTPException(status_code=404, detail=f"Unknown prompt stack section: {section_name}")

    editable_prompt_name = PROMPT_STACK_V2_EDITABLE_MAP.get(section_name)
    editable = editable_prompt_name is not None
    if editable:
        base = config.get_prompt(editable_prompt_name)
        text = str(base.get("text", ""))
        default_text = str(base.get("default_text", ""))
        is_overridden = bool(base.get("is_overridden", False))
    else:
        text = str(sections.get(section_name, ""))
        default_text = text
        is_overridden = False

    history_meta = _prompt_history_metadata(editable_prompt_name)
    return {
        "name": section_name,
        "label": section_name,
        "preview": text.replace("\n", " ")[:150],
        "is_overridden": is_overridden,
        "char_count": len(text),
        "text": text,
        "default_text": default_text,
        "editable": editable,
        "is_legacy": False,
        "source": "config_prompt" if editable else "runtime_derived",
        "stack_version": PROMPT_STACK_VERSION,
        "variants": list(PROMPT_STACK_V2_VARIANTS),
        "version": history_meta["version"],
        "updated_at": history_meta["updated_at"],
        "legacy_prompt_name": editable_prompt_name,
        "derived_from": editable_prompt_name if editable else "prompt_registry_v2",
        "read_only_reason": None if editable else "runtime_derived_section_not_editable_via_admin",
        "usage_markers": {"used_in_last_turn": False},
    }


def _group_feature_flags(snapshot: dict[str, bool]) -> dict[str, dict[str, bool]]:
    groups = {
        "neo_runtime": (
            "NEO_MINDBOT_ENABLED",
            "LEGACY_PIPELINE_ENABLED",
            "DISABLE_USER_LEVEL_ADAPTER",
        ),
        "pipeline": (
            "USE_NEW_DIAGNOSTICS_V1",
            "USE_DETERMINISTIC_ROUTE_RESOLVER",
            "USE_PROMPT_STACK_V2",
            "USE_OUTPUT_VALIDATION",
            "INFORMATIONAL_BRANCH_ENABLED",
        ),
        "quality": (
            "ENABLE_CONDITIONAL_RERANKER",
            "ENABLE_EMBEDDING_PROVIDER",
        ),
    }
    return {
        group: {flag: snapshot.get(flag, False) for flag in flags}
        for group, flags in groups.items()
    }


def _compute_agent_metrics() -> list[dict[str, Any]]:
    runtime_metrics = getattr(orchestrator, "_agent_metrics", None)
    source: dict[str, dict[str, Any]]
    if isinstance(runtime_metrics, dict) and runtime_metrics:
        source = runtime_metrics
    else:
        source = _agent_metrics

    result = []
    for agent_id in sorted(source.keys()):
        metric = source.get(agent_id, {})
        call_count = int(metric.get("call_count", 0))
        total_ms = int(metric.get("total_ms", 0))
        error_count = int(metric.get("error_count", 0))
        avg_ms = round(total_ms / call_count, 1) if call_count > 0 else 0
        result.append(
            {
                "id": agent_id,
                "enabled": bool(metric.get("enabled", True)),
                "call_count": call_count,
                "avg_latency_ms": avg_ms,
                "error_count": error_count,
                "error_rate": round(error_count / call_count, 4) if call_count > 0 else 0.0,
                "last_run": metric.get("last_run"),
            }
        )
    return result


def _get_thread_storage_dir() -> Path:
    storage_dir = getattr(thread_storage, "_dir", None)
    if storage_dir is not None:
        return Path(storage_dir).expanduser().resolve()
    return (Path(__file__).resolve().parent.parent / "data" / "threads").resolve()


def _list_active_threads() -> list[dict[str, Any]]:
    storage_dir = _get_thread_storage_dir()
    if not storage_dir.exists():
        return []
    threads: list[dict[str, Any]] = []
    for file_path in sorted(storage_dir.glob("*_active.json")):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            threads.append(
                {
                    "thread_id": str(payload.get("thread_id", "")),
                    "user_id": str(payload.get("user_id", "")),
                    "phase": str(payload.get("phase", "unknown")),
                    "response_mode": str(payload.get("response_mode", "unknown")),
                    "core_direction": str(payload.get("core_direction", "")),
                    "turn_count": int(payload.get("turn_count", 0) or 0),
                    "created_at": str(payload.get("created_at", "")),
                    "last_updated_at": str(payload.get("last_updated_at", "")),
                    "status": "active",
                    "open_loops_count": len(payload.get("open_loops", []) or []),
                    "closed_loops_count": len(payload.get("closed_loops", []) or []),
                }
            )
        except Exception:
            continue
    return threads


def _list_archived_threads() -> list[dict[str, Any]]:
    storage_dir = _get_thread_storage_dir()
    if not storage_dir.exists():
        return []
    threads: list[dict[str, Any]] = []
    for file_path in sorted(storage_dir.glob("*_archive.json")):
        user_id = file_path.stem.replace("_archive", "")
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            for item in payload if isinstance(payload, list) else []:
                threads.append(
                    {
                        "thread_id": str(item.get("thread_id", "")),
                        "user_id": user_id,
                        "final_phase": str(item.get("final_phase", "")),
                        "core_direction": str(item.get("core_direction", "")),
                        "archived_at": str(item.get("archived_at", "")),
                        "archive_reason": str(item.get("archive_reason", "")),
                        "status": "archived",
                    }
                )
        except Exception:
            continue
    return threads


def _get_agent_prompts_raw(agent_id: str) -> dict[str, str]:
    module_path = _AGENT_PROMPT_MAP.get(agent_id)
    if not module_path:
        raise HTTPException(status_code=404, detail=f"No prompts module for agent: {agent_id}")
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"Cannot load agent prompts: {exc}") from exc
    result: dict[str, str] = {}
    for attr in dir(module):
        if attr.startswith("_"):
            continue
        value = getattr(module, attr, None)
        if isinstance(value, str) and len(value) > 20:
            result[attr] = value
    return result


def _group_param_value(group_name: str, key: str, default: Any = None) -> Any:
    all_groups = config.get_all_config().get("groups", {})
    group = all_groups.get(group_name, {})
    params = group.get("params", {})
    if key not in params:
        return default
    return params[key].get("value", default)


def _load_prd_047_2_quality_calibration_status() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    artifact_path = repo_root / "TO_DO_LIST" / "logs" / "PRD-047.2" / "kernel_quality_direct.json"
    if not artifact_path.exists():
        return {
            "last_prd": "PRD-047.2",
            "last_direct_passed": False,
            "last_direct_cases_total": 0,
            "last_direct_cases_failed": 0,
            "artifact_found": False,
        }
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        summary = dict(payload.get("summary", {}))
        total = int(summary.get("cases_total", 0) or 0)
        failed = int(summary.get("cases_failed", 0) or 0)
        return {
            "last_prd": "PRD-047.2",
            "last_direct_passed": total > 0 and failed == 0,
            "last_direct_cases_total": total,
            "last_direct_cases_failed": failed,
            "artifact_found": True,
        }
    except Exception:
        return {
            "last_prd": "PRD-047.2",
            "last_direct_passed": False,
            "last_direct_cases_total": 0,
            "last_direct_cases_failed": 0,
            "artifact_found": False,
        }


def _load_prd_047_3_active_line_calibration_status() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    artifact_path = repo_root / "TO_DO_LIST" / "logs" / "PRD-047.3" / "active_line_direct.json"
    if not artifact_path.exists():
        return {
            "last_prd": "PRD-047.3",
            "last_direct_passed": False,
            "last_direct_cases_total": 0,
            "last_direct_cases_failed": 0,
            "artifact_found": False,
        }
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        summary = dict(payload.get("summary", {}))
        total = int(summary.get("cases_total", 0) or 0)
        failed = int(summary.get("cases_failed", 0) or 0)
        return {
            "last_prd": "PRD-047.3",
            "last_direct_passed": total > 0 and failed == 0,
            "last_direct_cases_total": total,
            "last_direct_cases_failed": failed,
            "artifact_found": True,
        }
    except Exception:
        return {
            "last_prd": "PRD-047.3",
            "last_direct_passed": False,
            "last_direct_cases_total": 0,
            "last_direct_cases_failed": 0,
            "artifact_found": False,
        }


def _load_prd_047_4_response_planner_calibration_status() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    artifact_path = repo_root / "TO_DO_LIST" / "logs" / "PRD-047.4" / "response_planner_direct.json"
    if not artifact_path.exists():
        return {
            "last_prd": "PRD-047.4",
            "last_direct_passed": False,
            "last_direct_cases_total": 0,
            "last_direct_cases_failed": 0,
            "artifact_found": False,
        }
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        summary = dict(payload.get("summary", {}))
        total = int(summary.get("cases_total", 0) or 0)
        failed = int(summary.get("cases_failed", 0) or 0)
        return {
            "last_prd": "PRD-047.4",
            "last_direct_passed": total > 0 and failed == 0,
            "last_direct_cases_total": total,
            "last_direct_cases_failed": failed,
            "artifact_found": True,
        }
    except Exception:
        return {
            "last_prd": "PRD-047.4",
            "last_direct_passed": False,
            "last_direct_cases_total": 0,
            "last_direct_cases_failed": 0,
            "artifact_found": False,
        }


def _load_prd_047_6_planner_drift_replay_status() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    logs_dir = repo_root / "TO_DO_LIST" / "logs" / "PRD-047.6"
    direct_path = logs_dir / "planner_drift_direct.json"
    live_path = logs_dir / "planner_drift_live.json"

    def _extract_status(path: Path) -> str:
        if not path.exists():
            return "missing"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            summary = dict(payload.get("summary", {}))
            failed = int(summary.get("cases_failed", 1) or 1)
            return "passed" if failed == 0 else "failed"
        except Exception:
            return "invalid"

    return {
        "prd": "PRD-047.6",
        "direct": _extract_status(direct_path),
        "live": _extract_status(live_path),
    }


def _load_prd_047_7_guided_live_testing_status() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    scenarios_path = (
        repo_root
        / "bot_psychologist"
        / "tests"
        / "evaluation"
        / "prd_047_7_guided_live_scenarios.json"
    )
    sample_summary_path = (
        repo_root
        / "TO_DO_LIST"
        / "live_feedback"
        / "PRD-047.7"
        / "reports"
        / "sample_session_summary.json"
    )

    scenario_count = 0
    if scenarios_path.exists():
        try:
            payload = json.loads(scenarios_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                scenario_count = len([item for item in payload if isinstance(item, dict)])
        except Exception:
            scenario_count = 0

    return {
        "schema_version": "live_feedback_v1",
        "enabled": True,
        "mode": "developer_local",
        "feedback_storage": "file_sanitized",
        "raw_dialogue_saved_by_default": False,
        "scenario_set": "prd_047_7_guided_live_scenarios",
        "scenario_count": scenario_count,
        "last_session_summary_available": sample_summary_path.exists(),
    }

__all__ = [name for name in globals() if not name.startswith("__")]
