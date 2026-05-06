#!/usr/bin/env python3
"""Run PRD-045.3 state analyzer calibration harness."""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.agents import state_analyzer_agent, thread_manager_agent
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "calibration" / "state_analyzer_calibration_cases.json"
DEFAULT_OUTPUT = REPO_ROOT / "TO_DO_LIST" / "reports" / "PRD-045.3_STATE_ANALYZER_CALIBRATION_REPORT.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "TO_DO_LIST" / "reports" / "PRD-045.3_STATE_ANALYZER_CALIBRATION_REPORT.md"

VALID_NERVOUS = {"window", "hyper", "hypo"}
VALID_INTENT = {"clarify", "vent", "explore", "contact", "solution"}
VALID_OPENNESS = {"open", "mixed", "defensive", "collapsed"}
VALID_OK_POSITION = {"I+W+", "I-W+", "I+W-", "I-W-"}
VALID_MODES = {"validate", "reflect", "explore", "regulate", "practice", "safe_override"}

CATEGORY_MINIMUMS = {
    "contact": 6,
    "low_resource_support": 8,
    "clarify": 8,
    "solution": 8,
    "vent": 6,
    "explore": 6,
    "defensive": 6,
    "collapsed": 5,
    "hyper": 5,
    "hypo": 5,
    "safety": 4,
    "ambiguous_short": 4,
    "continuity_followup": 4,
    "project_fear_evaluation": 4,
    "practice_request": 4,
}

INTENT_MINIMUMS = {"contact": 10, "clarify": 10, "solution": 10}
NERVOUS_MINIMUMS = {"hypo": 8, "hyper": 8}
MODE_MINIMUMS = {"validate": 8, "regulate": 8, "practice": 8, "reflect": 8}


@dataclass(frozen=True)
class CaseEvaluation:
    case_id: str
    category: str
    expected: dict[str, Any]
    actual: dict[str, Any]
    matches: dict[str, bool]
    severity: str
    note: str
    confidence_ok: bool
    user_message: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git_sha_short() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def _resolve_path(path_raw: str) -> Path:
    candidate = Path(path_raw)
    return candidate if candidate.is_absolute() else (REPO_ROOT / candidate).resolve()


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError(f"Dataset must be JSON list: {path}")
    return payload


def _case_categories(case: dict[str, Any]) -> set[str]:
    categories: set[str] = set()
    base = case.get("category")
    if isinstance(base, str) and base.strip():
        categories.add(base.strip())
    tags = case.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str) and tag.strip():
                categories.add(tag.strip())
    return categories


def _validate_dataset_shape(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not (60 <= len(cases) <= 80):
        errors.append(f"dataset size must be 60..80, got {len(cases)}")

    ids: set[str] = set()
    for idx, case in enumerate(cases):
        label = f"case[{idx}]"
        if not isinstance(case, dict):
            errors.append(f"{label}: not an object")
            continue
        for key in ("id", "title", "category", "user_message", "previous_thread", "expected", "notes"):
            if key not in case:
                errors.append(f"{label}: missing key `{key}`")

        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{label}: id must be non-empty string")
        elif case_id in ids:
            errors.append(f"{label}: duplicate id `{case_id}`")
        else:
            ids.add(case_id)

        if not isinstance(case.get("title"), str) or not str(case["title"]).strip():
            errors.append(f"{label}: title must be non-empty string")
        if not isinstance(case.get("category"), str) or not str(case["category"]).strip():
            errors.append(f"{label}: category must be non-empty string")
        if not isinstance(case.get("user_message"), str) or not str(case["user_message"]).strip():
            errors.append(f"{label}: user_message must be non-empty string")
        if case.get("previous_thread") is not None and not isinstance(case.get("previous_thread"), dict):
            errors.append(f"{label}: previous_thread must be null or object")
        if not isinstance(case.get("notes"), str):
            errors.append(f"{label}: notes must be string")

        expected = case.get("expected")
        if not isinstance(expected, dict):
            errors.append(f"{label}: expected must be object")
            continue
        for key in (
            "nervous_state",
            "intent",
            "openness",
            "ok_position",
            "response_mode_new_thread",
            "confidence_min",
        ):
            if key not in expected:
                errors.append(f"{label}: missing expected.{key}")
        if expected.get("nervous_state") not in VALID_NERVOUS:
            errors.append(f"{label}: invalid expected.nervous_state={expected.get('nervous_state')}")
        if expected.get("intent") not in VALID_INTENT:
            errors.append(f"{label}: invalid expected.intent={expected.get('intent')}")
        if expected.get("openness") not in VALID_OPENNESS:
            errors.append(f"{label}: invalid expected.openness={expected.get('openness')}")
        if expected.get("ok_position") not in VALID_OK_POSITION:
            errors.append(f"{label}: invalid expected.ok_position={expected.get('ok_position')}")
        if expected.get("response_mode_new_thread") not in VALID_MODES:
            errors.append(
                f"{label}: invalid expected.response_mode_new_thread={expected.get('response_mode_new_thread')}"
            )
        try:
            confidence_min = float(expected.get("confidence_min"))
        except (TypeError, ValueError):
            errors.append(f"{label}: expected.confidence_min must be float 0..1")
        else:
            if not (0.0 <= confidence_min <= 1.0):
                errors.append(f"{label}: expected.confidence_min out of range: {confidence_min}")
    return errors


def _coverage_summary(cases: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    category_counts: Counter[str] = Counter()
    intent_counts: Counter[str] = Counter()
    nervous_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    openness_counts: Counter[str] = Counter()
    low_confidence_cases = 0

    for case in cases:
        for category in _case_categories(case):
            category_counts[category] += 1

        expected = case.get("expected", {})
        intent = expected.get("intent")
        nervous = expected.get("nervous_state")
        mode = expected.get("response_mode_new_thread")
        openness = expected.get("openness")
        confidence_min = expected.get("confidence_min")

        if isinstance(intent, str):
            intent_counts[intent] += 1
        if isinstance(nervous, str):
            nervous_counts[nervous] += 1
        if isinstance(mode, str):
            mode_counts[mode] += 1
        if isinstance(openness, str):
            openness_counts[openness] += 1

        try:
            if float(confidence_min) <= 0.55:
                low_confidence_cases += 1
        except (TypeError, ValueError):
            pass

    return {
        "categories": dict(sorted(category_counts.items())),
        "intent": dict(sorted(intent_counts.items())),
        "nervous_state": dict(sorted(nervous_counts.items())),
        "response_mode_new_thread": dict(sorted(mode_counts.items())),
        "openness": dict(sorted(openness_counts.items())),
        "low_confidence_cases": {"<=0.55": low_confidence_cases},
    }


def _validate_coverage(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    coverage = _coverage_summary(cases)
    category_counts = coverage["categories"]
    intent_counts = coverage["intent"]
    nervous_counts = coverage["nervous_state"]
    mode_counts = coverage["response_mode_new_thread"]
    low_confidence_count = coverage["low_confidence_cases"]["<=0.55"]

    for category, minimum in CATEGORY_MINIMUMS.items():
        if category_counts.get(category, 0) < minimum:
            errors.append(
                f"category coverage `{category}` below minimum: {category_counts.get(category, 0)} < {minimum}"
            )
    for intent, minimum in INTENT_MINIMUMS.items():
        if intent_counts.get(intent, 0) < minimum:
            errors.append(f"intent coverage `{intent}` below minimum: {intent_counts.get(intent, 0)} < {minimum}")
    for nervous, minimum in NERVOUS_MINIMUMS.items():
        if nervous_counts.get(nervous, 0) < minimum:
            errors.append(
                f"nervous_state coverage `{nervous}` below minimum: {nervous_counts.get(nervous, 0)} < {minimum}"
            )
    for mode, minimum in MODE_MINIMUMS.items():
        if mode_counts.get(mode, 0) < minimum:
            errors.append(
                f"response_mode coverage `{mode}` below minimum: {mode_counts.get(mode, 0)} < {minimum}"
            )
    if low_confidence_count < 4:
        errors.append(f"low confidence cases (<=0.55) below minimum: {low_confidence_count} < 4")
    return errors


def _build_previous_thread(previous_thread: dict[str, Any] | None, user_id: str) -> ThreadState | None:
    if not previous_thread:
        return None
    core_direction = str(previous_thread.get("core_direction") or "continuity")
    phase = str(previous_thread.get("phase") or "explore")
    if phase not in {"stabilize", "clarify", "explore", "integrate"}:
        phase = "explore"
    open_loops_raw = previous_thread.get("open_loops")
    closed_loops_raw = previous_thread.get("closed_loops")
    open_loops = [str(item) for item in open_loops_raw] if isinstance(open_loops_raw, list) else []
    closed_loops = [str(item) for item in closed_loops_raw] if isinstance(closed_loops_raw, list) else []
    now = datetime.utcnow()
    return ThreadState(
        thread_id=f"cal_prev_{user_id}",
        user_id=user_id,
        core_direction=core_direction,
        phase=phase,  # type: ignore[arg-type]
        open_loops=open_loops,
        closed_loops=closed_loops,
        created_at=now,
        updated_at=now,
    )


def _severity_from_case(
    *,
    case: dict[str, Any],
    expected: dict[str, Any],
    actual: dict[str, Any],
    matches: dict[str, bool],
    confidence_ok: bool,
) -> tuple[str, str]:
    categories = _case_categories(case)
    expected_mode = str(expected["response_mode_new_thread"])
    actual_mode = str(actual["response_mode_new_thread"])
    expected_nervous = str(expected["nervous_state"])
    actual_nervous = str(actual["nervous_state"])
    expected_openness = str(expected["openness"])
    actual_openness = str(actual["openness"])
    actual_confidence = float(actual["confidence"])

    if expected_mode == "safe_override" and actual_mode != "safe_override":
        return "high", "Expected safety override but got non-safety mode."
    if (
        ("contact" in categories or "low_resource_support" in categories)
        and actual_mode in {"reflect", "explore"}
    ):
        return "high", "Low-resource/contact case routed to reflective/exploratory mode."
    if expected_nervous in {"hypo"} and actual_nervous == "window" and actual_mode == "explore":
        return "high", "Hypo case routed to explore with window classification."
    if "collapsed" in categories and actual_nervous == "window" and actual_mode == "explore":
        return "high", "Collapsed case routed to explore with window classification."
    if expected["intent"] == "solution" and actual_mode != "practice":
        return "high", "Solution intent expected practice mode."
    if expected_openness in {"defensive", "collapsed"} and actual_openness == "open" and actual_confidence >= 0.75:
        return "high", "Defensive/collapsed expected but model returned open with high confidence."

    important_fields = ("intent", "response_mode_new_thread", "nervous_state")
    important_mismatch = any(not matches.get(field, False) for field in important_fields)
    if important_mismatch:
        return "medium", "Mismatch in one or more important fields."
    if not confidence_ok:
        return "medium", "Confidence lower than expected minimum."
    if any(not value for value in matches.values()):
        return "low", "Non-critical mismatch."
    return "low", "All expected fields matched."


def _update_confusion(
    confusion: dict[str, dict[str, dict[str, int]]],
    *,
    field: str,
    expected: str,
    actual: str,
) -> None:
    bucket = confusion[field].setdefault(expected, {})
    bucket[actual] = int(bucket.get(actual, 0)) + 1


def _sorted_confusion(
    confusion: dict[str, dict[str, dict[str, int]]],
) -> dict[str, dict[str, dict[str, int]]]:
    result: dict[str, dict[str, dict[str, int]]] = {}
    for field, rows in confusion.items():
        sorted_rows: dict[str, dict[str, int]] = {}
        for expected_value in sorted(rows):
            sorted_rows[expected_value] = dict(sorted(rows[expected_value].items()))
        result[field] = sorted_rows
    return result


def _build_recommendations(case_results: list[CaseEvaluation]) -> list[str]:
    if not case_results:
        return ["Run live mode to collect analyzer and routing mismatches."]

    mismatch_by_pair: Counter[str] = Counter()
    high_by_category: Counter[str] = Counter()
    for item in case_results:
        if item.matches.get("intent") is False or item.matches.get("response_mode_new_thread") is False:
            mismatch_by_pair[f"{item.expected['intent']}->{item.actual['intent']} / {item.expected['response_mode_new_thread']}->{item.actual['response_mode_new_thread']}"] += 1
        if item.severity == "high":
            high_by_category[item.category] += 1

    recommendations: list[str] = []
    for pair, count in mismatch_by_pair.most_common(3):
        recommendations.append(f"Audit analyzer/thread routing pair `{pair}` (count={count}).")
    for category, count in high_by_category.most_common(2):
        recommendations.append(f"Add deterministic hints for `{category}` cases (high severity={count}).")
    if not recommendations:
        recommendations.append("No major mismatch clusters found; keep dataset and rerun after config changes.")
    return recommendations


async def _run_case_live(case: dict[str, Any]) -> CaseEvaluation:
    case_id = str(case["id"])
    user_id = f"cal_{case_id.lower()}"
    previous_thread = _build_previous_thread(case.get("previous_thread"), user_id)
    expected = case["expected"]
    user_message = str(case["user_message"])

    snapshot = await state_analyzer_agent.analyze(user_message=user_message, previous_thread=previous_thread)
    updated_thread = await thread_manager_agent.update(
        user_message=user_message,
        state_snapshot=snapshot,
        user_id=user_id,
        current_thread=None,
        archived_threads=[],
    )

    actual = {
        "nervous_state": snapshot.nervous_state,
        "intent": snapshot.intent,
        "openness": snapshot.openness,
        "ok_position": snapshot.ok_position,
        "response_mode_new_thread": updated_thread.response_mode,
        "confidence": float(snapshot.confidence),
        "safety_flag": bool(snapshot.safety_flag),
    }
    matches = {
        "nervous_state": actual["nervous_state"] == expected["nervous_state"],
        "intent": actual["intent"] == expected["intent"],
        "openness": actual["openness"] == expected["openness"],
        "ok_position": actual["ok_position"] == expected["ok_position"],
        "response_mode_new_thread": actual["response_mode_new_thread"] == expected["response_mode_new_thread"],
    }
    confidence_ok = actual["confidence"] >= float(expected["confidence_min"])
    severity, note = _severity_from_case(
        case=case,
        expected=expected,
        actual=actual,
        matches=matches,
        confidence_ok=confidence_ok,
    )
    return CaseEvaluation(
        case_id=case_id,
        category=str(case["category"]),
        expected=expected,
        actual=actual,
        matches=matches,
        severity=severity,
        note=note,
        confidence_ok=confidence_ok,
        user_message=user_message,
    )


def _accuracy(case_results: list[CaseEvaluation], field: str) -> float:
    if not case_results:
        return 0.0
    hits = sum(1 for item in case_results if item.matches.get(field, False))
    return round(hits / len(case_results), 4)


def _all_fields_exact_match(case_results: list[CaseEvaluation]) -> float:
    if not case_results:
        return 0.0
    hits = sum(1 for item in case_results if all(item.matches.values()))
    return round(hits / len(case_results), 4)


def _build_report(
    *,
    mode: str,
    dataset_path: Path,
    selected_cases: list[dict[str, Any]],
    coverage: dict[str, dict[str, int]],
    dataset_errors: list[str],
    coverage_errors: list[str],
    case_results: list[CaseEvaluation],
) -> dict[str, Any]:
    confusion_raw: dict[str, dict[str, dict[str, int]]] = defaultdict(dict)
    severity_counts: Counter[str] = Counter()
    case_payload: list[dict[str, Any]] = []

    for item in case_results:
        severity_counts[item.severity] += 1
        for field in ("nervous_state", "intent", "openness", "ok_position", "response_mode_new_thread"):
            _update_confusion(
                confusion_raw,
                field=field,
                expected=str(item.expected[field]),
                actual=str(item.actual[field]),
            )
        case_payload.append(
            {
                "id": item.case_id,
                "category": item.category,
                "user_message": item.user_message,
                "expected": item.expected,
                "actual": item.actual,
                "matches": item.matches,
                "confidence_ok": item.confidence_ok,
                "severity": item.severity,
                "notes": item.note,
            }
        )

    summary = {
        "nervous_state_accuracy": _accuracy(case_results, "nervous_state"),
        "intent_accuracy": _accuracy(case_results, "intent"),
        "openness_accuracy": _accuracy(case_results, "openness"),
        "ok_position_accuracy": _accuracy(case_results, "ok_position"),
        "response_mode_accuracy": _accuracy(case_results, "response_mode_new_thread"),
        "all_fields_exact_match": _all_fields_exact_match(case_results),
        "high_severity_mismatches": int(severity_counts.get("high", 0)),
        "medium_severity_mismatches": int(severity_counts.get("medium", 0)),
        "low_severity_mismatches": int(severity_counts.get("low", 0)),
    }

    return {
        "run_metadata": {
            "date": _utc_now_iso(),
            "git_sha": _git_sha_short(),
            "mode": mode,
            "python": platform.python_version(),
            "dataset_path": str(dataset_path),
            "cases_total": len(selected_cases),
            "cases_executed": len(case_results),
        },
        "dataset_validation": {
            "schema_errors": dataset_errors,
            "coverage_errors": coverage_errors,
            "coverage": coverage,
        },
        "summary": summary,
        "confusion": _sorted_confusion(confusion_raw),
        "case_results": case_payload,
        "recommendations": _build_recommendations(case_results),
    }


def _markdown_from_report(report: dict[str, Any]) -> str:
    meta = report.get("run_metadata", {})
    summary = report.get("summary", {})
    validation = report.get("dataset_validation", {})
    schema_errors = validation.get("schema_errors", []) or []
    coverage_errors = validation.get("coverage_errors", []) or []
    case_results = report.get("case_results", []) or []
    recommendations = report.get("recommendations", []) or []

    high_cases = [item for item in case_results if item.get("severity") == "high"][:10]
    mismatches = [item for item in case_results if not all((item.get("matches") or {}).values())]

    lines: list[str] = []
    lines.append("# PRD-045.3 State Analyzer Calibration Report")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append(f"- Date: {meta.get('date')}")
    lines.append(f"- Git SHA: {meta.get('git_sha')}")
    lines.append(f"- Mode: {meta.get('mode')}")
    lines.append(f"- Cases total: {meta.get('cases_total')}")
    lines.append(f"- Cases executed: {meta.get('cases_executed')}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- nervous_state accuracy: {summary.get('nervous_state_accuracy')}")
    lines.append(f"- intent accuracy: {summary.get('intent_accuracy')}")
    lines.append(f"- openness accuracy: {summary.get('openness_accuracy')}")
    lines.append(f"- ok_position accuracy: {summary.get('ok_position_accuracy')}")
    lines.append(f"- response_mode accuracy: {summary.get('response_mode_accuracy')}")
    lines.append(f"- all-fields exact match: {summary.get('all_fields_exact_match')}")
    lines.append(f"- high severity mismatches: {summary.get('high_severity_mismatches')}")
    lines.append("")
    lines.append("## Dataset Validation")
    lines.append(f"- Schema errors: {len(schema_errors)}")
    lines.append(f"- Coverage errors: {len(coverage_errors)}")
    if schema_errors:
        for error in schema_errors:
            lines.append(f"- schema: {error}")
    if coverage_errors:
        for error in coverage_errors:
            lines.append(f"- coverage: {error}")
    lines.append("")
    lines.append("## Most Common Mismatches")
    if mismatches:
        top = Counter()
        for item in mismatches:
            matches = item.get("matches") or {}
            expected = item.get("expected") or {}
            actual = item.get("actual") or {}
            for field, ok in matches.items():
                if not ok:
                    top[f"{field}: {expected.get(field)} -> {actual.get(field)}"] += 1
        for key, count in top.most_common(10):
            lines.append(f"- {key} (count={count})")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## High Severity Cases")
    if high_cases:
        for item in high_cases:
            lines.append(f"### {item.get('id')}")
            lines.append(f"- User message: {item.get('user_message')}")
            lines.append(f"- Expected: {json.dumps(item.get('expected'), ensure_ascii=False)}")
            lines.append(f"- Actual: {json.dumps(item.get('actual'), ensure_ascii=False)}")
            lines.append(f"- Why important: {item.get('notes')}")
            lines.append("")
    else:
        lines.append("- none")
        lines.append("")
    lines.append("## Recommendations")
    if recommendations:
        for idx, item in enumerate(recommendations, start=1):
            lines.append(f"{idx}. {item}")
    else:
        lines.append("1. Re-run in live mode to collect mismatch data.")
    lines.append("")
    return "\n".join(lines)


def _write_outputs(report: dict[str, Any], output_path: Path, markdown_output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_output_path.write_text(_markdown_from_report(report), encoding="utf-8")


def _select_cases(
    cases: list[dict[str, Any]],
    *,
    limit: int | None,
    case_id: str | None,
) -> list[dict[str, Any]]:
    selected = list(cases)
    if case_id:
        selected = [case for case in selected if str(case.get("id")) == case_id]
        if not selected:
            raise ValueError(f"Case id not found: {case_id}")
    if limit is not None and limit > 0:
        selected = selected[:limit]
    return selected


async def _run_live_cases(cases: list[dict[str, Any]]) -> list[CaseEvaluation]:
    results: list[CaseEvaluation] = []
    for case in cases:
        results.append(await _run_case_live(case))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run state analyzer calibration harness (PRD-045.3).")
    parser.add_argument("--mode", choices=("dry-run", "live"), default="dry-run")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--markdown-output", default=str(DEFAULT_MARKDOWN_OUTPUT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--case-id", default=None)
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    output_path = _resolve_path(args.output)
    markdown_output_path = _resolve_path(args.markdown_output)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    cases = _load_dataset(dataset_path)
    dataset_errors = _validate_dataset_shape(cases)
    coverage_errors = _validate_coverage(cases)
    if dataset_errors:
        raise ValueError("Dataset schema validation failed:\n- " + "\n- ".join(dataset_errors))

    selected_cases = _select_cases(cases, limit=args.limit, case_id=args.case_id)
    coverage = _coverage_summary(cases)

    if args.mode == "dry-run":
        report = _build_report(
            mode="dry-run",
            dataset_path=dataset_path,
            selected_cases=selected_cases,
            coverage=coverage,
            dataset_errors=dataset_errors,
            coverage_errors=coverage_errors,
            case_results=[],
        )
        _write_outputs(report, output_path=output_path, markdown_output_path=markdown_output_path)
        print(f"[OK] dry-run report JSON: {output_path}")
        print(f"[OK] dry-run report MD:   {markdown_output_path}")
        if coverage_errors:
            print(f"[WARN] coverage has {len(coverage_errors)} issues")
            return 2
        return 0

    case_results = asyncio.run(_run_live_cases(selected_cases))
    report = _build_report(
        mode="live",
        dataset_path=dataset_path,
        selected_cases=selected_cases,
        coverage=coverage,
        dataset_errors=dataset_errors,
        coverage_errors=coverage_errors,
        case_results=case_results,
    )
    _write_outputs(report, output_path=output_path, markdown_output_path=markdown_output_path)
    print(f"[OK] live report JSON: {output_path}")
    print(f"[OK] live report MD:   {markdown_output_path}")
    if coverage_errors:
        print(f"[WARN] coverage has {len(coverage_errors)} issues")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
