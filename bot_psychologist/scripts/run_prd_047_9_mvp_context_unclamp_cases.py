#!/usr/bin/env python3
"""Run PRD-047.9 MVP context-unclamp / adaptive dialogue policy evaluation."""

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
from bot_agent.multiagent.dialogue_policy import (
    build_effective_dialogue_policy,
    format_conversation_context_for_writer_with_meta,
)
from bot_agent.multiagent.response_planner import build_response_planner_decision

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_9_mvp_context_unclamp_cases.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.9"
REQUIRED_CASE_IDS = {
    "neurostalking_definition_full",
    "followup_expand_inherits_concept",
    "repair_expand_after_user_not_understand",
    "boss_example_explanation",
    "practice_catalog_not_one_step",
    "explicit_one_step_still_one_step",
    "explicit_short_still_short",
    "safety_still_safety",
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


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("dataset must be list")
    return [item for item in payload if isinstance(item, dict)]


def _validate_dataset(cases: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    found = {str(item.get("case_id", "")).strip() for item in cases}
    missing = sorted(REQUIRED_CASE_IDS.difference(found))
    if missing:
        errors.append(f"missing_required_cases:{','.join(missing)}")

    for idx, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id", "") or f"case_{idx}")
        expected = case.get("expected_planner")
        if not str(case.get("user_message", "")).strip():
            errors.append(f"{case_id}:missing_user_message")
        if not isinstance(expected, dict):
            errors.append(f"{case_id}:missing_expected_planner")
        else:
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


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
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

    checks = {
        "next_move": str(planner.get("next_move", "")) == str(expected.get("next_move", "")),
        "answer_shape": str(planner.get("answer_shape", "")) == str(expected.get("answer_shape", "")),
        "response_depth": str(planner.get("response_depth", "")) == str(expected.get("response_depth", "")),
    }
    failures = [name for name, ok in checks.items() if not ok]
    return {
        "case_id": str(case.get("case_id", "")),
        "group": str(case.get("group", "")),
        "evaluation": {
            "passed": not failures,
            "checks": checks,
            "failure_reasons": failures,
            "expected": expected,
            "actual": {
                "next_move": planner.get("next_move"),
                "answer_shape": planner.get("answer_shape"),
                "response_depth": planner.get("response_depth"),
                "question_policy": planner.get("question_policy"),
                "practice_policy": planner.get("practice_policy"),
            },
        },
    }


def _direct_writer_guard_check() -> dict[str, Any]:
    contract = WriterContract(
        user_message="скажи, а в нейросталкинге какие практики предлагаются чтобы это видеть",
        thread_state=ThreadState(
            thread_id="prd0479_direct",
            user_id="prd0479_user",
            core_direction="concept",
            phase="clarify",
            response_mode="reflect",
        ),
        memory_bundle=MemoryBundle(),
        dialogue_policy={"profile": "mvp_free_dialogue", "practice_overview_requested": True},
        response_planner={
            "enabled": True,
            "next_move": "answer_practice_overview",
            "answer_shape": "practice_catalog_explanation",
            "response_depth": "long",
            "question_policy": "optional_none",
            "practice_policy": "overview_allowed",
            "revoicing_policy": "suppressed",
        },
        knowledge_answer_guard={
            "knowledge_answer": {
                "needed": True,
                "concept": "нейросталкинг",
                "should_answer_directly": True,
                "kb_grounding_available": True,
                "answer_type": "practice_overview",
            },
            "practice_gate": {"practice_allowed": True},
        },
    )
    agent = WriterAgent(client=object(), model="gpt-5-mini")
    forced = agent._enforce_answer_compliance("Коротко: сделай один шаг.", contract)
    has_three_or_more_items = len(re.findall(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+", forced)) >= 3
    return {
        "has_three_or_more_items": has_three_or_more_items,
        "output_chars": len(str(forced or "")),
        "output_preview": str(forced or "")[:500],
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
    case_results = [_evaluate_case(case) for case in cases]
    total = len(case_results)
    passed = sum(1 for item in case_results if bool(item.get("evaluation", {}).get("passed", False)))

    context = (
        ("older " * 1300)
        + "\nRECENT FULL TURNS:\nUSER#turn_8: блин! а что делать то\n"
        + "ASSISTANT#turn_8: сначала разберем механизм\nUSER#turn_9: не понял, подробнее"
    )
    _, meta = format_conversation_context_for_writer_with_meta(
        conversation_context=context,
        profile="safe_guided",
        budget_chars=2800,
    )
    writer_guard = _direct_writer_guard_check()
    checks = {
        "cases_passed": passed == total,
        "context_truncated": bool(meta.get("context_truncated", False)),
        "context_preserved_recent_turns": int(meta.get("preserved_recent_turns_count", 0) or 0) >= 2,
        "writer_catalog_has_3_items": bool(writer_guard.get("has_three_or_more_items", False)),
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
        "context_meta": meta,
        "writer_guard": writer_guard,
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
        parsed: dict[str, Any]
        if raw.strip():
            try:
                payload_obj = json.loads(raw)
                parsed = payload_obj if isinstance(payload_obj, dict) else {"raw": payload_obj}
            except json.JSONDecodeError:
                parsed = {"raw": raw}
        else:
            parsed = {}
        return status_code, parsed


def _derive_api_root(api_base_url: str) -> str:
    base = api_base_url.rstrip("/")
    suffix = "/api/v1"
    if base.endswith(suffix):
        return base[: -len(suffix)]
    return base


def _run_live(
    *,
    api_base_url: str,
    admin_runtime_url: str,
    api_key: str,
    log_dir: Path,
) -> dict[str, Any]:
    headers = {"X-API-Key": api_key}
    try:
        runtime_status, runtime_payload = _http_json_request(
            method="GET",
            url=admin_runtime_url,
            headers=headers,
            timeout=30.0,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "mode": "live",
            "status": "blocked",
            "timestamp": _now_iso(),
            "reason": f"admin_runtime_unavailable:{exc.__class__.__name__}",
        }
    if runtime_status != 200:
        return {
            "mode": "live",
            "status": "blocked",
            "timestamp": _now_iso(),
            "reason": f"admin_runtime_status_{runtime_status}",
        }

    profile = str(dict(runtime_payload.get("dialogue_profile", {})).get("value", "") or "")
    policy = dict(runtime_payload.get("dialogue_policy", {})) if isinstance(runtime_payload.get("dialogue_policy"), dict) else {}
    runtime_drift = (
        dict(runtime_payload.get("planner_drift_guard", {}))
        if isinstance(runtime_payload.get("planner_drift_guard"), dict)
        else {}
    )
    if profile != "mvp_free_dialogue":
        return {
            "mode": "live",
            "status": "blocked",
            "timestamp": _now_iso(),
            "reason": f"dialogue_profile_not_mvp_free:{profile or 'unknown'}",
        }

    session_id = f"prd0479-live-{uuid.uuid4().hex[:10]}"
    query = "скажи, а в нейросталкинге какие практики предлагаются чтобы это видеть"
    request_payload = {
        "query": query,
        "session_id": session_id,
        "debug": True,
        "include_path": False,
        "include_feedback_prompt": True,
    }
    try:
        adaptive_status, adaptive_response = _http_json_request(
            method="POST",
            url=f"{api_base_url.rstrip('/')}/questions/adaptive",
            headers=headers,
            payload=request_payload,
            timeout=120.0,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "mode": "live",
            "status": "blocked",
            "timestamp": _now_iso(),
            "reason": f"adaptive_unavailable:{exc.__class__.__name__}",
        }

    if adaptive_status != 200:
        return {
            "mode": "live",
            "status": "failed",
            "timestamp": _now_iso(),
            "reason": f"adaptive_status_{adaptive_status}",
            "error_payload": adaptive_response,
        }

    trace_payload = dict(adaptive_response.get("trace", {})) if isinstance(adaptive_response.get("trace"), dict) else {}
    metadata_payload = dict(adaptive_response.get("metadata", {})) if isinstance(adaptive_response.get("metadata"), dict) else {}
    answer = str(adaptive_response.get("answer", "") or "")
    planner = dict(trace_payload.get("response_planner", {})) if isinstance(trace_payload.get("response_planner"), dict) else {}
    drift_guard = dict(trace_payload.get("planner_drift_guard", {})) if isinstance(trace_payload.get("planner_drift_guard"), dict) else {}

    resolved_session_id = str(metadata_payload.get("session_id") or trace_payload.get("session_id") or session_id)
    api_root = _derive_api_root(api_base_url)

    trace_status, trace_response = _http_json_request(
        method="GET",
        url=f"{api_root}/api/debug/session/{resolved_session_id}/multiagent-trace",
        headers=headers,
        timeout=60.0,
    )

    if trace_status == 200 and isinstance(trace_response, dict):
        writer_llm = dict(trace_response.get("writer_llm", {})) if isinstance(trace_response.get("writer_llm"), dict) else {}
        if not planner and isinstance(trace_response.get("response_planner"), dict):
            planner = dict(trace_response.get("response_planner", {}))
        if not drift_guard and isinstance(trace_response.get("planner_drift_guard"), dict):
            drift_guard = dict(trace_response.get("planner_drift_guard", {}))
    else:
        writer_llm = {}

    prompt_canvas = str(writer_llm.get("user_prompt", "") or "")
    practice_items = len(re.findall(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+", answer))
    practice_keywords = len(re.findall(r"(?iu)\b(практик|направлен|подход|формат)\w*", answer))
    has_multi_direction_signal = practice_items >= 3 or practice_keywords >= 3

    (log_dir / "live_neurostalking_practice_catalog_answer.md").write_text(answer, encoding="utf-8")
    (log_dir / "live_writer_prompt_canvas.txt").write_text(prompt_canvas, encoding="utf-8")

    checks = {
        "adaptive_status_ok": adaptive_status == 200,
        "trace_status_ok": trace_status == 200,
        "policy_advisory": str(policy.get("planner_authority", "")) == "advisory",
        "policy_high_autonomy": str(policy.get("writer_autonomy", "")) == "high",
        "planner_shape_catalog": str(planner.get("answer_shape", "")) == "practice_catalog_explanation",
        "answer_long_enough": len(answer) >= 320,
        "answer_has_3_directions": has_multi_direction_signal,
        "prompt_has_override_block": "MVP FREE DIALOGUE OVERRIDES:" in prompt_canvas,
        "prompt_has_context_budget": "context_budget_chars=" in prompt_canvas,
        "drift_guard_observe_only": (
            bool(drift_guard)
            and (
                drift_guard.get("blocking_user_answers") is False
                or (
                    str(runtime_drift.get("mode", "")).lower() == "observe_only"
                    and runtime_drift.get("blocking_user_answers") is False
                )
            )
        ),
    }
    return {
        "mode": "live",
        "status": "passed" if all(checks.values()) else "failed",
        "timestamp": _now_iso(),
        "checks": checks,
        "session_id": resolved_session_id,
        "trace_status": trace_status,
        "planner": planner,
        "dialogue_policy": policy,
        "planner_drift_guard": drift_guard,
        "answer_preview": answer[:800],
        "writer_prompt_preview": prompt_canvas[:2000],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.9 context unclamp evaluation")
    parser.add_argument("--mode", choices=["dry", "direct", "live"], default="dry")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--api-base-url", default=os.getenv("PRD0479_API_BASE_URL", "http://127.0.0.1:8001/api/v1"))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD0479_ADMIN_RUNTIME_URL", "http://127.0.0.1:8001/api/admin/runtime/effective"),
    )
    parser.add_argument("--api-key", default=os.getenv("PRD0479_API_KEY", "dev-key-001"))
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    log_dir = _resolve_path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    cases = _load_cases(dataset_path)

    if args.mode == "dry":
        payload = _run_dry(cases)
        output = log_dir / "context_unclamp_dry.json"
    elif args.mode == "direct":
        payload = _run_direct(cases)
        output = log_dir / "context_unclamp_direct.json"
    else:
        payload = _run_live(
            api_base_url=str(args.api_base_url),
            admin_runtime_url=str(args.admin_runtime_url),
            api_key=str(args.api_key),
            log_dir=log_dir,
        )
        output = log_dir / "context_unclamp_live.json"

    payload["prd"] = "PRD-047.9"
    payload["dataset"] = str(dataset_path)
    _write_json(output, payload)
    print(json.dumps({"status": payload.get("status"), "output": str(output)}, ensure_ascii=False))
    return 0 if payload.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
