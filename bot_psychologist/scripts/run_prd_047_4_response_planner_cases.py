#!/usr/bin/env python3
"""Run PRD-047.4 response planner calibration cases."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.response_planner import (  # noqa: E402
    build_response_planner_decision,
)

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_4_response_planner_cases.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.4"
DEFAULT_TRACE_SAMPLES = DEFAULT_LOG_DIR / "response_planner_trace_samples.json"
DEFAULT_POLICY_VIOLATIONS = DEFAULT_LOG_DIR / "response_planner_policy_violations_report.json"


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


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("dataset must be list")
    return sorted(
        [item for item in payload if isinstance(item, dict)],
        key=lambda item: (str(item.get("thread_id", "")), int(item.get("turn_index", 0) or 0)),
    )


def _as_ns(payload: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(**dict(payload or {}))


def _contains_text(items: list[str], needle: str) -> bool:
    low = str(needle or "").strip().lower()
    if not low:
        return True
    return any(low in str(item or "").lower() for item in (items or []))


def _build_case_signals(case: dict[str, Any]) -> dict[str, Any]:
    signals = dict(case.get("signals", {}))
    turns = [item for item in list(case.get("turns", []) or []) if isinstance(item, dict)]
    user_message = ""
    for turn in reversed(turns):
        if str(turn.get("role", "")).lower() == "user":
            user_message = str(turn.get("content", "") or "")
            break
    return {
        "user_message": user_message,
        "thread_state": _as_ns(dict(signals.get("thread_state", {}))),
        "state_snapshot": _as_ns(dict(signals.get("state_snapshot", {}))),
        "active_line": dict(signals.get("active_line", {})),
        "knowledge_answer_guard": dict(signals.get("knowledge_answer_guard", {})),
        "philosophy_kernel": dict(signals.get("philosophy_kernel", {})),
    }


def _local_expected_planner(
    *,
    user_message: str,
    thread_state: Any,
    state_snapshot: Any,
    active_line: dict[str, Any],
    knowledge_answer_guard: dict[str, Any],
    philosophy_kernel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = build_response_planner_decision(
        user_message=user_message,
        state_snapshot=state_snapshot,
        thread_state=thread_state,
        diagnostic_card=None,
        active_line=active_line,
        knowledge_answer_guard=knowledge_answer_guard,
        philosophy_kernel=dict(philosophy_kernel or {}),
        context_package=None,
    )
    return asdict(decision)


def _evaluate_case(
    *,
    case: dict[str, Any],
    actual: dict[str, Any] | None,
    expected_local: dict[str, Any] | None = None,
    mode: str,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    expected = dict(case.get("expected", {}))
    checks: dict[str, bool] = {}
    failure_reasons: list[str] = []

    checks["planner_present"] = isinstance(actual, dict) and bool(actual)
    if not checks["planner_present"]:
        failure_reasons.append(failure_reason or "missing_response_planner")
        return {
            "passed": False,
            "checks": checks,
            "failure_reasons": failure_reasons,
        }

    planner = dict(actual or {})
    must_avoid = [str(item) for item in list(planner.get("must_avoid", []) or [])]

    checks["enabled_true"] = bool(planner.get("enabled", False))
    enforce_dataset_expected = mode == "dry"
    checks["next_move_match"] = (
        str(planner.get("next_move", "")) == str(expected.get("next_move", ""))
        if enforce_dataset_expected
        else True
    )
    checks["answer_shape_match"] = (
        str(planner.get("answer_shape", "")) == str(expected.get("answer_shape", ""))
        if enforce_dataset_expected
        else True
    )
    checks["practice_policy_match"] = (
        str(planner.get("practice_policy", "")) == str(expected.get("practice_policy", ""))
        if enforce_dataset_expected
        else True
    )
    checks["question_policy_match"] = (
        str(planner.get("question_policy", "")) == str(expected.get("question_policy", ""))
        if enforce_dataset_expected
        else True
    )
    checks["revoicing_policy_match"] = (
        str(planner.get("revoicing_policy", "")) == str(expected.get("revoicing_policy", ""))
        if enforce_dataset_expected
        else True
    )

    required_avoid = [str(item) for item in list(expected.get("required_must_avoid_contains", []) or []) if str(item).strip()]
    checks["required_must_avoid_contains"] = (
        all(_contains_text(must_avoid, token) for token in required_avoid)
        if enforce_dataset_expected
        else True
    )

    if expected_local is not None:
        keys = ("next_move", "answer_shape", "practice_policy", "question_policy", "revoicing_policy")
        checks["local_expected_match"] = all(
            str(planner.get(key, "")) == str(expected_local.get(key, "")) for key in keys
        )
    else:
        checks["local_expected_match"] = True

    if mode == "live":
        checks["response_planner_error_null"] = planner.get("response_planner_error") is None
        checks["no_fallback_source_for_acceptance"] = "_fallback_source" not in planner
    else:
        checks["response_planner_error_null"] = True
        checks["no_fallback_source_for_acceptance"] = True

    for key, ok in checks.items():
        if not ok:
            if key == "enabled_true":
                failure_reasons.append("response_planner_disabled")
            elif key == "response_planner_error_null":
                failure_reasons.append("response_planner_error_present")
            elif key == "no_fallback_source_for_acceptance" and mode == "live":
                failure_reasons.append("live_response_planner_fallback_not_allowed_for_acceptance")
            else:
                failure_reasons.append(key)

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failure_reasons": failure_reasons,
    }


def _run_dry(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for case in cases:
        signals = _build_case_signals(case)
        planner = _local_expected_planner(
            user_message=str(signals["user_message"]),
            thread_state=signals["thread_state"],
            state_snapshot=signals["state_snapshot"],
            active_line=dict(signals["active_line"]),
            knowledge_answer_guard=dict(signals["knowledge_answer_guard"]),
            philosophy_kernel=dict(signals["philosophy_kernel"]),
        )
        evaluation = _evaluate_case(case=case, actual=planner, expected_local=planner, mode="dry")
        item = {
            "case_id": str(case.get("case_id", "unknown")),
            "group": case.get("group"),
            "mode": "dry",
            "query": str(signals["user_message"]),
            "response_planner": planner,
            "evaluation": evaluation,
        }
        results.append(item)
        samples.append(
            {
                "mode": "dry",
                "case_id": item["case_id"],
                "response_planner": planner,
            }
        )
    return results, samples


def _signals_from_debug(debug: dict[str, Any], query: str) -> dict[str, Any]:
    active_line = dict(debug.get("active_line", {})) if isinstance(debug.get("active_line"), dict) else {}
    knowledge_answer = dict(debug.get("knowledge_answer", {})) if isinstance(debug.get("knowledge_answer"), dict) else {}
    practice_gate = dict(debug.get("practice_gate", {})) if isinstance(debug.get("practice_gate"), dict) else {}
    return {
        "user_message": query,
        "thread_state": _as_ns(
            {
                "response_mode": debug.get("response_mode"),
                "safety_active": bool(debug.get("safety_flag", False)),
                "ok_position": debug.get("ok_position"),
            }
        ),
        "state_snapshot": _as_ns(
            {
                "safety_flag": bool(debug.get("safety_flag", False)),
                "nervous_state": debug.get("nervous_state"),
            }
        ),
        "active_line": active_line,
        "knowledge_answer_guard": {
            "knowledge_answer": knowledge_answer,
            "practice_gate": practice_gate,
        },
        "philosophy_kernel": dict(debug.get("philosophy_kernel", {})) if isinstance(debug.get("philosophy_kernel"), dict) else {},
    }


async def _run_direct_async(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from bot_agent.multiagent.orchestrator import orchestrator

    results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    run_nonce = uuid.uuid4().hex[:8]
    user_by_thread: dict[str, str] = {}

    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id", f"case_{index}"))
        thread_id = str(case.get("thread_id", f"thread_{index}"))
        turns = [item for item in list(case.get("turns", []) or []) if isinstance(item, dict)]
        query = str(turns[-1].get("content", "") if turns else "")
        if thread_id not in user_by_thread:
            user_by_thread[thread_id] = f"prd0474_direct_{run_nonce}_{thread_id}"
        user_id = user_by_thread[thread_id]

        result = await orchestrator.run(query=query, user_id=user_id)
        debug = dict(result.get("debug", {}))
        actual = dict(debug.get("response_planner", {})) if isinstance(debug.get("response_planner"), dict) else None
        if isinstance(actual, dict) and debug.get("response_planner_error") is not None:
            actual["response_planner_error"] = debug.get("response_planner_error")

        signals = _signals_from_debug(debug, query)
        expected_local = _local_expected_planner(
            user_message=signals["user_message"],
            thread_state=signals["thread_state"],
            state_snapshot=signals["state_snapshot"],
            active_line=dict(signals["active_line"]),
            knowledge_answer_guard=dict(signals["knowledge_answer_guard"]),
            philosophy_kernel=dict(signals["philosophy_kernel"]),
        )
        evaluation = _evaluate_case(
            case=case,
            actual=actual,
            expected_local=expected_local,
            mode="direct",
            failure_reason="missing_direct_debug_response_planner",
        )

        item = {
            "case_id": case_id,
            "group": case.get("group"),
            "mode": "direct",
            "query": query,
            "response_planner": actual,
            "expected_local": expected_local,
            "evaluation": evaluation,
        }
        results.append(item)
        samples.append(
            {
                "mode": "direct",
                "case_id": case_id,
                "response_planner": actual,
            }
        )
    return results, samples


def _http_json_request(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: float = 90.0,
) -> tuple[int, dict[str, Any]]:
    body = None
    req_headers = dict(headers)
    if payload is not None:
        req_headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url=url, method=method.upper(), headers=req_headers, data=body)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status_code = int(getattr(response, "status", 200))
        raw = response.read().decode("utf-8")
        data = json.loads(raw) if raw.strip() else {}
        return status_code, data if isinstance(data, dict) else {"raw": data}


def _extract_live_actual_planner(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    debug = dict(payload.get("debug", {})) if isinstance(payload.get("debug"), dict) else {}
    trace = dict(payload.get("trace", {})) if isinstance(payload.get("trace"), dict) else {}

    actual = None
    if isinstance(debug.get("response_planner"), dict):
        actual = dict(debug.get("response_planner"))
    elif isinstance(trace.get("response_planner"), dict):
        actual = dict(trace.get("response_planner"))
    else:
        return None, "missing_live_api_debug_response_planner"

    if debug.get("response_planner_error") is not None:
        actual["response_planner_error"] = debug.get("response_planner_error")
        return actual, "live_response_planner_error_present"
    if trace.get("response_planner_error") is not None:
        actual["response_planner_error"] = trace.get("response_planner_error")
        return actual, "live_response_planner_error_present"
    if not bool(actual.get("enabled", False)):
        return actual, "live_response_planner_disabled"
    if "_fallback_source" in actual:
        return actual, "live_response_planner_fallback_not_allowed_for_acceptance"
    return actual, None


def _run_live(
    cases: list[dict[str, Any]],
    *,
    base_url: str,
    api_key: str,
    admin_runtime_url: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headers = {"X-API-Key": api_key}
    try:
        status, payload = _http_json_request(method="GET", url=admin_runtime_url, headers=headers, timeout=30)
        if status != 200:
            return (
                {
                    "live_status": "failed",
                    "reason": f"admin_runtime_probe_status_{status}",
                    "case_results": [],
                },
                [],
            )
        planner_block = payload.get("response_planner")
        if not isinstance(planner_block, dict):
            return (
                {
                    "live_status": "failed",
                    "reason": "admin_runtime_missing_response_planner_block",
                    "case_results": [],
                },
                [],
            )
    except Exception as exc:  # noqa: BLE001
        return (
            {
                "live_status": "failed",
                "reason": f"admin_runtime_probe_failed:{exc}",
                "case_results": [],
            },
            [],
        )

    results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    user_by_thread: dict[str, str] = {}
    session_by_thread: dict[str, str] = {}

    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id", f"case_{index}"))
        thread_id = str(case.get("thread_id", f"thread_{index}"))
        turns = [item for item in list(case.get("turns", []) or []) if isinstance(item, dict)]
        query = str(turns[-1].get("content", "") if turns else "")

        if thread_id not in user_by_thread:
            user_by_thread[thread_id] = f"prd0474_live_user_{index}_{thread_id}"
            session_by_thread[thread_id] = f"prd0474_live_session_{index}_{thread_id}"

        failure_reason: str | None = None
        api_errors: list[str] = []
        payload: dict[str, Any] = {}
        actual: dict[str, Any] | None = None
        expected_local: dict[str, Any] | None = None

        try:
            status, payload = _http_json_request(
                method="POST",
                url=f"{base_url.rstrip('/')}/questions/adaptive",
                headers=headers,
                payload={
                    "query": query,
                    "user_id": user_by_thread[thread_id],
                    "session_id": session_by_thread[thread_id],
                    "debug": True,
                },
            )
            if status != 200:
                failure_reason = f"live_status_{status}"
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            api_errors.append(f"http_error={exc.code}:{detail}")
            failure_reason = "live_http_error"
        except Exception as exc:  # noqa: BLE001
            api_errors.append(str(exc))
            failure_reason = "live_request_exception"

        if failure_reason is None:
            actual, live_failure = _extract_live_actual_planner(payload)
            if live_failure is not None:
                failure_reason = live_failure

        debug = dict(payload.get("debug", {})) if isinstance(payload.get("debug"), dict) else {}
        if debug:
            signals = _signals_from_debug(debug, query)
            expected_local = _local_expected_planner(
                user_message=signals["user_message"],
                thread_state=signals["thread_state"],
                state_snapshot=signals["state_snapshot"],
                active_line=dict(signals["active_line"]),
                knowledge_answer_guard=dict(signals["knowledge_answer_guard"]),
                philosophy_kernel=dict(signals["philosophy_kernel"]),
            )

        evaluation = _evaluate_case(
            case=case,
            actual=actual,
            expected_local=expected_local,
            mode="live",
            failure_reason=failure_reason,
        )
        if failure_reason and failure_reason not in evaluation["failure_reasons"]:
            evaluation["failure_reasons"].append(failure_reason)
            evaluation["passed"] = False

        item = {
            "case_id": case_id,
            "group": case.get("group"),
            "mode": "live",
            "query": query,
            "api_errors": api_errors,
            "response_planner": actual,
            "expected_local": expected_local,
            "evaluation": evaluation,
        }
        results.append(item)
        samples.append(
            {
                "mode": "live",
                "case_id": case_id,
                "response_planner": actual,
                "failure_reason": failure_reason,
            }
        )

    return ({"live_status": "passed", "reason": "", "case_results": results}, samples)


def _build_summary(case_results: list[dict[str, Any]]) -> dict[str, int]:
    total = len(case_results)
    passed = sum(1 for item in case_results if bool(item.get("evaluation", {}).get("passed")))
    return {"cases_total": total, "cases_passed": passed, "cases_failed": max(0, total - passed)}


def _build_policy_violations_report(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    violations = []
    for item in case_results:
        evaluation = dict(item.get("evaluation", {}))
        if bool(evaluation.get("passed", False)):
            continue
        violations.append(
            {
                "case_id": item.get("case_id"),
                "group": item.get("group"),
                "failure_reasons": list(evaluation.get("failure_reasons", [])),
                "checks": dict(evaluation.get("checks", {})),
            }
        )
    return {
        "total_cases": len(case_results),
        "violations_count": len(violations),
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.4 response planner cases.")
    parser.add_argument("--mode", choices=("dry", "direct", "live"), default="dry")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output", default=None)
    parser.add_argument("--trace-samples-output", default=str(DEFAULT_TRACE_SAMPLES))
    parser.add_argument("--policy-violations-output", default=str(DEFAULT_POLICY_VIOLATIONS))
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--api-base-url", default=os.getenv("PRD0474_API_BASE", "http://localhost:8001/api/v1"))
    parser.add_argument("--api-key", default=os.getenv("PRD0474_API_KEY", os.getenv("BOT_API_KEY", "dev-key-001")))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD0474_ADMIN_RUNTIME_URL", "http://localhost:8001/api/admin/runtime/effective"),
    )
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    trace_output_path = _resolve_path(args.trace_samples_output)
    violations_path = _resolve_path(args.policy_violations_output)
    output_path = _resolve_path(args.output) if args.output else DEFAULT_LOG_DIR / f"response_planner_{args.mode}.json"

    cases = _load_cases(dataset_path)
    if args.case_id:
        cases = [item for item in cases if str(item.get("case_id", "")) == str(args.case_id)]
        if not cases:
            raise ValueError(f"case-id not found: {args.case_id}")
    if args.limit is not None and args.limit > 0:
        cases = cases[: args.limit]

    if args.mode == "dry":
        case_results, samples = _run_dry(cases)
        payload = {
            "prd_id": "PRD-047.4",
            "mode": "dry",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": _build_summary(case_results),
            "case_results": case_results,
        }
        _write_json(output_path, payload)
        _write_json(trace_output_path, {"prd_id": "PRD-047.4", "mode": "dry", "samples": samples})
        _write_json(violations_path, _build_policy_violations_report(case_results))
        print(output_path)
        return 0

    if args.mode == "direct":
        case_results, samples = asyncio.run(_run_direct_async(cases))
        payload = {
            "prd_id": "PRD-047.4",
            "mode": "direct",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": _build_summary(case_results),
            "case_results": case_results,
        }
        _write_json(output_path, payload)
        _write_json(trace_output_path, {"prd_id": "PRD-047.4", "mode": "direct", "samples": samples})
        _write_json(violations_path, _build_policy_violations_report(case_results))
        print(output_path)
        return 0

    live_payload, samples = _run_live(
        cases,
        base_url=str(args.api_base_url),
        api_key=str(args.api_key),
        admin_runtime_url=str(args.admin_runtime_url),
    )
    if str(live_payload.get("live_status")) != "passed":
        payload = {
            "prd_id": "PRD-047.4",
            "mode": "live",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": {"cases_total": 0, "cases_passed": 0, "cases_failed": 0},
            "case_results": [],
            "live_status": str(live_payload.get("live_status")),
            "reason": str(live_payload.get("reason", "")),
        }
        _write_json(output_path, payload)
        _write_json(trace_output_path, {"prd_id": "PRD-047.4", "mode": "live", "samples": samples})
        _write_json(violations_path, {"total_cases": 0, "violations_count": 0, "violations": []})
        print(output_path)
        return 0

    case_results = list(live_payload.get("case_results", []))
    payload = {
        "prd_id": "PRD-047.4",
        "mode": "live",
        "timestamp_utc": _now_iso(),
        "dataset": str(dataset_path),
        "summary": _build_summary(case_results),
        "case_results": case_results,
        "live_status": "passed",
        "reason": "",
    }
    _write_json(output_path, payload)
    _write_json(trace_output_path, {"prd_id": "PRD-047.4", "mode": "live", "samples": samples})
    _write_json(violations_path, _build_policy_violations_report(case_results))
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
