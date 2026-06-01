#!/usr/bin/env python3
"""Run PRD-047.10-HF1 dialogue pragmatics + retrieval gating evaluation."""

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
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.dialogue_pragmatics import (
    build_contextual_retrieval_decision_v1,
    build_dialogue_pragmatics_v1,
)
from bot_agent.multiagent.response_planner import build_response_planner_decision

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_10_hf1_dialogue_pragmatics_cases.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.10-HF1"
REQUIRED_CASE_IDS = {
    "HF1_SHORT_YES_PHRASE",
    "HF1_DA_KONECHNO_NO_REGULATE_STUB",
    "HF1_YES_EXAMPLE_WITH_KB",
    "HF1_YES_SHORT_PHRASE_RECENT_ONLY",
    "HF1_USER_SAYS_YOU_DID_NOT_ANSWER",
    "HF1_SHORT_YES_NO_CONTEXT",
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
    return [item for item in payload if isinstance(item, dict)]


def _validate_dataset(cases: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    found_ids = {str(item.get("case_id", "")).strip() for item in cases}
    missing = sorted(REQUIRED_CASE_IDS.difference(found_ids))
    if missing:
        errors.append(f"missing_required_cases:{','.join(missing)}")
    if len(cases) < 14:
        errors.append("dataset_has_less_than_14_cases")
    for case in cases:
        case_id = str(case.get("case_id", "unknown"))
        if not str(case.get("user_message", "")).strip():
            errors.append(f"{case_id}:missing_user_message")
        expected = case.get("expected")
        if not isinstance(expected, dict):
            errors.append(f"{case_id}:missing_expected")
    return len(errors) == 0, errors


def _semantic_hits(case: dict[str, Any]) -> list[SemanticHit]:
    hits: list[SemanticHit] = []
    for item in list(case.get("semantic_hits", []) or []):
        if not isinstance(item, dict):
            continue
        hits.append(
            SemanticHit(
                chunk_id=str(item.get("chunk_id", "") or ""),
                content=str(item.get("content", "") or ""),
                source=str(item.get("source", "kb") or "kb"),
                score=float(item.get("score", 0.0) or 0.0),
            )
        )
    return hits


def _evaluate_direct_case(case: dict[str, Any]) -> dict[str, Any]:
    expected = dict(case.get("expected", {}))
    pragmatics = build_dialogue_pragmatics_v1(
        user_message=str(case.get("user_message", "") or ""),
        conversation_context=str(case.get("conversation_context", "") or ""),
        previous_assistant_message=str(case.get("previous_assistant_message", "") or ""),
        dialogue_policy=dict(case.get("dialogue_policy", {})),
        active_frame={},
        thread_state=None,
    )
    decision = build_contextual_retrieval_decision_v1(
        dialogue_pragmatics=pragmatics,
        knowledge_answer_guard=dict(case.get("knowledge_answer_guard", {})),
        semantic_hits=_semantic_hits(case),
    )

    checks: dict[str, bool] = {}
    if "is_contextual_followup" in expected:
        checks["is_contextual_followup"] = bool(pragmatics.get("is_contextual_followup", False)) == bool(
            expected.get("is_contextual_followup", False)
        )
    if "is_short_utterance" in expected:
        checks["is_short_utterance"] = bool(pragmatics.get("is_short_utterance", False)) == bool(
            expected.get("is_short_utterance", False)
        )
    if "previous_assistant_offer_type" in expected:
        checks["previous_assistant_offer_type"] = str(
            pragmatics.get("previous_assistant_offer_type", "")
        ) == str(expected.get("previous_assistant_offer_type", ""))
    if "should_answer_directly" in expected:
        checks["should_answer_directly"] = bool(pragmatics.get("should_answer_directly", False)) == bool(
            expected.get("should_answer_directly", False)
        )
    if "repair_user_dissatisfaction" in expected:
        checks["repair_user_dissatisfaction"] = bool(
            pragmatics.get("repair_user_dissatisfaction", False)
        ) == bool(expected.get("repair_user_dissatisfaction", False))
    if "retrieval_action_allowed" in expected:
        checks["retrieval_action_allowed"] = str(decision.get("retrieval_action", "")) in {
            str(item) for item in list(expected.get("retrieval_action_allowed", []) or [])
        }
    if "rag_included_min" in expected:
        checks["rag_included_min"] = int(decision.get("rag_included_count", 0) or 0) >= int(
            expected.get("rag_included_min", 0) or 0
        )
    if "rag_included_max" in expected:
        checks["rag_included_max"] = int(decision.get("rag_included_count", 0) or 0) <= int(
            expected.get("rag_included_max", 0) or 0
        )

    planner = build_response_planner_decision(
        user_message=str(case.get("user_message", "") or ""),
        state_snapshot=SimpleNamespace(safety_flag=False, nervous_state="window"),
        thread_state=SimpleNamespace(response_mode="reflect", safety_active=False, ok_position="I+W+"),
        diagnostic_card=None,
        active_line={
            "user_intent": "understand_mechanism",
            "continuity_mode": "continue_existing_line",
            "should_ask_question": False,
            "should_offer_practice": False,
            "revoicing_allowed": False,
        },
        knowledge_answer_guard=dict(case.get("knowledge_answer_guard", {})),
        philosophy_kernel={},
        context_package=None,
        dialogue_policy={
            "profile": "mvp_free_dialogue",
            "active_concept": str(dict(case.get("dialogue_policy", {})).get("active_concept", "") or ""),
            "dialogue_pragmatics": pragmatics,
        },
    ).to_dict()
    checks["planner_has_shape"] = bool(str(planner.get("answer_shape", "")).strip())

    if str(case.get("case_id", "")) == "HF1_DA_KONECHNO_NO_REGULATE_STUB":
        writer = WriterAgent(client=object(), model="gpt-5-mini")
        contract = WriterContract(
            user_message=str(case.get("user_message", "") or ""),
            thread_state=ThreadState(
                thread_id="hf1-direct",
                user_id="hf1",
                core_direction="",
                phase="clarify",
                response_mode="reflect",
            ),
            memory_bundle=MemoryBundle(),
            response_planner=planner,
            dialogue_policy={"profile": "mvp_free_dialogue"},
            dialogue_pragmatics=pragmatics,
            retrieval_decision=decision,
        )
        enforced = writer._enforce_answer_compliance(
            "Сфокусируюсь на разборе, без практик по умолчанию.",
            contract,
        )
        lowered = enforced.lower()
        checks["no_regulate_stub"] = "сфокусируюсь на разборе" not in lowered
        checks["followup_fulfilled"] = (
            "фраз" in lowered
            or "исправляюсь" in lowered
            or "продолжаю по твоему запросу" in lowered
        )

    failures = [name for name, ok in checks.items() if not ok]
    return {
        "case_id": str(case.get("case_id", "")),
        "group": str(case.get("group", "")),
        "pragmatics": pragmatics,
        "retrieval_decision": {
            key: value
            for key, value in decision.items()
            if key != "rag_included_for_writer"
        },
        "planner": {
            "next_move": planner.get("next_move"),
            "answer_shape": planner.get("answer_shape"),
            "response_depth": planner.get("response_depth"),
            "question_policy": planner.get("question_policy"),
            "practice_policy": planner.get("practice_policy"),
        },
        "evaluation": {
            "passed": len(failures) == 0,
            "checks": checks,
            "failure_reasons": failures,
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
    results = [_evaluate_direct_case(case) for case in cases]
    total = len(results)
    passed = sum(1 for item in results if bool(item.get("evaluation", {}).get("passed", False)))
    checks = {
        "cases_passed": passed == total,
        "required_cases_present": REQUIRED_CASE_IDS.issubset(
            {str(item.get("case_id", "")) for item in results}
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
        "case_results": results,
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


def _run_live(*, base_url: str, api_key: str, admin_runtime_url: str) -> dict[str, Any]:
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

    session_id = f"prd04710hf1-live-{uuid.uuid4().hex[:8]}"
    flow = [
        "что такое нейросталкинг?",
        "да, предложи",
        "ты снова не ответил на свой же вопрос, да предложи",
    ]
    api_root = _derive_api_root(base_url)
    traces: list[dict[str, Any]] = []
    answers: list[str] = []
    statuses: list[int] = []

    for query in flow:
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
        statuses.append(status_code)
        if status_code != 200:
            answers.append("")
            traces.append({})
            continue
        answers.append(str(payload.get("answer", "") or ""))
        trace_payload = dict(payload.get("trace", {})) if isinstance(payload.get("trace"), dict) else {}
        traces.append(trace_payload)

    trace_status, trace_full = _http_json_request(
        method="GET",
        url=f"{api_root}/api/debug/session/{session_id}/multiagent-trace",
        headers=headers,
        timeout=60.0,
    )

    last_answer = answers[-1] if answers else ""
    last_lower = last_answer.lower()
    checks = {
        "all_status_200": all(code == 200 for code in statuses),
        "no_422": not any(code == 422 for code in statuses),
        "last_answer_not_stub": "сфокусируюсь на разборе" not in last_lower,
        "trace_endpoint_ok": trace_status == 200 and isinstance(trace_full, dict),
        "trace_has_dialogue_pragmatics": isinstance(
            dict(trace_full).get("dialogue_pragmatics"),
            dict,
        ),
        "trace_has_retrieval_decision": isinstance(
            dict(trace_full).get("retrieval_decision"),
            dict,
        ),
    }
    return {
        "mode": "live",
        "status": "passed" if all(checks.values()) else "failed",
        "timestamp": _now_iso(),
        "session_id": session_id,
        "checks": checks,
        "statuses": statuses,
        "queries": flow,
        "answers_preview": [item[:500] for item in answers],
        "trace_preview": {
            "dialogue_pragmatics": dict(trace_full).get("dialogue_pragmatics", {}),
            "retrieval_decision": dict(trace_full).get("retrieval_decision", {}),
        },
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
        "# PRD-047.10-HF1 Live Eval",
        "",
        f"- status: `{payload.get('status')}`",
        f"- timestamp_utc: `{payload.get('timestamp')}`",
        f"- session_id: `{payload.get('session_id', '')}`",
        "",
        "## Checks",
    ]
    for key, value in dict(payload.get("checks", {})).items():
        lines.append(f"- {key}: `{bool(value)}`")
    lines.append("")
    lines.append("## Answers Preview")
    for idx, answer in enumerate(list(payload.get("answers_preview", []) or []), start=1):
        lines.append(f"### Turn {idx}")
        lines.append("```text")
        lines.append(str(answer))
        lines.append("```")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.10-HF1 dialogue pragmatics eval")
    parser.add_argument("--mode", choices=["dry", "direct", "live"], default="dry")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--base-url", default=os.getenv("PRD04710HF1_BASE_URL", "http://127.0.0.1:8001/api/v1"))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD04710HF1_ADMIN_RUNTIME_URL", "http://127.0.0.1:8001/api/admin/runtime/effective"),
    )
    parser.add_argument("--api-key", default=os.getenv("PRD04710HF1_API_KEY", "dev-key-001"))
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
        output_json = _resolve_path(args.output_json) if args.output_json else log_dir / "dialogue_pragmatics_dry.json"
    elif args.mode == "direct":
        payload = _run_direct(cases)
        output_json = _resolve_path(args.output_json) if args.output_json else log_dir / "dialogue_pragmatics_direct.json"
    else:
        payload = _run_live(
            base_url=str(args.base_url),
            api_key=str(args.api_key),
            admin_runtime_url=str(args.admin_runtime_url),
        )
        output_json = _resolve_path(args.output_json) if args.output_json else log_dir / "dialogue_pragmatics_live.json"

    payload["prd"] = "PRD-047.10-HF1"
    payload["dataset"] = str(dataset_path)
    _write_json(output_json, payload)

    if args.mode == "live":
        output_md = _resolve_path(args.output_md) if args.output_md else log_dir / "dialogue_pragmatics_live.md"
        _write_md(output_md, _build_live_markdown(payload))

    print(json.dumps({"status": payload.get("status"), "output": str(output_json)}, ensure_ascii=False))
    return 0 if payload.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
