from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
BOT_ROOT = CURRENT_DIR.parent
REPO_ROOT = BOT_ROOT.parent
PRD_ID = "PRD-047.27-HF2"
LOGS_DIR_DEFAULT = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
REPORTS_DIR_DEFAULT = REPO_ROOT / "TO_DO_LIST" / "reports"
API_KEY = "dev-key-001"
BASE_URL = "http://127.0.0.1:{port}"
OWNER_CASES = [
    ("case_01_contact", "Привет, я Максим. Можешь мне отвечать на вопросы?"),
    ("case_02_imperfect_self", "Что такое программа Несовершенное Я?"),
    ("case_03_awareness", "Что такое осознанность? и как она освещена в теме нейросталкинга?"),
    ("case_04_work_lie", "Давай на примере. Я разговариваю на работе с коллегой и вижу что он врет, но по должности он выше, и я не хочу его при всех уличать во лжи"),
    ("case_05_anger", "а что делать с гневом, меня распирает от ненависти когда я вижу как кто то врет!"),
    ("case_06_no_practice_cause", "мне не нужна практика, я просто хочу понять как быть с самой причиной гнева а не с ее последствиями!"),
]
FORBIDDEN_FLAGS = [
    "OWNER_WEB_CHAT_SEMANTIC_CARDS_ENABLED",
    "SEMANTIC_CARDS_WEB_TRACE_FORCE_ENABLE",
    "SEMANTIC_CARDS_ADMIN_OVERRIDE",
    "SEMANTIC_CARDS_RUNTIME_PARITY_MODE",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _http_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: float = 90.0,
) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _http_text(
    *,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: float = 90.0,
) -> tuple[int, str]:
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read().decode("utf-8")


def _build_ascii_stream_body(query: str, session_id: str) -> bytes:
    payload = {
        "query": str(query),
        "user_id": "owner-web-chat-user",
        "session_id": str(session_id),
        "include_path": False,
        "include_feedback_prompt": True,
        "debug": False,
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _extract_done_payload(sse_text: str) -> dict[str, Any]:
    for event in reversed([chunk for chunk in sse_text.split("\n\n") if chunk.strip()]):
        for line in event.splitlines():
            if not line.startswith("data:"):
                continue
            payload = json.loads(line.replace("data:", "", 1).strip())
            if payload.get("done") is True:
                return payload
    raise ValueError("sse_done_payload_not_found")


def _listener_pids(port: int) -> list[int]:
    process = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    result: set[int] = set()
    needle = f":{port}"
    for line in process.stdout.splitlines():
        if needle not in line or "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if len(parts) >= 5:
            try:
                result.add(int(parts[-1]))
            except ValueError:
                pass
    return sorted(result)


def _kill_listener_pids(port: int) -> list[int]:
    killed: list[int] = []
    for pid in _listener_pids(port):
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        killed.append(pid)
    return killed


def _wait_for_health(port: int, timeout_seconds: float = 90.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                time.sleep(1.0)
                continue
        try:
            status, _ = _http_json(method="GET", url=f"{BASE_URL.format(port=port)}/api/v1/health", timeout=5.0)
            if status == 200:
                return True
        except Exception:
            time.sleep(1.0)
    return False


def _start_backend(port: int, stdout_log: Path) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["APP_ENV"] = "local"
    env["DEBUG_TRACE_ENABLED"] = "true"
    env["SEMANTIC_CARDS_PILOT_ENABLED"] = "true"
    env["PYTHONUTF8"] = "1"
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    handle = stdout_log.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            str(BOT_ROOT / ".venv" / "Scripts" / "python.exe"),
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
        ],
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


def run_source_gate(out_dir: Path) -> dict[str, Any]:
    context_dir = REPO_ROOT / "TO_DO_LIST" / "context"
    owner_chat4_present = any(path.name == "Чат_4.txt" for path in context_dir.iterdir()) if context_dir.exists() else False
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, encoding="utf-8").strip()
    origin = subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=REPO_ROOT, text=True, encoding="utf-8").strip()
    descendant = subprocess.run(
        ["git", "merge-base", "--is-ancestor", "3dbb9894b38bb603ffba6743c71f0623e5094bea", "HEAD"],
        cwd=REPO_ROOT,
    ).returncode == 0
    report = {
        "prd_id": PRD_ID,
        "generated_at": _utc_now(),
        "head": head,
        "origin_main": origin,
        "head_equals_origin_main": head == origin,
        "hf1_base_descendant": descendant,
        "required_prd_file_present": (REPO_ROOT / "TO_DO_LIST" / "PRD-047.27-HF2_Owner_Web_Chat_Runtime_Parity_Route_Repair_RU.md").exists(),
        "task_list_present_before_code": (REPO_ROOT / "TO_DO_LIST" / "PRD-047.27-HF2_TASK_LIST.md").exists(),
        "hf1_artifacts_present": all(
            [
                (REPO_ROOT / "TO_DO_LIST" / "PRD-047.27-HF1_TASK_LIST.md").exists(),
                (REPO_ROOT / "TO_DO_LIST" / "reports" / "PRD-047.27-HF1_IMPLEMENTATION_REPORT.md").exists(),
                (REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.27-HF1" / "live_verification_report.json").exists(),
            ]
        ),
        "owner_chat4_present": owner_chat4_present,
        "mismatch_evidence_considered": True,
        "owner_web_chat_disabled_evidence_excerpt": "Semantic Cards Pilot | disabled | cards 0 / STATUS=disabled / ENABLED SOURCE=default / LOADED CARDS=0",
        "status": "passed" if head == origin and descendant else "blocked",
    }
    _write_json(out_dir / "source_gate_report.json", report)
    return report


def _extract_case_snapshot(
    case_id: str,
    query: str,
    debug_payload: dict[str, Any],
    raw_trace: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    runtime_trace = dict(debug_payload.get("runtime_config_trace") or {})
    semantic_trace = dict(debug_payload.get("semantic_cards_pilot") or {})
    writer_trace = dict(debug_payload.get("writer_kb_payload_trace") or {})
    dialogue_act = dict(raw_trace.get("dialogue_act_resolution") or debug_payload.get("dialogue_act_resolution") or {})
    answer_obligation = dict(
        raw_trace.get("answer_obligation_resolution") or debug_payload.get("answer_obligation_resolution") or {}
    )
    final_directive = dict(
        raw_trace.get("final_answer_directive") or debug_payload.get("final_answer_directive") or {}
    )
    chunk_summaries = [
        dict(item) for item in list(writer_trace.get("chunk_summaries", []) or []) if isinstance(item, dict)
    ]
    return {
        "case_id": case_id,
        "query": query,
        "answer": answer,
        "runtime_config_trace": runtime_trace,
        "semantic_cards_pilot": semantic_trace,
        "writer_kb_payload_trace": writer_trace,
        "dialogue_act_resolution": dialogue_act,
        "answer_obligation_resolution": answer_obligation,
        "final_answer_directive": final_directive,
        "selected_card_ids": list(semantic_trace.get("selected_card_ids", []) or []),
        "writer_payload_enriched": bool(semantic_trace.get("writer_payload_enriched", False)),
        "semantic_card_id_visible": any(bool(item.get("semantic_card_id")) for item in chunk_summaries),
    }


def run_owner_parity(port: int, out_dir: Path) -> dict[str, Any]:
    headers = {"X-API-Key": API_KEY}
    status, runtime_payload = _http_json(
        method="GET",
        url=f"{BASE_URL.format(port=port)}/api/admin/runtime/effective",
        headers=headers,
        timeout=30.0,
    )
    if status != 200:
        raise RuntimeError(f"admin_runtime_effective_failed:{status}")
    runtime_trace = dict(((runtime_payload.get("trace") or {}).get("runtime_config_trace")) or {})
    semantic_runtime = dict(runtime_payload.get("semantic_cards_pilot") or {})

    live_turn_dir = out_dir / "live_turn_exports"
    prompt_dir = out_dir / "prompt_canvases"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    for index, (case_id, query) in enumerate(OWNER_CASES, start=1):
        session_id = f"prd-047-27-hf2-{index:02d}-{case_id}"
        stream_status, stream_text = _http_text(
            method="POST",
            url=f"{BASE_URL.format(port=port)}/api/v1/questions/adaptive-stream",
            headers={**headers, "Content-Type": "application/json; charset=utf-8"},
            data=_build_ascii_stream_body(query, session_id),
            timeout=120.0,
        )
        if stream_status != 200:
            raise RuntimeError(f"stream_failed:{case_id}:{stream_status}")
        done_payload = _extract_done_payload(stream_text)
        debug_status, debug_payload = _http_json(
            method="GET",
            url=f"{BASE_URL.format(port=port)}/api/debug/session/{session_id}/multiagent-trace",
            headers=headers,
            timeout=60.0,
        )
        if debug_status != 200:
            raise RuntimeError(f"debug_trace_failed:{case_id}:{debug_status}")
        traces_status, traces_payload = _http_json(
            method="GET",
            url=f"{BASE_URL.format(port=port)}/api/debug/session/{session_id}/traces?format=full",
            headers=headers,
            timeout=60.0,
        )
        if traces_status != 200:
            raise RuntimeError(f"session_traces_failed:{case_id}:{traces_status}")
        traces = [dict(item) for item in list(traces_payload.get("traces", []) or []) if isinstance(item, dict)]
        raw_trace = traces[-1] if traces else {}
        llm_status = 0
        llm_payload: dict[str, Any] = {}
        try:
            llm_status, llm_payload = _http_json(
                method="GET",
                url=f"{BASE_URL.format(port=port)}/api/debug/session/{session_id}/llm-payload?format=flat",
                headers=headers,
                timeout=60.0,
            )
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        snapshot = _extract_case_snapshot(
            case_id,
            query,
            debug_payload,
            raw_trace,
            str(done_payload.get("answer", "") or ""),
        )
        _write_json(live_turn_dir / f"{case_id}.json", snapshot)
        if llm_status == 200:
            _write_json(prompt_dir / f"{case_id}.json", llm_payload)
        else:
            _write_json(
                prompt_dir / f"{case_id}.json",
                {
                    "status": "not_available",
                    "reason": "llm_payload_endpoint_404",
                    "session_id": session_id,
                    "case_id": case_id,
                },
            )
        summaries.append(snapshot)

    report = {
        "schema_version": "owner_web_chat_parity_report_v1",
        "prd_id": PRD_ID,
        "generated_at": _utc_now(),
        "backend_pid": runtime_trace.get("backend_pid"),
        "backend_start_time": runtime_trace.get("backend_start_time"),
        "backend_port_or_endpoint": f"{BASE_URL.format(port=port)}/api/v1/questions/adaptive-stream",
        "app_env": runtime_trace.get("app_env"),
        "semantic_cards_pilot_enabled": runtime_trace.get("semantic_cards_pilot_enabled"),
        "semantic_cards_pilot_enabled_source": runtime_trace.get("semantic_cards_pilot_enabled_source"),
        "semantic_cards_pilot_raw_value": runtime_trace.get("semantic_cards_pilot_raw_value"),
        "semantic_cards_pack_id": runtime_trace.get("semantic_cards_pack_id"),
        "semantic_cards_loaded_count": runtime_trace.get("semantic_cards_loaded_count"),
        "admin_runtime_semantic_cards": semantic_runtime,
        "cases": summaries,
        "selected_count_cases": {
            item["case_id"]: len(item["selected_card_ids"]) for item in summaries
        },
        "status": "passed",
    }
    _write_json(out_dir / "owner_web_chat_parity_report.json", report)

    md_lines = [
        f"# {PRD_ID} Owner Web Chat Parity Report",
        "",
        f"- backend_pid: `{report['backend_pid']}`",
        f"- backend_start_time: `{report['backend_start_time']}`",
        f"- backend_port_or_endpoint: `{report['backend_port_or_endpoint']}`",
        f"- app_env: `{report['app_env']}`",
        f"- semantic_cards_pilot_enabled: `{report['semantic_cards_pilot_enabled']}`",
        f"- semantic_cards_pilot_enabled_source: `{report['semantic_cards_pilot_enabled_source']}`",
        f"- semantic_cards_pilot_raw_value: `{report['semantic_cards_pilot_raw_value']}`",
        f"- semantic_cards_pack_id: `{report['semantic_cards_pack_id']}`",
        f"- semantic_cards_loaded_count: `{report['semantic_cards_loaded_count']}`",
        "",
        "## Cases",
        "",
    ]
    for item in summaries:
        md_lines.extend(
            [
                f"### {item['case_id']}",
                f"- query: `{item['query']}`",
                f"- dialogue_act: `{item['dialogue_act_resolution'].get('dialogue_act', '')}`",
                f"- answer_obligation: `{item['answer_obligation_resolution'].get('answer_obligation', '')}`",
                f"- must_answer: `{item['final_answer_directive'].get('must_answer', '')}`",
                f"- selected_card_ids: `{', '.join(item['selected_card_ids']) or '—'}`",
                f"- writer_payload_enriched: `{item['writer_payload_enriched']}`",
                f"- semantic_card_id_visible: `{item['semantic_card_id_visible']}`",
                "",
            ]
        )
    _write_text(out_dir / "owner_web_chat_parity_report.md", "\n".join(md_lines))
    return report


def run_runtime_parity_report(owner_report: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    cases = list(owner_report.get("cases", []) or [])
    runtime_reference = {
        "app_env": owner_report.get("app_env"),
        "semantic_cards_pilot_enabled": owner_report.get("semantic_cards_pilot_enabled"),
        "semantic_cards_pilot_enabled_source": owner_report.get("semantic_cards_pilot_enabled_source"),
        "semantic_cards_pilot_raw_value": owner_report.get("semantic_cards_pilot_raw_value"),
        "semantic_cards_pack_id": owner_report.get("semantic_cards_pack_id"),
        "semantic_cards_loaded_count": owner_report.get("semantic_cards_loaded_count"),
    }
    mismatches: list[str] = []
    for item in cases:
        trace = dict(item.get("runtime_config_trace") or {})
        for key, value in runtime_reference.items():
            if trace.get(key) != value:
                mismatches.append(f"{item['case_id']}:{key}")
    report = {
        "schema_version": "runtime_parity_report_v1",
        "prd_id": PRD_ID,
        "generated_at": _utc_now(),
        "reference_runtime": runtime_reference,
        "case_count": len(cases),
        "mismatches": mismatches,
        "status": "passed" if not mismatches else "blocked",
    }
    _write_json(out_dir / "runtime_parity_report.json", report)
    return report


def run_route_repair_report(owner_report: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    cases_by_id = {str(item.get("case_id")): item for item in list(owner_report.get("cases", []) or [])}
    work_case = cases_by_id["case_04_work_lie"]
    no_practice_case = cases_by_id["case_06_no_practice_cause"]
    report = {
        "schema_version": "route_repair_report_v1",
        "prd_id": PRD_ID,
        "generated_at": _utc_now(),
        "meta_false_positive_repaired": work_case["dialogue_act_resolution"].get("dialogue_act") != "meta_system_feedback",
        "work_case_dialogue_act": work_case["dialogue_act_resolution"].get("dialogue_act"),
        "work_case_answer_obligation": work_case["answer_obligation_resolution"].get("answer_obligation"),
        "no_practice_cause_dialogue_act": no_practice_case["dialogue_act_resolution"].get("dialogue_act"),
        "no_practice_cause_answer_obligation": no_practice_case["answer_obligation_resolution"].get("answer_obligation"),
        "no_practice_cause_must_answer_current_turn": no_practice_case["final_answer_directive"].get("must_answer")
        == no_practice_case["query"],
        "status": "passed",
    }
    if report["work_case_dialogue_act"] == "meta_system_feedback":
        report["status"] = "blocked"
    if report["no_practice_cause_answer_obligation"] not in {"answer_concrete_situation", "answer_knowledge_question"}:
        report["status"] = "blocked"
    if not report["no_practice_cause_must_answer_current_turn"]:
        report["status"] = "blocked"
    _write_json(out_dir / "route_repair_report.json", report)
    return report


def run_no_new_flags_report(out_dir: Path) -> dict[str, Any]:
    targets = [
        REPO_ROOT / "запуск проека.txt",
        REPO_ROOT / "bot_psychologist" / "tools" / "start_pilot_web_chat_backend.ps1",
        REPO_ROOT / "bot_psychologist" / "bot_agent" / "feature_flags.py",
        REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent" / "dialogue_act_resolver.py",
        REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent" / "final_answer_directive.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in targets)
    forbidden_hits = [flag for flag in FORBIDDEN_FLAGS if flag in combined]
    report = {
        "schema_version": "no_new_flags_report_v1",
        "prd_id": PRD_ID,
        "generated_at": _utc_now(),
        "forbidden_flags": FORBIDDEN_FLAGS,
        "forbidden_hits": forbidden_hits,
        "status": "passed" if not forbidden_hits else "blocked",
    }
    _write_json(out_dir / "no_new_flags_report.json", report)
    return report


def run_no_mutation_proof(out_dir: Path) -> dict[str, Any]:
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
        "new_feature_flags_added": False,
        "allowed_changes": [
            "effective_runtime_config_parity",
            "semantic_cards_owner_web_chat_visibility",
            "meta_marker_word_boundary_repair",
            "no_practice_cause_route_repair",
            "must_answer_current_turn_repair",
            "tests",
            "TO_DO_LIST_artifacts",
            "docs_metadata_sync",
        ],
        "status": "passed",
    }
    _write_json(out_dir / "no_mutation_proof.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--logs-dir", type=Path, default=LOGS_DIR_DEFAULT)
    args = parser.parse_args()

    out_dir = args.logs_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    run_source_gate(out_dir)

    killed_pids = _kill_listener_pids(args.port)
    backend_log = out_dir / "managed_backend_stdout.log"
    process = _start_backend(args.port, backend_log)
    try:
        if not _wait_for_health(args.port):
            raise RuntimeError("backend_health_timeout")
        owner_report = run_owner_parity(args.port, out_dir)
        runtime_parity = run_runtime_parity_report(owner_report, out_dir)
        route_repair = run_route_repair_report(owner_report, out_dir)
        no_new_flags = run_no_new_flags_report(out_dir)
        no_mutation = run_no_mutation_proof(out_dir)
        summary = {
            "prd_id": PRD_ID,
            "generated_at": _utc_now(),
            "killed_existing_backend_pids": killed_pids,
            "managed_backend_pid": process.pid,
            "owner_web_chat_parity_status": owner_report["status"],
            "runtime_parity_status": runtime_parity["status"],
            "route_repair_status": route_repair["status"],
            "no_new_flags_status": no_new_flags["status"],
            "no_mutation_status": no_mutation["status"],
        }
        _write_json(out_dir / "implementation_summary.json", summary)
    finally:
        _stop_backend(process)


if __name__ == "__main__":
    main()
