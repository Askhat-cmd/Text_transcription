#!/usr/bin/env python3
"""Run PRD-045.0 quality baseline harness in dry-run or live mode."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "quality_baseline_cases.json"
DEFAULT_OUTPUT = REPO_ROOT / "TO_DO_LIST" / "reports" / "PRD-045.0_quality_baseline_report.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "TO_DO_LIST" / "reports" / "PRD-045.0_quality_baseline_report.md"

GENERIC_PHRASE_MARKERS = [
    "я понимаю",
    "это нормально",
    "важно помнить",
    "попробуй разобраться",
    "дай себе время",
    "всё индивидуально",
    "тебе стоит",
    "просто",
]


@dataclass
class LiveRuntimeConfig:
    base_url: str
    api_key: str
    device_fingerprint: str = "sha256:quality-baseline-harness"


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
    if candidate.is_absolute():
        return candidate
    return (REPO_ROOT / candidate).resolve()


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError(f"Dataset must be JSON list: {path}")
    return payload


def _validate_dataset_shape(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    for idx, case in enumerate(cases):
        label = f"case[{idx}]"
        if not isinstance(case, dict):
            errors.append(f"{label}: not an object")
            continue
        for key in ("id", "title", "category", "user_turns", "expected"):
            if key not in case:
                errors.append(f"{label}: missing key `{key}`")
        case_id = case.get("id")
        if isinstance(case_id, str):
            if case_id in ids:
                errors.append(f"{label}: duplicate id `{case_id}`")
            ids.add(case_id)
        else:
            errors.append(f"{label}: id must be string")
        turns = case.get("user_turns")
        if not isinstance(turns, list) or not turns:
            errors.append(f"{label}: user_turns must be non-empty list")
        expected = case.get("expected")
        if not isinstance(expected, dict):
            errors.append(f"{label}: expected must be object")
        else:
            if "should" not in expected or not isinstance(expected.get("should"), list):
                errors.append(f"{label}: expected.should must be list")
            if "should_not" not in expected or not isinstance(expected.get("should_not"), list):
                errors.append(f"{label}: expected.should_not must be list")
    return errors


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[A-Za-zА-Яа-яЁё0-9]{3,}", text.lower())}


def _is_practice_expected(expected: dict[str, Any]) -> bool:
    should_joined = " ".join(item.lower() for item in expected.get("should", []) if isinstance(item, str))
    focus = [str(item).lower() for item in expected.get("quality_focus", [])]
    return (
        "micro-step" in should_joined
        or "concrete" in should_joined
        or "practice" in should_joined
        or "practice_step" in focus
        or "actionability" in focus
    )


def _build_heuristic_quality(
    *,
    answer: str,
    case_turns: list[str],
    expected: dict[str, Any],
) -> dict[str, Any]:
    answer_norm = answer.strip()
    question_count = answer.count("?")
    generic_phrase_risk = any(marker in answer_norm.lower() for marker in GENERIC_PHRASE_MARKERS)
    numbered_list = bool(re.search(r"(?m)^\\s*\\d+[\\.)]\\s+", answer_norm))
    answer_tokens = _tokenize(answer_norm)
    context_tokens = _tokenize(" ".join(case_turns))
    mentions_user_context = bool(answer_tokens.intersection(context_tokens))
    practice_markers = ("шаг", "сделай", "попробуй", "начни", "сегодня", "15 минут", "таймер")
    has_practice_step = any(marker in answer_norm.lower() for marker in practice_markers)
    expected_practice = _is_practice_expected(expected)

    return {
        "too_short": len(answer_norm) < 40,
        "too_long": len(answer_norm) > 1400,
        "too_many_questions": question_count > 3,
        "contains_numbered_list": numbered_list,
        "generic_phrase_risk": generic_phrase_risk,
        "mentions_user_context": mentions_user_context,
        "has_practice_step_when_expected": (has_practice_step if expected_practice else None),
    }


def _http_json_request(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict[str, Any]]:
    body_bytes = None
    req_headers = dict(headers)
    if payload is not None:
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url=url, method=method.upper(), headers=req_headers, data=body_bytes)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status_code = int(getattr(response, "status", 200))
        raw = response.read().decode("utf-8")
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            data = {"raw": data}
        return status_code, data


def _probe_live_runtime(config: LiveRuntimeConfig) -> tuple[bool, str]:
    headers = {
        "X-API-Key": config.api_key,
        "X-Session-Id": "quality-baseline-probe",
        "X-Device-Fingerprint": config.device_fingerprint,
    }
    try:
        status, payload = _http_json_request(
            method="GET",
            url=f"{config.base_url.rstrip('/')}/identity/me",
            headers=headers,
            payload=None,
            timeout=10.0,
        )
        if status != 200:
            return False, f"identity probe failed with status={status} payload={payload}"
        return True, "ok"
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        return False, f"identity probe HTTPError status={error.code}: {detail}"
    except Exception as error:
        return False, f"identity probe failed: {error}"


def _extract_debug_summary(response: dict[str, Any], session_id: str) -> tuple[dict[str, Any], float | None]:
    trace_payload = response.get("trace")
    debug_payload = response.get("debug")
    if isinstance(trace_payload, dict):
        trace = trace_payload
    elif isinstance(debug_payload, dict):
        trace = debug_payload
    else:
        trace = {}
    metadata = response.get("metadata") if isinstance(response.get("metadata"), dict) else {}
    state = response.get("state_analysis") if isinstance(response.get("state_analysis"), dict) else {}

    latency_seconds = response.get("processing_time_seconds")
    latency_ms: float | None = None
    if isinstance(latency_seconds, (int, float)):
        latency_ms = float(latency_seconds) * 1000.0

    semantic_hits_detail = trace.get("semantic_hits_detail")
    semantic_hits_count = None
    if isinstance(semantic_hits_detail, list):
        semantic_hits_count = len(semantic_hits_detail)
    elif isinstance(trace.get("semantic_hits"), int):
        semantic_hits_count = int(trace.get("semantic_hits"))

    debug_summary = {
        "pipeline_version": trace.get("pipeline_version") or metadata.get("pipeline_version"),
        "nervous_state": trace.get("nervous_state") or state.get("primary_state"),
        "intent": trace.get("intent"),
        "safety_flag": trace.get("safety_flag"),
        "confidence": state.get("confidence") if state else trace.get("confidence"),
        "thread_id": trace.get("thread_id") or trace.get("session_id") or metadata.get("session_id") or session_id,
        "phase": trace.get("phase"),
        "relation_to_thread": trace.get("relation_to_thread"),
        "continuity_score": trace.get("continuity_score"),
        "response_mode": metadata.get("recommended_mode") or trace.get("recommended_mode"),
        "context_turns": trace.get("memory_turns"),
        "semantic_hits_count": semantic_hits_count,
        "model_used": trace.get("primary_model") or metadata.get("model_used"),
        "model_temperature": trace.get("temperature"),
        "model_max_tokens": trace.get("max_tokens"),
        "validator_blocked": trace.get("validator_blocked"),
        "validator_quality_flags": trace.get("validator_quality_flags"),
        "quality_trace_version": trace.get("quality_trace_version"),
        "quality_trace": trace.get("quality_trace"),
        "quality_trace_error": trace.get("quality_trace_error"),
        "timings": trace.get("timings") if isinstance(trace.get("timings"), dict) else {},
    }
    return debug_summary, latency_ms


def _run_case_live(case: dict[str, Any], config: LiveRuntimeConfig) -> tuple[dict[str, Any], list[str]]:
    case_id = str(case["id"])
    case_title = str(case["title"])
    case_category = str(case["category"])
    user_turns = [str(item) for item in case["user_turns"]]
    expected = case["expected"] if isinstance(case["expected"], dict) else {}

    session_id = f"qb-session-{case_id.lower()}"
    test_user_id = f"qb_user_{case_id.lower()}"
    headers = {
        "X-API-Key": config.api_key,
        "X-Session-Id": session_id,
        "X-Device-Fingerprint": config.device_fingerprint,
    }

    turn_records: list[dict[str, Any]] = []
    case_errors: list[str] = []
    for turn_index, user_message in enumerate(user_turns, start=1):
        payload = {
            "query": user_message,
            "user_id": test_user_id,
            "session_id": session_id,
            "include_path": False,
            "include_feedback_prompt": False,
            "debug": True,
        }
        try:
            status, response = _http_json_request(
                method="POST",
                url=f"{config.base_url.rstrip('/')}/questions/adaptive",
                headers=headers,
                payload=payload,
                timeout=120.0,
            )
            if status != 200:
                case_errors.append(f"turn {turn_index}: status={status} payload={response}")
                break
            answer = str(response.get("answer", "") or "")
            debug_summary, latency_ms = _extract_debug_summary(response, session_id=session_id)
            turn_records.append(
                {
                    "case_id": case_id,
                    "turn_index": turn_index,
                    "user_message": user_message,
                    "answer": answer,
                    "debug": debug_summary,
                    "heuristic_quality": _build_heuristic_quality(
                        answer=answer,
                        case_turns=user_turns[:turn_index],
                        expected=expected,
                    ),
                    "latency_ms": latency_ms,
                }
            )
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            case_errors.append(f"turn {turn_index}: HTTPError {error.code}: {detail}")
            break
        except Exception as error:  # noqa: BLE001
            case_errors.append(f"turn {turn_index}: {error}")
            break

    case_result = {
        "case_id": case_id,
        "title": case_title,
        "category": case_category,
        "turns": len(user_turns),
        "test_user_id": test_user_id,
        "session_id": session_id,
        "expected": expected,
        "turn_results": turn_records,
        "final_answer": turn_records[-1]["answer"] if turn_records else None,
        "final_debug_summary": turn_records[-1]["debug"] if turn_records else None,
        "final_heuristic_quality": turn_records[-1]["heuristic_quality"] if turn_records else None,
        "error": "; ".join(case_errors) if case_errors else None,
    }
    return case_result, case_errors


def _run_case_dry(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case["id"])
    return {
        "case_id": case_id,
        "title": str(case["title"]),
        "category": str(case["category"]),
        "turns": len(case.get("user_turns", [])),
        "test_user_id": f"qb_user_{case_id.lower()}",
        "session_id": f"qb-session-{case_id.lower()}",
        "expected": case.get("expected"),
        "turn_results": [],
        "final_answer": None,
        "final_debug_summary": None,
        "final_heuristic_quality": None,
        "error": None,
    }


def _markdown_from_report(report: dict[str, Any]) -> str:
    meta = report.get("run_metadata", {})
    runtime = report.get("runtime_config_snapshot", {})
    summary = report.get("summary", {})
    errors = report.get("errors", [])
    cases = report.get("case_results", [])

    lines: list[str] = []
    lines.append("# PRD-045.0 Quality Baseline Report")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append(f"- Date: {meta.get('date')}")
    lines.append(f"- Git SHA: {meta.get('git_sha')}")
    lines.append(f"- Mode: {meta.get('mode')}")
    lines.append(f"- Python: {meta.get('python')}")
    lines.append(f"- Backend used: {meta.get('backend_used')}")
    lines.append(f"- OpenAI/API available: {meta.get('api_available')}")
    lines.append(f"- Dataset path: {meta.get('dataset_path')}")
    lines.append(f"- Cases total: {meta.get('cases_total')}")
    lines.append(f"- Cases executed: {meta.get('cases_executed')}")
    lines.append("")
    lines.append("## Runtime Config Snapshot")
    lines.append(f"- State Analyzer model: {runtime.get('state_analyzer_model')}")
    lines.append(f"- Writer model: {runtime.get('writer_model')}")
    lines.append(f"- max_tokens: {runtime.get('max_tokens')}")
    lines.append(f"- temperature: {runtime.get('temperature')}")
    lines.append(f"- RAG top_k: {runtime.get('rag_top_k')}")
    lines.append(f"- RAG min_score: {runtime.get('rag_min_score')}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Cases executed: {summary.get('cases_executed')}")
    lines.append(f"- Errors: {summary.get('errors_count')}")
    lines.append(f"- Safety cases: {summary.get('safety_cases')}")
    lines.append(f"- Avg latency: {summary.get('avg_latency_ms')}")
    lines.append(f"- Generic-risk flags: {summary.get('generic_risk_flags')}")
    lines.append(f"- Continuity-risk flags: {summary.get('continuity_risk_flags')}")
    lines.append("")
    lines.append("## Case Results")
    for case in cases:
        final_debug = case.get("final_debug_summary") if isinstance(case.get("final_debug_summary"), dict) else {}
        quality_trace = final_debug.get("quality_trace") if isinstance(final_debug.get("quality_trace"), dict) else None
        quality_summary_flags = (
            quality_trace.get("summary_flags")
            if isinstance(quality_trace, dict) and isinstance(quality_trace.get("summary_flags"), list)
            else None
        )
        lines.append(f"### {case.get('case_id')} — {case.get('title')}")
        lines.append(f"- Category: {case.get('category')}")
        lines.append(f"- Turns: {case.get('turns')}")
        lines.append(f"- Final answer: {case.get('final_answer')}")
        lines.append(
            "- Debug summary: "
            + json.dumps(
                {
                    "pipeline_version": final_debug.get("pipeline_version"),
                    "response_mode": final_debug.get("response_mode"),
                    "continuity_score": final_debug.get("continuity_score"),
                    "semantic_hits_count": final_debug.get("semantic_hits_count"),
                    "validator_blocked": final_debug.get("validator_blocked"),
                },
                ensure_ascii=False,
            )
        )
        if quality_summary_flags is not None:
            lines.append(f"- Quality trace summary: {json.dumps(quality_summary_flags, ensure_ascii=False)}")
        else:
            lines.append("- Quality trace: null")
        lines.append(f"- Heuristic flags: {json.dumps(case.get('final_heuristic_quality'), ensure_ascii=False)}")
        note = case.get("error") or "ok"
        lines.append(f"- Notes: {note}")
        lines.append("")
    lines.append("## Errors / Limitations")
    if errors:
        for error in errors:
            lines.append(f"- {error}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Next Recommendations")
    lines.append("- Use this baseline as reference for PRD-045.x quality improvements.")
    lines.append("- Add richer continuity/specificity checks after trace fields are stabilized.")
    lines.append("- Re-run live mode after backend/runtime config changes.")
    lines.append("")
    return "\n".join(lines)


def _build_report(
    *,
    mode: str,
    dataset_path: Path,
    selected_cases: list[dict[str, Any]],
    case_results: list[dict[str, Any]],
    errors: list[str],
    backend_used: str,
    api_available: bool,
) -> dict[str, Any]:
    latencies: list[float] = []
    generic_risk = 0
    continuity_risk = 0
    safety_cases = 0

    state_model = None
    writer_model = None
    max_tokens = None
    temperature = None
    rag_top_k = None
    rag_min_score = None

    for case in case_results:
        expected = case.get("expected") or {}
        if "safety_routing" in [str(item).lower() for item in expected.get("quality_focus", [])]:
            safety_cases += 1
        if "safety_sensitivity" in [str(item).lower() for item in expected.get("quality_focus", [])]:
            safety_cases += 1

        heuristic = case.get("final_heuristic_quality") or {}
        if heuristic.get("generic_phrase_risk"):
            generic_risk += 1
        multi_turn = int(case.get("turns", 0)) > 1
        if multi_turn and heuristic.get("mentions_user_context") is False:
            continuity_risk += 1

        for turn_result in case.get("turn_results", []):
            latency = turn_result.get("latency_ms")
            if isinstance(latency, (int, float)):
                latencies.append(float(latency))
            debug = turn_result.get("debug") or {}
            if state_model is None and debug.get("classifier_model"):
                state_model = debug.get("classifier_model")
            if writer_model is None and debug.get("model_used"):
                writer_model = debug.get("model_used")
            if max_tokens is None and debug.get("model_max_tokens") is not None:
                max_tokens = debug.get("model_max_tokens")
            if temperature is None and debug.get("model_temperature") is not None:
                temperature = debug.get("model_temperature")

    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else None
    return {
        "run_metadata": {
            "date": _utc_now_iso(),
            "git_sha": _git_sha_short(),
            "mode": mode,
            "python": platform.python_version(),
            "backend_used": backend_used,
            "api_available": api_available,
            "dataset_path": str(dataset_path),
            "cases_total": len(selected_cases),
            "cases_executed": len(case_results),
            "live_runtime_executed": mode == "live" and api_available and not errors,
        },
        "runtime_config_snapshot": {
            "state_analyzer_model": state_model,
            "writer_model": writer_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "rag_top_k": rag_top_k,
            "rag_min_score": rag_min_score,
        },
        "summary": {
            "cases_executed": len(case_results),
            "errors_count": len([case for case in case_results if case.get("error")]) + len(errors),
            "safety_cases": safety_cases,
            "avg_latency_ms": avg_latency,
            "generic_risk_flags": generic_risk,
            "continuity_risk_flags": continuity_risk,
        },
        "errors": errors,
        "case_results": case_results,
    }


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


def _write_outputs(report: dict[str, Any], output_path: Path, markdown_output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_output_path.write_text(_markdown_from_report(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run quality baseline harness (PRD-045.0).")
    parser.add_argument("--mode", choices=("dry-run", "live"), default="dry-run")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--markdown-output", default=str(DEFAULT_MARKDOWN_OUTPUT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--case-id", default=None)
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("QUALITY_BASELINE_API_BASE", "http://localhost:8001/api/v1"),
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("QUALITY_BASELINE_API_KEY", os.getenv("BOT_API_KEY", "test-key-001")),
    )
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    output_path = _resolve_path(args.output)
    markdown_output_path = _resolve_path(args.markdown_output)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    cases = _load_dataset(dataset_path)
    dataset_errors = _validate_dataset_shape(cases)
    if dataset_errors:
        raise ValueError("Dataset schema validation failed:\n- " + "\n- ".join(dataset_errors))

    selected_cases = _select_cases(cases, limit=args.limit, case_id=args.case_id)
    errors: list[str] = []
    case_results: list[dict[str, Any]] = []

    if args.mode == "dry-run":
        case_results = [_run_case_dry(case) for case in selected_cases]
        report = _build_report(
            mode="dry-run",
            dataset_path=dataset_path,
            selected_cases=selected_cases,
            case_results=case_results,
            errors=errors,
            backend_used="none",
            api_available=False,
        )
        _write_outputs(report, output_path=output_path, markdown_output_path=markdown_output_path)
        print(f"[OK] dry-run report JSON: {output_path}")
        print(f"[OK] dry-run report MD:   {markdown_output_path}")
        return 0

    live_config = LiveRuntimeConfig(base_url=args.api_base_url, api_key=args.api_key)
    api_available, probe_message = _probe_live_runtime(live_config)
    if not api_available:
        errors.append(
            "Live mode unavailable: "
            + probe_message
            + " | Start backend and provide a valid X-API-Key. "
            + "Example: python -m uvicorn api.main:app --host 0.0.0.0 --port 8001"
        )
        report = _build_report(
            mode="live",
            dataset_path=dataset_path,
            selected_cases=selected_cases,
            case_results=[],
            errors=errors,
            backend_used=live_config.base_url,
            api_available=False,
        )
        _write_outputs(report, output_path=output_path, markdown_output_path=markdown_output_path)
        print(f"[WARN] live mode unavailable; report generated with errors: {output_path}")
        return 2

    for case in selected_cases:
        try:
            case_result, case_errors = _run_case_live(case, config=live_config)
            case_results.append(case_result)
            errors.extend(case_errors)
        except Exception as error:  # noqa: BLE001
            case_id = str(case.get("id", "<unknown>"))
            errors.append(f"{case_id}: unexpected runner error: {error}")
            errors.append(traceback.format_exc())

    report = _build_report(
        mode="live",
        dataset_path=dataset_path,
        selected_cases=selected_cases,
        case_results=case_results,
        errors=errors,
        backend_used=live_config.base_url,
        api_available=True,
    )
    _write_outputs(report, output_path=output_path, markdown_output_path=markdown_output_path)
    print(f"[OK] live report JSON: {output_path}")
    print(f"[OK] live report MD:   {markdown_output_path}")
    if errors:
        print(f"[WARN] live run completed with {len(errors)} errors")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
