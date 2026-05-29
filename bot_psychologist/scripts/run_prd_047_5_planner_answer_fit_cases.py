#!/usr/bin/env python3
"""Run PRD-047.5-HF1 planner quality calibration and answer-fit cases."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
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

REQUIRED_GROUP_MIN_COUNTS = {
    "low_resource_short_support": 4,
    "soft_distress_safety_adjacent": 3,
    "defensive_i_plus_w_minus": 3,
    "thanks_close": 3,
    "no_question_request": 3,
    "explicit_practice_step": 3,
    "mechanism_continue_regression": 3,
    "known_concept_regression": 2,
    "repair_after_bot_misalignment": 2,
}

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_5_planner_answer_fit_cases.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.5-HF1"
_QUESTION_POLICY_NONE_MARKERS = [
    "что именно",
    "почему",
    "как ты",
    "можешь ли",
    "хочешь",
]
_PRACTICE_POLICY_FORBIDDEN_MARKERS = [
    "практик",
    "упражн",
]
_PRACTICE_POLICY_FORBIDDEN_PATTERNS = [
    r"\bсделай\b",
    r"\bпопробуй\b",
    r"\bпоставь\s+таймер\b",
    r"\bтаймер\b",
    r"\bвдох\b",
    r"\bвыдох\b",
    r"\b(?:один|первый)\s+шаг\b",
    r"\bзапиши\b",
    r"\bвыпиши\b",
]
_PRACTICE_NEGATION_PATTERNS = [
    r"\bне\s+даю\b",
    r"\bне\s+нужно\b",
    r"\bбез\s+практик\w*",
    r"\bне\s+предлага\w+\s+практик\w*",
]
_SAFETY_ANALYSIS_MARKERS = [
    "механизм",
    "прогнозирован",
    "контрол",
    "съедает ресурс",
    "до начала действия",
    "активная линия",
    "паттерн",
    "драйвер",
    "программа",
]
_SAFETY_GROUNDING_MARKERS = [
    "я рядом",
    "сейчас",
    "здесь",
    "опора",
    "стабилизир",
    "снизить перегруз",
    "не нужно разбирать",
    "коротко",
    "без давления",
]
_SHORT_SUPPORT_ANALYSIS_MARKERS = [
    "механизм",
    "теория",
    "стратегия",
    "прогнозирован",
    "контрол",
    "паттерн",
]
_SUPPORTIVE_CONTACT_MARKERS = [
    "я рядом",
    "коротко",
    "без давления",
    "не нужно",
    "поддерж",
]


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


def _write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("dataset must be list")
    items = [item for item in payload if isinstance(item, dict)]
    return sorted(items, key=lambda item: str(item.get("case_id", "")))


def _contains_any(text: str, markers: list[str]) -> bool:
    lowered = str(text or "").lower()
    return any(str(marker or "").lower() in lowered for marker in markers)


def _count_questions(text: str) -> int:
    return str(text or "").count("?")


def _contains_any_regex(text: str, patterns: list[str]) -> bool:
    lowered = str(text or "").lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def _has_forbidden_practice_instruction(text: str) -> bool:
    lowered = str(text or "").lower()
    has_marker = _contains_any(lowered, _PRACTICE_POLICY_FORBIDDEN_MARKERS) or _contains_any_regex(
        lowered, _PRACTICE_POLICY_FORBIDDEN_PATTERNS
    )
    if not has_marker:
        return False
    if _contains_any_regex(lowered, _PRACTICE_NEGATION_PATTERNS):
        return False
    return True


def _planner_case_signature(planner: dict[str, Any]) -> str:
    next_move = str(planner.get("next_move", "") or "")
    answer_shape = str(planner.get("answer_shape", "") or "")
    return f"{next_move}:{answer_shape}"


def _validate_dataset(cases: list[dict[str, Any]]) -> tuple[bool, list[str], dict[str, int]]:
    errors: list[str] = []
    coverage: dict[str, int] = {}

    if len(cases) < 22:
        errors.append(f"dataset_too_small:{len(cases)}")

    for idx, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id", "") or f"case_{idx}")
        group = str(case.get("group", "")).strip()
        coverage[group] = coverage.get(group, 0) + 1

        turns = [item for item in list(case.get("turns", []) or []) if isinstance(item, dict)]
        if not turns:
            errors.append(f"{case_id}:missing_turns")
            continue
        if not any(str(t.get("role", "")).lower() == "user" for t in turns):
            errors.append(f"{case_id}:missing_user_turn")

        expected_planner = dict(case.get("expected_planner", {}))
        expected_fit = dict(case.get("expected_answer_fit", {}))
        for key in ("next_move", "answer_shape", "response_depth", "question_policy", "practice_policy", "revoicing_policy"):
            if not str(expected_planner.get(key, "")).strip():
                errors.append(f"{case_id}:missing_expected_planner_{key}")
        if "max_chars" not in expected_fit:
            errors.append(f"{case_id}:missing_expected_answer_fit_max_chars")
        if "max_questions" not in expected_fit:
            errors.append(f"{case_id}:missing_expected_answer_fit_max_questions")

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


def _evaluate_planner(actual: dict[str, Any] | None, expected: dict[str, Any]) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    reasons: list[str] = []
    planner = dict(actual or {})

    checks["planner_present"] = isinstance(actual, dict) and bool(actual)
    if not checks["planner_present"]:
        return checks, ["missing_response_planner"]

    checks["enabled_true"] = bool(planner.get("enabled", False))
    for key in ("next_move", "answer_shape", "response_depth", "question_policy", "practice_policy", "revoicing_policy"):
        checks[f"{key}_match"] = str(planner.get(key, "")) == str(expected.get(key, ""))

    if not checks["enabled_true"]:
        reasons.append("response_planner_disabled")
    for key, ok in checks.items():
        if not ok and key not in {"planner_present", "enabled_true"}:
            reasons.append(key)
    return checks, reasons


def _answer_has_one_step(text: str) -> bool:
    lowered = str(text or "").lower()
    if re.search(r"(^|\n)\s*(?:[-*•]|\d+[.)])\s+", lowered):
        return False
    step_markers = ("сделай", "начни", "открой", "выбери", "напиши", "шаг")
    return any(marker in lowered for marker in step_markers)


def _evaluate_answer_fit(answer: str, expected_fit: dict[str, Any], expected_planner: dict[str, Any]) -> tuple[dict[str, bool], list[str]]:
    checks: dict[str, bool] = {}
    reasons: list[str] = []
    text = str(answer or "").strip()
    lowered = text.lower()

    checks["answer_present"] = bool(text)
    if not checks["answer_present"]:
        return checks, ["missing_final_answer"]

    max_chars_raw = expected_fit.get("max_chars", 10000)
    max_questions_raw = expected_fit.get("max_questions", 10)
    max_chars = int(max_chars_raw if max_chars_raw is not None else 10000)
    max_questions = int(max_questions_raw if max_questions_raw is not None else 10)
    forbidden = [str(item) for item in list(expected_fit.get("forbidden_markers", []) or []) if str(item).strip()]
    required_any = [str(item) for item in list(expected_fit.get("required_semantics_any", []) or []) if str(item).strip()]

    checks["max_chars"] = len(text) <= max_chars
    checks["max_questions"] = _count_questions(text) <= max_questions
    checks["forbidden_markers"] = not _contains_any(lowered, forbidden)
    checks["required_semantics_any"] = True if not required_any else _contains_any(lowered, required_any)

    expected_shape = str(expected_planner.get("answer_shape", "") or "")
    expected_move = str(expected_planner.get("next_move", "") or "")
    expected_question_policy = str(expected_planner.get("question_policy", "") or "")
    expected_practice_policy = str(expected_planner.get("practice_policy", "") or "")

    if expected_shape == "one_step":
        checks["one_step_shape"] = _answer_has_one_step(text)
    else:
        checks["one_step_shape"] = True

    if expected_move == "close_gently":
        checks["close_no_new_loop"] = (_count_questions(text) == 0) and not _contains_any(lowered, ["практик", "упражн", "шаг", "таймер"])
    else:
        checks["close_no_new_loop"] = True

    if expected_move == "clarify_one_point":
        checks["clarify_has_one_question"] = _count_questions(text) == 1
    else:
        checks["clarify_has_one_question"] = True

    if expected_move == "give_short_support":
        checks["short_support_not_lecture"] = len(text) <= max_chars and not _contains_any(lowered, _SHORT_SUPPORT_ANALYSIS_MARKERS)
        checks["short_support_supportive_contact"] = _contains_any(lowered, _SUPPORTIVE_CONTACT_MARKERS)
        checks["short_support_no_practice"] = not _has_forbidden_practice_instruction(lowered)
        checks["short_support_no_question"] = _count_questions(text) == 0
    else:
        checks["short_support_not_lecture"] = True
        checks["short_support_supportive_contact"] = True
        checks["short_support_no_practice"] = True
        checks["short_support_no_question"] = True

    if expected_move == "stabilize_safety":
        checks["safety_shape_short"] = len(text) <= max_chars and _count_questions(text) == 0
        checks["safety_no_mechanism_language"] = not _contains_any(lowered, _SAFETY_ANALYSIS_MARKERS)
        checks["safety_has_grounding_semantics"] = _contains_any(lowered, _SAFETY_GROUNDING_MARKERS)
        checks["safety_no_unsolicited_practice"] = not _has_forbidden_practice_instruction(lowered)
    else:
        checks["safety_shape_short"] = True
        checks["safety_no_mechanism_language"] = True
        checks["safety_has_grounding_semantics"] = True
        checks["safety_no_unsolicited_practice"] = True

    if expected_question_policy == "none":
        checks["question_policy_none_strict"] = (_count_questions(text) == 0) and not _contains_any(lowered, _QUESTION_POLICY_NONE_MARKERS)
    else:
        checks["question_policy_none_strict"] = True

    if expected_practice_policy == "forbidden":
        checks["practice_policy_forbidden_strict"] = not _has_forbidden_practice_instruction(lowered)
    else:
        checks["practice_policy_forbidden_strict"] = True

    if expected_shape == "safety_grounding":
        checks["planner_answer_shape_alignment"] = (
            checks["safety_shape_short"]
            and checks["safety_no_mechanism_language"]
            and checks["safety_has_grounding_semantics"]
        )
    elif expected_shape == "short_support":
        checks["planner_answer_shape_alignment"] = (
            checks["short_support_not_lecture"]
            and checks["short_support_supportive_contact"]
            and checks["short_support_no_practice"]
            and checks["short_support_no_question"]
        )
    elif expected_shape == "one_question":
        checks["planner_answer_shape_alignment"] = checks["clarify_has_one_question"] and len(text) <= max_chars
    elif expected_shape == "gentle_close":
        checks["planner_answer_shape_alignment"] = checks["close_no_new_loop"] and len(text) <= max_chars
    elif expected_shape == "one_step":
        checks["planner_answer_shape_alignment"] = checks["one_step_shape"]
    else:
        checks["planner_answer_shape_alignment"] = True

    for key, ok in checks.items():
        if not ok:
            reasons.append(key)
    return checks, reasons


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


def _extract_planner_from_payload(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    debug = dict(payload.get("debug", {})) if isinstance(payload.get("debug"), dict) else {}
    trace = dict(payload.get("trace", {})) if isinstance(payload.get("trace"), dict) else {}
    planner = None
    if isinstance(debug.get("response_planner"), dict):
        planner = dict(debug.get("response_planner"))
    elif isinstance(trace.get("response_planner"), dict):
        planner = dict(trace.get("response_planner"))
    else:
        return None, "missing_live_api_debug_response_planner"

    planner_error = debug.get("response_planner_error")
    if planner_error is None:
        planner_error = trace.get("response_planner_error")
    if planner_error is not None:
        planner["response_planner_error"] = planner_error
        return planner, "live_response_planner_error_present"

    if not bool(planner.get("enabled", False)):
        return planner, "live_response_planner_disabled"
    if "_fallback_source" in planner:
        return planner, "live_response_planner_fallback_not_allowed_for_acceptance"
    return planner, None


def _build_case_result(
    *,
    case: dict[str, Any],
    mode: str,
    answer: str,
    planner: dict[str, Any] | None,
    planner_failure_reason: str | None = None,
) -> dict[str, Any]:
    expected_planner = dict(case.get("expected_planner", {}))
    expected_fit = dict(case.get("expected_answer_fit", {}))

    planner_checks, planner_reasons = _evaluate_planner(planner, expected_planner)
    fit_checks, fit_reasons = _evaluate_answer_fit(answer, expected_fit, expected_planner)

    failure_reasons = list(planner_reasons) + list(fit_reasons)
    if planner_failure_reason and planner_failure_reason not in failure_reasons:
        failure_reasons.append(planner_failure_reason)

    passed = (len(planner_reasons) == 0) and (len(fit_reasons) == 0) and (planner_failure_reason is None)

    return {
        "case_id": str(case.get("case_id", "unknown")),
        "group": str(case.get("group", "")),
        "mode": mode,
        "query": _extract_query(case),
        "response_planner": planner,
        "answer": answer,
        "evaluation": {
            "passed": passed,
            "planner_checks": planner_checks,
            "answer_fit_checks": fit_checks,
            "failure_reasons": failure_reasons,
        },
    }


def _run_dry(cases: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ok, schema_errors, coverage = _validate_dataset(cases)
    case_results: list[dict[str, Any]] = []
    for case in cases:
        case_results.append(
            {
                "case_id": str(case.get("case_id", "unknown")),
                "group": str(case.get("group", "")),
                "mode": "dry",
                "evaluation": {
                    "passed": True,
                    "schema_checks": {
                        "has_expected_planner": isinstance(case.get("expected_planner"), dict),
                        "has_expected_answer_fit": isinstance(case.get("expected_answer_fit"), dict),
                    },
                    "failure_reasons": [],
                },
            }
        )

    if not ok:
        for item in case_results:
            item["evaluation"]["passed"] = False
            item["evaluation"]["failure_reasons"] = list(schema_errors)

    payload = {
        "dataset_valid": ok,
        "schema_errors": schema_errors,
        "group_coverage": coverage,
        "case_results": case_results,
    }
    samples = [
        {
            "mode": "dry",
            "case_id": str(case.get("case_id", "unknown")),
            "group": str(case.get("group", "")),
            "expected_planner": dict(case.get("expected_planner", {})),
            "expected_answer_fit": dict(case.get("expected_answer_fit", {})),
        }
        for case in cases[:8]
    ]
    return payload, samples


async def _run_direct_async(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from bot_agent.multiagent.orchestrator import orchestrator

    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    run_nonce = uuid.uuid4().hex[:8]

    for idx, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id", f"case_{idx}"))
        user_id = f"prd0475_direct_{run_nonce}_{idx}"
        query = _extract_query(case)

        planner = None
        answer = ""
        planner_failure: str | None = None
        try:
            result = await orchestrator.run(query=query, user_id=user_id)
            answer = str(result.get("answer", "") or "")
            debug = dict(result.get("debug", {}))
            if isinstance(debug.get("response_planner"), dict):
                planner = dict(debug.get("response_planner"))
            if debug.get("response_planner_error") is not None:
                planner_failure = "direct_response_planner_error_present"
                if isinstance(planner, dict):
                    planner["response_planner_error"] = debug.get("response_planner_error")
        except Exception as exc:  # noqa: BLE001
            planner_failure = f"direct_orchestrator_exception:{exc.__class__.__name__}"

        case_result = _build_case_result(
            case=case,
            mode="direct",
            answer=answer,
            planner=planner,
            planner_failure_reason=planner_failure,
        )
        case_results.append(case_result)
        samples.append(
            {
                "mode": "direct",
                "case_id": case_id,
                "response_planner": planner,
                "answer_preview": answer[:220],
                "failure_reason": planner_failure,
            }
        )

    return case_results, samples


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
            return ({"live_status": "failed", "reason": f"admin_runtime_probe_status_{status}", "case_results": []}, [])
        planner_block = payload.get("response_planner")
        if not isinstance(planner_block, dict):
            return ({"live_status": "failed", "reason": "admin_runtime_missing_response_planner_block", "case_results": []}, [])
    except Exception as exc:  # noqa: BLE001
        return ({"live_status": "failed", "reason": f"admin_runtime_probe_failed:{exc}", "case_results": []}, [])

    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    user_by_thread: dict[str, str] = {}
    session_by_thread: dict[str, str] = {}

    for idx, case in enumerate(cases, start=1):
        thread_id = str(case.get("thread_id", f"thread_{idx}"))
        case_id = str(case.get("case_id", f"case_{idx}"))
        query = _extract_query(case)

        if thread_id not in user_by_thread:
            user_by_thread[thread_id] = f"prd0475_live_user_{idx}_{thread_id}"
            session_by_thread[thread_id] = f"prd0475_live_session_{idx}_{thread_id}"

        planner = None
        answer = ""
        planner_failure: str | None = None
        api_errors: list[str] = []

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
                planner_failure = f"live_status_{status}"
            else:
                answer = str(payload.get("answer", "") or payload.get("response", "") or "")
                planner, planner_extract_error = _extract_planner_from_payload(payload)
                if planner_extract_error is not None:
                    planner_failure = planner_extract_error
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            api_errors.append(f"http_error={exc.code}:{detail}")
            planner_failure = "live_http_error"
        except Exception as exc:  # noqa: BLE001
            api_errors.append(str(exc))
            planner_failure = "live_request_exception"

        case_result = _build_case_result(
            case=case,
            mode="live",
            answer=answer,
            planner=planner,
            planner_failure_reason=planner_failure,
        )
        case_result["api_errors"] = api_errors
        case_results.append(case_result)
        samples.append(
            {
                "mode": "live",
                "case_id": case_id,
                "response_planner": planner,
                "answer_preview": answer[:220],
                "failure_reason": planner_failure,
            }
        )

    return ({"live_status": "passed", "reason": "", "case_results": case_results}, samples)


def _build_summary(case_results: list[dict[str, Any]]) -> dict[str, int]:
    total = len(case_results)
    passed = sum(1 for item in case_results if bool(item.get("evaluation", {}).get("passed")))
    return {"cases_total": total, "cases_passed": passed, "cases_failed": max(0, total - passed)}


def _build_strict_answer_fit_summary(case_results: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "safety_grounding_mismatch_count": 0,
        "short_support_mismatch_count": 0,
        "question_policy_violation_count": 0,
        "practice_policy_violation_count": 0,
        "planner_answer_shape_mismatch_count": 0,
    }
    for item in case_results:
        planner = dict(item.get("response_planner", {})) if isinstance(item.get("response_planner"), dict) else {}
        checks = dict(item.get("evaluation", {}).get("answer_fit_checks", {}))
        reasons = [str(x) for x in list(item.get("evaluation", {}).get("failure_reasons", []))]
        signature = _planner_case_signature(planner)
        if signature == "stabilize_safety:safety_grounding" and (
            "safety_no_mechanism_language" in reasons
            or "safety_has_grounding_semantics" in reasons
            or "safety_shape_short" in reasons
            or checks.get("planner_answer_shape_alignment") is False
        ):
            summary["safety_grounding_mismatch_count"] += 1
        if signature == "give_short_support:short_support" and (
            "short_support_not_lecture" in reasons
            or "short_support_supportive_contact" in reasons
            or "short_support_no_practice" in reasons
            or "short_support_no_question" in reasons
            or checks.get("planner_answer_shape_alignment") is False
        ):
            summary["short_support_mismatch_count"] += 1
        if "question_policy_none_strict" in reasons:
            summary["question_policy_violation_count"] += 1
        if "practice_policy_forbidden_strict" in reasons:
            summary["practice_policy_violation_count"] += 1
        if "planner_answer_shape_alignment" in reasons:
            summary["planner_answer_shape_mismatch_count"] += 1
    return summary


def _build_false_positive_regression() -> dict[str, Any]:
    expected_planner = {
        "next_move": "stabilize_safety",
        "answer_shape": "safety_grounding",
        "response_depth": "short",
        "question_policy": "none",
        "practice_policy": "required_for_safety_or_grounding",
        "revoicing_policy": "suppressed",
    }
    expected_fit = {
        "max_chars": 320,
        "max_questions": 0,
        "forbidden_markers": ["теория", "лекция"],
        "required_semantics_any": [],
    }
    answer = (
        "Здесь важнее увидеть механизм: прогнозирование и контроль пытаются снизить риск, "
        "но забирают ресурс еще до начала действия."
    )
    checks, reasons = _evaluate_answer_fit(answer, expected_fit, expected_planner)
    return {
        "prd_id": "PRD-047.5-HF1",
        "regression_case_id": "hf1_negative_safety_mechanism_answer",
        "expected_passed": False,
        "actual_passed": len(reasons) == 0,
        "planner": expected_planner,
        "answer": answer,
        "answer_fit_checks": checks,
        "failure_reasons": reasons,
    }


def _build_summary_md(*, mode: str, summary: dict[str, int], dataset_path: Path, extra: dict[str, Any] | None = None) -> str:
    lines = [
        f"# PRD-047.5-HF1 Planner Answer-Fit Summary ({mode})",
        "",
        f"- dataset: `{dataset_path}`",
        f"- cases_total: `{summary.get('cases_total', 0)}`",
        f"- cases_passed: `{summary.get('cases_passed', 0)}`",
        f"- cases_failed: `{summary.get('cases_failed', 0)}`",
    ]
    if extra:
        for key, value in extra.items():
            lines.append(f"- {key}: `{value}`")
    lines.append("")
    return "\n".join(lines)


def _select_cases(cases: list[dict[str, Any]], case_id: str | None, limit: int | None) -> list[dict[str, Any]]:
    selected = list(cases)
    if case_id:
        selected = [item for item in selected if str(item.get("case_id", "")) == str(case_id)]
        if not selected:
            raise ValueError(f"case-id not found: {case_id}")
    if isinstance(limit, int) and limit > 0:
        selected = selected[:limit]
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.5-HF1 planner answer-fit calibration cases.")
    parser.add_argument("--mode", choices=("dry", "direct", "live"), default="dry")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--api-base-url", default=os.getenv("PRD0475_API_BASE", "http://localhost:8013/api/v1"))
    parser.add_argument("--api-key", default=os.getenv("PRD0475_API_KEY", os.getenv("BOT_API_KEY", "dev-key-001")))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD0475_ADMIN_RUNTIME_URL", "http://localhost:8013/api/admin/runtime/effective"),
    )
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_json = output_dir / f"planner_answer_fit_{args.mode}.json"
    trace_json = output_dir / "planner_answer_fit_trace_samples.json"
    summary_md = output_dir / "planner_answer_fit_summary.md"
    false_positive_json = output_dir / "answer_fit_false_positive_regression.json"

    cases = _load_cases(dataset_path)
    cases = _select_cases(cases, args.case_id, args.limit)

    if args.mode == "dry":
        payload, samples = _run_dry(cases)
        case_results = list(payload.get("case_results", []))
        summary = _build_summary(case_results)
        final = {
            "prd_id": "PRD-047.5-HF1",
            "mode": "dry",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": summary,
            "strict_answer_fit": _build_strict_answer_fit_summary(case_results),
            "dataset_validation": {
                "dataset_valid": bool(payload.get("dataset_valid", False)),
                "schema_errors": list(payload.get("schema_errors", [])),
                "group_coverage": dict(payload.get("group_coverage", {})),
            },
            "case_results": case_results,
        }
        _write_json(output_json, final)
        _write_json(false_positive_json, _build_false_positive_regression())
        _write_json(trace_json, {"prd_id": "PRD-047.5-HF1", "mode": "dry", "samples": samples})
        _write_md(
            summary_md,
            _build_summary_md(
                mode="dry",
                summary=summary,
                dataset_path=dataset_path,
                extra={"dataset_valid": bool(payload.get("dataset_valid", False))},
            ),
        )
        print(output_json)
        return 0

    if args.mode == "direct":
        case_results, samples = asyncio.run(_run_direct_async(cases))
        summary = _build_summary(case_results)
        final = {
            "prd_id": "PRD-047.5-HF1",
            "mode": "direct",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": summary,
            "strict_answer_fit": _build_strict_answer_fit_summary(case_results),
            "case_results": case_results,
        }
        _write_json(output_json, final)
        _write_json(false_positive_json, _build_false_positive_regression())
        _write_json(trace_json, {"prd_id": "PRD-047.5-HF1", "mode": "direct", "samples": samples})
        _write_md(summary_md, _build_summary_md(mode="direct", summary=summary, dataset_path=dataset_path))
        print(output_json)
        return 0

    live_payload, samples = _run_live(
        cases,
        base_url=str(args.api_base_url),
        api_key=str(args.api_key),
        admin_runtime_url=str(args.admin_runtime_url),
    )
    if str(live_payload.get("live_status")) != "passed":
        final = {
            "prd_id": "PRD-047.5-HF1",
            "mode": "live",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": {"cases_total": 0, "cases_passed": 0, "cases_failed": 0},
            "strict_answer_fit": {
                "safety_grounding_mismatch_count": 0,
                "short_support_mismatch_count": 0,
                "question_policy_violation_count": 0,
                "practice_policy_violation_count": 0,
                "planner_answer_shape_mismatch_count": 0,
            },
            "case_results": [],
            "live_status": str(live_payload.get("live_status", "failed")),
            "reason": str(live_payload.get("reason", "")),
        }
        _write_json(output_json, final)
        _write_json(false_positive_json, _build_false_positive_regression())
        _write_json(trace_json, {"prd_id": "PRD-047.5-HF1", "mode": "live", "samples": samples})
        _write_md(
            summary_md,
            _build_summary_md(
                mode="live",
                summary=final["summary"],
                dataset_path=dataset_path,
                extra={"live_status": final["live_status"], "reason": final["reason"]},
            ),
        )
        print(output_json)
        return 0

    case_results = list(live_payload.get("case_results", []))
    summary = _build_summary(case_results)
    final = {
        "prd_id": "PRD-047.5-HF1",
        "mode": "live",
        "timestamp_utc": _now_iso(),
        "dataset": str(dataset_path),
        "summary": summary,
        "strict_answer_fit": _build_strict_answer_fit_summary(case_results),
        "case_results": case_results,
        "live_status": "passed",
        "reason": "",
    }
    _write_json(output_json, final)
    _write_json(false_positive_json, _build_false_positive_regression())
    _write_json(trace_json, {"prd_id": "PRD-047.5-HF1", "mode": "live", "samples": samples})
    _write_md(summary_md, _build_summary_md(mode="live", summary=summary, dataset_path=dataset_path, extra={"live_status": "passed"}))
    print(output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
