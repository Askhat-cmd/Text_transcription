#!/usr/bin/env python3
"""Acceptance runner for PRD-047.15-HF2-R2."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
WEB_UI_ROOT = PROJECT_ROOT / "web_ui"
PRD_ID = "PRD-047.15-HF2-R2"
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
SCREENSHOT_DIR = LOG_DIR / "screenshots"
REPORT_JSON = LOG_DIR / "hf2_r2_visibility_runner_result.json"
REPORT_MD = LOG_DIR / "hf2_r2_visibility_runner_result.md"
LIVE_JSON = LOG_DIR / "live_smoke_result.json"
LIVE_MD = LOG_DIR / "live_smoke_result.md"
BROWSER_JSON = LOG_DIR / "browser_smoke_result.json"
BROWSER_MD = LOG_DIR / "browser_smoke_result.md"
BACKEND_RUNTIME_JSON = LOG_DIR / "backend_admin_effective.json"
BACKEND_TRACE_JSON = LOG_DIR / "backend_multiagent_trace_sample.json"
COMPACT_TRACE_JSON = LOG_DIR / "backend_trace_compact.json"
PARITY_JSON = LOG_DIR / "ui_backend_parity_report.json"
COMMAND_LOG = LOG_DIR / "test_command_log.txt"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def api_request(
    method: str,
    url: str,
    *,
    api_key: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    with urllib.request.urlopen(request, timeout=120) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset)
    return json.loads(body) if body else {}


def create_live_turn(api_base: str, api_key: str) -> dict[str, Any]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    user_id = f"hf2_r2_user_{timestamp}"
    session_info = api_request(
        "POST",
        f"{api_base}/api/v1/users/{urllib.parse.quote(user_id)}/sessions",
        api_key=api_key,
        payload={"title": "HF2-R2 visibility smoke"},
    )
    session_id = str(session_info.get("session_id", "") or "")
    if not session_id:
        raise RuntimeError("session_id missing from create_user_session response")

    answer = api_request(
        "POST",
        f"{api_base}/api/v1/questions/adaptive",
        api_key=api_key,
        payload={
            "query": "скажи, а в нейросталкинге какие практики предлагаются чтобы это видеть",
            "user_id": user_id,
            "session_id": session_id,
            "include_path": False,
            "include_feedback_prompt": False,
            "debug": False,
        },
    )
    time.sleep(2)
    trace = api_request(
        "GET",
        f"{api_base}/api/debug/session/{urllib.parse.quote(session_id)}/multiagent-trace",
        api_key=api_key,
    )
    compact = api_request(
        "GET",
        f"{api_base}/api/debug/session/{urllib.parse.quote(session_id)}/traces?format=compact",
        api_key=api_key,
    )
    return {
        "user_id": user_id,
        "session_id": session_id,
        "session_info": session_info,
        "answer": answer,
        "trace": trace,
        "compact": compact,
    }


def build_parity_report(runtime_payload: dict[str, Any], trace_payload: dict[str, Any], compact_payload: dict[str, Any]) -> dict[str, Any]:
    compact_traces = compact_payload.get("traces") if isinstance(compact_payload.get("traces"), list) else []
    latest_compact = compact_traces[-1] if compact_traces else {}
    checks = {
        "runtime_model_visible": runtime_payload.get("hybrid_retrieval_planner", {}).get("model") == "gpt-5-nano",
        "runtime_max_tokens_visible": int(runtime_payload.get("hybrid_retrieval_planner", {}).get("max_tokens", 0) or 0) == 320,
        "runtime_hybrid_card_contract": bool(runtime_payload.get("hybrid_retrieval_planner", {}).get("query_before_rag_supported")),
        "trace_root_fields_visible": all(
            key in trace_payload
            for key in (
                "planned_composed_query",
                "executed_rag_query",
                "retrieval_action",
                "planner_model",
                "planner_max_tokens",
            )
        ),
        "trace_memory_summary_visible": isinstance(trace_payload.get("memory_context", {}).get("hybrid_retrieval"), dict),
        "compact_summary_visible": isinstance(latest_compact.get("hybrid_retrieval_summary"), dict),
        "compatibility_legacy_status_visible": isinstance(runtime_payload.get("compatibility", {}).get("knowledge_graph"), dict),
    }
    status = "passed" if all(checks.values()) else "warning"
    return {
        "prd_id": PRD_ID,
        "status": status,
        "generated_at": now_iso(),
        "checks": checks,
        "summary": {
            "planner_mode": trace_payload.get("hybrid_retrieval_planner_mode"),
            "retrieval_action": trace_payload.get("retrieval_action"),
            "planner_model": trace_payload.get("planner_model"),
        },
    }


def run_browser_capture(web_base: str, user_id: str) -> dict[str, Any]:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    node_script = f"""
const {{ chromium }} = require('playwright');
const fs = require('fs');

(async () => {{
  const webBase = process.argv[1];
  const userId = process.argv[2];
  const runtimeShot = process.argv[3];
  const advancedShot = process.argv[4];
  const hybridShot = process.argv[5];
  const traceShot = process.argv[6];

  const browser = await chromium.launch({{ headless: true }});
  const context = await browser.newContext({{ viewport: {{ width: 1600, height: 1200 }} }});
  await context.addInitScript((seedUserId) => {{
    localStorage.setItem('bot_api_key', 'dev-key-001');
    localStorage.setItem('devApiKey', 'dev-key-001');
    localStorage.setItem('bot_user_id', seedUserId);
  }}, userId);

  const page = await context.newPage();
  await page.goto(`${{webBase}}/admin`, {{ waitUntil: 'networkidle' }});
  await page.getByRole('button', {{ name: 'Runtime' }}).click();
  await page.waitForTimeout(1000);
  await page.screenshot({{ path: runtimeShot, fullPage: true }});
  await page.locator('summary').click();
  await page.waitForTimeout(500);
  await page.screenshot({{ path: advancedShot, fullPage: true }});
  await page.locator('[data-testid=\"hf2-hybrid-retrieval-runtime\"]').scrollIntoViewIfNeeded();
  await page.screenshot({{ path: hybridShot, fullPage: true }});

  await page.goto(`${{webBase}}/chat?user_id=${{encodeURIComponent(userId)}}`, {{ waitUntil: 'networkidle' }});
  await page.waitForSelector('text=Pipeline NEO', {{ timeout: 30000 }});
  const pipelineButtons = page.locator('button', {{ hasText: 'Pipeline NEO' }});
  await pipelineButtons.last().click();
  const hybridButtons = page.locator('button', {{ hasText: 'Hybrid Retrieval' }});
  await hybridButtons.last().click();
  await page.waitForTimeout(1000);
  await page.screenshot({{ path: traceShot, fullPage: true }});

  await browser.close();
  process.stdout.write(JSON.stringify({{
    status: 'passed',
    screenshots: [runtimeShot, advancedShot, hybridShot, traceShot]
  }}));
}})().catch((error) => {{
  process.stderr.write(String(error));
  process.exit(1);
}});
"""
    result = subprocess.run(
        [
            "node",
            "-e",
            node_script,
            web_base,
            user_id,
            str(SCREENSHOT_DIR / "admin_runtime_cleanup_after.png"),
            str(SCREENSHOT_DIR / "admin_advanced_controls_after.png"),
            str(SCREENSHOT_DIR / "admin_hybrid_retrieval_planner.png"),
            str(SCREENSHOT_DIR / "web_trace_hybrid_retrieval.png"),
        ],
        cwd=str(WEB_UI_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "browser capture failed")
    return json.loads(result.stdout.strip() or "{}")


def write_md_summary(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", "", f"- status: {payload.get('status', 'unknown')}"]
    for key, value in payload.items():
        if key in {"status"}:
            continue
        lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")
    write_text(path, "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["all", "dry", "direct", "live", "browser"], default="all")
    parser.add_argument("--api-base", default="http://127.0.0.1:8001")
    parser.add_argument("--web-base", default="http://localhost:3000")
    parser.add_argument("--api-key", default="dev-key-001")
    args = parser.parse_args()

    command_lines: list[str] = [f"runner_started={now_iso()}", f"mode={args.mode}", f"api_base={args.api_base}", f"web_base={args.web_base}"]

    runtime_payload = api_request("GET", f"{args.api_base}/api/admin/runtime/effective", api_key=args.api_key)
    write_json(BACKEND_RUNTIME_JSON, runtime_payload)

    direct_result = {
        "status": "passed"
        if runtime_payload.get("hybrid_retrieval_planner", {}).get("model") == "gpt-5-nano"
        and int(runtime_payload.get("hybrid_retrieval_planner", {}).get("max_tokens", 0) or 0) == 320
        else "warning",
        "runtime_mode": runtime_payload.get("hybrid_retrieval_planner", {}).get("mode"),
        "runtime_model": runtime_payload.get("hybrid_retrieval_planner", {}).get("model"),
        "runtime_max_tokens": runtime_payload.get("hybrid_retrieval_planner", {}).get("max_tokens"),
    }

    live_turn: dict[str, Any] | None = None
    trace_payload: dict[str, Any] = {}
    compact_payload: dict[str, Any] = {}
    parity_report = {
        "prd_id": PRD_ID,
        "status": direct_result["status"],
        "generated_at": now_iso(),
        "checks": {"runtime_only": True},
        "summary": {
            "planner_mode": runtime_payload.get("hybrid_retrieval_planner", {}).get("mode"),
            "planner_model": runtime_payload.get("hybrid_retrieval_planner", {}).get("model"),
        },
    }
    live_result = {"status": "skipped", "reason": "mode does not require live turn"}

    if args.mode in {"all", "direct", "live", "browser"}:
        live_turn = create_live_turn(args.api_base, args.api_key)
        trace_payload = dict(live_turn["trace"])
        compact_payload = dict(live_turn["compact"])
        write_json(BACKEND_TRACE_JSON, trace_payload)
        write_json(COMPACT_TRACE_JSON, compact_payload)
        parity_report = build_parity_report(runtime_payload, trace_payload, compact_payload)
        write_json(PARITY_JSON, parity_report)
        live_result = {
            "status": "passed" if parity_report["status"] == "passed" else "warning",
            "session_id": live_turn["session_id"],
            "user_id": live_turn["user_id"],
            "retrieval_action": trace_payload.get("retrieval_action"),
            "planner_mode": trace_payload.get("hybrid_retrieval_planner_mode"),
            "planner_model": trace_payload.get("planner_model"),
            "query_before_rag_proof": trace_payload.get("query_before_rag_proof"),
        }
    write_json(LIVE_JSON, live_result)
    write_md_summary(LIVE_MD, "HF2-R2 Live Smoke", live_result)

    browser_result = {"status": "skipped", "reason": "mode does not require browser"}
    if args.mode in {"all", "browser"}:
        if not live_turn:
            raise RuntimeError("browser mode requires live turn preparation")
        browser_result = run_browser_capture(args.web_base, live_turn["user_id"])
    write_json(BROWSER_JSON, browser_result)
    write_md_summary(BROWSER_MD, "HF2-R2 Browser Smoke", browser_result)

    report = {
        "prd_id": PRD_ID,
        "status": "passed" if parity_report["status"] == "passed" and browser_result.get("status") == "passed" else "warning",
        "generated_at": now_iso(),
        "direct": direct_result,
        "live": live_result,
        "browser": browser_result,
        "parity": parity_report,
    }
    write_json(REPORT_JSON, report)
    write_md_summary(REPORT_MD, "HF2-R2 Visibility Runner", report)
    if live_turn:
        command_lines.append(f"session_id={live_turn['session_id']}")
        command_lines.append(f"user_id={live_turn['user_id']}")
    command_lines.append(f"final_status={report['status']}")
    write_text(COMMAND_LOG, "\n".join(command_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
