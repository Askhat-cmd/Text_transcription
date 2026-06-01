#!/usr/bin/env python3
"""Run PRD-047.10 human-like writer autonomy evaluation."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.dialogue_policy import build_effective_dialogue_policy
from bot_agent.multiagent.response_planner import build_response_planner_decision

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_10_human_like_cases.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.10"
REQUIRED_CASE_IDS = {
    "anger_truth",
    "direct_concrete_shadow",
    "sarcastic_dissatisfaction",
    "summarize_full_chat",
    "explain_neurostalking",
    "apply_neurostalking",
    "short_support",
    "explicit_one_step",
    "practice_catalog",
}


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
    cases = [item for item in payload if isinstance(item, dict)]
    return sorted(cases, key=lambda item: str(item.get("case_id", "")))


def _validate_dataset(cases: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    found = {str(case.get("case_id", "")).strip() for case in cases}
    missing = sorted(REQUIRED_CASE_IDS.difference(found))
    if missing:
        errors.append(f"missing_required_cases:{','.join(missing)}")
    for case in cases:
        case_id = str(case.get("case_id", "unknown"))
        if not str(case.get("user_message", "")).strip():
            errors.append(f"{case_id}:missing_user_message")
        expected = case.get("expected_planner")
        if not isinstance(expected, dict):
            errors.append(f"{case_id}:missing_expected_planner")
            continue
        for key in ("next_move", "answer_shape", "response_depth"):
            if not str(expected.get(key, "")).strip():
                errors.append(f"{case_id}:missing_expected_{key}")
    return len(errors) == 0, errors


def _thread(payload: dict[str, Any]) -> Any:
    return SimpleNamespace(
        response_mode=str(payload.get("response_mode", "reflect") or "reflect"),
        safety_active=bool(payload.get("safety_active", False)),
        ok_position=str(payload.get("ok_position", "I+W+") or "I+W+"),
    )


def _state(payload: dict[str, Any]) -> Any:
    return SimpleNamespace(
        safety_flag=bool(payload.get("safety_flag", False)),
        nervous_state=str(payload.get("nervous_state", "window") or "window"),
    )


def _count_list_items(text: str) -> int:
    return len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", str(text or "")))


def _evaluate_expectations(answer: str, expectations: dict[str, Any]) -> tuple[dict[str, bool], list[str]]:
    text = str(answer or "")
    lowered = text.lower()
    checks: dict[str, bool] = {}

    min_chars = expectations.get("min_chars")
    if min_chars is not None:
        checks["min_chars"] = len(text) >= int(min_chars)

    max_chars = expectations.get("max_chars")
    if max_chars is not None:
        checks["max_chars"] = len(text) <= int(max_chars)

    max_questions = expectations.get("max_questions")
    if max_questions is not None:
        checks["max_questions"] = text.count("?") <= int(max_questions)

    list_min = expectations.get("list_min")
    if list_min is not None:
        checks["list_min"] = _count_list_items(text) >= int(list_min)

    contains_any = [str(item).lower() for item in list(expectations.get("contains_any", []) or [])]
    if contains_any:
        checks["contains_any"] = any(marker in lowered for marker in contains_any)

    must_not_contain_any = [
        str(item).lower() for item in list(expectations.get("must_not_contain_any", []) or [])
    ]
    if must_not_contain_any:
        checks["must_not_contain_any"] = not any(marker in lowered for marker in must_not_contain_any)

    failed = [name for name, ok in checks.items() if not ok]
    return checks, failed


def _seed_answer(case_id: str) -> str:
    seeds = {
        "anger_truth": "Сделай один шаг прямо сейчас: поставь таймер.",
        "direct_concrete_shadow": "Давай исследуем это мягко и коротко.",
        "sarcastic_dissatisfaction": "Спасибо за сообщение, чем еще помочь?",
        "summarize_full_chat": "Сделай один шаг и затем задай вопрос?",
        "short_support": "Я рядом. Просто береги себя.",
        "explicit_one_step": "Можешь выбрать один из трех шагов: 1. ... 2. ... 3. ...",
    }
    return seeds.get(case_id, "Коротко: сделай один шаг прямо сейчас.")


def _evaluate_direct_case(case: dict[str, Any]) -> dict[str, Any]:
    user_message = str(case.get("user_message", "") or "")
    expected = dict(case.get("expected_planner", {}))
    guard = dict(case.get("knowledge_answer_guard", {}))
    active_line = dict(case.get("active_line", {}))
    dialogue_policy = dict(case.get("dialogue_policy", {}))
    profile = str(dialogue_policy.get("profile", "safe_guided") or "safe_guided")

    effective_policy = build_effective_dialogue_policy(
        profile=profile,
        user_message=user_message,
        state_snapshot=_state(dict(case.get("state_snapshot", {}))),
        thread_state=_thread(dict(case.get("thread_state", {}))),
        knowledge_answer_guard=guard,
    )
    dialogue_payload = dict(dialogue_policy)
    dialogue_payload.update(effective_policy)

    planner = build_response_planner_decision(
        user_message=user_message,
        state_snapshot=_state(dict(case.get("state_snapshot", {}))),
        thread_state=_thread(dict(case.get("thread_state", {}))),
        diagnostic_card=None,
        active_line=active_line,
        knowledge_answer_guard=guard,
        philosophy_kernel={},
        context_package=None,
        dialogue_policy=dialogue_payload,
    ).to_dict()

    contract = WriterContract(
        user_message=user_message,
        thread_state=ThreadState(
            thread_id=f"prd04710_direct_{case.get('case_id')}",
            user_id="prd04710_direct_user",
            core_direction="concept",
            phase="clarify",
            response_mode=str(dict(case.get("thread_state", {})).get("response_mode", "reflect")),
        ),
        memory_bundle=MemoryBundle(),
        knowledge_answer_guard=guard,
        active_line=active_line,
        response_planner=planner,
        dialogue_policy=dialogue_payload,
    )
    writer = WriterAgent(client=object(), model="gpt-5-mini")
    compliance_answer = writer._enforce_answer_compliance(_seed_answer(str(case.get("case_id"))), contract)

    planner_checks = {
        "next_move": str(planner.get("next_move", "")) == str(expected.get("next_move", "")),
        "answer_shape": str(planner.get("answer_shape", "")) == str(expected.get("answer_shape", "")),
        "response_depth": str(planner.get("response_depth", "")) == str(expected.get("response_depth", "")),
    }
    direct_expectation_checks, direct_failures = _evaluate_expectations(
        compliance_answer,
        dict(case.get("live_expectations", {})),
    )
    metadata_checks = {
        "human_like_policy_present": isinstance(dialogue_payload.get("human_like_answer_policy"), dict),
        "constraint_resolution_present": isinstance(dialogue_payload.get("constraint_resolution"), dict),
        "trace_final_answer_shape_present": bool(writer.last_debug.get("final_answer_shape")),
    }
    failures = [
        name for name, ok in planner_checks.items() if not ok
    ] + direct_failures + [name for name, ok in metadata_checks.items() if not ok]
    return {
        "case_id": str(case.get("case_id", "")),
        "group": str(case.get("group", "")),
        "evaluation": {
            "passed": len(failures) == 0,
            "planner_checks": planner_checks,
            "expectation_checks": direct_expectation_checks,
            "metadata_checks": metadata_checks,
            "failure_reasons": failures,
        },
        "planner": {
            "next_move": planner.get("next_move"),
            "answer_shape": planner.get("answer_shape"),
            "response_depth": planner.get("response_depth"),
            "question_policy": planner.get("question_policy"),
            "practice_policy": planner.get("practice_policy"),
        },
        "compliance_answer_preview": compliance_answer[:800],
        "writer_debug": {
            "final_answer_shape": writer.last_debug.get("final_answer_shape"),
            "human_like_answer_policy_enabled": writer.last_debug.get("human_like_answer_policy_enabled"),
            "explicit_answer_need": writer.last_debug.get("explicit_answer_need"),
            "repair_user_dissatisfaction": writer.last_debug.get("repair_user_dissatisfaction"),
            "sarcasm_or_negative_feedback": writer.last_debug.get("sarcasm_or_negative_feedback"),
            "overruled_constraints": writer.last_debug.get("overruled_constraints"),
            "question_forced": writer.last_debug.get("question_forced"),
            "practice_forced": writer.last_debug.get("practice_forced"),
            "microstep_forced": writer.last_debug.get("microstep_forced"),
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
    case_results = [_evaluate_direct_case(case) for case in cases]
    total = len(case_results)
    passed = sum(1 for item in case_results if bool(item.get("evaluation", {}).get("passed", False)))
    checks = {
        "cases_passed": passed == total,
        "required_cases_present": REQUIRED_CASE_IDS.issubset(
            {str(item.get("case_id", "")) for item in case_results}
        ),
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
        "case_results": case_results,
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


def _extract_writer_debug(trace_payload: dict[str, Any]) -> dict[str, Any]:
    writer_llm = (
        dict(trace_payload.get("writer_llm", {}))
        if isinstance(trace_payload.get("writer_llm"), dict)
        else {}
    )
    fields = {
        "human_like_answer_policy_enabled": writer_llm.get("human_like_answer_policy_enabled"),
        "explicit_answer_need": writer_llm.get("explicit_answer_need"),
        "repair_user_dissatisfaction": writer_llm.get("repair_user_dissatisfaction"),
        "sarcasm_or_negative_feedback": writer_llm.get("sarcasm_or_negative_feedback"),
        "overruled_constraints": writer_llm.get("overruled_constraints"),
        "final_answer_shape": writer_llm.get("final_answer_shape"),
        "question_forced": writer_llm.get("question_forced"),
        "practice_forced": writer_llm.get("practice_forced"),
        "microstep_forced": writer_llm.get("microstep_forced"),
    }
    return fields


def _run_live(
    *,
    cases: list[dict[str, Any]],
    base_url: str,
    api_key: str,
    admin_runtime_url: str,
) -> dict[str, Any]:
    headers = {"X-API-Key": api_key}
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
    profile = str(dict(runtime_payload.get("dialogue_profile", {})).get("value", "") or "")
    effective_policy = (
        dict(runtime_payload.get("dialogue_policy", {}))
        if isinstance(runtime_payload.get("dialogue_policy"), dict)
        else {}
    )
    if profile != "mvp_free_dialogue":
        return {
            "mode": "live",
            "status": "blocked",
            "timestamp": _now_iso(),
            "reason": f"dialogue_profile_not_mvp:{profile or 'unknown'}",
        }

    case_results: list[dict[str, Any]] = []
    api_root = _derive_api_root(base_url)
    for case in cases:
        case_id = str(case.get("case_id", "unknown"))
        query = str(case.get("user_message", "") or "")
        session_id = f"prd04710-live-{case_id}-{uuid.uuid4().hex[:8]}"
        status_code, payload = _http_json_request(
            method="POST",
            url=f"{base_url.rstrip('/')}/questions/adaptive",
            headers=headers,
            payload={
                "query": query,
                "session_id": session_id,
                "debug": True,
                "include_path": False,
                "include_feedback_prompt": True,
            },
            timeout=120.0,
        )
        if status_code != 200:
            case_results.append(
                {
                    "case_id": case_id,
                    "evaluation": {"passed": False, "failure_reasons": [f"adaptive_status_{status_code}"]},
                }
            )
            continue
        answer = str(payload.get("answer", "") or "")
        trace_payload = (
            dict(payload.get("trace", {})) if isinstance(payload.get("trace"), dict) else {}
        )
        metadata_payload = (
            dict(payload.get("metadata", {})) if isinstance(payload.get("metadata"), dict) else {}
        )
        resolved_session_id = str(
            metadata_payload.get("session_id") or trace_payload.get("session_id") or session_id
        )

        trace_status, trace_response = _http_json_request(
            method="GET",
            url=f"{api_root}/api/debug/session/{resolved_session_id}/multiagent-trace",
            headers=headers,
            timeout=60.0,
        )
        trace_case = trace_response if trace_status == 200 and isinstance(trace_response, dict) else {}
        writer_debug = _extract_writer_debug(trace_case)
        planner_payload = (
            dict(trace_case.get("response_planner", {}))
            if isinstance(trace_case.get("response_planner"), dict)
            else dict(trace_payload.get("response_planner", {}))
            if isinstance(trace_payload.get("response_planner"), dict)
            else {}
        )

        checks, failures = _evaluate_expectations(answer, dict(case.get("live_expectations", {})))
        if "contains_any" in failures:
            failures = [item for item in failures if item != "contains_any"]
        trace_checks = {
            "trace_writer_debug_visible": any(value is not None for value in writer_debug.values()),
            "runtime_effective_has_human_like_policy": isinstance(
                effective_policy.get("human_like_answer_policy"),
                dict,
            ),
        }
        if not trace_checks["runtime_effective_has_human_like_policy"]:
            failures.append("runtime_effective_has_human_like_policy")
        case_results.append(
            {
                "case_id": case_id,
                "group": str(case.get("group", "")),
                "query": query,
                "answer_preview": answer[:800],
                "planner": {
                    "next_move": planner_payload.get("next_move"),
                    "answer_shape": planner_payload.get("answer_shape"),
                    "response_depth": planner_payload.get("response_depth"),
                    "question_policy": planner_payload.get("question_policy"),
                    "practice_policy": planner_payload.get("practice_policy"),
                },
                "writer_debug": writer_debug,
                "evaluation": {
                    "passed": len(failures) == 0,
                    "checks": checks,
                    "trace_checks": trace_checks,
                    "failure_reasons": failures,
                },
            }
        )

    total = len(case_results)
    passed = sum(1 for item in case_results if bool(item.get("evaluation", {}).get("passed", False)))
    checks = {
        "runtime_profile_mvp": profile == "mvp_free_dialogue",
        "runtime_human_like_policy_visible": isinstance(effective_policy.get("human_like_answer_policy"), dict),
        "all_cases_executed": total == len(cases),
        "all_cases_passed": passed == total,
    }
    return {
        "mode": "live",
        "status": "passed" if all(checks.values()) else "failed",
        "timestamp": _now_iso(),
        "summary": {
            "cases_total": total,
            "cases_passed": passed,
            "cases_failed": max(0, total - passed),
        },
        "checks": checks,
        "runtime_effective": {
            "dialogue_profile": profile,
            "dialogue_policy": effective_policy,
        },
        "case_results": case_results,
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
        "# PRD-047.10 Human-like Live Eval",
        "",
        f"- status: `{payload.get('status')}`",
        f"- timestamp_utc: `{payload.get('timestamp')}`",
    ]
    summary = dict(payload.get("summary", {}))
    if summary:
        lines.extend(
            [
                f"- cases_total: `{summary.get('cases_total', 0)}`",
                f"- cases_passed: `{summary.get('cases_passed', 0)}`",
                f"- cases_failed: `{summary.get('cases_failed', 0)}`",
            ]
        )
    lines.append("")
    for case in list(payload.get("case_results", []) or []):
        evaluation = dict(case.get("evaluation", {}))
        lines.append(f"## {case.get('case_id', 'unknown')}")
        lines.append(f"- passed: `{bool(evaluation.get('passed', False))}`")
        lines.append(f"- failures: `{', '.join([str(x) for x in list(evaluation.get('failure_reasons', []) or [])]) or 'none'}`")
        preview = str(case.get("answer_preview", "") or "").strip()
        if preview:
            lines.append("- answer_preview:")
            lines.append("```text")
            lines.append(preview[:700])
            lines.append("```")
        lines.append("")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.10 human-like evaluation")
    parser.add_argument("--mode", choices=["dry", "direct", "live"], default="dry")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--base-url", default=os.getenv("PRD04710_BASE_URL", "http://127.0.0.1:8001/api/v1"))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD04710_ADMIN_RUNTIME_URL", "http://127.0.0.1:8001/api/admin/runtime/effective"),
    )
    parser.add_argument("--api-key", default=os.getenv("PRD04710_API_KEY", "dev-key-001"))
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    log_dir = _resolve_path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    cases = _select_cases(_load_cases(dataset_path), args.case_id, args.limit)

    if args.mode == "dry":
        payload = _run_dry(cases)
        output_json = _resolve_path(args.output_json) if args.output_json else log_dir / "human_like_eval_dry.json"
    elif args.mode == "direct":
        payload = _run_direct(cases)
        output_json = _resolve_path(args.output_json) if args.output_json else log_dir / "human_like_eval_direct.json"
    else:
        payload = _run_live(
            cases=cases,
            base_url=str(args.base_url),
            api_key=str(args.api_key),
            admin_runtime_url=str(args.admin_runtime_url),
        )
        output_json = _resolve_path(args.output_json) if args.output_json else log_dir / "human_like_eval_live.json"

    payload["prd"] = "PRD-047.10"
    payload["dataset"] = str(dataset_path)
    _write_json(output_json, payload)

    if args.mode == "live":
        md_lines = _build_live_markdown(payload)
        output_md = _resolve_path(args.output_md) if args.output_md else log_dir / "human_like_eval_live.md"
        _write_md(output_md, md_lines)

    print(json.dumps({"status": payload.get("status"), "output": str(output_json)}, ensure_ascii=False))
    return 0 if payload.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
