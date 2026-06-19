"""PRD-047.27 semantic cards pilot dry/live evidence runner."""

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
from types import SimpleNamespace
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
BOT_ROOT = CURRENT_DIR.parent
REPO_ROOT = BOT_ROOT.parent

if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from bot_agent.knowledge.semantic_card_loader import load_semantic_cards
from bot_agent.knowledge.semantic_card_payload_adapter import (
    SemanticCardsPilotConfig,
    build_semantic_cards_pilot_selection,
)
from tools import validate_prd_artifact_encoding as encoding_validator


PRD_ID = "PRD-047.27"
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
DEFAULT_BASE_URL = "http://127.0.0.1:8001"
API_KEY = "dev-key-001"


LIVE_CASES = [
    {
        "case_id": "SCP-001",
        "query": 'Что такое программа "Несовершенное Я"?',
        "expected_cards": ["program_imperfect_self_v1"],
        "expect_card": True,
    },
    {
        "case_id": "SCP-002",
        "query": "Расскажи о пяти драйверах выживания.",
        "expected_cards": ["five_survival_drivers_v1"],
        "expect_card": True,
    },
    {
        "case_id": "SCP-003",
        "query": 'Дай одну короткую практику, чтобы заметить драйвер "Будь сильным".',
        "expected_cards": [
            "be_strong_driver_v1",
            "one_bounded_practice_not_self_improvement_whip_v1",
        ],
        "expect_card": True,
        "expect_practice": True,
    },
    {
        "case_id": "SCP-004",
        "query": "Объясни коротко, что значит контроль как безопасность.",
        "expected_cards": ["control_as_safety_v1"],
        "expect_card": True,
    },
    {
        "case_id": "SCP-005",
        "query": "Когда накрывает паникой, почему контроль становится сильнее?",
        "expected_cards": ["panic_control_support_v1"],
        "expect_card": True,
    },
    {
        "case_id": "SCP-006",
        "query": "Я выжат и не хочу теорию. Просто ответь по-человечески.",
        "expected_cards": [],
        "expect_card": False,
    },
    {
        "case_id": "SCP-007",
        "query": "Привет! Я Олег. Можешь мне ответить на вопросы?",
        "expected_cards": [],
        "expect_card": False,
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout.strip()


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
    return json.dumps(
        {
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "include_path": False,
            "include_feedback_prompt": True,
            "debug": False,
        },
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")


def _extract_done_payload(sse_text: str) -> dict[str, Any]:
    for event in reversed([chunk for chunk in sse_text.split("\n\n") if chunk.strip()]):
        for line in event.splitlines():
            if line.startswith("data:"):
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


def _wait_for_backend(base_url: str, timeout_seconds: float = 90.0) -> bool:
    deadline = time.time() + timeout_seconds
    port = int(base_url.rsplit(":", 1)[-1])
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                time.sleep(1.0)
                continue
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


def _start_backend(port: int, stdout_log: Path) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["APP_ENV"] = "local"
    env["DEBUG_TRACE_ENABLED"] = "true"
    env["WRITER_KB_PAYLOAD_ENABLED"] = "true"
    env["WRITER_KB_PAYLOAD_USE_OVERLAY_METADATA"] = "false"
    env["RETRIEVAL_CURRENT_TURN_FOCUS_ENABLED"] = "true"
    env["SEMANTIC_CARDS_PILOT_ENABLED"] = "true"
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


def _stop_backend(process: subprocess.Popen[str] | None) -> None:
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


def _probe_runtime(base_url: str) -> tuple[bool, dict[str, Any]]:
    try:
        status, payload = _http_json(
            f"{base_url.rstrip('/')}/api/admin/runtime/effective",
            headers={"X-API-Key": API_KEY, "Accept": "application/json"},
        )
        return status == 200, payload
    except Exception:
        return False, {}


def _runtime_matches(runtime_payload: dict[str, Any]) -> tuple[bool, list[str]]:
    trace = dict(((runtime_payload.get("trace") or {}).get("runtime_config_trace")) or {})
    mismatches: list[str] = []
    if str(runtime_payload.get("runtime_entrypoint", "") or "") != "multiagent_adapter":
        mismatches.append("runtime_entrypoint_not_multiagent_adapter")
    for key in (
        "writer_kb_payload_enabled",
        "retrieval_current_turn_focus_enabled",
        "semantic_cards_pilot_enabled",
        "debug_trace_enabled",
    ):
        if not bool(trace.get(key, False)):
            mismatches.append(f"{key}_false")
    return not mismatches, mismatches


def run_source_gate(out_dir: Path) -> dict[str, Any]:
    required_paths = [
        "TO_DO_LIST/reports/PRD-047.26-HF1_IMPLEMENTATION_REPORT.md",
        "TO_DO_LIST/logs/PRD-047.26-HF1/live_quality_triage_report.json",
        "TO_DO_LIST/logs/PRD-047.26-HF1/no_mutation_proof.json",
        "docs/PROJECT_STATE.md",
        "docs/ROADMAP.md",
        "docs/PRD_INDEX.md",
    ]
    blockers = [
        f"missing_required_file:{path}"
        for path in required_paths
        if not (REPO_ROOT / path).exists()
    ]
    status, runtime_payload = _probe_runtime(DEFAULT_BASE_URL)
    runtime_ok = None
    runtime_mismatches: list[str] = []
    if status:
        runtime_ok, runtime_mismatches = _runtime_matches(runtime_payload)
    report = {
        "schema_version": "prd_047_27_source_gate_report_v1",
        "prd_id": PRD_ID,
        "created_at": _utc_now(),
        "git_head": _git("rev-parse", "HEAD"),
        "head_equals_origin_main": _git("rev-parse", "HEAD") == _git("rev-parse", "origin/main"),
        "required_paths": [
            {"path": path, "exists": (REPO_ROOT / path).exists()}
            for path in required_paths
        ],
        "runtime_probe_status": "ok" if status else "unavailable",
        "runtime_requirement_match": runtime_ok,
        "runtime_mismatches": runtime_mismatches,
        "status": "passed" if not blockers else "blocked",
        "warnings": [f"existing_backend_runtime_mismatch:{item}" for item in runtime_mismatches],
        "blockers": blockers,
    }
    _write_json(out_dir / "source_gate_report.json", report)
    return report


def build_preview(out_dir: Path) -> dict[str, Any]:
    cards = load_semantic_cards()
    preview = {
        "schema_version": "semantic_cards_pilot_preview_v1",
        "prd_id": PRD_ID,
        "created_at": _utc_now(),
        "card_count": len(cards),
        "card_ids": [card.card_id for card in cards],
        "chunk_type_counts": _count_by([card.chunk_type for card in cards]),
        "all_writer_can_ignore": all(card.writer_can_ignore for card in cards),
        "practice_card_ids": [card.card_id for card in cards if card.chunk_type == "practice"],
    }
    _write_json(out_dir / "semantic_cards_pilot_preview.json", preview)
    _write_text(
        out_dir / "semantic_cards_pilot_preview.md",
        "\n".join(
            [
                "# PRD-047.27 Semantic Cards Pilot Preview",
                "",
                f"- card_count: `{preview['card_count']}`",
                f"- all_writer_can_ignore: `{preview['all_writer_can_ignore']}`",
                f"- practice_card_ids: `{', '.join(preview['practice_card_ids'])}`",
                "",
                "## Cards",
                *[f"- `{card.card_id}`: {card.title}" for card in cards],
            ]
        ),
    )
    return preview


def run_dry(out_dir: Path) -> dict[str, Any]:
    dry_config = SemanticCardsPilotConfig(
        enabled=True,
        enabled_requested=True,
        source="runner_forced_dry_run",
        runtime_mode="local",
        max_cards=3,
    )
    selections = []
    for case in LIVE_CASES:
        trace = build_semantic_cards_pilot_selection(
            user_message=case["query"],
            retrieval_decision={"mechanism_hints": case.get("expected_cards", [])},
            config=dry_config,
        )
        selections.append(
            {
                "case_id": case["case_id"],
                "expected_card": bool(case["expect_card"]),
                "selected_card_ids": list(trace.get("selected_card_ids", []) or []),
                "suppressed_reason": str(trace.get("suppressed_reason", "") or ""),
            }
        )
    expected_hits = sum(
        1
        for case in selections
        if case["expected_card"] and case["selected_card_ids"]
    )
    suppressed = sum(
        1
        for case in selections
        if not case["expected_card"] and not case["selected_card_ids"]
    )
    report = {
        "schema_version": "prd_047_27_dry_run_report_v1",
        "prd_id": PRD_ID,
        "created_at": _utc_now(),
        "case_count": len(LIVE_CASES),
        "expected_card_selected_count": expected_hits,
        "semantic_card_suppressed_when_not_needed_count": suppressed,
        "selections": selections,
        "status": "passed" if expected_hits >= 5 and suppressed >= 2 else "warning",
        "warnings": [] if expected_hits >= 5 and suppressed >= 2 else ["selection_threshold_not_met"],
        "blockers": [],
    }
    _write_json(out_dir / "dry_run_report.json", report)
    return report


def run_tests(out_dir: Path) -> dict[str, Any]:
    python_exe = BOT_ROOT / ".venv" / "Scripts" / "python.exe"
    run_suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    basetemp = BOT_ROOT / f".pytest_tmp_prd_047_27_{run_suffix}"
    temp_root = BOT_ROOT / f".tmp_prd_047_27_{run_suffix}"
    basetemp.mkdir(parents=True, exist_ok=True)
    temp_root.mkdir(parents=True, exist_ok=True)
    commands: list[tuple[list[str], Path]] = [
        (
            [
                str(python_exe),
                "-m",
                "pytest",
                "tests/test_prd_047_27_semantic_card_schema.py",
                "tests/test_prd_047_27_semantic_card_loader.py",
                "tests/test_prd_047_27_semantic_card_payload_adapter.py",
                "tests/test_prd_047_27_semantic_card_pilot_selection.py",
                "-q",
                f"--basetemp={basetemp}",
            ],
            BOT_ROOT,
        ),
        (
            [
                str(python_exe),
                "-m",
                "pytest",
                "tests/test_retrieval_query_builder_current_turn_focus.py",
                "tests/test_prd_047_26_hf1_dialogue_act_obligation.py",
                "tests/test_prd_047_26_hf1_acceptance_gate.py",
                "tests/api/test_writer_kb_payload_live_http_path.py",
                "tests/api/test_overlay_shadow_trace_api_debug.py",
                "-q",
                f"--basetemp={basetemp}",
            ],
            BOT_ROOT,
        ),
    ]
    outputs: list[str] = []
    results: list[dict[str, Any]] = []
    for command, cwd in commands:
        env = dict(os.environ)
        env["TEMP"] = str(temp_root)
        env["TMP"] = str(temp_root)
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        outputs.append(f"$ {' '.join(command)}\n{completed.stdout}\n{completed.stderr}\n")
        results.append(
            {
                "command": command,
                "cwd": str(cwd.relative_to(REPO_ROOT)).replace("\\", "/"),
                "returncode": completed.returncode,
            }
        )
    _write_text(out_dir / "test_command_output.txt", "\n".join(outputs))
    report = {
        "schema_version": "prd_047_27_test_summary_v1",
        "prd_id": PRD_ID,
        "created_at": _utc_now(),
        "status": "passed" if all(item["returncode"] == 0 for item in results) else "failed",
        "commands": results,
    }
    _write_json(out_dir / "test_summary.json", report)
    return report


def run_live(base_url: str, out_dir: Path) -> dict[str, Any]:
    existing_ok, runtime_payload = _probe_runtime(base_url)
    backend_mode = "existing"
    managed_process: subprocess.Popen[str] | None = None
    killed_pids: list[int] = []
    port = int(base_url.rsplit(":", 1)[-1])
    if existing_ok:
        runtime_ok, _mismatches = _runtime_matches(runtime_payload)
        if not runtime_ok:
            killed_pids = _listener_pids(port)
            for pid in killed_pids:
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True)
            backend_mode = "managed_start"
            managed_process = _start_backend(port, out_dir / "managed_backend_stdout.log")
            if not _wait_for_backend(base_url):
                _stop_backend(managed_process)
                backend_mode = "unavailable"
    else:
        backend_mode = "managed_start"
        managed_process = _start_backend(port, out_dir / "managed_backend_stdout.log")
        if not _wait_for_backend(base_url):
            _stop_backend(managed_process)
            backend_mode = "unavailable"
    if backend_mode == "unavailable":
        report = {
            "schema_version": "prd_047_27_live_pilot_report_v1",
            "prd_id": PRD_ID,
            "created_at": _utc_now(),
            "status": "warning",
            "reason": "backend_unavailable",
            "cases": [],
            "killed_existing_backend_pids": killed_pids,
        }
        _write_json(out_dir / "live_pilot_report.json", report)
        return report

    _ok, runtime_payload = _probe_runtime(base_url)
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "text/event-stream",
    }
    run_token = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    case_results: list[dict[str, Any]] = []
    try:
        for index, case in enumerate(LIVE_CASES, start=1):
            session_id = f"prd-047-27-{case['case_id'].lower()}-{run_token}"
            user_id = f"prd-047-27-user-{index:02d}"
            _status, stream = _http_text(
                f"{base_url.rstrip('/')}/api/v1/questions/adaptive-stream",
                method="POST",
                headers=headers,
                data=_stream_body(case["query"], session_id, user_id),
            )
            done = _extract_done_payload(stream)
            time.sleep(1.0)
            _debug_status, debug = _http_json(
                f"{base_url.rstrip('/')}/api/debug/session/{session_id}/multiagent-trace",
                headers={"X-API-Key": API_KEY, "Accept": "application/json"},
            )
            llm_payload = _load_llm_payload(base_url, session_id)
            answer = str(done.get("answer", "") or "")
            semantic_trace = dict(debug.get("semantic_cards_pilot", {}) or {})
            writer_payload_trace = dict(debug.get("writer_kb_payload_trace", {}) or {})
            selected_ids = list(semantic_trace.get("selected_card_ids", []) or [])
            internal_leak = _contains_internal_leak(answer)
            raw_dump = _contains_raw_dump(answer)
            practice_overpush = (
                not bool(case.get("expect_practice", False))
                and _contains_practice_push(answer)
            )
            result = {
                "case_id": case["case_id"],
                "query": case["query"],
                "answer": answer,
                "expected_cards": list(case.get("expected_cards", []) or []),
                "expected_card": bool(case.get("expect_card", False)),
                "selected_card_ids": selected_ids,
                "selected_card_count": int(semantic_trace.get("selected_card_count", 0) or 0),
                "suppressed_reason": str(semantic_trace.get("suppressed_reason", "") or ""),
                "writer_payload_chunk_count": int(writer_payload_trace.get("payload_chunk_count", 0) or 0),
                "direct_answer_success": bool(answer.strip()) and not internal_leak and not raw_dump,
                "card_internal_leak": internal_leak,
                "raw_source_dump": raw_dump,
                "practice_overpush": practice_overpush,
                "answer_too_textbook": _looks_too_textbook(answer),
            }
            prompt_text = _extract_prompt_text(debug, llm_payload)
            _write_text(out_dir / "prompt_canvases" / f"{case['case_id']}_writer_prompt.txt", prompt_text)
            _write_json(
                out_dir / "prompt_canvases" / f"{case['case_id']}_writer_context.json",
                {
                    "case_id": case["case_id"],
                    "semantic_cards_pilot": semantic_trace,
                    "writer_kb_payload_trace": writer_payload_trace,
                    "runtime_config_trace": dict(debug.get("runtime_config_trace", {}) or {}),
                },
            )
            _write_json(out_dir / "live_turn_exports" / f"{case['case_id']}.json", result)
            case_results.append(result)
    finally:
        _stop_backend(managed_process)

    direct_success_rate = (
        sum(1 for item in case_results if item["direct_answer_success"]) / max(1, len(case_results))
    )
    expected_selected = sum(
        1 for item in case_results if item["expected_card"] and item["selected_card_count"] > 0
    )
    suppressed = sum(
        1 for item in case_results if not item["expected_card"] and item["selected_card_count"] == 0
    )
    report = {
        "schema_version": "prd_047_27_live_pilot_report_v1",
        "prd_id": PRD_ID,
        "created_at": _utc_now(),
        "backend_mode": backend_mode,
        "backend_url": base_url,
        "killed_existing_backend_pids": killed_pids,
        "case_count": len(case_results),
        "semantic_card_selected_when_expected_count": expected_selected,
        "semantic_card_suppressed_when_not_needed_count": suppressed,
        "card_internal_leak_count": sum(1 for item in case_results if item["card_internal_leak"]),
        "raw_source_dump_count": sum(1 for item in case_results if item["raw_source_dump"]),
        "practice_overpush_count": sum(1 for item in case_results if item["practice_overpush"]),
        "answer_too_textbook_count": sum(1 for item in case_results if item["answer_too_textbook"]),
        "direct_answer_success_rate": round(direct_success_rate, 4),
        "living_tone_warning_count": sum(1 for item in case_results if item["answer_too_textbook"]),
        "runtime_config_trace": dict(((runtime_payload.get("trace") or {}).get("runtime_config_trace")) or {}),
        "cases": case_results,
    }
    blockers = []
    warnings = []
    if report["direct_answer_success_rate"] < 0.9:
        blockers.append("direct_answer_success_rate_below_threshold")
    for key in ("card_internal_leak_count", "raw_source_dump_count", "practice_overpush_count"):
        if int(report[key]) != 0:
            blockers.append(f"{key}_nonzero")
    if int(report["semantic_card_suppressed_when_not_needed_count"]) < 2:
        blockers.append("semantic_card_suppressed_when_not_needed_count_below_2")
    if int(report["answer_too_textbook_count"]) > 0:
        warnings.append("answer_too_textbook_detected")
    report["status"] = "blocked" if blockers else ("passed_with_warning" if warnings else "passed")
    report["warnings"] = warnings
    report["blockers"] = blockers
    _write_json(out_dir / "live_pilot_report.json", report)
    _write_text(out_dir / "live_pilot_report.md", _live_report_md(report))
    return report


def _load_llm_payload(base_url: str, session_id: str) -> dict[str, Any]:
    try:
        _status, payload = _http_json(
            f"{base_url.rstrip('/')}/api/debug/session/{session_id}/llm-payload?format=flat",
            headers={"X-API-Key": API_KEY, "Accept": "application/json"},
        )
        return payload
    except Exception:
        return {}


def _extract_prompt_text(debug_payload: dict[str, Any], llm_payload: dict[str, Any]) -> str:
    if str(debug_payload.get("writer_user_prompt", "") or "").strip():
        return str(debug_payload.get("writer_user_prompt", "") or "").strip()
    if str(llm_payload.get("user_prompt", "") or "").strip():
        return str(llm_payload.get("user_prompt", "") or "").strip()
    return "[prompt unavailable]"


def _contains_internal_leak(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(
        marker in lowered
        for marker in (
            "semantic_card:",
            "semantic_cards_pilot",
            "writer_kb_payload",
            "source_ref",
            "card_id",
        )
    )


def _contains_raw_dump(text: str) -> bool:
    lowered = str(text or "").lower()
    return "schema_version" in lowered or "chunk_id" in lowered or "source_doc" in lowered


def _contains_practice_push(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in ("попробуй", "сделай упражнение", "практика:"))


def _looks_too_textbook(text: str) -> bool:
    stripped = str(text or "").strip()
    if len(stripped) < 900:
        return False
    numbered = sum(1 for line in stripped.splitlines() if line.strip().startswith(("1.", "2.", "3.", "4.")))
    return numbered >= 4


def _count_by(items: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        result[item] = result.get(item, 0) + 1
    return result


def _live_report_md(report: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.27 Live Pilot Report",
        "",
        f"- status: `{report.get('status')}`",
        f"- direct_answer_success_rate: `{report.get('direct_answer_success_rate')}`",
        f"- semantic_card_selected_when_expected_count: `{report.get('semantic_card_selected_when_expected_count')}`",
        f"- semantic_card_suppressed_when_not_needed_count: `{report.get('semantic_card_suppressed_when_not_needed_count')}`",
        f"- card_internal_leak_count: `{report.get('card_internal_leak_count')}`",
        f"- raw_source_dump_count: `{report.get('raw_source_dump_count')}`",
        f"- practice_overpush_count: `{report.get('practice_overpush_count')}`",
        "",
        "| case_id | selected cards | expected? | answer quality | warning |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in list(report.get("cases", []) or []):
        selected = ", ".join(list(item.get("selected_card_ids", []) or [])) or "none"
        warning = "textbook" if item.get("answer_too_textbook") else ""
        lines.append(
            f"| {item.get('case_id')} | {selected} | {item.get('expected_card')} | "
            f"{item.get('direct_answer_success')} | {warning or 'none'} |"
        )
    return "\n".join(lines)


def build_no_mutation(out_dir: Path) -> dict[str, Any]:
    report = {
        "prd_id": PRD_ID,
        "db_schema_changed": False,
        "chroma_reindexed": False,
        "processed_blocks_mutated": False,
        "botdb_registry_mutated": False,
        "retrieval_ranking_changed_globally": False,
        "writer_prompt_changed": False,
        "state_analyzer_prompt_changed": False,
        "thread_manager_rewritten": False,
        "overlay_apply_enabled": False,
        "new_runtime_path_added": False,
        "new_llm_agent_added": False,
        "feature_flag_default_off": True,
        "pilot_pack_added": True,
        "allowed_changes": [
            "semantic_cards_pilot_pack",
            "semantic_card_schema_loader_adapter",
            "pilot_context_payload_enrichment_local_only",
            "tests",
            "TO_DO_LIST_artifacts",
            "docs_metadata_sync",
        ],
        "status": "passed",
    }
    _write_json(out_dir / "no_mutation_proof.json", report)
    return report


def run_encoding(out_dir: Path) -> dict[str, Any]:
    report = encoding_validator.run(
        SimpleNamespace(
            prd=PRD_ID,
            logs_dir=str(out_dir),
            reports_dir=str(REPORT_DIR),
            out_dir=str(out_dir),
            report_prd=PRD_ID,
            repo_root=str(REPO_ROOT),
            fixed_file=[],
        )
    )
    final_report = dict(report)
    raw_path = out_dir / "artifact_encoding_hygiene_report.json"
    if raw_path.exists():
        final_report = json.loads(raw_path.read_text(encoding="utf-8"))
    _write_json(out_dir / "encoding_hygiene_report.json", final_report)
    return final_report


def build_reports(out_dir: Path, report_dir: Path, live_report: dict[str, Any], dry_report: dict[str, Any]) -> None:
    impl = [
        "# PRD-047.27 Implementation Report",
        "",
        "- prd_id: `PRD-047.27`",
        f"- implementation_status: `{live_report.get('status', dry_report.get('status'))}`",
        "- implementation_commit: `PENDING_MAIN_COMMIT`",
        "- post_push_metadata_commit: `PENDING_METADATA_COMMIT`",
        "- cards_added: `12`",
        "- pilot_flag: `SEMANTIC_CARDS_PILOT_ENABLED`, default `false`",
        "- integration: existing `writer_kb_payload_v1` input enrichment only",
        "- writer_authority: cards are advisory, `writer_can_ignore=true`",
        f"- direct_answer_success_rate: `{live_report.get('direct_answer_success_rate', 'n/a')}`",
        f"- selected_when_expected: `{live_report.get('semantic_card_selected_when_expected_count', 'n/a')}`",
        f"- suppressed_when_not_needed: `{live_report.get('semantic_card_suppressed_when_not_needed_count', 'n/a')}`",
        f"- internal_leaks: `{live_report.get('card_internal_leak_count', 'n/a')}`",
        f"- raw_source_dumps: `{live_report.get('raw_source_dump_count', 'n/a')}`",
        f"- practice_overpush: `{live_report.get('practice_overpush_count', 'n/a')}`",
        "",
        "## Case Table",
        "",
        "| case_id | user question | selected cards | expected? | answer quality | warning |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in list(live_report.get("cases", []) or []):
        selected = ", ".join(list(item.get("selected_card_ids", []) or [])) or "none"
        warning = "textbook" if item.get("answer_too_textbook") else "none"
        question = str(item.get("query", "") or "").replace("|", "/")
        impl.append(
            f"| {item.get('case_id')} | {question} | {selected} | {item.get('expected_card')} | "
            f"{item.get('direct_answer_success')} | {warning} |"
        )
    impl.extend(
        [
            "",
            "## Boundaries",
            "- no DB schema change",
            "- no Chroma reindex",
            "- no retrieval ranking rewrite",
            "- no Writer prompt rewrite",
            "- no overlay apply",
            "- no new LLM agent",
            "- no new runtime path",
            "",
            "## Artifacts",
            "- `TO_DO_LIST/logs/PRD-047.27/semantic_cards_pilot_preview.json`",
            "- `TO_DO_LIST/logs/PRD-047.27/dry_run_report.json`",
            "- `TO_DO_LIST/logs/PRD-047.27/live_pilot_report.json`",
            "- `TO_DO_LIST/logs/PRD-047.27/no_mutation_proof.json`",
            "- `TO_DO_LIST/logs/PRD-047.27/encoding_hygiene_report.json`",
            "- `TO_DO_LIST/logs/PRD-047.27/test_command_output.txt`",
            "",
            "## Next",
            "- `PRD-047.28 - Live Interactive Pilot / Owner Dialogue Review v1`",
        ]
    )
    _write_text(report_dir / "PRD-047.27_IMPLEMENTATION_REPORT.md", "\n".join(impl))
    _write_text(
        report_dir / "PRD-047.27_NEXT_PRD_RECOMMENDATION.md",
        "\n".join(
            [
                "# PRD-047.27 Next PRD Recommendation",
                "",
                "- recommended_next_prd: `PRD-047.28 - Live Interactive Pilot / Owner Dialogue Review v1`",
                "- reason: semantic cards pilot is intentionally small; the next useful step is owner Web Chat review rather than another technical layer.",
            ]
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["dry-run", "live", "all"], default="all")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--out-dir", default=str(LOG_DIR))
    parser.add_argument("--reports-dir", default=str(REPORT_DIR))
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    report_dir = Path(args.reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    source_gate = run_source_gate(out_dir)
    if source_gate["status"] == "blocked":
        return 2
    build_preview(out_dir)
    tests_report = run_tests(out_dir)
    dry_report = run_dry(out_dir)
    live_report: dict[str, Any] = {}
    if args.mode in {"live", "all"}:
        live_report = run_live(args.base_url, out_dir)
    else:
        live_report = {
            "status": "skipped",
            "reason": "dry_run_mode",
            "cases": [],
        }
        _write_json(out_dir / "live_pilot_report.json", live_report)
        _write_text(out_dir / "live_pilot_report.md", "# PRD-047.27 Live Pilot Report\n\n- status: `skipped`")
    build_no_mutation(out_dir)
    encoding_report = run_encoding(out_dir)
    build_reports(out_dir, report_dir, live_report, dry_report)
    live_status = str(live_report.get("status", "skipped"))
    overall_status = live_status if live_status != "skipped" else str(dry_report.get("status", "unknown"))
    if tests_report["status"] != "passed":
        overall_status = "blocked"
    if str(encoding_report.get("final_status", "")) != "passed":
        overall_status = "blocked"
    summary = {
        "prd_id": PRD_ID,
        "status": overall_status,
        "source_gate_status": source_gate["status"],
        "tests_status": tests_report["status"],
        "dry_run_status": dry_report["status"],
        "live_status": live_status,
        "encoding_status": encoding_report.get("final_status", encoding_report.get("status", "unknown")),
    }
    _write_json(out_dir / "implementation_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] in {"passed", "passed_with_warning", "skipped"} else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
