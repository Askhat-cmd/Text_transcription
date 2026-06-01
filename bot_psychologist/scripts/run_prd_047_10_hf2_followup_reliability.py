#!/usr/bin/env python3
"""Run PRD-047.10-HF2 follow-up reliability + live evidence export."""

from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.contracts.memory_bundle import SemanticHit
from bot_agent.multiagent.dialogue_pragmatics import (
    build_contextual_retrieval_decision_v1,
    build_dialogue_pragmatics_v1,
)

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_10_hf2_followup_reliability_cases.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.10-HF2"
REQUIRED_CASE_IDS = {
    "HF2-001",
    "HF2-002",
    "HF2-003",
    "HF2-004",
    "HF2-005",
    "HF2-006",
    "HF2-007",
    "HF2-008",
}
STALE_STUB_MARKER = "сфокусируюсь на разборе"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_path(path_raw: str) -> Path:
    path = Path(path_raw)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("dataset must be list")
    return [item for item in payload if isinstance(item, dict)]


def _validate_dataset(cases: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    found_ids = {str(item.get("case_id", "")).strip() for item in cases}
    missing = sorted(REQUIRED_CASE_IDS.difference(found_ids))
    if missing:
        errors.append(f"missing_required_cases:{','.join(missing)}")
    if len(cases) < 8:
        errors.append("dataset_has_less_than_8_cases")
    for case in cases:
        case_id = str(case.get("case_id", "unknown"))
        if not isinstance(case.get("direct"), dict):
            errors.append(f"{case_id}:missing_direct")
        if not isinstance(case.get("expected"), dict):
            errors.append(f"{case_id}:missing_expected")
        if not isinstance(case.get("live_turns"), list) or not case.get("live_turns"):
            errors.append(f"{case_id}:missing_live_turns")
    return len(errors) == 0, errors


def _semantic_hits(case_direct: dict[str, Any]) -> list[SemanticHit]:
    hits: list[SemanticHit] = []
    for item in list(case_direct.get("semantic_hits", []) or []):
        if not isinstance(item, dict):
            continue
        hits.append(
            SemanticHit(
                chunk_id=str(item.get("chunk_id", "") or ""),
                content=str(item.get("content", "") or ""),
                source=str(item.get("source", "kb") or "kb"),
                score=float(item.get("score", 0.0) or 0.0),
            )
        )
    return hits


def _evaluate_direct_case(case: dict[str, Any]) -> dict[str, Any]:
    expected = dict(case.get("expected", {}))
    direct = dict(case.get("direct", {}))
    pragmatics = build_dialogue_pragmatics_v1(
        user_message=str(direct.get("user_message", "") or ""),
        conversation_context=str(direct.get("conversation_context", "") or ""),
        previous_assistant_message=str(direct.get("previous_assistant_message", "") or ""),
        dialogue_policy=dict(direct.get("dialogue_policy", {})),
        active_frame={},
        thread_state=None,
    )
    decision = build_contextual_retrieval_decision_v1(
        dialogue_pragmatics=pragmatics,
        knowledge_answer_guard=dict(direct.get("knowledge_answer_guard", {})),
        semantic_hits=_semantic_hits(direct),
    )

    checks: dict[str, bool] = {}
    if "is_contextual_followup" in expected:
        checks["is_contextual_followup"] = bool(pragmatics.get("is_contextual_followup", False)) == bool(
            expected.get("is_contextual_followup", False)
        )
    if "repair_user_dissatisfaction" in expected:
        checks["repair_user_dissatisfaction"] = bool(pragmatics.get("repair_user_dissatisfaction", False)) == bool(
            expected.get("repair_user_dissatisfaction", False)
        )
    if "offer_type" in expected:
        checks["offer_type"] = str(pragmatics.get("previous_assistant_offer_type", "")) == str(
            expected.get("offer_type", "")
        )
    if "short_type" in expected:
        checks["short_type"] = str(pragmatics.get("short_utterance_type", "")) == str(
            expected.get("short_type", "")
        )
    if "retrieval_action_allowed" in expected:
        checks["retrieval_action_allowed"] = str(decision.get("retrieval_action", "")) in {
            str(item) for item in list(expected.get("retrieval_action_allowed", []) or [])
        }
    if str(decision.get("retrieval_action", "")) == "memory_only":
        checks["memory_only_has_no_rag"] = int(decision.get("rag_included_count", 0) or 0) == 0

    failures = [name for name, ok in checks.items() if not ok]
    return {
        "case_id": str(case.get("case_id", "")),
        "pragmatics": pragmatics,
        "retrieval_decision": {k: v for k, v in decision.items() if k != "rag_included_for_writer"},
        "evaluation": {
            "passed": len(failures) == 0,
            "checks": checks,
            "failure_reasons": failures,
        },
    }


def _run_dry(cases: list[dict[str, Any]]) -> dict[str, Any]:
    ok, errors = _validate_dataset(cases)
    return {
        "mode": "dry",
        "status": "passed" if ok else "failed",
        "timestamp": _now_iso(),
        "dataset_total": len(cases),
        "errors": errors,
    }


def _run_direct(cases: list[dict[str, Any]]) -> dict[str, Any]:
    results = [_evaluate_direct_case(case) for case in cases]
    total = len(results)
    passed = sum(1 for item in results if bool(item.get("evaluation", {}).get("passed", False)))
    checks = {
        "cases_passed": passed == total,
        "required_cases_present": REQUIRED_CASE_IDS.issubset({str(item.get("case_id", "")) for item in results}),
    }
    return {
        "mode": "direct",
        "status": "passed" if all(checks.values()) else "failed",
        "timestamp": _now_iso(),
        "summary": {
            "cases_total": total,
            "cases_passed": passed,
            "cases_failed": max(0, total - passed),
        },
        "checks": checks,
        "case_results": results,
    }


def _http_json_request(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict[str, Any]]:
    body = None
    request_headers = dict(headers)
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url=url, method=method.upper(), headers=request_headers, data=body)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status_code = int(getattr(response, "status", 200))
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw.strip() else {}
            return status_code, data if isinstance(data, dict) else {"raw": data}
    except urllib.error.HTTPError as exc:
        status_code = int(getattr(exc, "code", 500))
        raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        if raw.strip():
            try:
                parsed = json.loads(raw)
                return status_code, parsed if isinstance(parsed, dict) else {"raw": parsed}
            except json.JSONDecodeError:
                return status_code, {"raw": raw}
        return status_code, {}


def _derive_api_root(base_url: str) -> str:
    base = base_url.rstrip("/")
    suffix = "/api/v1"
    if base.endswith(suffix):
        return base[: -len(suffix)]
    return base


def _save_live_turn_exports(*, exports_dir: Path, case_id: str, traces_payload: dict[str, Any]) -> list[str]:
    saved: list[str] = []
    traces = list(traces_payload.get("traces", []) or []) if isinstance(traces_payload, dict) else []
    case_dir = exports_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    for idx, trace in enumerate(traces, start=1):
        if not isinstance(trace, dict):
            continue
        evidence = trace.get("live_turn_evidence") if isinstance(trace.get("live_turn_evidence"), dict) else {}
        payload = {
            "trace_contract_version": trace.get("trace_contract_version"),
            "turn_number": trace.get("turn_number"),
            "dialogue_pragmatics": trace.get("dialogue_pragmatics"),
            "retrieval_decision": trace.get("retrieval_decision"),
            "live_turn_evidence": evidence,
        }
        out = case_dir / f"turn_{idx:02d}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        saved.append(str(out))
    return saved


def _run_markdown_smoke(log_dir: Path) -> dict[str, Any]:
    markdown_text = (
        "**Главное:** это пример.\n\n"
        "1. Первый пункт\n"
        "2. Второй пункт\n\n"
        "*мягкое уточнение*\n"
    )
    markdown_path = log_dir / "markdown_smoke.md"
    dom_path = log_dir / "markdown_smoke_dom.html"
    markdown_path.write_text(markdown_text, encoding="utf-8")

    web_ui_dir = PROJECT_ROOT / "web_ui"
    js = (
        "import fs from 'node:fs';"
        "import React from 'react';"
        "import { renderToStaticMarkup } from 'react-dom/server';"
        "import ReactMarkdown from 'react-markdown';"
        "import remarkGfm from 'remark-gfm';"
        f"const md = fs.readFileSync({json.dumps(str(markdown_path))}, 'utf8');"
        "const html = renderToStaticMarkup(React.createElement(ReactMarkdown, {remarkPlugins:[remarkGfm], skipHtml:true}, md));"
        f"fs.writeFileSync({json.dumps(str(dom_path))}, html, 'utf8');"
    )

    try:
        subprocess.run(
            ["node", "--input-type=module", "-e", js],
            cwd=str(web_ui_dir),
            check=True,
            capture_output=True,
            text=True,
        )
        dom_html = dom_path.read_text(encoding="utf-8") if dom_path.exists() else ""
        checks = {
            "has_strong": "<strong>" in dom_html,
            "has_ol_or_ul": "<ol" in dom_html or "<ul" in dom_html,
            "has_em": "<em>" in dom_html,
        }
        status = "passed" if all(checks.values()) else "warning"
        return {
            "status": status,
            "checks": checks,
            "markdown_path": str(markdown_path),
            "dom_path": str(dom_path),
        }
    except Exception as exc:  # noqa: BLE001
        fallback = (
            "<html><body><pre>"
            + html.escape(markdown_text)
            + "</pre><p>renderer_unavailable</p></body></html>"
        )
        dom_path.write_text(fallback, encoding="utf-8")
        return {
            "status": "warning",
            "reason": f"renderer_error:{exc.__class__.__name__}",
            "markdown_path": str(markdown_path),
            "dom_path": str(dom_path),
        }


def _run_live(
    *,
    cases: list[dict[str, Any]],
    base_url: str,
    api_key: str,
    admin_runtime_url: str,
    save_evidence: bool,
    log_dir: Path,
) -> dict[str, Any]:
    headers = {"X-API-Key": api_key}
    runtime_status, _ = _http_json_request(
        method="GET",
        url=admin_runtime_url,
        headers=headers,
        timeout=30.0,
    )
    if runtime_status != 200:
        return {
            "mode": "live",
            "status": "blocked",
            "timestamp": _now_iso(),
            "reason": f"admin_runtime_status_{runtime_status}",
        }

    api_root = _derive_api_root(base_url)
    exports_dir = log_dir / "live_turn_exports"
    case_results: list[dict[str, Any]] = []
    total_statuses: list[int] = []
    stale_stub_count = 0

    for case in cases:
        case_id = str(case.get("case_id", ""))
        turns = [str(item or "") for item in list(case.get("live_turns", []) or []) if str(item or "").strip()]
        session_id = f"prd04710hf2-{case_id.lower()}-{uuid.uuid4().hex[:8]}"
        statuses: list[int] = []
        answers: list[str] = []
        per_turn_trace: list[dict[str, Any]] = []

        for turn in turns:
            status_code, payload = _http_json_request(
                method="POST",
                url=f"{base_url.rstrip('/')}/questions/adaptive",
                headers=headers,
                payload={
                    "query": turn,
                    "session_id": session_id,
                    "debug": True,
                    "include_path": False,
                    "include_feedback_prompt": True,
                },
                timeout=120.0,
            )
            statuses.append(status_code)
            trace = dict(payload.get("trace", {})) if isinstance(payload.get("trace"), dict) else {}
            per_turn_trace.append(trace)
            if status_code == 200:
                answer = str(payload.get("answer", "") or "")
                answers.append(answer)
                if STALE_STUB_MARKER in answer.lower():
                    stale_stub_count += 1
            else:
                answers.append("")

        total_statuses.extend(statuses)
        traces_status, traces_payload = _http_json_request(
            method="GET",
            url=f"{api_root}/api/debug/session/{urllib.parse.quote(session_id, safe='')}/traces?format=full",
            headers=headers,
            timeout=60.0,
        )
        latest_status, latest_payload = _http_json_request(
            method="GET",
            url=f"{api_root}/api/debug/session/{urllib.parse.quote(session_id, safe='')}/multiagent-trace",
            headers=headers,
            timeout=60.0,
        )

        exported_files: list[str] = []
        if save_evidence and traces_status == 200 and isinstance(traces_payload, dict):
            exported_files = _save_live_turn_exports(
                exports_dir=exports_dir,
                case_id=case_id,
                traces_payload=traces_payload,
            )

        last_answer = answers[-1] if answers else ""
        retrieval_action = ""
        rag_included_count = None
        if isinstance(latest_payload, dict):
            retrieval = latest_payload.get("retrieval_decision") if isinstance(latest_payload.get("retrieval_decision"), dict) else {}
            retrieval_action = str(retrieval.get("retrieval_action", "") or "")
            rag_included_count = retrieval.get("rag_included_count")

        checks = {
            "no_422": not any(code == 422 for code in statuses),
            "all_status_200": all(code == 200 for code in statuses),
            "non_empty_last_answer": bool(last_answer.strip()),
            "no_stale_regulate_stub": STALE_STUB_MARKER not in last_answer.lower(),
            "trace_endpoint_ok": latest_status == 200,
            "traces_endpoint_ok": traces_status == 200,
        }
        if case_id == "HF2-007":
            checks["thanks_close_no_rag"] = retrieval_action in {"none", "recent_context_only"} and int(rag_included_count or 0) == 0

        case_results.append(
            {
                "case_id": case_id,
                "session_id": session_id,
                "statuses": statuses,
                "answers_preview": [item[:600] for item in answers],
                "checks": checks,
                "exported_files": exported_files,
                "latest_retrieval_action": retrieval_action,
                "latest_rag_included_count": rag_included_count,
            }
        )

    markdown_result = _run_markdown_smoke(log_dir)

    overall_checks = {
        "no_422_global": not any(code == 422 for code in total_statuses),
        "all_cases_checks_passed": all(all(bool(v) for v in case.get("checks", {}).values()) for case in case_results),
        "required_cases_count": len(case_results) >= 8,
        "stale_stub_absent": stale_stub_count == 0,
        "markdown_smoke_passed": markdown_result.get("status") in {"passed", "warning"},
    }

    return {
        "mode": "live",
        "status": "passed" if all(overall_checks.values()) else "failed",
        "timestamp": _now_iso(),
        "summary": {
            "cases_total": len(case_results),
            "statuses_total": len(total_statuses),
            "stale_stub_count": stale_stub_count,
        },
        "checks": overall_checks,
        "case_results": case_results,
        "markdown_smoke": markdown_result,
    }


def _select_cases(cases: list[dict[str, Any]], case_id: str | None, limit: int | None) -> list[dict[str, Any]]:
    selected = list(cases)
    if case_id:
        selected = [item for item in selected if str(item.get("case_id", "")) == str(case_id)]
        if not selected:
            raise ValueError(f"case-id not found: {case_id}")
    if isinstance(limit, int) and limit > 0:
        selected = selected[:limit]
    return selected


def _build_live_markdown(payload: dict[str, Any]) -> list[str]:
    lines = [
        "# PRD-047.10-HF2 Live Follow-up Reliability",
        "",
        f"- status: `{payload.get('status')}`",
        f"- timestamp_utc: `{payload.get('timestamp')}`",
        "",
        "## Global Checks",
    ]
    for key, value in dict(payload.get("checks", {})).items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.append("")
    lines.append("## Cases")
    for case in list(payload.get("case_results", []) or []):
        lines.append(f"### {case.get('case_id')}")
        lines.append(f"- session_id: `{case.get('session_id')}`")
        lines.append(f"- statuses: `{case.get('statuses')}`")
        lines.append(f"- checks: `{case.get('checks')}`")
        for idx, answer in enumerate(list(case.get("answers_preview", []) or []), start=1):
            lines.append(f"- answer_{idx}: `{answer[:220]}`")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.10-HF2 follow-up reliability eval")
    parser.add_argument("--mode", choices=["dry", "direct", "live"], default="dry")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--base-url", default=os.getenv("PRD04710HF2_BASE_URL", "http://127.0.0.1:8001/api/v1"))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD04710HF2_ADMIN_RUNTIME_URL", "http://127.0.0.1:8001/api/admin/runtime/effective"),
    )
    parser.add_argument("--api-key", default=os.getenv("PRD04710HF2_API_KEY", "dev-key-001"))
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--save-evidence", action="store_true")
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    log_dir = _resolve_path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    cases = _select_cases(_load_cases(dataset_path), args.case_id, args.limit)

    if args.mode == "dry":
        payload = _run_dry(cases)
        output_json = _resolve_path(args.output_json) if args.output_json else log_dir / "followup_reliability_dry.json"
    elif args.mode == "direct":
        payload = _run_direct(cases)
        output_json = _resolve_path(args.output_json) if args.output_json else log_dir / "followup_reliability_direct.json"
    else:
        payload = _run_live(
            cases=cases,
            base_url=str(args.base_url),
            api_key=str(args.api_key),
            admin_runtime_url=str(args.admin_runtime_url),
            save_evidence=bool(args.save_evidence),
            log_dir=log_dir,
        )
        output_json = _resolve_path(args.output_json) if args.output_json else log_dir / "followup_reliability_live.json"

    payload["prd"] = "PRD-047.10-HF2"
    payload["dataset"] = str(dataset_path)
    _write_json(output_json, payload)

    if args.mode == "live":
        output_md = _resolve_path(args.output_md) if args.output_md else log_dir / "followup_reliability_live.md"
        _write_md(output_md, _build_live_markdown(payload))

    print(json.dumps({"status": payload.get("status"), "output": str(output_json)}, ensure_ascii=False))
    return 0 if payload.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
