#!/usr/bin/env python3
"""Run PRD-047.6 planner runtime drift guard evaluation cases."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.planner_drift_guard import (  # noqa: E402
    PLANNER_DRIFT_GUARD_VERSION,
    build_planner_drift_check,
)

REQUIRED_GROUP_MIN_COUNTS = {
    "safety_grounding_positive": 4,
    "safety_grounding_negative": 3,
    "short_support_positive": 4,
    "short_support_negative": 3,
    "question_policy_none": 3,
    "practice_policy_forbidden": 3,
    "gentle_close": 3,
    "one_step": 3,
    "known_concept_direct": 3,
    "defensive_one_question": 3,
}

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_6_planner_drift_cases.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.6"


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
    items = [item for item in payload if isinstance(item, dict)]
    return sorted(items, key=lambda item: str(item.get("case_id", "")))


def _validate_dataset(cases: list[dict[str, Any]]) -> tuple[bool, list[str], dict[str, int]]:
    errors: list[str] = []
    coverage: dict[str, int] = {}

    if len(cases) < 32:
        errors.append(f"dataset_too_small:{len(cases)}")

    for idx, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id", "") or f"case_{idx}")
        group = str(case.get("group", "")).strip()
        coverage[group] = coverage.get(group, 0) + 1

        turns = [item for item in list(case.get("turns", []) or []) if isinstance(item, dict)]
        if not turns:
            errors.append(f"{case_id}:missing_turns")
        if not any(str(item.get("role", "")).lower() == "user" for item in turns):
            errors.append(f"{case_id}:missing_user_turn")

        planner = case.get("planner")
        if not isinstance(planner, dict):
            errors.append(f"{case_id}:missing_planner")
        else:
            for key in (
                "next_move",
                "answer_shape",
                "question_policy",
                "practice_policy",
                "revoicing_policy",
            ):
                if not str(planner.get(key, "")).strip():
                    errors.append(f"{case_id}:missing_planner_{key}")

        candidate_answer = str(case.get("candidate_answer", "") or "").strip()
        if not candidate_answer:
            errors.append(f"{case_id}:missing_candidate_answer")

        expected = case.get("expected_drift")
        if not isinstance(expected, dict):
            errors.append(f"{case_id}:missing_expected_drift")
        else:
            status = str(expected.get("status", "") or "")
            if status not in {"ok", "warning", "critical"}:
                errors.append(f"{case_id}:invalid_expected_status")

    for group, minimum in REQUIRED_GROUP_MIN_COUNTS.items():
        count = coverage.get(group, 0)
        if count < minimum:
            errors.append(f"group_coverage_failed:{group}:{count}<{minimum}")

    return len(errors) == 0, errors, coverage


def _extract_query(case: dict[str, Any]) -> str:
    turns = [item for item in list(case.get("turns", []) or []) if isinstance(item, dict)]
    for turn in reversed(turns):
        if str(turn.get("role", "")).lower() == "user":
            return str(turn.get("content", "") or "")
    return ""


def _evaluate_direct_case(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("case_id", ""))
    planner = dict(case.get("planner", {})) if isinstance(case.get("planner"), dict) else {}
    candidate_answer = str(case.get("candidate_answer", "") or "")
    expected = dict(case.get("expected_drift", {})) if isinstance(case.get("expected_drift"), dict) else {}

    check = build_planner_drift_check(response_planner=planner, final_answer=candidate_answer).to_dict()

    expected_status = str(expected.get("status", "ok") or "ok")
    must_have = [
        str(flag) for flag in list(expected.get("must_have_flags", []) or []) if str(flag).strip()
    ]
    must_not_have = [
        str(flag) for flag in list(expected.get("must_not_have_flags", []) or []) if str(flag).strip()
    ]

    checks = {
        "status_match": str(check.get("status", "")) == expected_status,
        "must_have_flags": all(flag in list(check.get("flags", []) or []) for flag in must_have),
        "must_not_have_flags": all(flag not in list(check.get("flags", []) or []) for flag in must_not_have),
        "version_match": str(check.get("version", "")) == PLANNER_DRIFT_GUARD_VERSION,
    }
    failure_reasons = [key for key, ok in checks.items() if not ok]
    passed = not failure_reasons

    return {
        "case_id": case_id,
        "group": case.get("group"),
        "query": _extract_query(case),
        "evaluation": {
            "passed": passed,
            "checks": checks,
            "failure_reasons": failure_reasons,
            "expected": expected,
            "actual": check,
        },
        "planner": planner,
    }


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


def _extract_live_drift_payload(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    debug = dict(payload.get("debug", {})) if isinstance(payload.get("debug"), dict) else {}
    trace = dict(payload.get("trace", {})) if isinstance(payload.get("trace"), dict) else {}

    drift = None
    if isinstance(debug.get("planner_drift_guard"), dict):
        drift = dict(debug.get("planner_drift_guard"))
    elif isinstance(trace.get("planner_drift_guard"), dict):
        drift = dict(trace.get("planner_drift_guard"))
    else:
        return None, "missing_live_api_debug_planner_drift_guard"

    drift_error = debug.get("planner_drift_guard_error")
    if drift_error is None:
        drift_error = trace.get("planner_drift_guard_error")
    if drift_error is not None:
        drift["planner_drift_guard_error"] = drift_error
        return drift, "live_planner_drift_guard_error_present"

    if str(drift.get("version", "")) != PLANNER_DRIFT_GUARD_VERSION:
        return drift, "live_planner_drift_guard_version_mismatch"

    if not bool(drift.get("enabled", False)):
        return drift, "live_planner_drift_guard_disabled"

    if "drift_guard_exception" in list(drift.get("flags", []) or []):
        return drift, "live_planner_drift_guard_exception_fallback"

    return drift, None


def _build_summary(case_results: list[dict[str, Any]]) -> dict[str, int]:
    total = len(case_results)
    passed = sum(1 for item in case_results if bool(item.get("evaluation", {}).get("passed", False)))
    return {
        "cases_total": total,
        "cases_passed": passed,
        "cases_failed": max(0, total - passed),
    }


def _strict_drift_counters(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    warning_count = 0
    critical_count = 0
    missing_payload_count = 0
    fallback_used = False

    for item in case_results:
        evaluation = dict(item.get("evaluation", {}))
        actual = dict(evaluation.get("actual", {})) if isinstance(evaluation.get("actual"), dict) else {}
        reasons = [str(reason) for reason in list(evaluation.get("failure_reasons", []) or [])]
        status = str(actual.get("status", ""))
        if status == "warning":
            warning_count += 1
        elif status == "critical":
            critical_count += 1
        if any(reason.startswith("missing_live_api_debug_planner_drift_guard") for reason in reasons):
            missing_payload_count += 1
        if any("fallback" in reason for reason in reasons):
            fallback_used = True

    return {
        "warning_count": warning_count,
        "critical_count": critical_count,
        "missing_drift_payload_count": missing_payload_count,
        "runner_side_fallback_used": fallback_used,
    }


def _build_negative_regression() -> dict[str, Any]:
    regression_cases = [
        {
            "case_id": "neg_001_safety_mechanism",
            "planner": {
                "next_move": "stabilize_safety",
                "answer_shape": "safety_grounding",
                "question_policy": "none",
                "practice_policy": "required_for_safety_or_grounding",
                "revoicing_policy": "suppressed",
            },
            "answer": "Это механизм прогнозирования и контроля, давай разберем его подробно.",
            "required_flag": "safety_mechanism_drift",
        },
        {
            "case_id": "neg_002_short_support_lecture",
            "planner": {
                "next_move": "give_short_support",
                "answer_shape": "short_support",
                "question_policy": "none",
                "practice_policy": "forbidden",
                "revoicing_policy": "suppressed",
            },
            "answer": (
                "Это длинная теория о механизме контроля и стратегии, которая объясняет цикл в деталях, "
                "добавляет расширенный анализ, несколько уровней интерпретации и повторяющиеся пояснения, "
                "чтобы ответ вышел заметно длиннее ожидаемого поддерживающего формата."
            ),
            "required_flag": "short_support_missing_contact",
        },
        {
            "case_id": "neg_003_question_policy",
            "planner": {
                "next_move": "deepen_mechanism",
                "answer_shape": "mechanism_explanation",
                "question_policy": "none",
                "practice_policy": "forbidden",
                "revoicing_policy": "suppressed",
            },
            "answer": "Почему ты снова идешь в этот цикл?",
            "required_flag": "question_policy_violation",
        },
        {
            "case_id": "neg_004_practice_forbidden",
            "planner": {
                "next_move": "deepen_mechanism",
                "answer_shape": "mechanism_explanation",
                "question_policy": "none",
                "practice_policy": "forbidden",
                "revoicing_policy": "suppressed",
            },
            "answer": "Сделай упражнение: поставь таймер и выпиши три пункта.",
            "required_flag": "practice_policy_forbidden_violation",
        },
        {
            "case_id": "neg_005_close_new_loop",
            "planner": {
                "next_move": "close_gently",
                "answer_shape": "gentle_close",
                "question_policy": "none",
                "practice_policy": "forbidden",
                "revoicing_policy": "minimal_allowed",
            },
            "answer": "Хочешь, я дам новое задание на завтра?",
            "required_flag": "close_opened_new_loop",
        },
    ]

    case_results: list[dict[str, Any]] = []
    for item in regression_cases:
        check = build_planner_drift_check(
            response_planner=dict(item["planner"]),
            final_answer=str(item["answer"]),
        ).to_dict()
        required_flag = str(item["required_flag"])
        status = str(check.get("status", "ok"))
        passed = status in {"warning", "critical"} and required_flag in list(check.get("flags", []) or [])
        case_results.append(
            {
                "case_id": item["case_id"],
                "required_flag": required_flag,
                "actual_status": status,
                "actual_flags": list(check.get("flags", []) or []),
                "passed": passed,
            }
        )

    return {
        "prd_id": "PRD-047.6",
        "version": PLANNER_DRIFT_GUARD_VERSION,
        "expected_passed": False,
        "actual_passed": all(bool(item.get("passed")) for item in case_results),
        "case_results": case_results,
    }


def _run_live(
    cases: list[dict[str, Any]],
    *,
    base_url: str,
    api_key: str,
    admin_runtime_url: str,
    repeat: int,
) -> dict[str, Any]:
    headers = {"X-API-Key": api_key}

    try:
        runtime_status, runtime_payload = _http_json_request(
            method="GET",
            url=admin_runtime_url,
            headers=headers,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "live_status": "failed",
            "reason": f"admin_runtime_probe_failed:{exc}",
            "case_results": [],
            "strict_drift": {
                "warning_count": 0,
                "critical_count": 0,
                "missing_drift_payload_count": 0,
                "runner_side_fallback_used": False,
            },
            "fresh_backend_confirmed": False,
            "admin_runtime_effective_contains_planner_drift_guard": False,
            "live_trace_contains_debug_planner_drift_guard": False,
        }

    if runtime_status != 200:
        return {
            "live_status": "failed",
            "reason": f"admin_runtime_probe_status_{runtime_status}",
            "case_results": [],
            "strict_drift": {
                "warning_count": 0,
                "critical_count": 0,
                "missing_drift_payload_count": 0,
                "runner_side_fallback_used": False,
            },
            "fresh_backend_confirmed": False,
            "admin_runtime_effective_contains_planner_drift_guard": False,
            "live_trace_contains_debug_planner_drift_guard": False,
        }

    planner_drift_block = runtime_payload.get("planner_drift_guard")
    if not isinstance(planner_drift_block, dict):
        return {
            "live_status": "failed",
            "reason": "admin_runtime_missing_planner_drift_guard_block",
            "case_results": [],
            "strict_drift": {
                "warning_count": 0,
                "critical_count": 0,
                "missing_drift_payload_count": 0,
                "runner_side_fallback_used": False,
            },
            "fresh_backend_confirmed": False,
            "admin_runtime_effective_contains_planner_drift_guard": False,
            "live_trace_contains_debug_planner_drift_guard": False,
        }

    live_cases = [item for item in cases if bool(item.get("live_replay", False))]
    if not live_cases:
        live_cases = [item for item in cases if "positive" in str(item.get("group", ""))][:3]
    if not live_cases:
        live_cases = cases[:3]

    results: list[dict[str, Any]] = []
    missing_payload_count = 0
    trace_payload_seen = False
    fallback_used = False

    for rep in range(max(1, int(repeat))):
        for index, case in enumerate(live_cases, start=1):
            case_id = str(case.get("case_id", f"case_{index}"))
            query = _extract_query(case)
            user_id = f"prd0476_live_user_{rep+1}_{index}_{uuid.uuid4().hex[:8]}"
            session_id = f"prd0476_live_session_{rep+1}_{index}_{uuid.uuid4().hex[:8]}"

            failure_reason: str | None = None
            api_errors: list[str] = []
            payload: dict[str, Any] = {}
            drift_payload: dict[str, Any] | None = None

            try:
                status, payload = _http_json_request(
                    method="POST",
                    url=f"{base_url.rstrip('/')}/questions/adaptive",
                    headers=headers,
                    payload={
                        "query": query,
                        "user_id": user_id,
                        "session_id": session_id,
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
                drift_payload, failure_reason = _extract_live_drift_payload(payload)
                if drift_payload is not None:
                    trace_payload_seen = True

            if failure_reason == "missing_live_api_debug_planner_drift_guard":
                missing_payload_count += 1
            if failure_reason and "fallback" in failure_reason:
                fallback_used = True

            expected_status = str(dict(case.get("expected_drift", {})).get("status", "ok") or "ok")
            actual_status = str(dict(drift_payload or {}).get("status", ""))
            must_have = [
                str(flag)
                for flag in list(dict(case.get("expected_drift", {})).get("must_have_flags", []) or [])
                if str(flag).strip()
            ]
            actual_flags = [str(flag) for flag in list(dict(drift_payload or {}).get("flags", []) or [])]

            checks = {
                "drift_payload_present": drift_payload is not None,
                "drift_payload_error_absent": failure_reason is None,
                "expected_status_match": actual_status == expected_status,
                "expected_flags_present": all(flag in actual_flags for flag in must_have),
            }

            evaluation_reasons = [key for key, ok in checks.items() if not ok]
            if failure_reason and failure_reason not in evaluation_reasons:
                evaluation_reasons.append(failure_reason)

            results.append(
                {
                    "case_id": case_id,
                    "group": case.get("group"),
                    "repeat_index": rep + 1,
                    "query": query,
                    "api_errors": api_errors,
                    "evaluation": {
                        "passed": len(evaluation_reasons) == 0,
                        "checks": checks,
                        "failure_reasons": evaluation_reasons,
                        "expected": dict(case.get("expected_drift", {})),
                        "actual": dict(drift_payload or {}),
                    },
                }
            )

    strict_drift = _strict_drift_counters(results)
    strict_drift["missing_drift_payload_count"] = missing_payload_count
    strict_drift["runner_side_fallback_used"] = fallback_used

    warning_count = strict_drift["warning_count"]
    critical_count = strict_drift["critical_count"]
    acceptance_passed = (
        critical_count == 0
        and warning_count <= 1
        and missing_payload_count == 0
        and fallback_used is False
    )

    return {
        "live_status": "passed" if acceptance_passed else "failed",
        "reason": "" if acceptance_passed else "live_acceptance_failed",
        "repeat": max(1, int(repeat)),
        "live_case_count": len(live_cases),
        "total_live_samples": len(results),
        "case_results": results,
        "strict_drift": strict_drift,
        "fresh_backend_confirmed": True,
        "admin_runtime_effective_contains_planner_drift_guard": True,
        "live_trace_contains_debug_planner_drift_guard": trace_payload_seen,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.6 planner drift guard cases.")
    parser.add_argument("--mode", choices=("dry", "direct", "live"), default="dry")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output", default=None)
    parser.add_argument("--summary-output", default=str(DEFAULT_LOG_DIR / "planner_drift_summary.json"))
    parser.add_argument(
        "--negative-regression-output",
        default=str(DEFAULT_LOG_DIR / "planner_drift_negative_regression.json"),
    )
    parser.add_argument("--api-base-url", default=os.getenv("PRD0476_API_BASE", "http://127.0.0.1:8015/api/v1"))
    parser.add_argument("--api-key", default=os.getenv("PRD0476_API_KEY", os.getenv("BOT_API_KEY", "dev-key-001")))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD0476_ADMIN_RUNTIME_URL", "http://127.0.0.1:8015/api/admin/runtime/effective"),
    )
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    output_path = _resolve_path(args.output) if args.output else DEFAULT_LOG_DIR / f"planner_drift_{args.mode}.json"
    summary_path = _resolve_path(args.summary_output)
    negative_path = _resolve_path(args.negative_regression_output)

    cases = _load_cases(dataset_path)
    if args.case_id:
        cases = [item for item in cases if str(item.get("case_id", "")) == str(args.case_id)]
        if not cases:
            raise ValueError(f"case-id not found: {args.case_id}")
    if args.limit is not None and args.limit > 0:
        cases = cases[: args.limit]

    dataset_ok, dataset_errors, coverage = _validate_dataset(cases)

    if args.mode == "dry":
        case_results = []
        for case in cases:
            case_results.append(
                {
                    "case_id": case.get("case_id"),
                    "group": case.get("group"),
                    "evaluation": {
                        "passed": dataset_ok,
                        "checks": {"dataset_valid": dataset_ok},
                        "failure_reasons": list(dataset_errors),
                        "expected": dict(case.get("expected_drift", {})),
                        "actual": {},
                    },
                }
            )
        strict = _strict_drift_counters(case_results)
        payload = {
            "prd_id": "PRD-047.6",
            "mode": "dry",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "dataset_valid": dataset_ok,
            "dataset_errors": dataset_errors,
            "coverage": coverage,
            "summary": _build_summary(case_results),
            "strict_drift": strict,
            "case_results": case_results,
        }
    elif args.mode == "direct":
        case_results = [_evaluate_direct_case(case) for case in cases]
        strict = _strict_drift_counters(case_results)
        payload = {
            "prd_id": "PRD-047.6",
            "mode": "direct",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "dataset_valid": dataset_ok,
            "dataset_errors": dataset_errors,
            "coverage": coverage,
            "summary": _build_summary(case_results),
            "strict_drift": strict,
            "case_results": case_results,
        }
    else:
        live_payload = _run_live(
            cases,
            base_url=args.api_base_url,
            api_key=args.api_key,
            admin_runtime_url=args.admin_runtime_url,
            repeat=max(1, int(args.repeat)),
        )
        case_results = list(live_payload.get("case_results", []))
        payload = {
            "prd_id": "PRD-047.6",
            "mode": "live",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "dataset_valid": dataset_ok,
            "dataset_errors": dataset_errors,
            "coverage": coverage,
            "summary": _build_summary(case_results),
            "strict_drift": dict(live_payload.get("strict_drift", {})),
            "fresh_backend_confirmed": bool(live_payload.get("fresh_backend_confirmed", False)),
            "admin_runtime_effective_contains_planner_drift_guard": bool(
                live_payload.get("admin_runtime_effective_contains_planner_drift_guard", False)
            ),
            "live_trace_contains_debug_planner_drift_guard": bool(
                live_payload.get("live_trace_contains_debug_planner_drift_guard", False)
            ),
            "repeat": int(live_payload.get("repeat", max(1, int(args.repeat)))),
            "live_case_count": int(live_payload.get("live_case_count", 0)),
            "total_live_samples": int(live_payload.get("total_live_samples", len(case_results))),
            "live_status": str(live_payload.get("live_status", "failed")),
            "reason": str(live_payload.get("reason", "")),
            "case_results": case_results,
        }

    _write_json(output_path, payload)

    negative_regression = _build_negative_regression()
    _write_json(negative_path, negative_regression)

    summary_payload = {
        "prd_id": "PRD-047.6",
        "mode": args.mode,
        "timestamp_utc": _now_iso(),
        "summary": dict(payload.get("summary", {})),
        "strict_drift": dict(payload.get("strict_drift", {})),
        "dataset_valid": bool(payload.get("dataset_valid", False)),
        "dataset_errors_count": len(list(payload.get("dataset_errors", []) or [])),
        "negative_regression_actual_passed": bool(negative_regression.get("actual_passed", False)),
    }
    _write_json(summary_path, summary_payload)

    print(json.dumps({
        "mode": args.mode,
        "output": str(output_path),
        "summary": payload.get("summary", {}),
        "strict_drift": payload.get("strict_drift", {}),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
