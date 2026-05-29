#!/usr/bin/env python3
"""Run PRD-047.8 MVP free dialogue profile evaluation."""

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
from bot_agent.multiagent.dialogue_policy import apply_active_concept_continuation
from bot_agent.multiagent.response_planner import build_response_planner_decision

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_8_mvp_free_dialogue_cases.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.8"
REQUIRED_GROUP_MIN_COUNTS = {
    "known_concept_full_answer": 3,
    "continuation_not_short_support": 2,
    "explicit_short_user": 2,
    "developer_free_answer": 5,
    "minimal_guardrails": 3,
    "practice_gate": 3,
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
    items = [item for item in payload if isinstance(item, dict)]
    return sorted(items, key=lambda item: str(item.get("case_id", "")))


def _validate_dataset(cases: list[dict[str, Any]]) -> tuple[bool, list[str], dict[str, int]]:
    errors: list[str] = []
    coverage: dict[str, int] = {}

    if len(cases) < 18:
        errors.append(f"dataset_too_small:{len(cases)}")

    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id", "") or f"case_{index}")
        group = str(case.get("group", "")).strip()
        coverage[group] = coverage.get(group, 0) + 1

        if not str(case.get("user_message", "")).strip():
            errors.append(f"{case_id}:missing_user_message")

        expected = case.get("expected_planner")
        if not isinstance(expected, dict):
            errors.append(f"{case_id}:missing_expected_planner")
        else:
            for key in ("next_move", "answer_shape", "response_depth"):
                if not str(expected.get(key, "")).strip():
                    errors.append(f"{case_id}:missing_expected_{key}")

        dialogue_policy = case.get("dialogue_policy")
        if not isinstance(dialogue_policy, dict):
            errors.append(f"{case_id}:missing_dialogue_policy")
        elif str(dialogue_policy.get("profile", "")).strip() != "mvp_free_dialogue":
            errors.append(f"{case_id}:profile_must_be_mvp_free_dialogue")

    for group, minimum in REQUIRED_GROUP_MIN_COUNTS.items():
        count = coverage.get(group, 0)
        if count < minimum:
            errors.append(f"group_coverage_failed:{group}:{count}<{minimum}")

    return len(errors) == 0, errors, coverage


def _thread_state(payload: dict[str, Any]) -> Any:
    return SimpleNamespace(
        response_mode=str(payload.get("response_mode", "reflect") or "reflect"),
        safety_active=bool(payload.get("safety_active", False)),
        ok_position=str(payload.get("ok_position", "I+W+") or "I+W+"),
    )


def _state_snapshot(payload: dict[str, Any]) -> Any:
    return SimpleNamespace(
        safety_flag=bool(payload.get("safety_flag", False)),
        nervous_state=str(payload.get("nervous_state", "window") or "window"),
    )


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    user_message = str(case.get("user_message", "") or "")
    thread = _thread_state(dict(case.get("thread_state", {})))
    state = _state_snapshot(dict(case.get("state_snapshot", {})))
    active_line = dict(case.get("active_line", {}))
    guard = dict(case.get("knowledge_answer_guard", {}))
    dialogue_policy = dict(case.get("dialogue_policy", {}))
    expected = dict(case.get("expected_planner", {}))

    planner = build_response_planner_decision(
        user_message=user_message,
        state_snapshot=state,
        thread_state=thread,
        diagnostic_card=None,
        active_line=active_line,
        knowledge_answer_guard=guard,
        philosophy_kernel={},
        context_package=None,
        dialogue_policy=dialogue_policy,
    ).to_dict()
    checks = {
        "next_move": str(planner.get("next_move", "")) == str(expected.get("next_move", "")),
        "answer_shape": str(planner.get("answer_shape", "")) == str(expected.get("answer_shape", "")),
        "response_depth": str(planner.get("response_depth", "")) == str(expected.get("response_depth", "")),
        "question_policy_present": bool(str(planner.get("question_policy", "")).strip()),
        "practice_policy_present": bool(str(planner.get("practice_policy", "")).strip()),
    }
    failure_reasons = [name for name, ok in checks.items() if not ok]
    return {
        "case_id": str(case.get("case_id", "")),
        "group": str(case.get("group", "")),
        "user_message": user_message,
        "evaluation": {
            "passed": not failure_reasons,
            "checks": checks,
            "failure_reasons": failure_reasons,
            "expected": expected,
            "actual": {
                key: planner.get(key)
                for key in (
                    "next_move",
                    "answer_shape",
                    "response_depth",
                    "question_policy",
                    "practice_policy",
                    "revoicing_policy",
                )
            },
        },
    }


def _build_direct_writer_contract(profile: str = "mvp_free_dialogue") -> WriterContract:
    return WriterContract(
        user_message="я не понял, объясни нормально и развернуто",
        thread_state=ThreadState(
            thread_id="prd0478_direct",
            user_id="prd0478_direct_user",
            core_direction="known_concept",
            phase="clarify",
            response_mode="reflect",
        ),
        memory_bundle=MemoryBundle(),
        knowledge_answer_guard={
            "knowledge_answer": {
                "needed": True,
                "concept": "нейросталкинг",
                "should_answer_directly": True,
                "kb_grounding_available": True,
            },
            "practice_gate": {"practice_allowed": False},
        },
        response_planner={
            "enabled": True,
            "next_move": "repair_misalignment",
            "answer_shape": "repair_and_expand",
            "response_depth": "long",
            "question_policy": "none",
            "practice_policy": "allowed_if_explicit",
            "revoicing_policy": "suppressed",
        },
        dialogue_policy={
            "profile": profile,
            "expansion_requested": True,
            "repair_and_expand_requested": True,
            "active_concept": "нейросталкинг",
        },
    )


def _run_dry(cases: list[dict[str, Any]]) -> dict[str, Any]:
    valid, errors, coverage = _validate_dataset(cases)
    return {
        "mode": "dry",
        "status": "passed" if valid else "failed",
        "timestamp": _now_iso(),
        "dataset_total": len(cases),
        "coverage": coverage,
        "errors": errors,
    }


def _run_direct(cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_results = [_evaluate_case(case) for case in cases]
    total = len(case_results)
    passed = sum(1 for item in case_results if bool(item.get("evaluation", {}).get("passed", False)))

    inherited_guard, inherited_concept = apply_active_concept_continuation(
        user_message="можешь подробнее?",
        dialogue_profile="mvp_free_dialogue",
        knowledge_answer_guard={"knowledge_answer": {"needed": False, "concept": ""}},
        thread_active_frame={"active_concept": "нейросталкинг"},
    )
    inherited_ok = (
        inherited_concept == "нейросталкинг"
        and bool(dict(inherited_guard.get("knowledge_answer", {})).get("should_answer_directly", False))
    )

    agent = WriterAgent(client=object(), model="gpt-5-mini")
    contract = _build_direct_writer_contract()
    repaired = agent._enforce_answer_compliance("Коротко.", contract)
    relaxed_constraints_ok = len(str(repaired or "")) > 260

    return {
        "mode": "direct",
        "status": "passed" if passed == total and inherited_ok and relaxed_constraints_ok else "failed",
        "timestamp": _now_iso(),
        "summary": {
            "cases_total": total,
            "cases_passed": passed,
            "cases_failed": max(0, total - passed),
            "active_concept_inheritance_ok": inherited_ok,
            "writer_repair_and_expand_relaxed_ok": relaxed_constraints_ok,
        },
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
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status_code = int(getattr(response, "status", 200))
        raw = response.read().decode("utf-8")
        data = json.loads(raw) if raw.strip() else {}
        return status_code, data if isinstance(data, dict) else {"raw": data}


def _run_live(
    *,
    api_base_url: str,
    admin_runtime_url: str,
    api_key: str,
) -> dict[str, Any]:
    runtime_headers = {"X-API-Key": api_key}
    try:
        runtime_status, runtime_payload = _http_json_request(
            method="GET",
            url=admin_runtime_url,
            headers=runtime_headers,
            timeout=30.0,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "mode": "live",
            "status": "blocked",
            "timestamp": _now_iso(),
            "reason": f"admin_runtime_unavailable:{exc.__class__.__name__}",
            "runtime_checked": False,
            "chat_checked": False,
        }

    if runtime_status != 200:
        return {
            "mode": "live",
            "status": "blocked",
            "timestamp": _now_iso(),
            "reason": f"admin_runtime_status_{runtime_status}",
            "runtime_checked": True,
            "chat_checked": False,
        }

    profile = str(dict(runtime_payload.get("dialogue_profile", {})).get("value", "") or "")
    if profile != "mvp_free_dialogue":
        return {
            "mode": "live",
            "status": "blocked",
            "timestamp": _now_iso(),
            "reason": f"dialogue_profile_not_mvp_free:{profile or 'unknown'}",
            "runtime_checked": True,
            "chat_checked": False,
        }

    user_id = f"prd0478_live_{uuid.uuid4().hex[:8]}"
    chat_payload = {
        "user_id": user_id,
        "query": "что такое нейросталкинг, и как его можно применять в жизни? Ответь развернуто.",
        "developer_trace_mode": True,
    }
    try:
        chat_status, chat_response = _http_json_request(
            method="POST",
            url=f"{api_base_url.rstrip('/')}/chat",
            headers=runtime_headers,
            payload=chat_payload,
            timeout=120.0,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "mode": "live",
            "status": "blocked",
            "timestamp": _now_iso(),
            "reason": f"chat_unavailable:{exc.__class__.__name__}",
            "runtime_checked": True,
            "chat_checked": False,
        }

    answer = str(chat_response.get("answer", "") or "")
    planner = dict(chat_response.get("debug", {}).get("response_planner", {})) if isinstance(chat_response.get("debug"), dict) else {}
    checks = {
        "chat_status_ok": chat_status == 200,
        "answer_not_short": len(answer) >= 280,
        "planner_not_short_support": str(planner.get("answer_shape", "")) != "short_support",
        "planner_shape_is_expanded": str(planner.get("answer_shape", "")) in {
            "concept_explanation_full",
            "expanded_explanation",
            "repair_and_expand",
            "example_driven_explanation",
        },
    }
    return {
        "mode": "live",
        "status": "passed" if all(checks.values()) else "failed",
        "timestamp": _now_iso(),
        "runtime_checked": True,
        "chat_checked": True,
        "checks": checks,
        "planner": planner,
        "answer_preview": answer[:800],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.8 MVP free dialogue evaluation")
    parser.add_argument("--mode", choices=["dry", "direct", "live"], default="dry")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--api-base-url", default=os.getenv("PRD0478_API_BASE_URL", "http://127.0.0.1:8015/api/v1"))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD0478_ADMIN_RUNTIME_URL", "http://127.0.0.1:8015/api/admin/runtime/effective"),
    )
    parser.add_argument("--api-key", default=os.getenv("PRD0478_API_KEY", "dev-key-001"))
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    log_dir = _resolve_path(args.log_dir)
    cases = _load_cases(dataset_path)

    if args.mode == "dry":
        payload = _run_dry(cases)
        output_path = log_dir / "mvp_free_dialogue_dry.json"
    elif args.mode == "direct":
        payload = _run_direct(cases)
        output_path = log_dir / "mvp_free_dialogue_direct.json"
    else:
        payload = _run_live(
            api_base_url=str(args.api_base_url),
            admin_runtime_url=str(args.admin_runtime_url),
            api_key=str(args.api_key),
        )
        output_path = log_dir / "mvp_free_dialogue_live.json"

    payload["prd"] = "PRD-047.8"
    payload["dataset"] = str(dataset_path)
    _write_json(output_path, payload)
    print(json.dumps({"status": payload.get("status"), "output": str(output_path)}, ensure_ascii=False))
    return 0 if payload.get("status") in {"passed", "blocked"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

