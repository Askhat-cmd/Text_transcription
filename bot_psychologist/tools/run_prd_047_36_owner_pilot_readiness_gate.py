from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.config import config
from bot_agent.storage.session_manager import SessionManager

from tools.prd_047_36_owner_pilot_readiness_gate_lib import (
    build_delivery_spot_check,
    build_payload_excerpt_integrity_records,
    build_scenarios,
    build_trace_consistency_check,
    evaluate_scenario,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.36"
LIVE_EXPORTS_DIR = OUT_DIR / "live_turn_exports"
PROMPT_DIR = OUT_DIR / "prompt_canvases"
DEV_HEADERS = {
    "X-API-Key": "dev-key-001",
    "X-Device-Fingerprint": "prd-047-36-readiness-gate",
    "Content-Type": "application/json; charset=utf-8",
}


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_preview(text: str, *, max_len: int = 240) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3].rstrip() + "..."


def _extract_acceptance_gate(latest_trace: dict[str, Any]) -> dict[str, Any]:
    direct = _safe_dict(latest_trace.get("final_answer_acceptance_gate"))
    if direct:
        return direct
    live_turn = _safe_dict(latest_trace.get("live_turn_evidence"))
    writer = _safe_dict(live_turn.get("writer"))
    return _safe_dict(writer.get("final_answer_acceptance_gate"))


def _http_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: float = 90.0,
) -> tuple[int, dict[str, Any]]:
    response = httpx.request(method, url, headers=headers, json=payload, timeout=timeout)
    try:
        body = response.json()
    except json.JSONDecodeError:
        body = {"raw": response.text}
    return response.status_code, body if isinstance(body, dict) else {"raw": body}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _export_live_turns(*, scenario_id: str, traces_payload: dict[str, Any]) -> list[str]:
    saved: list[str] = []
    traces = _safe_list(traces_payload.get("traces"))
    case_dir = LIVE_EXPORTS_DIR / scenario_id
    case_dir.mkdir(parents=True, exist_ok=True)
    for index, trace in enumerate(traces, start=1):
        if not isinstance(trace, dict):
            continue
        payload = {
            "turn_number": trace.get("turn_number"),
            "live_turn_evidence": _safe_dict(trace.get("live_turn_evidence")),
            "retrieval_decision": _safe_dict(trace.get("retrieval_decision")),
            "runtime_truth_trace_v1": _safe_dict(trace.get("runtime_truth_trace_v1")),
        }
        out = case_dir / f"turn_{index:02d}.json"
        _write_json(out, payload)
        saved.append(str(out))
    return saved


def _save_prompt_canvases(*, scenario_id: str, latest_trace: dict[str, Any]) -> list[str]:
    saved: list[str] = []
    writer_llm = _safe_dict(latest_trace.get("writer_llm"))
    if writer_llm.get("system_prompt"):
        system_path = PROMPT_DIR / f"{scenario_id}_system_prompt.txt"
        _write_text(system_path, str(writer_llm.get("system_prompt", "")))
        saved.append(str(system_path))
    if writer_llm.get("user_prompt"):
        user_path = PROMPT_DIR / f"{scenario_id}_user_prompt.txt"
        _write_text(user_path, str(writer_llm.get("user_prompt", "")))
        saved.append(str(user_path))
    return saved


def _load_memory_answer(session_id: str) -> str:
    manager = SessionManager(str(config.BOT_DB_PATH))
    for _ in range(10):
        payload = manager.load_session(session_id)
        if isinstance(payload, dict):
            turns = _safe_list(payload.get("conversation_turns"))
            if turns:
                last = turns[-1]
                if isinstance(last, dict) and str(last.get("bot_response", "") or "").strip():
                    return str(last.get("bot_response", "") or "")
        time.sleep(0.5)
    return ""


def _build_scenario_matrix(results: list[dict[str, Any]], verdict: str) -> str:
    lines = [
        "# PRD-047.36 Scenario Matrix",
        "",
        f"- overall_verdict: `{verdict}`",
        "",
        "| Scenario | Status | Tags | Answer Preview |",
        "| --- | --- | --- | --- |",
    ]
    for item in results:
        lines.append(
            "| {scenario_id} | {status} | {tags} | {preview} |".format(
                scenario_id=item["scenario_id"],
                status=item["status"],
                tags=", ".join(item.get("tags", [])) or "none",
                preview=_safe_preview(item.get("answer", ""), max_len=120).replace("|", "/"),
            )
        )
    return "\n".join(lines) + "\n"


def _build_payload_report(results: list[dict[str, Any]]) -> str:
    lines = ["# PRD-047.36 Payload Excerpt Integrity", ""]
    for item in results:
        lines.append(f"## {item['scenario_id']}")
        records = _safe_list(item.get("payload_excerpt_integrity_records"))
        if not records:
            lines.append("- no payload chunks inspected")
            lines.append("")
            continue
        for record in records:
            payload = _safe_dict(record.get("payload_excerpt_integrity_v1"))
            lines.extend(
                [
                    f"- chunk_id: `{payload.get('chunk_id', '')}`",
                    f"- content_truncated: `{bool(payload.get('content_truncated', False))}`",
                    f"- matched_span_in_excerpt: `{payload.get('matched_span_in_excerpt')}`",
                    f"- key_definition_in_excerpt: `{payload.get('key_definition_in_excerpt')}`",
                    f"- blocker: `{bool(payload.get('blocker', False))}`",
                ]
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def _build_delivery_report(results: list[dict[str, Any]]) -> str:
    lines = ["# PRD-047.36 Final Answer Delivery Spot Check", ""]
    for item in results:
        delivery = _safe_dict(item.get("delivery_spot_check", {})).get("delivery_spot_check_v1", {})
        delivery = _safe_dict(delivery)
        lines.extend(
            [
                f"## {item['scenario_id']}",
                f"- strict_raw_compare: `{delivery.get('strict_raw_compare')}`",
                f"- writer_raw_vs_api_match: `{delivery.get('writer_raw_vs_api_match')}`",
                f"- api_vs_memory_match: `{delivery.get('api_vs_memory_match')}`",
                f"- visible_chat_accessible: `{delivery.get('visible_chat_accessible')}`",
                f"- visible_chat_vs_api_match: `{delivery.get('visible_chat_vs_api_match')}`",
                f"- acceptance_gate_status: `{delivery.get('acceptance_gate_status')}`",
                f"- must_quarantine_answer: `{delivery.get('must_quarantine_answer')}`",
                f"- quarantine_reason: `{delivery.get('quarantine_reason')}`",
                f"- quarantine_explains_memory_gap: `{delivery.get('quarantine_explains_memory_gap')}`",
                f"- blocker: `{delivery.get('blocker')}`",
                f"- blocker_reasons: `{', '.join(delivery.get('blocker_reasons', [])) or 'none'}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def _build_trace_report(results: list[dict[str, Any]]) -> str:
    lines = ["# PRD-047.36 Trace Consistency Report", ""]
    for item in results:
        trace_check = _safe_dict(item.get("trace_consistency", {})).get("trace_consistency_v1", {})
        trace_check = _safe_dict(trace_check)
        source_trace = _safe_dict(item.get("source_trace"))
        lines.extend(
            [
                f"## {item['scenario_id']}",
                f"- loss_stage: `{source_trace.get('loss_stage', 'missing')}`",
                f"- loss_reason: `{source_trace.get('loss_reason', '')}`",
                f"- trace_status: `{trace_check.get('status', 'missing')}`",
                f"- warning: `{trace_check.get('warning', '')}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def run_gate(
    *,
    backend_base_url: str,
    frontend_base_url: str,
) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LIVE_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)

    health_status, health_payload = _http_json(
        method="GET",
        url=f"{backend_base_url.rstrip('/')}/api/v1/health",
        headers={"X-API-Key": DEV_HEADERS["X-API-Key"]},
        timeout=30.0,
    )
    frontend_status = 0
    try:
        frontend_response = httpx.get(frontend_base_url.rstrip("/"), timeout=15.0)
        frontend_status = frontend_response.status_code
    except Exception:
        frontend_status = 0

    results: list[dict[str, Any]] = []
    blocker_tags: list[str] = []
    warning_tags: list[str] = []

    for scenario in build_scenarios():
        session_id = f"prd-047-36-{scenario.scenario_id.lower()}-{uuid4().hex[:8]}"
        turn_answers: list[str] = []
        last_payload: dict[str, Any] = {}
        for turn in scenario.turns:
            status_code, payload = _http_json(
                method="POST",
                url=f"{backend_base_url.rstrip('/')}/api/v1/questions/adaptive",
                headers={**DEV_HEADERS, "X-Session-Id": session_id},
                payload={
                    "query": turn,
                    "session_id": session_id,
                    "debug": True,
                    "include_path": False,
                    "include_feedback_prompt": True,
                },
                timeout=120.0,
            )
            if status_code != 200:
                last_payload = {"status_code": status_code, "payload": payload}
                break
            last_payload = payload
            turn_answers.append(str(payload.get("answer", "") or ""))

        traces_status, traces_payload = _http_json(
            method="GET",
            url=f"{backend_base_url.rstrip('/')}/api/debug/session/{urllib.parse.quote(session_id, safe='')}/traces?format=full",
            headers={"X-API-Key": DEV_HEADERS["X-API-Key"]},
            timeout=60.0,
        )
        latest_status, latest_trace = _http_json(
            method="GET",
            url=f"{backend_base_url.rstrip('/')}/api/debug/session/{urllib.parse.quote(session_id, safe='')}/multiagent-trace",
            headers={"X-API-Key": DEV_HEADERS["X-API-Key"]},
            timeout=60.0,
        )

        exported_files = _export_live_turns(scenario_id=scenario.scenario_id, traces_payload=traces_payload) if traces_status == 200 else []
        prompt_files = _save_prompt_canvases(scenario_id=scenario.scenario_id, latest_trace=latest_trace) if latest_status == 200 else []

        runtime_truth_trace = _safe_dict(latest_trace.get("runtime_truth_trace_v1"))
        writer_grounding_visibility = _safe_dict(latest_trace.get("writer_grounding_visibility_v1"))
        source_trace = _safe_dict(runtime_truth_trace.get("source_chunk_match_trace_v1"))
        live_turn_evidence = _safe_dict(latest_trace.get("live_turn_evidence"))
        writer_context_package = _safe_dict(
            _safe_dict(_safe_dict(live_turn_evidence.get("writer")).get("prompt_assembly")).get("writer_context_package")
        )
        writer_kb_payload = _safe_dict(writer_context_package.get("writer_kb_payload"))
        payload_chunks = [
            dict(item)
            for item in _safe_list(writer_kb_payload.get("chunks"))
            if isinstance(item, dict)
        ]
        payload_records = build_payload_excerpt_integrity_records(
            scenario_id=scenario.scenario_id,
            user_message=scenario.turns[-1],
            payload_chunks=payload_chunks,
            source_trace=source_trace,
        )
        api_answer = str(last_payload.get("answer", "") or "")
        writer_raw_answer = str(_safe_dict(latest_trace.get("writer_llm")).get("llm_response_raw", "") or "")
        writer_section = _safe_dict(live_turn_evidence.get("writer"))
        writer_answer_value = writer_section.get("answer")
        writer_final_answer = (
            str(_safe_dict(writer_answer_value).get("text", "") or "")
            if isinstance(writer_answer_value, dict)
            else str(writer_answer_value or "")
        ) or api_answer
        memory_answer = _load_memory_answer(session_id)
        acceptance_gate = _extract_acceptance_gate(latest_trace)
        validator = _safe_dict(latest_trace.get("validator"))
        delivery = build_delivery_spot_check(
            writer_raw_answer=writer_final_answer,
            api_answer=api_answer,
            memory_answer=memory_answer,
            visible_chat_answer=None,
            validator_blocked=bool(validator.get("is_blocked", False)),
            acceptance_retry_attempted=bool(latest_trace.get("final_answer_acceptance_retry_attempted", False)),
            acceptance_gate_status=str(acceptance_gate.get("status", "") or ""),
            must_quarantine_answer=bool(acceptance_gate.get("must_quarantine_answer", False)),
            quarantine_reason=str(acceptance_gate.get("quarantine_reason", "") or ""),
        )
        trace_consistency = build_trace_consistency_check(source_trace)
        scenario_eval = evaluate_scenario(
            scenario=scenario,
            answer=api_answer,
            runtime_truth_trace=runtime_truth_trace,
            writer_grounding_visibility=writer_grounding_visibility,
            source_trace=source_trace,
        )

        if any(
            bool(_safe_dict(record.get("payload_excerpt_integrity_v1")).get("blocker", False))
            for record in payload_records
        ):
            scenario_eval = dict(scenario_eval)
            scenario_eval["status"] = "BLOCKER"
            scenario_eval.setdefault("tags", []).append("payload_excerpt_lost_match")
        if bool(_safe_dict(delivery.get("delivery_spot_check_v1")).get("blocker", False)):
            scenario_eval = dict(scenario_eval)
            scenario_eval["status"] = "BLOCKER"
            scenario_eval.setdefault("tags", []).append("delivery_integrity_mismatch")
        if str(_safe_dict(trace_consistency.get("trace_consistency_v1")).get("status", "")) == "warning":
            if scenario_eval.get("status") == "PASS":
                scenario_eval = dict(scenario_eval)
                scenario_eval["status"] = "PASS_WITH_WARNING"
            scenario_eval.setdefault("tags", []).append("trace_consistency_warning")

        status = str(scenario_eval.get("status", "INCONCLUSIVE"))
        tags = [str(item) for item in list(scenario_eval.get("tags", [])) if str(item).strip()]
        if status == "BLOCKER":
            blocker_tags.extend(tags)
        elif status == "PASS_WITH_WARNING":
            warning_tags.extend(tags)

        results.append(
            {
                "scenario_id": scenario.scenario_id,
                "title": scenario.title,
                "session_id": session_id,
                "status": status,
                "tags": tags,
                "notes": list(scenario_eval.get("notes", [])),
                "turns": list(scenario.turns),
                "answer": api_answer,
                "answers_by_turn": turn_answers,
                "writer_final_answer": writer_final_answer,
                "writer_raw_answer": writer_raw_answer,
                "memory_answer": memory_answer,
                "runtime_truth_trace": runtime_truth_trace,
                "writer_grounding_visibility": writer_grounding_visibility,
                "source_trace": source_trace,
                "writer_kb_payload_trace": _safe_dict(latest_trace.get("writer_kb_payload_trace")),
                "payload_excerpt_integrity_records": payload_records,
                "delivery_spot_check": delivery,
                "trace_consistency": trace_consistency,
                "trace_endpoint_status": latest_status,
                "traces_endpoint_status": traces_status,
                "health_context": {
                    "backend_health_status": health_status,
                    "frontend_status": frontend_status,
                    "acceptance_gate_status": acceptance_gate.get("status"),
                },
                "exported_files": exported_files,
                "prompt_files": prompt_files,
            }
        )

    if any(item["status"] == "BLOCKER" for item in results):
        verdict = "BLOCKER"
    elif any(item["status"] == "PASS_WITH_WARNING" for item in results):
        verdict = "ACCEPTED_WITH_WARNING"
    elif all(item["status"] == "PASS" for item in results):
        verdict = "ACCEPTED"
    else:
        verdict = "ACCEPTED_WITH_WARNING"

    scenario_results = {
        "schema_version": "prd_047_36_owner_pilot_readiness_gate_v1",
        "overall_verdict": verdict,
        "backend_health_status": health_status,
        "backend_health_payload": health_payload,
        "frontend_status": frontend_status,
        "scenarios": results,
    }
    _write_json(OUT_DIR / "scenario_results.json", scenario_results)
    _write_text(OUT_DIR / "scenario_matrix.md", _build_scenario_matrix(results, verdict))
    _write_text(OUT_DIR / "payload_excerpt_integrity_report.md", _build_payload_report(results))
    _write_text(OUT_DIR / "final_answer_delivery_spot_check.md", _build_delivery_report(results))
    _write_text(OUT_DIR / "trace_consistency_report.md", _build_trace_report(results))

    live_lines = [
        "# PRD-047.36 Live Owner Readiness Report",
        "",
        f"- overall_verdict: `{verdict}`",
        f"- backend_health_status: `{health_status}`",
        f"- frontend_status: `{frontend_status}`",
        f"- scenarios_total: `{len(results)}`",
        f"- blocker_tags: `{', '.join(sorted(set(blocker_tags))) or 'none'}`",
        f"- warning_tags: `{', '.join(sorted(set(warning_tags))) or 'none'}`",
        "",
    ]
    for item in results:
        live_lines.extend(
            [
                f"## {item['scenario_id']} — {item['title']}",
                f"- status: `{item['status']}`",
                f"- tags: `{', '.join(item.get('tags', [])) or 'none'}`",
                f"- answer_preview: `{_safe_preview(item.get('answer', ''))}`",
                "",
            ]
        )
    _write_text(OUT_DIR / "live_owner_readiness_report.md", "\n".join(live_lines) + "\n")
    return scenario_results


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--frontend-base-url", default="http://127.0.0.1:3000")
    args = parser.parse_args()
    result = run_gate(
        backend_base_url=str(args.backend_base_url),
        frontend_base_url=str(args.frontend_base_url),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
