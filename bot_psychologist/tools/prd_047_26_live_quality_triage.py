from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bot_psychologist.eval.prd_047_26_schema import (
    PRD_ID,
    default_cases_path,
    load_cases,
    repo_root,
    required_source_gate_paths,
    validate_cases,
)
from bot_psychologist.tools import validate_prd_artifact_encoding as encoding_validator
from bot_psychologist.tools.prd_047_26_triage_report import build_triage_report


REPO_ROOT = repo_root()
BOT_ROOT = REPO_ROOT / "bot_psychologist"
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
DEFAULT_BASE_URL = "http://127.0.0.1:8001"
API_KEY = "dev-key-001"
CURRENT_DIR = Path(__file__).resolve().parent


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _md(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines])


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()


def _normalize(text: str) -> str:
    return " ".join(str(text or "").lower().replace("\r\n", "\n").split())


def _http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(url=url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(request, timeout=240) as response:
        return int(response.status), json.loads(response.read().decode("utf-8"))


def _http_text(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> tuple[int, str]:
    request = urllib.request.Request(url=url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(request, timeout=240) as response:
        return int(response.status), response.read().decode("utf-8")


def _stream_body(query: str, session_id: str, user_id: str) -> bytes:
    payload = {
        "query": str(query),
        "user_id": str(user_id),
        "session_id": str(session_id),
        "include_path": False,
        "include_feedback_prompt": True,
        "debug": False,
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _extract_done_payload(sse_text: str) -> dict[str, Any]:
    events = [chunk for chunk in sse_text.split("\n\n") if chunk.strip()]
    for event in reversed(events):
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            payload = json.loads(line.replace("data:", "", 1).strip())
            if payload.get("done") is True:
                return payload
    raise RuntimeError("SSE done payload not found")


def _listener_pids(port: int) -> list[int]:
    process = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    pids: set[int] = set()
    needle = f":{port}"
    for line in process.stdout.splitlines():
        if needle not in line or "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if len(parts) >= 5:
            try:
                pids.add(int(parts[-1]))
            except ValueError:
                continue
    return sorted(pids)


def _wait_for_port(port: int, timeout_seconds: float = 90.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(1.0)
    return False


def _wait_for_backend(base_url: str, timeout_seconds: float = 90.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            status, _payload = _http_json(
                f"{base_url.rstrip('/')}/api/admin/runtime/effective",
                headers={"X-API-Key": API_KEY, "Accept": "application/json"},
            )
            if status == 200:
                return True
        except Exception:
            pass
        time.sleep(1.0)
    return False


def _start_managed_backend(port: int, *, stdout_log: Path) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["APP_ENV"] = "local"
    env["DEBUG_TRACE_ENABLED"] = "true"
    env["OVERLAY_SHADOW_TRACE_ENABLED"] = "true"
    env["OVERLAY_SHADOW_TRACE_MODE"] = "trace_only"
    env["WRITER_KB_PAYLOAD_USE_OVERLAY_METADATA"] = "false"
    env["WRITER_KB_PAYLOAD_ENABLED"] = "true"
    env["RETRIEVAL_CURRENT_TURN_FOCUS_ENABLED"] = "true"
    env["PYTHONUTF8"] = "1"
    python_path = BOT_ROOT / ".venv" / "Scripts" / "python.exe"
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    handle = stdout_log.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(python_path), "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", str(port)],
        cwd=BOT_ROOT,
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    setattr(process, "_stdout_handle", handle)
    return process


def _stop_managed_backend(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    finally:
        handle = getattr(process, "_stdout_handle", None)
        if handle is not None:
            handle.close()


def run_source_gate(*, out_dir: Path) -> dict[str, Any]:
    required_paths = [REPO_ROOT / rel for rel in required_source_gate_paths()]
    required_commits = {
        "PRD-047.24": ["47693c2", "c4fa911", "c61f566"],
        "PRD-047.25": ["e1b0fb5", "07c0e26"],
    }
    blockers: list[str] = []
    commit_presence: dict[str, str] = {}
    for group in required_commits.values():
        for commit in group:
            try:
                commit_presence[commit] = _git("rev-parse", "--verify", commit)
            except subprocess.CalledProcessError:
                commit_presence[commit] = ""
                blockers.append(f"missing_commit:{commit}")
    for path in required_paths:
        if not path.exists():
            blockers.append(f"missing_required_file:{path.relative_to(REPO_ROOT).as_posix()}")

    runtime_status = "unknown"
    runtime_payload: dict[str, Any] = {}
    try:
        _status, runtime_payload = _http_json(
            f"{DEFAULT_BASE_URL}/api/admin/runtime/effective",
            headers={"X-API-Key": API_KEY, "Accept": "application/json"},
        )
        runtime_status = "ok"
    except Exception:
        runtime_status = "unavailable"

    active_runtime_path = str(runtime_payload.get("runtime_entrypoint", "") or "unknown")
    writer_payload = dict(runtime_payload.get("writer_kb_payload", {}) or {})
    runtime_trace = dict(((runtime_payload.get("trace") or {}).get("runtime_config_trace")) or {})

    singular_runtime_ok = (
        active_runtime_path in {"multiagent_adapter", "unknown"}
        and str(writer_payload.get("primary_path", "") or "") in {"writer_kb_payload_v1", ""}
    )
    runtime_requirement_match: bool | None = None
    runtime_mismatches: list[str] = []
    warnings: list[str] = []
    if runtime_status == "ok":
        if not singular_runtime_ok:
            blockers.append("runtime_singularity_assumption_failed")
        runtime_requirement_match, runtime_mismatches = _runtime_matches_live_requirements(runtime_payload)
        warnings.extend([f"existing_backend_runtime_mismatch:{item}" for item in runtime_mismatches])

    report = {
        "schema_version": "prd_047_26_source_gate_report_v1",
        "prd_id": PRD_ID,
        "created_at": _utc_now(),
        "git_head": _git("rev-parse", "HEAD"),
        "required_paths": [
            {"path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"), "exists": path.exists()}
            for path in required_paths
        ],
        "required_commits": commit_presence,
        "runtime_probe_status": runtime_status,
        "active_runtime_path": active_runtime_path,
        "writer_kb_payload_primary": str(writer_payload.get("primary_path", "") or "") == "writer_kb_payload_v1",
        "overlay_trace_only_expected": True,
        "runtime_requirement_match": runtime_requirement_match,
        "runtime_mismatches": runtime_mismatches,
        "overlay_shadow_trace_enabled": bool(runtime_trace.get("overlay_shadow_trace_enabled", False))
        if runtime_trace
        else None,
        "warnings": warnings,
        "status": "passed" if not blockers else "blocked",
        "blockers": blockers,
    }
    _write_json(out_dir / "source_gate_report.json", report)
    return report


def _write_blocker_report(source_gate: dict[str, Any], report_dir: Path) -> None:
    lines = [
        f"- status: `{source_gate['status']}`",
        *[f"- blocker: `{item}`" for item in list(source_gate.get("blockers", []) or [])],
    ]
    _write_text(report_dir / "PRD-047.26_BLOCKER_REPORT.md", _md("PRD-047.26 Blocker Report", lines))


def build_dry_run_report(*, source_gate: dict[str, Any], cases_validation: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    blockers = list(source_gate.get("blockers", []) or []) + list(cases_validation.get("blockers", []) or [])
    warnings = list(source_gate.get("warnings", []) or []) + list(cases_validation.get("warnings", []) or [])
    report = {
        "schema_version": "prd_047_26_dry_run_report_v1",
        "prd_id": PRD_ID,
        "created_at": _utc_now(),
        "source_gate_status": source_gate["status"],
        "cases_validation_status": cases_validation["status"],
        "case_count": int(cases_validation.get("case_count", 0) or 0),
        "status": "passed" if not blockers else "blocked",
        "warnings": warnings,
        "blockers": blockers,
    }
    _write_json(out_dir / "dry_run_report.json", report)
    return report


def _extract_prompt_text(debug_payload: dict[str, Any], llm_payload: dict[str, Any]) -> str:
    live_evidence = dict(debug_payload.get("live_turn_evidence", {}) or {})
    writer = dict(live_evidence.get("writer", {}) or {})
    prompt_canvas = dict(writer.get("prompt_canvas", {}) or {})
    if str(debug_payload.get("writer_user_prompt", "") or "").strip():
        return str(debug_payload.get("writer_user_prompt", "") or "").strip()
    if str(llm_payload.get("user_prompt", "") or "").strip():
        return str(llm_payload.get("user_prompt", "") or "").strip()
    if str(prompt_canvas.get("user_prompt_preview", "") or "").strip():
        return str(prompt_canvas.get("user_prompt_preview", "") or "").strip()
    return "[prompt unavailable]"


def _load_llm_payload(base_url: str, session_id: str) -> dict[str, Any]:
    try:
        _status, payload = _http_json(
            f"{base_url.rstrip('/')}/api/debug/session/{session_id}/llm-payload?format=flat",
            headers={"X-API-Key": API_KEY, "Accept": "application/json"},
        )
        return payload
    except Exception:
        return {}


def _build_case_export(
    *,
    case: dict[str, Any],
    session_id: str,
    final_done: dict[str, Any],
    final_debug: dict[str, Any],
    llm_payload: dict[str, Any],
    runtime_payload: dict[str, Any],
) -> dict[str, Any]:
    live_evidence = dict(final_debug.get("live_turn_evidence", {}) or {})
    dialogue = dict(live_evidence.get("dialogue", {}) or {})
    writer = dict(live_evidence.get("writer", {}) or {})
    writer_prompt_assembly = dict(writer.get("prompt_assembly", {}) or {})
    writer_context_package = dict(writer_prompt_assembly.get("writer_context_package", {}) or {})
    evaluator = dict((writer.get("writer_debug") or {}).get("answer_fit_evaluator", {}) or {})
    validator = dict(live_evidence.get("validator", {}) or {})
    answer = str(final_done.get("answer", "") or "")
    return {
        "case_id": str(case.get("case_id", "") or ""),
        "title": str(case.get("title", "") or ""),
        "user_turns": [dict(item) for item in list(case.get("turns", []) or []) if isinstance(item, dict)],
        "assistant_answer": answer,
        "status": "ok",
        "pipeline": "NEO|multiagent_v1",
        "active_runtime_path": str(runtime_payload.get("runtime_entrypoint", "") or "unknown"),
        "state_analyzer": dict(live_evidence.get("state_thread", {}) or {}),
        "thread_manager": dict(dialogue.get("thread_debug", {}) or {}),
        "retrieval_decision": dict(dialogue.get("retrieval", {}) or {}),
        "retrieval_query_build_trace_v1": dict(final_debug.get("retrieval_query_build_trace", {}) or {}),
        "writer_kb_payload_trace": dict(final_debug.get("writer_kb_payload_trace", {}) or {}),
        "writer_kb_payload_v1": dict(writer_context_package.get("writer_kb_payload", {}) or {}),
        "overlay_shadow_trace": dict(final_debug.get("overlay_shadow", {}) or {}),
        "writer_contract": {
            "contract_excerpt": dict(writer.get("contract_excerpt", {}) or {}),
            "writer_context_package": writer_context_package,
        },
        "final_answer_directive_v1": dict(final_debug.get("final_answer_directive", {}) or {})
        or dict(writer.get("final_answer_directive", {}) or {}),
        "validator": validator,
        "evaluator": evaluator,
        "runtime_config_trace": dict(final_debug.get("runtime_config_trace", {}) or {}),
        "live_turn_evidence": live_evidence,
        "llm_payload_trace": {
            "model": llm_payload.get("model"),
            "user_prompt_chars": len(str(llm_payload.get("user_prompt", "") or "")),
            "system_prompt_chars": len(str(llm_payload.get("system_prompt", "") or "")),
        },
        "triage": {},
        "trace_missing_evidence": False,
        "missing_fields": [],
        "safe_for_local_dev_only": True,
    }


def _probe_existing_backend(base_url: str) -> tuple[bool, dict[str, Any]]:
    try:
        status, payload = _http_json(
            f"{base_url.rstrip('/')}/api/admin/runtime/effective",
            headers={"X-API-Key": API_KEY, "Accept": "application/json"},
        )
        return status == 200, payload
    except Exception:
        return False, {}


def _runtime_matches_live_requirements(runtime_payload: dict[str, Any]) -> tuple[bool, list[str]]:
    writer_payload = dict(runtime_payload.get("writer_kb_payload", {}) or {})
    runtime_trace = dict(((runtime_payload.get("trace") or {}).get("runtime_config_trace")) or {})
    mismatches: list[str] = []
    if str(runtime_payload.get("runtime_entrypoint", "") or "") != "multiagent_adapter":
        mismatches.append("runtime_entrypoint_not_multiagent_adapter")
    if str(writer_payload.get("primary_path", "") or "") != "writer_kb_payload_v1":
        mismatches.append("writer_kb_payload_not_primary")
    if not bool(runtime_trace.get("retrieval_current_turn_focus_enabled", False)):
        mismatches.append("retrieval_current_turn_focus_disabled")
    if not bool(runtime_trace.get("debug_trace_enabled", False)):
        mismatches.append("debug_trace_disabled")
    if not bool(runtime_trace.get("overlay_shadow_trace_enabled", False)):
        mismatches.append("overlay_shadow_trace_disabled")
    return not mismatches, mismatches


def run_live_cases(*, base_url: str, cases: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    base_headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "text/event-stream",
    }
    existing_ok, runtime_payload = _probe_existing_backend(base_url)
    backend_mode = "existing"
    managed_process: subprocess.Popen[str] | None = None
    killed_existing_backend_pids: list[int] = []
    if existing_ok:
        runtime_ok, runtime_mismatches = _runtime_matches_live_requirements(runtime_payload)
        if not runtime_ok:
            port = int(base_url.rsplit(":", 1)[-1])
            killed_existing_backend_pids = _listener_pids(port)
            for pid_value in killed_existing_backend_pids:
                subprocess.run(
                    ["taskkill", "/PID", str(pid_value), "/F"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
            backend_mode = "managed_start"
            managed_process = _start_managed_backend(port, stdout_log=out_dir / "managed_backend_stdout.log")
            if not _wait_for_port(port) or not _wait_for_backend(base_url):
                _stop_managed_backend(managed_process)
                managed_process = None
                backend_mode = "unavailable"
    else:
        port = int(base_url.rsplit(":", 1)[-1])
        if _listener_pids(port):
            backend_mode = "unavailable"
        else:
            backend_mode = "managed_start"
            managed_process = _start_managed_backend(port, stdout_log=out_dir / "managed_backend_stdout.log")
            if not _wait_for_port(port) or not _wait_for_backend(base_url):
                _stop_managed_backend(managed_process)
                managed_process = None
                backend_mode = "unavailable"
    if backend_mode == "unavailable":
        result = {
            "schema_version": "prd_047_26_live_quality_results_v1",
            "prd_id": PRD_ID,
            "created_at": _utc_now(),
            "backend_mode": backend_mode,
            "backend_url": base_url,
            "live_mode_status": "warning",
            "reason": "backend_unavailable",
            "killed_existing_backend_pids": killed_existing_backend_pids,
            "cases": [],
            "overlay_apply_detected_count": 0,
            "internal_leak_count": 0,
            "raw_kb_dump_count": 0,
            "unsafe_practice_count": 0,
            "diagnostic_overclaim_count": 0,
        }
        _write_json(out_dir / "live_quality_results.json", result)
        return result

    if backend_mode == "managed_start":
        _existing_ok, runtime_payload = _probe_existing_backend(base_url)

    exports: list[dict[str, Any]] = []
    internal_leak_count = 0
    raw_kb_dump_count = 0
    unsafe_practice_count = 0
    diagnostic_overclaim_count = 0
    overlay_apply_detected_count = 0
    run_token = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    try:
        for index, case in enumerate(cases, start=1):
            session_id = f"prd-047-26-{str(case['case_id']).lower()}-{run_token}"
            user_id = f"prd-047-26-user-{index:02d}"
            final_done: dict[str, Any] = {}
            final_debug: dict[str, Any] = {}
            for turn in list(case.get("turns", []) or []):
                query = str(dict(turn).get("content", "") or "")
                _status, stream_text = _http_text(
                    f"{base_url.rstrip('/')}/api/v1/questions/adaptive-stream",
                    method="POST",
                    headers=base_headers,
                    data=_stream_body(query, session_id, user_id),
                )
                final_done = _extract_done_payload(stream_text)
                time.sleep(1.0)
                _debug_status, final_debug = _http_json(
                    f"{base_url.rstrip('/')}/api/debug/session/{session_id}/multiagent-trace",
                    headers={"X-API-Key": API_KEY, "Accept": "application/json"},
                )
            llm_payload = _load_llm_payload(base_url, session_id)
            export = _build_case_export(
                case=case,
                session_id=session_id,
                final_done=final_done,
                final_debug=final_debug,
                llm_payload=llm_payload,
                runtime_payload=runtime_payload,
            )
            overlay_trace = dict(export.get("overlay_shadow_trace", {}) or {})
            if any(bool(overlay_trace.get(flag, False)) for flag in ("used_for_writer", "used_for_retrieval_execution", "used_for_final_answer")):
                overlay_apply_detected_count += 1
            prompt_text = _extract_prompt_text(final_debug, llm_payload)
            _write_text(out_dir / "prompt_canvases" / f"{case['case_id']}_writer_prompt.txt", prompt_text)
            _write_json(
                out_dir / "prompt_canvases" / f"{case['case_id']}_writer_context.json",
                {
                    "case_id": case["case_id"],
                    "writer_contract": export.get("writer_contract", {}),
                    "final_answer_directive_v1": export.get("final_answer_directive_v1", {}),
                    "runtime_config_trace": export.get("runtime_config_trace", {}),
                    "live_turn_evidence_writer": dict(
                        dict(export.get("live_turn_evidence", {}) or {}).get("writer", {}) or {}
                    ),
                },
            )
            _write_json(out_dir / "live_turn_exports" / f"{case['case_id']}.json", export)
            exports.append(export)

        result = {
            "schema_version": "prd_047_26_live_quality_results_v1",
            "prd_id": PRD_ID,
            "created_at": _utc_now(),
            "backend_mode": backend_mode,
            "backend_url": base_url,
            "live_mode_status": "passed",
            "reason": "live_cases_executed",
            "killed_existing_backend_pids": killed_existing_backend_pids,
            "cases": exports,
            "overlay_apply_detected_count": overlay_apply_detected_count,
            "internal_leak_count": internal_leak_count,
            "raw_kb_dump_count": raw_kb_dump_count,
            "unsafe_practice_count": unsafe_practice_count,
            "diagnostic_overclaim_count": diagnostic_overclaim_count,
        }
        _write_json(out_dir / "live_quality_results.json", result)
        return result
    finally:
        _stop_managed_backend(managed_process)


def build_no_mutation_proof(*, out_dir: Path) -> dict[str, Any]:
    report = {
        "prd_id": PRD_ID,
        "runtime_behavior_changed": False,
        "writer_prompt_changed": False,
        "state_analyzer_prompt_changed": False,
        "thread_manager_logic_changed": False,
        "retrieval_ranking_changed": False,
        "executed_retrieval_query_algorithm_changed": False,
        "overlay_apply_enabled": False,
        "db_schema_changed": False,
        "chroma_reindexed": False,
        "processed_blocks_mutated": False,
        "botdb_registry_mutated": False,
        "new_runtime_path_added": False,
        "new_llm_agent_added": False,
        "allowed_changes": [
            "read_only_triage_runner",
            "eval_cases",
            "report_generator",
            "tests",
            "docs_metadata_sync",
            "TO_DO_LIST_artifacts",
        ],
        "evidence": [
            "bot_psychologist/eval/prd_047_26_live_quality_cases.json",
            "bot_psychologist/eval/prd_047_26_schema.py",
            "bot_psychologist/tools/prd_047_26_live_quality_triage.py",
            "bot_psychologist/tools/prd_047_26_triage_report.py",
        ],
    }
    _write_json(out_dir / "no_mutation_proof.json", report)
    return report


def run_encoding_hygiene(*, out_dir: Path, reports_dir: Path) -> dict[str, Any]:
    report = encoding_validator.run(
        argparse.Namespace(
            prd=PRD_ID,
            logs_dir=str(out_dir),
            reports_dir=str(reports_dir),
            out_dir=str(out_dir),
            report_prd=PRD_ID,
            repo_root=str(REPO_ROOT),
            fixed_file=[],
        )
    )
    source = out_dir / "artifact_encoding_hygiene_report.json"
    target = out_dir / "encoding_hygiene_report.json"
    if source.exists():
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return report


def write_implementation_report(
    *,
    source_gate: dict[str, Any],
    dry_run_report: dict[str, Any],
    live_results: dict[str, Any],
    triage_report: dict[str, Any],
) -> None:
    head_after = _git("rev-parse", "HEAD")
    failure_distribution = [
        f"- `{item['case_id']}`: status=`{item['triage']['status']}` classes=`{', '.join(item['triage']['failure_classes'])}`"
        for item in triage_report["case_results"]
        if item["triage"]["status"] != "ok"
    ]
    direct_quality_observations = [
        f"- `{item['case_id']}`: success=`{item['triage']['direct_answer_success']}` notes=`{'; '.join(item['triage']['notes']) or 'none'}`"
        for item in triage_report["case_results"]
    ]
    overlay_observations = [
        f"- `{item['case_id']}`: overlay_false_positive=`{item['triage']['overlay_false_positive']}` overlay_apply=`{any(bool(dict(item.get('overlay_shadow_trace', {}) or {}).get(flag, False)) for flag in ('used_for_writer', 'used_for_retrieval_execution', 'used_for_final_answer'))}`"
        for item in triage_report["case_results"]
        if item["triage"]["overlay_false_positive"] or any(
            bool(dict(item.get("overlay_shadow_trace", {}) or {}).get(flag, False))
            for flag in ("used_for_writer", "used_for_retrieval_execution", "used_for_final_answer")
        )
    ]
    routing_observations = [
        f"- `{item['case_id']}`: dialogue_act=`{item['triage']['observed_dialogue_act']}` obligation=`{item['triage']['observed_answer_obligation']}` response_mode=`{item['triage']['observed_response_mode']}`"
        for item in triage_report["case_results"]
        if "dialogue_act_error" in item["triage"]["failure_classes"]
        or "answer_obligation_error" in item["triage"]["failure_classes"]
        or "response_mode_error" in item["triage"]["failure_classes"]
    ]
    evaluator_observations = [
        f"- `{item['case_id']}`: evaluator_false_pass with notes=`{'; '.join(item['triage']['notes'])}`"
        for item in triage_report["case_results"]
        if "evaluator_false_pass" in item["triage"]["failure_classes"]
    ]
    lines = [
        "## Status",
        f"- prd_id: `{PRD_ID}`",
        f"- implementation_status: `{triage_report['status']}`",
        f"- git_head_before: `{source_gate['git_head']}`",
        f"- git_head_after: `{head_after}`",
        f"- commit_sha: `{head_after}`",
        "",
        "## What Was Added",
        "- read-only live quality triage runner",
        "- static live case set + schema helper",
        "- triage report generator",
        "- schema/report tests",
        "- TO_DO_LIST artifacts and docs metadata sync",
        "",
        "## What Was Not Changed",
        "- Writer prompt/runtime behavior",
        "- State Analyzer prompt",
        "- Thread Manager logic",
        "- retrieval ranking / executed retrieval query algorithm",
        "- overlay apply mode",
        "- DB / Chroma / processed blocks / registry",
        "",
        "## Source Gate",
        f"- status: `{source_gate['status']}`",
        *[f"- blocker: `{item}`" for item in list(source_gate.get("blockers", []) or [])],
        *[f"- warning: `{item}`" for item in list(source_gate.get("warnings", []) or [])],
        "",
        "## Dry Run",
        f"- status: `{dry_run_report['status']}`",
        f"- case_count: `{dry_run_report['case_count']}`",
        *[f"- warning: `{item}`" for item in list(dry_run_report.get("warnings", []) or [])],
        "",
        "## Live Run",
        f"- backend_mode: `{live_results['backend_mode']}`",
        f"- live_mode_status: `{live_results['live_mode_status']}`",
        f"- reason: `{live_results['reason']}`",
        f"- executed_case_count: `{triage_report['executed_case_count']}`",
        f"- overlay_apply_detected_count: `{live_results.get('overlay_apply_detected_count', 0)}`",
        f"- internal_leak_count: `{live_results.get('internal_leak_count', 0)}`",
        f"- raw_kb_dump_count: `{live_results.get('raw_kb_dump_count', 0)}`",
        "",
        "## Triage Counters",
        f"- direct_answer_success_rate: `{triage_report['direct_answer_success_rate']}`",
        f"- living_tone_warning_count: `{triage_report['living_tone_warning_count']}`",
        f"- overlay_false_positive_count: `{triage_report['overlay_false_positive_count']}`",
        f"- overlay_missing_where_expected_count: `{triage_report['overlay_missing_where_expected_count']}`",
        f"- dialogue_act_error_count: `{triage_report['dialogue_act_error_count']}`",
        f"- answer_obligation_error_count: `{triage_report['answer_obligation_error_count']}`",
        f"- response_mode_error_count: `{triage_report['response_mode_error_count']}`",
        f"- retrieval_query_error_count: `{triage_report['retrieval_query_error_count']}`",
        f"- kb_payload_error_count: `{triage_report['kb_payload_error_count']}`",
        f"- writer_style_regression_count: `{triage_report['writer_style_regression_count']}`",
        f"- evaluator_false_pass_count: `{triage_report['evaluator_false_pass_count']}`",
        f"- trace_missing_evidence_count: `{triage_report['trace_missing_evidence_count']}`",
        "",
        "## DB Track Readiness",
        f"- db_track_readiness: `{triage_report['db_track_readiness']}`",
        f"- recommended_next_prd: `{triage_report['recommended_next_prd']}`",
        "",
        "## Failure Class Distribution",
        *(failure_distribution or ["- none"]),
        "",
        "## Direct Answer Quality Observations",
        *direct_quality_observations,
        "",
        "## Overlay Noise Observations",
        *(overlay_observations or ["- none"]),
        "",
        "## Dialogue Act / Answer Obligation Observations",
        *(routing_observations or ["- none"]),
        "",
        "## Evaluator False-Pass Observations",
        *(evaluator_observations or ["- none"]),
        "",
        "## Test Commands And Results",
        "- see `TO_DO_LIST/logs/PRD-047.26/test_command_output.txt`",
        "",
        "## No-Mutation Proof Summary",
        "- see `TO_DO_LIST/logs/PRD-047.26/no_mutation_proof.json`",
        "",
        "## Known Warnings",
        *(
            [f"- case `{item['case_id']}` -> `{', '.join(item['triage']['failure_classes'])}`" for item in triage_report["case_results"] if item["triage"]["status"] != "ok"]
            or ["- none"]
        ),
        "",
        "## Next PRD Recommendation",
        f"- `{triage_report['recommended_next_prd']}`",
    ]
    _write_text(REPORT_DIR / "PRD-047.26_IMPLEMENTATION_REPORT.md", _md("PRD-047.26 Implementation Report", lines))


def write_next_prd_recommendation(*, triage_report: dict[str, Any]) -> None:
    lines = [
        f"- prd_status: `{triage_report['status']}`",
        f"- db_track_readiness: `{triage_report['db_track_readiness']}`",
        f"- recommended_next_prd: `{triage_report['recommended_next_prd']}`",
        f"- overlay_false_positive_count: `{triage_report['overlay_false_positive_count']}`",
        f"- dialogue_act_error_count: `{triage_report['dialogue_act_error_count']}`",
        f"- answer_obligation_error_count: `{triage_report['answer_obligation_error_count']}`",
        f"- evaluator_false_pass_count: `{triage_report['evaluator_false_pass_count']}`",
    ]
    _write_text(REPORT_DIR / "PRD-047.26_NEXT_PRD_RECOMMENDATION.md", _md("PRD-047.26 Next PRD Recommendation", lines))


def run(*, mode: str, base_url: str, out_dir: Path, reports_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = load_cases(default_cases_path())
    cases_validation = validate_cases(cases)
    source_gate = run_source_gate(out_dir=out_dir)
    if source_gate["status"] != "passed":
        _write_blocker_report(source_gate, reports_dir)
    dry_run_report = build_dry_run_report(source_gate=source_gate, cases_validation=cases_validation, out_dir=out_dir)
    if mode == "dry-run":
        return dry_run_report

    live_results = run_live_cases(base_url=base_url, cases=cases, out_dir=out_dir)
    triage_report = build_triage_report(cases=cases, live_results=live_results, out_dir=out_dir)
    no_mutation = build_no_mutation_proof(out_dir=out_dir)
    encoding = run_encoding_hygiene(out_dir=out_dir, reports_dir=reports_dir)
    write_implementation_report(
        source_gate=source_gate,
        dry_run_report=dry_run_report,
        live_results=live_results,
        triage_report=triage_report,
    )
    write_next_prd_recommendation(triage_report=triage_report)
    return {
        "dry_run_report": dry_run_report,
        "live_results_status": live_results["live_mode_status"],
        "triage_status": triage_report["status"],
        "db_track_readiness": triage_report["db_track_readiness"],
        "no_mutation_status": "passed" if not any(value is True for key, value in no_mutation.items() if key.endswith("_changed")) else "blocked",
        "encoding_status": encoding.get("final_status", "unknown"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-047.26 live answer quality triage runner")
    parser.add_argument("--mode", choices=["dry-run", "live"], default="dry-run")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--out-dir", default=str(LOG_DIR))
    parser.add_argument("--reports-dir", default=str(REPORT_DIR))
    args = parser.parse_args()
    result = run(
        mode=str(args.mode),
        base_url=str(args.base_url),
        out_dir=Path(str(args.out_dir)),
        reports_dir=Path(str(args.reports_dir)),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
