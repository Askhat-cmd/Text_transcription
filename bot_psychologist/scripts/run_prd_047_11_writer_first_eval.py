#!/usr/bin/env python3
"""PRD-047.11 writer-first consolidation evaluator."""

from __future__ import annotations

import argparse
import base64
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

from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1
from bot_agent.multiagent.stale_stub_detector import contains_stale_stub, detect_stale_stub

DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.11"
DEFAULT_BASE_URL = "http://127.0.0.1:8001/api/v1"
DEFAULT_ADMIN_RUNTIME_URL = "http://127.0.0.1:8001/api/admin/runtime/effective"
DEFAULT_CHAT_URL = "http://127.0.0.1:5173/chat"
STALE_TEXTS = (
    "\u041e\u0442\u0432\u0435\u0447\u0443 \u043f\u043e \u0441\u0443\u0442\u0438 \u0431\u0435\u0437 "
    "\u043d\u0430\u0432\u044f\u0437\u044b\u0432\u0430\u043d\u0438\u044f \u043f\u0440\u0430\u043a\u0442\u0438\u043a",
    "\u041a\u043b\u044e\u0447\u0435\u0432\u043e\u0439 \u0443\u0437\u0435\u043b \u0432 \u0442\u043e\u043c, \u0447\u0442\u043e "
    "\u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c "
    "\u043c\u043e\u0436\u0435\u0442 \u0432\u043a\u043b\u044e\u0447\u0430\u0442\u044c "
    "\u0432\u043d\u0443\u0442\u0440\u0435\u043d\u043d\u044e\u044e \u043f\u0435\u0440\u0435\u0433\u0440\u0443\u0437\u043a\u0443",
    "\u0421\u0444\u043e\u043a\u0443\u0441\u0438\u0440\u0443\u044e\u0441\u044c \u043d\u0430 \u0440\u0430\u0437\u0431\u043e\u0440\u0435, "
    "\u0431\u0435\u0437 \u043f\u0440\u0430\u043a\u0442\u0438\u043a \u043f\u043e \u0443\u043c\u043e\u043b\u0447\u0430\u043d\u0438\u044e",
)
_PLACEHOLDER_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5NnZQAAAAASUVORK5CYII="
)

LIVE_SCENARIOS: list[dict[str, Any]] = [
    {
        "case_id": "WFA-001",
        "turns": [
            "\u0447\u0442\u043e \u0442\u0430\u043a\u043e\u0435 "
            "\u043d\u0435\u0439\u0440\u043e\u0441\u0442\u0430\u043b\u043a\u0438\u043d\u0433, "
            "\u0438 \u043a\u0430\u043a \u0435\u0433\u043e \u043c\u043e\u0436\u043d\u043e "
            "\u043f\u0440\u0438\u043c\u0435\u043d\u044f\u0442\u044c \u0432 \u0436\u0438\u0437\u043d\u0438?",
            "\u0434\u0430",
        ],
    },
    {
        "case_id": "WFA-002",
        "turns": [
            "\u0442\u044b \u0437\u0430\u0434\u0430\u043b \u043c\u043d\u0435 \u0432\u043e\u043f\u0440\u043e\u0441, "
            "\u044f \u043e\u0442\u0432\u0435\u0442\u0438\u043b \u0442\u0435\u0431\u0435 \u0434\u0430! "
            "\u041f\u043e\u0447\u0435\u043c\u0443 \u0442\u044b \u043d\u0435 "
            "\u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u043b \u043b\u0438\u043d\u0438\u044e?"
        ],
    },
    {
        "case_id": "WFA-003",
        "turns": [
            "\u0447\u0435\u043c \u043e\u0442\u043b\u0438\u0447\u0430\u0435\u0442\u0441\u044f "
            "\u041d\u0435\u0439\u0440\u043e\u0441\u0442\u0430\u043b\u043a\u0438\u043d\u0433 "
            "\u043e\u0442 \u041d\u0435\u043e\u0441\u0442\u0430\u043b\u043a\u0438\u043d\u0433\u0430?"
        ],
    },
    {
        "case_id": "WFA-004",
        "turns": ["\u0442\u0435\u0431\u044f \u0441\u043d\u043e\u0432\u0430 \u0437\u0430\u0433\u043b\u044e\u0447\u0438\u043b\u043e?"],
    },
    {
        "case_id": "WFA-005",
        "turns": [
            "\u0434\u0430\u0432\u0430\u0439 \u0440\u0430\u0437\u0431\u0435\u0440\u0435\u043c "
            "\u044d\u0442\u043e \u043d\u0430 \u043f\u0440\u0438\u043c\u0435\u0440\u0435: "
            "\u043d\u0430 \u0440\u0430\u0431\u043e\u0442\u0435 \u043d\u0430\u0447\u0430\u043b\u044c\u043d\u0438\u043a "
            "\u043d\u0435 \u043f\u0440\u0430\u0432, \u043d\u043e \u044f \u0437\u0430\u0436\u0438\u043c\u0430\u044e "
            "\u0441\u0435\u0431\u044f..."
        ],
    },
    {
        "case_id": "WFA-006",
        "turns": ["\u0441\u043f\u0430\u0441\u0438\u0431\u043e"],
    },
]
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _http_json_request(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict[str, Any]]:
    body = None
    req_headers = dict(headers)
    if payload is not None:
        req_headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url=url, method=method.upper(), headers=req_headers, data=body)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw.strip() else {}
            return status, data if isinstance(data, dict) else {"raw": data}
    except urllib.error.HTTPError as exc:
        status = int(getattr(exc, "code", 500))
        raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        if raw.strip():
            try:
                data = json.loads(raw)
                return status, data if isinstance(data, dict) else {"raw": data}
            except json.JSONDecodeError:
                return status, {"raw": raw}
        return status, {}


def _derive_api_root(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/api/v1"):
        return base[:-7]
    return base


def _run_dry(log_dir: Path) -> dict[str, Any]:
    required = [
        "bot_psychologist/bot_agent/multiagent/final_answer_directive.py",
        "bot_psychologist/bot_agent/multiagent/stale_stub_detector.py",
        "bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py",
    ]
    checks = {path: _resolve_path(path).exists() for path in required}
    return {
        "mode": "dry",
        "status": "passed" if all(checks.values()) else "failed",
        "timestamp": _now_iso(),
        "checks": checks,
    }


def _run_direct() -> dict[str, Any]:
    from types import SimpleNamespace

    results: list[dict[str, Any]] = []
    for scenario in LIVE_SCENARIOS:
        user_message = str(list(scenario["turns"])[-1])
        directive = build_final_answer_directive_v1(
            user_message=user_message,
            dialogue_policy={"profile": "mvp_free_dialogue"},
            dialogue_pragmatics={},
            response_planner={},
            active_line={},
            diagnostic_card={},
            diagnostic_center_shadow={},
            retrieval_decision={},
            knowledge_answer_guard={},
            thread_state=SimpleNamespace(safety_active=False),
            state_snapshot=SimpleNamespace(safety_flag=False),
        ).to_dict()
        results.append(
            {
                "case_id": scenario["case_id"],
                "user_intent": directive.get("user_intent"),
                "obligation": directive.get("answer_obligation"),
                "planner_role": directive.get("planner_role"),
                "has_suppressed_constraints": bool(directive.get("suppressed_legacy_constraints")),
            }
        )
    passed = all(
        item["planner_role"] == "advisory_context_only" and item["obligation"]
        for item in results
    )
    return {
        "mode": "direct",
        "status": "passed" if passed else "failed",
        "timestamp": _now_iso(),
        "case_results": results,
    }


def _save_live_export(
    *,
    exports_root: Path,
    session_id: str,
    traces_payload: dict[str, Any],
    answers: list[str],
    turns: list[str],
) -> list[str]:
    saved: list[str] = []
    session_dir = exports_root / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    traces = list(traces_payload.get("traces", []) or [])
    for index, trace in enumerate(traces, start=1):
        if not isinstance(trace, dict):
            continue
        evidence = trace.get("live_turn_evidence") if isinstance(trace.get("live_turn_evidence"), dict) else {}
        payload_path = session_dir / f"{index:02d}.json"
        payload_path.write_text(
            json.dumps(
                {
                    "trace_contract_version": trace.get("trace_contract_version"),
                    "turn_number": trace.get("turn_number"),
                    "final_answer_directive": trace.get("final_answer_directive"),
                    "writer_user_prompt": trace.get("writer_user_prompt"),
                    "live_turn_evidence": evidence,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        saved.append(str(payload_path))

        writer_prompt = str(trace.get("writer_user_prompt", "") or "")
        _write_text(session_dir / f"{index:02d}_writer_prompt.txt", writer_prompt)
        if index - 1 < len(answers):
            _write_text(session_dir / f"{index:02d}_final_answer.md", str(answers[index - 1] or ""))
    conversation_md = []
    for idx, turn in enumerate(turns, start=1):
        answer = answers[idx - 1] if idx - 1 < len(answers) else ""
        conversation_md.append(f"## Turn {idx}\n\n**User:** {turn}\n\n**Assistant:** {answer}\n")
    _write_text(session_dir / "conversation.md", "\n".join(conversation_md))
    return saved


def run_web_chat_markdown_real_smoke(
    *,
    chat_url: str,
    log_dir: Path,
    api_key: str = "dev-key-001",
) -> dict[str, Any]:
    out_json = log_dir / "web_chat_markdown_real_smoke.json"
    out_html = log_dir / "web_chat_markdown_real_smoke.html"
    out_png = log_dir / "web_chat_markdown_real_smoke.png"
    script = f"""
const fs = require('node:fs');
const path = require('node:path');
async function main() {{
  let browser = null;
  let playwright = null;
  try {{
    playwright = require('playwright');
  }} catch (e) {{
    try {{
      const fallbackPath = path.join(process.cwd(), 'bot_psychologist', 'web_ui', 'node_modules', 'playwright');
      playwright = require(fallbackPath);
    }} catch (e2) {{
      fs.writeFileSync({json.dumps(str(out_json))}, JSON.stringify({{
        status: 'warning',
        reason: 'playwright_not_installed'
      }}, null, 2), 'utf8');
      fs.writeFileSync({json.dumps(str(out_html))}, '<html><body>playwright_not_installed</body></html>', 'utf8');
      return;
    }}
  }}
  try {{
    browser = await playwright.chromium.launch({{ headless: true }});
    const page = await browser.newPage();
    await page.goto({json.dumps(chat_url)}, {{ waitUntil: 'domcontentloaded', timeout: 60000 }});
    await page.waitForTimeout(1500);
    const apiInput = page.locator('input[placeholder="Введите API key"]');
    if (await apiInput.count()) {{
      if (await apiInput.first().isVisible().catch(() => false)) {{
        await apiInput.first().fill({json.dumps(api_key)});
        const saveButton = page.getByRole('button', {{ name: 'Сохранить настройки' }});
        if (await saveButton.count()) {{
          if (await saveButton.first().isVisible().catch(() => false)) {{
            await saveButton.first().click();
            await page.waitForTimeout(1200);
          }}
        }}
      }}
    }}
    await page.fill('textarea', 'Ответь строго в Markdown и сохрани формат: **Жирный текст**\\n\\n*Курсивный текст*\\n\\n- пункт 1\\n- пункт 2\\n- пункт 3');
    await page.keyboard.press('Enter');
    await page.waitForFunction(() => {{
      return Boolean(document.querySelector('strong')) &&
        Boolean(document.querySelector('em')) &&
        (Boolean(document.querySelector('ul')) || Boolean(document.querySelector('ol'))) &&
        Boolean(document.querySelector('p'));
    }}, {{ timeout: 90000 }}).catch(() => null);
    await page.waitForTimeout(1500);
    const html = await page.content();
    fs.writeFileSync({json.dumps(str(out_html))}, html, 'utf8');
    await page.screenshot({{ path: {json.dumps(str(out_png))}, fullPage: true }});
    const checks = {{
      hasStrong: html.includes('<strong>'),
      hasEm: html.includes('<em>'),
      hasList: html.includes('<ul') || html.includes('<ol'),
      hasParagraph: html.includes('<p>')
    }};
    const status = (checks.hasStrong && checks.hasEm && checks.hasList && checks.hasParagraph) ? 'passed' : 'warning';
    fs.writeFileSync({json.dumps(str(out_json))}, JSON.stringify({{ status, checks }}, null, 2), 'utf8');
  }} catch (e) {{
    fs.writeFileSync({json.dumps(str(out_json))}, JSON.stringify({{
      status: 'warning',
      reason: 'playwright_execution_error:' + String(e && e.name ? e.name : 'error')
    }}, null, 2), 'utf8');
    fs.writeFileSync({json.dumps(str(out_html))}, '<html><body>playwright_execution_error</body></html>', 'utf8');
  }} finally {{
    if (browser) {{
      await browser.close().catch(() => {{}});
    }}
  }}
}}
main();
"""
    try:
        subprocess.run(
            ["node", "-e", script],
            cwd=str(REPO_ROOT),
            check=False,
            capture_output=True,
            text=True,
            timeout=420,
        )
    except Exception as exc:  # noqa: BLE001
        payload = {"status": "warning", "reason": f"playwright_launch_failed:{exc.__class__.__name__}"}
        _write_json(out_json, payload)
        _write_text(out_html, "<html><body>playwright_launch_failed</body></html>")
        out_png.write_bytes(base64.b64decode(_PLACEHOLDER_PNG_BASE64))
        return payload
    if not out_png.exists():
        out_png.write_bytes(base64.b64decode(_PLACEHOLDER_PNG_BASE64))
    if out_json.exists():
        return json.loads(out_json.read_text(encoding="utf-8"))
    payload = {"status": "warning", "reason": "missing_smoke_output"}
    _write_json(out_json, payload)
    _write_text(out_html, "<html><body>missing_smoke_output</body></html>")
    return payload


def _run_live(
    *,
    base_url: str,
    admin_runtime_url: str,
    api_key: str,
    log_dir: Path,
    chat_url: str,
) -> dict[str, Any]:
    headers = {"X-API-Key": api_key}
    admin_config_url = f"{base_url.rstrip('/')}/admin/config"
    _http_json_request(
        method="POST",
        url=admin_config_url,
        headers=headers,
        payload={"key": "DIALOGUE_PROFILE", "value": "mvp_free_dialogue"},
        timeout=20.0,
    )
    runtime_status, runtime_payload = _http_json_request(
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
    exports_root = log_dir / "live_turn_exports"
    case_results: list[dict[str, Any]] = []
    stale_stub_count = 0
    missing_directive_count = 0

    for scenario in LIVE_SCENARIOS:
        case_id = str(scenario["case_id"])
        turns = [str(turn) for turn in list(scenario["turns"] or [])]
        session_id = f"prd04711-{case_id.lower()}-{uuid.uuid4().hex[:8]}"
        statuses: list[int] = []
        answers: list[str] = []
        turn_traces: list[dict[str, Any]] = []
        stale_hits: list[dict[str, Any]] = []

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
                timeout=150.0,
            )
            statuses.append(status_code)
            answer = str(payload.get("answer", "") or "")
            answers.append(answer)
            turn_traces.append(dict(payload.get("trace", {})) if isinstance(payload.get("trace"), dict) else {})
            stale = detect_stale_stub(answer)
            if bool(stale.get("detected", False)):
                stale_stub_count += 1
                stale_hits.append(stale)

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
        exported_files = []
        if traces_status == 200 and isinstance(traces_payload, dict):
            exported_files = _save_live_export(
                exports_root=exports_root,
                session_id=session_id,
                traces_payload=traces_payload,
                answers=answers,
                turns=turns,
            )

        trace_stale = contains_stale_stub(latest_payload if isinstance(latest_payload, dict) else {})
        if bool(trace_stale.get("detected", False)):
            stale_stub_count += 1

        final_directive = None
        if isinstance(latest_payload, dict):
            final_directive = latest_payload.get("final_answer_directive")
            if not isinstance(final_directive, dict):
                live_ev = latest_payload.get("live_turn_evidence")
                if isinstance(live_ev, dict):
                    writer_payload = live_ev.get("writer")
                    if isinstance(writer_payload, dict):
                        candidate = writer_payload.get("final_answer_directive")
                        if isinstance(candidate, dict):
                            final_directive = candidate
        if not isinstance(final_directive, dict):
            for trace in reversed(turn_traces):
                if not isinstance(trace, dict):
                    continue
                live_ev = trace.get("live_turn_evidence")
                if isinstance(live_ev, dict):
                    writer_payload = live_ev.get("writer")
                    if isinstance(writer_payload, dict) and isinstance(
                        writer_payload.get("final_answer_directive"), dict
                    ):
                        final_directive = writer_payload.get("final_answer_directive")
                        break
        has_final_directive = isinstance(final_directive, dict) and bool(final_directive)
        if not has_final_directive:
            missing_directive_count += 1

        checks = {
            "all_status_200": all(code == 200 for code in statuses),
            "non_empty_answer": all(bool(item.strip()) for item in answers),
            "no_stale_stub_in_answers": len(stale_hits) == 0,
            "final_answer_directive_present": has_final_directive,
            "trace_endpoint_ok": latest_status == 200,
            "traces_endpoint_ok": traces_status == 200,
            "writer_first_runtime_enabled": bool(
                dict(runtime_payload.get("dialogue_policy", {})).get(
                    "writer_first_prompt_assembly_enabled", False
                )
            ),
        }
        case_results.append(
            {
                "case_id": case_id,
                "session_id": session_id,
                "statuses": statuses,
                "answers": answers,
                "checks": checks,
                "exported_files": exported_files,
            }
        )

    markdown_smoke = run_web_chat_markdown_real_smoke(
        chat_url=chat_url,
        log_dir=log_dir,
        api_key=api_key,
    )
    all_checks = {
        "all_cases_passed": all(all(bool(v) for v in case["checks"].values()) for case in case_results),
        "stale_stub_absent_global": stale_stub_count == 0,
        "final_answer_directive_present_global": missing_directive_count == 0,
        "markdown_real_smoke_passed": str(markdown_smoke.get("status", "")) == "passed",
    }
    return {
        "mode": "live",
        "status": "passed" if all(all_checks.values()) else "warning",
        "timestamp": _now_iso(),
        "checks": all_checks,
        "summary": {
            "cases_total": len(case_results),
            "stale_stub_count": stale_stub_count,
            "missing_final_answer_directive_count": missing_directive_count,
        },
        "case_results": case_results,
        "web_chat_markdown_real_smoke": markdown_smoke,
    }


def _build_live_md(payload: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.11 Writer-First Live Eval",
        "",
        f"- status: `{payload.get('status')}`",
        f"- timestamp_utc: `{payload.get('timestamp')}`",
        "",
        "## Checks",
    ]
    for key, value in dict(payload.get("checks", {})).items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.append("")
    lines.append("## Cases")
    for item in list(payload.get("case_results", []) or []):
        lines.append(f"### {item.get('case_id')}")
        lines.append(f"- session_id: `{item.get('session_id')}`")
        lines.append(f"- checks: `{item.get('checks')}`")
        for idx, answer in enumerate(list(item.get("answers", []) or []), start=1):
            lines.append(f"- answer_{idx}: `{answer[:240]}`")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.11 writer-first eval")
    parser.add_argument("--mode", choices=["dry", "direct", "live"], default="dry")
    parser.add_argument("--base-url", default=os.getenv("PRD04711_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD04711_ADMIN_RUNTIME_URL", DEFAULT_ADMIN_RUNTIME_URL),
    )
    parser.add_argument("--api-key", default=os.getenv("PRD04711_API_KEY", "dev-key-001"))
    parser.add_argument("--chat-url", default=os.getenv("PRD04711_CHAT_URL", DEFAULT_CHAT_URL))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    args = parser.parse_args()

    log_dir = _resolve_path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "dry":
        payload = _run_dry(log_dir)
        out_json = _resolve_path(args.output_json) if args.output_json else log_dir / "writer_first_eval_dry.json"
    elif args.mode == "direct":
        payload = _run_direct()
        out_json = _resolve_path(args.output_json) if args.output_json else log_dir / "writer_first_eval_direct.json"
    else:
        payload = _run_live(
            base_url=str(args.base_url),
            admin_runtime_url=str(args.admin_runtime_url),
            api_key=str(args.api_key),
            log_dir=log_dir,
            chat_url=str(args.chat_url),
        )
        out_json = _resolve_path(args.output_json) if args.output_json else log_dir / "writer_first_eval_live.json"
        out_md = _resolve_path(args.output_md) if args.output_md else log_dir / "writer_first_eval_live.md"
        _write_text(out_md, _build_live_md(payload))

    payload["prd"] = "PRD-047.11"
    _write_json(out_json, payload)
    print(json.dumps({"status": payload.get("status"), "output": str(out_json)}, ensure_ascii=False))
    return 0 if payload.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())


