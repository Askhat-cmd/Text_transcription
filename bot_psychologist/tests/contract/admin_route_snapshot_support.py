from __future__ import annotations

from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import patch

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from api.dependencies import get_identity_service
from api.main import app
from api.session_store import get_session_store
from bot_agent.config import config
from bot_agent.multiagent.thread_storage import thread_storage
from bot_agent.runtime_config import RuntimeConfig


ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}
SNAPSHOT_SCHEMA_VERSION = "prd_047_42_apply_admin_routes_snapshot_v1"
_BOT_DB_PATH_RE = re.compile(r"(?i).*[\\/](bot_sessions\.db)$")
_THREAD_DIR_RE = re.compile(r"(?i).*[\\/]threads$")
_DATA_ROOT_RE = re.compile(r"(?i).*[\\/]voice_bot_pipeline[\\/]data$")


def _load_state_module():
    try:
        return importlib.import_module("api.admin_surface_bootstrap")
    except ModuleNotFoundError:
        return importlib.import_module("api.admin_routes")


_STATE_MODULE = _load_state_module()
_ROUTES_MODULE = importlib.import_module("api.admin_routes")
_DEFAULT_AGENT_METRICS = deepcopy(getattr(_STATE_MODULE, "_agent_metrics"))
_DEFAULT_ORCHESTRATOR_MODE = deepcopy(getattr(_STATE_MODULE, "_orchestrator_mode"))


@dataclass(frozen=True)
class RouteCase:
    case_id: str
    method: str
    path: str
    route_pattern: str
    expected_status: int
    request_factory: Callable[[TestClient, "SnapshotContext"], dict[str, Any]]


@dataclass
class SnapshotContext:
    root: Path
    override_path: Path
    thread_dir: Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class _FakeIdentityService:
    async def get_user(self, user_id: str):
        if user_id != "demo_user":
            return None
        return SimpleNamespace(
            id=user_id,
            created_at=datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc),
            status="active",
        )

    async def get_linked_identities(self, user_id: str):
        if user_id != "demo_user":
            return []
        return [
            SimpleNamespace(
                provider="telegram",
                external_id="123456789",
                verified_at=datetime(2026, 7, 9, 12, 5, tzinfo=timezone.utc),
            )
        ]

    async def get_active_sessions(self, user_id: str, limit: int = 50):
        if user_id != "demo_user":
            return []
        return [
            SimpleNamespace(
                session_id="session_demo_001",
                channel="web",
                last_seen_at=datetime(2026, 7, 9, 12, 10, tzinfo=timezone.utc),
            )
        ][:limit]


def _build_threads_payload(ctx: SnapshotContext) -> None:
    ctx.thread_dir.mkdir(parents=True, exist_ok=True)
    active_payload = {
        "thread_id": "thread_demo_active",
        "user_id": "demo_user",
        "phase": "clarify",
        "response_mode": "reflect",
        "core_direction": "clarity",
        "turn_count": 3,
        "created_at": "2026-07-09T12:00:00+00:00",
        "last_updated_at": "2026-07-09T12:10:00+00:00",
        "open_loops": ["loop_a"],
        "closed_loops": ["loop_b"],
    }
    archive_payload = [
        {
            "thread_id": "thread_demo_archive",
            "final_phase": "archive",
            "core_direction": "stability",
            "archived_at": "2026-07-09T12:20:00+00:00",
            "archive_reason": "manual_cleanup",
        }
    ]
    (ctx.thread_dir / "demo_user_active.json").write_text(
        json.dumps(active_payload, ensure_ascii=False),
        encoding="utf-8",
    )
    (ctx.thread_dir / "demo_user_archive.json").write_text(
        json.dumps(archive_payload, ensure_ascii=False),
        encoding="utf-8",
    )


def _seed_agent_trace(client: TestClient) -> None:
    client.post(
        "/api/admin/agents/traces/record",
        headers=ADMIN_HEADERS,
        json={
            "agent_id": "writer",
            "request_id": "req_seed",
            "user_id": "demo_user",
            "input_preview": "input",
            "output_preview": "output",
            "latency_ms": 42,
            "error": False,
        },
    )


def _normalize_payload(payload: Any) -> Any:
    unstable_keys = {
        "timestamp",
        "server_time",
        "created_at",
        "updated_at",
        "last_seen_at",
        "verified_at",
        "archived_at",
        "last_updated_at",
        "last_run",
        "backend_start_time",
    }
    secretish_keys = {"session_id", "backend_pid"}
    if isinstance(payload, dict):
        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            if key in unstable_keys and value is not None:
                normalized[key] = "<normalized-datetime>"
            elif key in secretish_keys and value is not None:
                normalized[key] = f"<normalized-{key}>"
            else:
                normalized[key] = _normalize_payload(value)
        return normalized
    if isinstance(payload, list):
        return [_normalize_payload(item) for item in payload]
    if isinstance(payload, str):
        if _BOT_DB_PATH_RE.match(payload):
            return "<normalized-bot-db-path>"
        if _DATA_ROOT_RE.match(payload):
            return "<normalized-data-root>"
        if _THREAD_DIR_RE.match(payload):
            return "<normalized-thread-dir>"
    return payload


def _response_body(response) -> Any:
    try:
        return _normalize_payload(response.json())
    except Exception:
        return {"text": response.text}


def _router_inventory(router, label: str) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = sorted(method for method in route.methods if method not in {"HEAD", "OPTIONS"})
        inventory.append(
            {
                "router": label,
                "name": route.name,
                "path": route.path,
                "methods": methods,
            }
        )
    return inventory


def _request_with_prefix(
    prefix: str,
    suffix: str,
    *,
    case_id: str,
    method: str,
    route_pattern: str | None = None,
    expected_status: int,
    request_factory: Callable[[TestClient, SnapshotContext], dict[str, Any]],
) -> RouteCase:
    return RouteCase(
        case_id=f"{prefix.strip('/').replace('/', '_')}_{case_id}",
        method=method,
        path=f"{prefix}{suffix}",
        route_pattern=f"{prefix}{route_pattern or suffix}",
        expected_status=expected_status,
        request_factory=request_factory,
    )


def _simple_request(*, json_body: Any = None, params: dict[str, Any] | None = None):
    def _factory(_client: TestClient, _ctx: SnapshotContext) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if json_body is not None:
            payload["json"] = deepcopy(json_body)
        if params:
            payload["params"] = dict(params)
        return payload

    return _factory


def _import_request(prefix: str):
    def _factory(client: TestClient, _ctx: SnapshotContext) -> dict[str, Any]:
        export_payload = client.get(f"{prefix}/export", headers=ADMIN_HEADERS).json()
        return {"json": export_payload}

    return _factory


def _threads_list_request(status_value: str):
    def _factory(_client: TestClient, ctx: SnapshotContext) -> dict[str, Any]:
        _build_threads_payload(ctx)
        return {"params": {"status": status_value, "user_id": "demo_user", "limit": 10}}

    return _factory


def _thread_delete_request(_client: TestClient, ctx: SnapshotContext) -> dict[str, Any]:
    _build_threads_payload(ctx)
    return {}


def _agent_traces_request(_client: TestClient, _ctx: SnapshotContext) -> dict[str, Any]:
    _seed_agent_trace(_client)
    return {"params": {"limit": 5, "agent_id": "writer"}}


def _overview_request(client: TestClient, _ctx: SnapshotContext) -> dict[str, Any]:
    _seed_agent_trace(client)
    return {}


def route_cases() -> list[RouteCase]:
    both_prefixes = ("/api/admin", "/api/v1/admin")
    legacy_only_prefix = "/api/admin"
    cases: list[RouteCase] = []

    def add_both(
        suffix: str,
        *,
        case_id: str,
        method: str,
        route_pattern: str | None = None,
        expected_status: int = 200,
        request_factory: Callable[[TestClient, SnapshotContext], dict[str, Any]] | None = None,
    ) -> None:
        factory = request_factory or _simple_request()
        for prefix in both_prefixes:
            cases.append(
                _request_with_prefix(
                    prefix,
                    suffix,
                    case_id=case_id,
                    method=method,
                    route_pattern=route_pattern,
                    expected_status=expected_status,
                    request_factory=factory,
                )
            )

    def add_legacy(
        suffix: str,
        *,
        case_id: str,
        method: str,
        route_pattern: str | None = None,
        expected_status: int = 200,
        request_factory: Callable[[TestClient, SnapshotContext], dict[str, Any]] | None = None,
    ) -> None:
        factory = request_factory or _simple_request()
        cases.append(
            _request_with_prefix(
                legacy_only_prefix,
                suffix,
                case_id=case_id,
                method=method,
                route_pattern=route_pattern,
                expected_status=expected_status,
                request_factory=factory,
            )
        )

    grouped_config_payload = {
        "routing": {"FREE_CONVERSATION_MODE": True},
        "llm": {"MAX_TOKENS_SOFT_CAP": 4096},
        "runtime": {"DIALOGUE_PROFILE": "mvp_free_dialogue"},
    }
    diagnostic_control_payload = {
        "mode": "allowlist",
        "force_disabled": False,
        "allowlist_user_ids": ["creator", "pilot_001"],
    }
    prompt_payload = {"content": "# Snapshot\nСтабильный admin prompt override для контракта."}
    prompt_stack_payload = {"text": "CORE IDENTITY snapshot payload long enough for route contract."}
    toggle_payload = {"enabled": False}
    metric_payload = {"agent_id": "writer", "latency_ms": 123, "error": False}
    orchestrator_payload = {"pipeline_mode": "full_multiagent"}
    agent_prompt_payload = {"text": "Writer prompt override snapshot payload with more than twenty chars."}
    agent_llm_payload = {"model": "gpt-4o-mini", "temperature": 0.55}

    add_both("/config", case_id="get_config", method="GET")
    add_both("/config/schema", case_id="get_config_schema", method="GET")
    add_both("/config/schema-v104", case_id="get_config_schema_v104", method="GET")
    add_both("/config", case_id="post_config", method="POST", request_factory=_simple_request(json_body=grouped_config_payload))
    add_both("/config", case_id="put_config", method="PUT", request_factory=_simple_request(json_body=grouped_config_payload))
    add_both("/config/MAX_TOKENS_SOFT_CAP", case_id="delete_config_key", method="DELETE", route_pattern="/config/{key}")
    add_both("/config/reset-all", case_id="reset_all_config", method="POST")
    add_both("/status", case_id="status", method="GET")
    add_both("/runtime/effective", case_id="runtime_effective", method="GET", request_factory=_simple_request(params={"session_id": "demo-session"}))
    add_both("/diagnostic-center/effective", case_id="diagnostic_center_effective", method="GET")
    add_both("/diagnostic-center/control", case_id="diagnostic_center_control", method="POST", request_factory=_simple_request(json_body=diagnostic_control_payload))
    add_both("/diagnostic-center/reset", case_id="diagnostic_center_reset", method="POST")
    add_both("/diagnostics/effective", case_id="diagnostics_effective", method="GET", request_factory=_simple_request(params={"session_id": "demo-session"}))
    add_both("/trace/last", case_id="trace_last", method="GET", expected_status=410, request_factory=_simple_request(params={"session_id": "demo-session"}))
    add_both("/trace/recent", case_id="trace_recent", method="GET", expected_status=410, request_factory=_simple_request(params={"session_id": "demo-session", "limit": 3}))
    add_both("/reload-data", case_id="reload_data", method="POST")
    add_both("/prompts", case_id="get_prompts", method="GET")
    add_both("/prompts/stack-v2", case_id="get_prompt_stack_v2", method="GET")
    add_both("/prompts/stack-v2/usage", case_id="get_prompt_stack_v2_usage", method="GET", expected_status=410, request_factory=_simple_request(params={"session_id": "demo-session"}))
    add_both("/prompts/prompt_system_base", case_id="get_prompt", method="GET", route_pattern="/prompts/{name}")
    add_both("/prompts/stack-v2/CORE_IDENTITY", case_id="get_prompt_stack_v2_detail", method="GET", route_pattern="/prompts/stack-v2/{name}")
    add_both("/prompts/prompt_system_base", case_id="set_prompt", method="PUT", route_pattern="/prompts/{name}", request_factory=_simple_request(json_body=prompt_payload))
    add_both("/prompts/stack-v2/CORE_IDENTITY", case_id="set_prompt_stack_v2", method="PUT", route_pattern="/prompts/stack-v2/{name}", request_factory=_simple_request(json_body=prompt_stack_payload))
    add_both("/prompts/prompt_system_base/reset", case_id="reset_prompt_post", method="POST", route_pattern="/prompts/{name}/reset")
    add_both("/prompts/prompt_system_base", case_id="reset_prompt_delete", method="DELETE", route_pattern="/prompts/{name}")
    add_both("/prompts/stack-v2/CORE_IDENTITY/reset", case_id="reset_prompt_stack_v2", method="POST", route_pattern="/prompts/stack-v2/{name}/reset")
    add_legacy("/prompts/reset-all", case_id="reset_all_prompts", method="POST")
    add_legacy("/history", case_id="history", method="GET")
    add_both("/export", case_id="export", method="GET")
    for prefix in both_prefixes:
        cases.append(
            _request_with_prefix(
                prefix,
                "/import",
                case_id="import",
                method="POST",
                expected_status=200,
                request_factory=_import_request(prefix),
            )
        )
    add_legacy("/agents/status", case_id="agents_status", method="GET")
    add_legacy("/agents/writer/toggle", case_id="agents_toggle", method="POST", route_pattern="/agents/{agent_id}/toggle", request_factory=_simple_request(json_body=toggle_payload))
    add_legacy("/agents/metrics/record", case_id="agents_metrics_record", method="POST", request_factory=_simple_request(json_body=metric_payload))
    add_legacy("/orchestrator/config", case_id="orchestrator_get_config", method="GET")
    add_legacy("/orchestrator/config", case_id="orchestrator_patch_config", method="PATCH", request_factory=_simple_request(json_body=orchestrator_payload))
    add_legacy("/agents/traces", case_id="agents_traces", method="GET", request_factory=_agent_traces_request)
    add_legacy("/overview", case_id="overview", method="GET", request_factory=_overview_request)
    add_legacy("/agents/traces/record", case_id="agents_traces_record", method="POST", request_factory=_simple_request(json_body=metric_payload | {"request_id": "req_001", "user_id": "demo_user", "input_preview": "input", "output_preview": "output"}))
    add_legacy("/threads", case_id="threads_active", method="GET", request_factory=_threads_list_request("active"))
    add_legacy("/threads/demo_user", case_id="threads_delete", method="DELETE", route_pattern="/threads/{user_id}", request_factory=_thread_delete_request)
    add_legacy("/agents/writer/prompts", case_id="agent_prompts_get", method="GET", route_pattern="/agents/{agent_id}/prompts")
    add_legacy("/agents/writer/prompts/WRITER_SYSTEM", case_id="agent_prompts_update", method="PUT", route_pattern="/agents/{agent_id}/prompts/{prompt_key}", request_factory=_simple_request(json_body=agent_prompt_payload))
    add_legacy("/agents/writer/prompts/WRITER_SYSTEM/reset", case_id="agent_prompts_reset", method="POST", route_pattern="/agents/{agent_id}/prompts/{prompt_key}/reset")
    add_legacy("/agents/llm-config", case_id="agents_llm_config", method="GET")
    add_legacy("/agents/writer/llm-config", case_id="agent_llm_patch", method="PATCH", route_pattern="/agents/{agent_id}/llm-config", request_factory=_simple_request(json_body=agent_llm_payload))
    add_legacy("/agents/writer/llm-config/reset", case_id="agent_llm_reset", method="POST", route_pattern="/agents/{agent_id}/llm-config/reset")
    add_legacy("/reset-all", case_id="reset_all", method="POST")
    add_both("/users/demo_user/identity", case_id="user_identity", method="GET", route_pattern="/users/{user_id}/identity")

    return cases


@contextmanager
def isolated_admin_client():
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        override_path = root / "admin_overrides.json"
        thread_dir = root / "threads"
        ctx = SnapshotContext(root=root, override_path=override_path, thread_dir=thread_dir)
        store = get_session_store()
        app.dependency_overrides[get_identity_service] = lambda: _FakeIdentityService()
        data_loader = getattr(_STATE_MODULE, "data_loader")
        agent_metrics = getattr(_STATE_MODULE, "_agent_metrics")
        agent_metrics_lock = getattr(_STATE_MODULE, "_agent_metrics_lock")
        agent_traces = getattr(_STATE_MODULE, "_agent_traces")
        agent_prompt_overrides = getattr(_STATE_MODULE, "_agent_prompt_overrides")
        orchestrator_mode = getattr(_STATE_MODULE, "_orchestrator_mode")

        with ExitStack() as stack:
            stack.enter_context(patch.object(RuntimeConfig, "OVERRIDES_PATH", override_path, create=True))
            stack.enter_context(patch.object(RuntimeConfig, "_cache_mtime", 0.0, create=True))
            stack.enter_context(patch.object(RuntimeConfig, "_cache", {}, create=True))
            stack.enter_context(patch.object(config, "OVERRIDES_PATH", override_path, create=True))
            stack.enter_context(patch.object(config, "WARMUP_ON_START", False, create=True))
            stack.enter_context(patch.object(thread_storage, "_dir", thread_dir, create=True))
            stack.enter_context(patch.object(store, "_sessions", {}, create=True))
            stack.enter_context(patch.object(store, "_blobs", {}, create=True))
            stack.enter_context(patch.object(data_loader, "reload", return_value=[]))

            with agent_metrics_lock:
                agent_metrics.clear()
                agent_metrics.update(deepcopy(_DEFAULT_AGENT_METRICS))
                agent_traces.clear()
                agent_prompt_overrides.clear()
                orchestrator_mode.clear()
                orchestrator_mode.update(deepcopy(_DEFAULT_ORCHESTRATOR_MODE))

            try:
                with TestClient(app, base_url="http://localhost") as client:
                    yield client, ctx
            finally:
                app.dependency_overrides.clear()


def execute_route_case(case: RouteCase) -> dict[str, Any]:
    with isolated_admin_client() as (client, ctx):
        payload = case.request_factory(client, ctx)
        response = client.request(
            case.method,
            case.path,
            headers=ADMIN_HEADERS,
            params=payload.get("params"),
            json=payload.get("json"),
        )
        return {
            "case_id": case.case_id,
            "method": case.method,
            "path": case.path,
            "status_code": response.status_code,
            "body": _response_body(response),
        }


def capture_admin_route_snapshot() -> dict[str, Any]:
    responses = [execute_route_case(case) for case in route_cases()]
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "captured_at": _now_iso(),
        "routers": {
            "legacy": _router_inventory(_ROUTES_MODULE.admin_router, "legacy"),
            "v1": _router_inventory(_ROUTES_MODULE.admin_router_v1, "v1"),
        },
        "route_case_count": len(responses),
        "responses": responses,
    }


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    diffs: list[str] = []
    if before.get("routers") != after.get("routers"):
        diffs.append("Router inventory/order changed.")

    before_map = {item["case_id"]: item for item in before.get("responses", [])}
    after_map = {item["case_id"]: item for item in after.get("responses", [])}
    if set(before_map) != set(after_map):
        missing_before = sorted(set(after_map) - set(before_map))
        missing_after = sorted(set(before_map) - set(after_map))
        diffs.append(f"Case id mismatch: missing_before={missing_before}, missing_after={missing_after}")
        return diffs

    for case_id in sorted(before_map):
        if before_map[case_id] != after_map[case_id]:
            diffs.append(
                f"Diff in {case_id}: before={json.dumps(before_map[case_id], ensure_ascii=False, sort_keys=True)} "
                f"after={json.dumps(after_map[case_id], ensure_ascii=False, sort_keys=True)}"
            )
    return diffs
