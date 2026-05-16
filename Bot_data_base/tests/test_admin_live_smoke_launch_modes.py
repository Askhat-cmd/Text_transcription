from __future__ import annotations

from pathlib import Path

from review.admin_live_smoke import run_admin_live_smoke


class _FakeProcess:
    def __init__(self) -> None:
        self._running = True

    def poll(self) -> int | None:
        return None if self._running else 0

    def terminate(self) -> None:
        self._running = False

    def wait(self, timeout: float | None = None) -> int:
        self._running = False
        return 0

    def kill(self) -> None:
        self._running = False


def _online_fetch(_: str) -> dict:
    return {"ok": True, "status_code": 200, "body": {"ok": True, "blocks": {"production_total": 247}, "chroma": {"count": 247}}, "error": None}


def _online_contract_fetch(url: str) -> dict:
    if url.endswith("/api/status"):
        return {"ok": True, "status_code": 200, "body": {"ok": True}, "error": None}
    if url.endswith("/api/registry") or url.endswith("/api/registry/"):
        return {
            "ok": True,
            "status_code": 200,
            "body": {"sources": [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 247}]},
            "error": None,
        }
    if url.endswith("/api/dashboard") or url.endswith("/api/dashboard/"):
        return {
            "ok": True,
            "status_code": 200,
            "body": {"blocks": {"production_total": 247}, "chroma": {"count": 247}},
            "error": None,
        }
    return {"ok": False, "status_code": None, "body": None, "error": "unknown"}


def _offline_fetch(_: str) -> dict:
    return {"ok": False, "status_code": None, "body": None, "error": "connection refused"}


def test_existing_server_alive_mode_external_existing(tmp_path: Path) -> None:
    process_factory_called = {"value": False}

    def _process_factory(command: list[str], cwd: Path, log_path: Path):  # noqa: ANN001
        process_factory_called["value"] = True
        raise AssertionError("process_factory must not be called when server already alive")

    result = run_admin_live_smoke(
        admin_base_url="http://127.0.0.1:8000",
        try_start_server=True,
        repo_root=tmp_path,
        http_get=_online_contract_fetch,
        process_factory=_process_factory,
    )
    manifest = result["manifest"]
    smoke = result["smoke"]
    assert process_factory_called["value"] is False
    assert manifest["server_launch_mode"] == "external_existing"
    assert manifest["server_started_by_hf1"] is False
    assert smoke["admin_runtime_status"] == "passed"
    assert smoke["admin_consistency_passed"] is True


def test_server_unavailable_no_start_mode_is_blocker(tmp_path: Path) -> None:
    result = run_admin_live_smoke(
        admin_base_url="http://127.0.0.1:8000",
        try_start_server=False,
        repo_root=tmp_path,
        http_get=_offline_fetch,
    )
    manifest = result["manifest"]
    smoke = result["smoke"]
    assert manifest["server_launch_mode"] == "not_started"
    assert manifest["server_started_by_hf1"] is False
    assert smoke["admin_runtime_status"] == "blocked_admin_api_unavailable"
    assert smoke["admin_consistency_passed"] is False


def test_server_unavailable_try_start_succeeds(tmp_path: Path) -> None:
    state = {"started": False}

    def _fetch(url: str) -> dict:
        if not state["started"]:
            return _offline_fetch(url)
        return _online_contract_fetch(url)

    def _discover(**_: object) -> dict:
        return {
            "canonical_launch_command_found": True,
            "canonical_launch_command": ["python", "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
            "canonical_launch_command_str": "python -m uvicorn api.main:app --host 127.0.0.1 --port 8000",
            "launch_command_source": "Bot_data_base/README.md:14",
            "cwd": str(tmp_path),
        }

    def _process_factory(command: list[str], cwd: Path, log_path: Path) -> _FakeProcess:  # noqa: ARG001
        state["started"] = True
        log_path.write_text("server started", encoding="utf-8")
        return _FakeProcess()

    result = run_admin_live_smoke(
        admin_base_url="http://127.0.0.1:8000",
        try_start_server=True,
        repo_root=tmp_path,
        http_get=_fetch,
        discover_launch=_discover,
        process_factory=_process_factory,
    )
    manifest = result["manifest"]
    smoke = result["smoke"]
    assert manifest["server_launch_mode"] == "hf1_subprocess"
    assert manifest["server_started_by_hf1"] is True
    assert manifest["shutdown_performed"] is True
    assert manifest["shutdown_status"] == "ok"
    assert smoke["admin_runtime_status"] == "passed"
    assert smoke["admin_consistency_passed"] is True


def test_server_unavailable_try_start_fails_launch_blocker(tmp_path: Path) -> None:
    def _discover(**_: object) -> dict:
        return {
            "canonical_launch_command_found": True,
            "canonical_launch_command": ["python", "-m", "uvicorn", "api.main:app"],
            "canonical_launch_command_str": "python -m uvicorn api.main:app",
            "launch_command_source": "Bot_data_base/README.md:14",
            "cwd": str(tmp_path),
        }

    def _process_factory(command: list[str], cwd: Path, log_path: Path):  # noqa: ANN001, ARG001
        raise RuntimeError("cannot start")

    result = run_admin_live_smoke(
        admin_base_url="http://127.0.0.1:8000",
        try_start_server=True,
        repo_root=tmp_path,
        http_get=_offline_fetch,
        discover_launch=_discover,
        process_factory=_process_factory,
    )
    smoke = result["smoke"]
    assert smoke["admin_runtime_status"] == "blocked_admin_launch_failed"
    assert smoke["admin_consistency_passed"] is False
    assert any("admin_subprocess_start_failed" in item for item in smoke["issues"])
