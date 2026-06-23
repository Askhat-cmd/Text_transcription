from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
BOT_ROOT = CURRENT_DIR.parent
REPO_ROOT = BOT_ROOT.parent
FIXTURE_PATH = REPO_ROOT / "TO_DO_LIST" / "fixtures" / "PRD-047.29" / "current_pipeline_simplification_cases_ru.jsonl"
LOG_DIR_DEFAULT = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.29"
API_KEY = "dev-key-001"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ascii_body(query: str, session_id: str) -> bytes:
    payload = {"query": query, "debug": True, "session_id": session_id}
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _http_json(method: str, url: str, *, data: bytes | None = None) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, json.loads(raw) if raw.strip().startswith("{") else {"detail": raw}


def _load_cases(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            rows.append(json.loads(stripped))
    return rows


def _answer_text(payload: dict[str, Any]) -> str:
    for key in ("answer", "response", "message", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _lowered_items(values: list[Any]) -> list[str]:
    return [str(item).lower() for item in values if str(item).strip()]


def _wait_for_debug(base_url: str, session_id: str, retries: int = 20) -> dict[str, Any]:
    for _ in range(retries):
        status, payload = _http_json(
            "GET",
            f"{base_url}/api/debug/session/{session_id}/multiagent-trace",
        )
        if status == 200:
            return payload
        time.sleep(1.0)
    raise RuntimeError(f"debug_trace_timeout:{session_id}")


def _evaluate_case(case: dict[str, Any], answer: str, debug_payload: dict[str, Any]) -> dict[str, Any]:
    expected = dict(case.get("expected", {}) or {})
    runtime_summary = dict(debug_payload.get("runtime_trace_summary_v1") or {})
    active_constraints = [str(item) for item in list(runtime_summary.get("latest_turn_constraints", []) or [])]
    expected_constraints = [str(item) for item in list(expected.get("latest_turn_constraints", []) or [])]
    answer_lower = answer.lower()
    mismatches: list[str] = []
    if active_constraints != expected_constraints:
        mismatches.append(
            f"latest_turn_constraints expected={expected_constraints} actual={active_constraints}"
        )
    for key in ("kb_visible_to_writer", "semantic_cards_visible_to_writer", "practice_blocked_by_user_request"):
        if key in expected and bool(runtime_summary.get(key)) != bool(expected.get(key)):
            mismatches.append(f"{key} expected={expected.get(key)} actual={runtime_summary.get(key)}")
    for phrase in _lowered_items(list(expected.get("must_not_contain", []) or [])):
        if phrase in answer_lower:
            mismatches.append(f"answer_contains_forbidden:{phrase}")
    required_any = _lowered_items(list(expected.get("must_contain_any", []) or []))
    if required_any and not any(phrase in answer_lower for phrase in required_any):
        mismatches.append(f"answer_missing_any_of:{required_any}")
    return {
        "case_id": str(case.get("case_id", "")),
        "title": str(case.get("title", "")),
        "query": str(case.get("query", "")),
        "answer": answer,
        "runtime_trace_summary_v1": runtime_summary,
        "status": "passed" if not mismatches else "blocked",
        "mismatches": mismatches,
    }


def run_live_smoke(*, base_url: str, fixture_path: Path, log_dir: Path) -> dict[str, Any]:
    fixture_path = fixture_path.resolve()
    log_dir = log_dir.resolve()
    cases = _load_cases(fixture_path)
    results: list[dict[str, Any]] = []
    exports_dir = log_dir / "live_turn_exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    for case in cases:
        case_id = str(case.get("case_id", "") or "")
        session_id = f"prd-047-29-{case_id.lower()}"
        status, response_payload = _http_json(
            "POST",
            f"{base_url}/api/v1/questions/adaptive",
            data=_ascii_body(str(case.get("query", "")), session_id),
        )
        if status != 200:
            raise RuntimeError(f"adaptive_failed:{case_id}:{status}")
        debug_payload = _wait_for_debug(base_url, session_id)
        answer = _answer_text(response_payload)
        row = _evaluate_case(case, answer, debug_payload)
        _write_json(exports_dir / f"{case_id}.json", row)
        results.append(row)

    report = {
        "schema_version": "prd_047_29_live_smoke_report_v1",
        "generated_at": _utc_now(),
        "base_url": base_url,
        "fixture_path": str(fixture_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "case_count": len(results),
        "passed_count": sum(1 for item in results if item["status"] == "passed"),
        "blocked_count": sum(1 for item in results if item["status"] != "passed"),
        "cases": results,
        "status": "passed" if all(item["status"] == "passed" for item in results) else "blocked",
    }
    _write_json(log_dir / "live_pilot_smoke_report.json", report)

    lines = [
        "# PRD-047.29 Live Pilot Smoke Report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- base_url: `{base_url}`",
        f"- fixture_path: `{report['fixture_path']}`",
        f"- case_count: `{report['case_count']}`",
        f"- passed_count: `{report['passed_count']}`",
        f"- blocked_count: `{report['blocked_count']}`",
        f"- status: `{report['status']}`",
        "",
        "## Cases",
        "",
    ]
    for item in results:
        summary = dict(item.get("runtime_trace_summary_v1", {}) or {})
        lines.extend(
            [
                f"### {item['case_id']} - {item['title']}",
                f"- status: `{item['status']}`",
                f"- latest_turn_constraints: `{', '.join(summary.get('latest_turn_constraints', [])) or 'none'}`",
                f"- kb_visible_to_writer: `{summary.get('kb_visible_to_writer')}`",
                f"- semantic_cards_visible_to_writer: `{summary.get('semantic_cards_visible_to_writer')}`",
                f"- final_directive_mode: `{summary.get('final_directive_mode')}`",
                f"- practice_blocked_by_user_request: `{summary.get('practice_blocked_by_user_request')}`",
                f"- warnings: `{', '.join(summary.get('warnings', [])) or 'none'}`",
                f"- mismatches: `{'; '.join(item.get('mismatches', [])) or 'none'}`",
                f"- answer_excerpt: `{item['answer'][:240]}`",
                "",
            ]
        )
    _write_text(log_dir / "live_pilot_smoke_report.md", "\n".join(lines))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH)
    parser.add_argument("--log-dir", type=Path, default=LOG_DIR_DEFAULT)
    args = parser.parse_args()
    run_live_smoke(base_url=args.base_url.rstrip("/"), fixture_path=args.fixture, log_dir=args.log_dir)


if __name__ == "__main__":
    main()
