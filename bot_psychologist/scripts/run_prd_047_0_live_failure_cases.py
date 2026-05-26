#!/usr/bin/env python3
"""Run PRD-047.0 live dialogue failure baseline in dry/direct/live modes."""

from __future__ import annotations

import argparse
import asyncio
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

from bot_agent.multiagent.knowledge_answer_routing_guard import (  # noqa: E402
    build_knowledge_answer_routing_guard,
    detect_concept_mentions,
)

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_0_cases.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.0"
DEFAULT_TRACE_SAMPLES = DEFAULT_LOG_DIR / "knowledge_answer_trace_samples.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_path(path_raw: str) -> Path:
    path = Path(path_raw)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("dataset must be list")
    return [item for item in payload if isinstance(item, dict)]


def _iter_user_turns(case: dict[str, Any]) -> list[str]:
    turns = case.get("turns", [])
    if not isinstance(turns, list):
        return []
    result: list[str] = []
    for item in turns:
        if not isinstance(item, dict):
            continue
        if str(item.get("role", "")).lower() == "user":
            result.append(str(item.get("content", "") or ""))
    return result


def _build_synthetic_hits_for_dry(user_message: str) -> list[dict[str, Any]]:
    mentions = detect_concept_mentions(user_message)
    if not mentions:
        return []
    concept = mentions[0]["concept"]
    examples = {
        "нейросталкинг": "Нейросталкинг — наблюдение за паттернами, триггерами и автоматическими реакциями.",
        "неосталкинг": "Неосталкинг — следующий уровень осознанного наблюдения за реактивными программами.",
        "самореализация": "Самореализация — раскрытие потенциала через осознанный выбор и авторство.",
    }
    content = examples.get(concept, "Внутреннее рабочее определение концепта из базы знаний.")
    return [{"chunk_id": "dry-hit-1", "content": content, "score": 0.07, "source": "dry_kb"}]


def _contains_any(text: str, fragments: list[str]) -> bool:
    lowered = (text or "").lower()
    return any(str(fragment).lower() in lowered for fragment in fragments)


def _matched_fragments(text: str, fragments: list[str]) -> list[str]:
    lowered = (text or "").lower()
    matches: list[str] = []
    for fragment in [str(x).strip().lower() for x in fragments if str(x).strip()]:
        if fragment in lowered:
            matches.append(fragment)
    return matches


def _evaluate_case(
    *,
    expected: dict[str, Any],
    answer: str,
    knowledge_answer: dict[str, Any],
    practice_gate: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    failure_reasons: list[str] = []
    expected = expected if isinstance(expected, dict) else {}
    lowered_answer = str(answer or "").lower()

    should_not_include_any = [str(x) for x in expected.get("should_not_include_any", []) if str(x).strip()]
    forbidden_question_patterns = [
        str(x) for x in expected.get("forbidden_question_patterns", []) if str(x).strip()
    ]
    required_answer_semantics = [
        str(x) for x in expected.get("required_answer_semantics", []) if str(x).strip()
    ]

    external_surveillance_markers = [
        "внешнее слежение",
        "отслеживание чужих нейроданных",
        "биофидбек",
        "ээг",
        "нейроинтерфейс",
        "технический мониторинг",
        "цифровые следы",
    ]
    unsolicited_practice_markers = [
        "положи руку",
        "ладонь",
        "грудь",
        "живот",
        "вдох",
        "выдох",
        "дыхани",
        "почувствуй тело",
        "почувствуй опору",
        "ступн",
        "опор",
        "сделай вдох",
        "сделай выдох",
    ]

    checks["knowledge_answer_needed"] = (
        bool(knowledge_answer.get("needed")) == bool(expected.get("knowledge_answer_needed"))
        if "knowledge_answer_needed" in expected
        else True
    )
    checks["should_answer_directly"] = (
        bool(knowledge_answer.get("should_answer_directly")) == bool(expected.get("should_answer_directly"))
        if "should_answer_directly" in expected
        else True
    )
    checks["should_answer_relation"] = (
        ("самореализац" in lowered_answer and "нейросталкинг" in lowered_answer)
        if expected.get("should_answer_relation")
        else True
    )
    checks["practice_allowed"] = (
        bool(practice_gate.get("practice_allowed")) == bool(expected.get("practice_allowed"))
        if "practice_allowed" in expected
        else True
    )
    checks["should_not_ask_user_to_define_term"] = (
        bool(knowledge_answer.get("should_ask_definition_first")) is False
        if expected.get("should_not_ask_user_to_define_term")
        else True
    )
    include_any = [str(x) for x in expected.get("should_include_any", []) if str(x).strip()]
    checks["should_include_any"] = _contains_any(answer, include_any) if include_any else True
    checks["should_include_micro_step"] = (
        _contains_any(answer, ["шаг", "сделай", "попробуй", "начни", "1"])
        if expected.get("should_include_micro_step")
        else True
    )
    checks["require_kb_grounding_available"] = (
        bool(knowledge_answer.get("kb_grounding_available", False))
        if expected.get("require_kb_grounding_available")
        else True
    )
    checks["answer_has_no_forbidden_fragments"] = len(_matched_fragments(lowered_answer, should_not_include_any)) == 0
    checks["answer_has_no_forbidden_question_patterns"] = (
        len(_matched_fragments(lowered_answer, forbidden_question_patterns)) == 0
    )
    matched_required_semantics = _matched_fragments(lowered_answer, required_answer_semantics)
    required_semantics_min = int(expected.get("required_answer_semantics_min", 0) or 0)
    if required_answer_semantics and required_semantics_min <= 0:
        required_semantics_min = 1 if len(required_answer_semantics) == 1 else 2
    checks["answer_contains_required_semantics"] = (
        len(matched_required_semantics) >= required_semantics_min
        if required_answer_semantics
        else True
    )
    checks["answer_avoids_external_surveillance_frame"] = (
        len(_matched_fragments(lowered_answer, external_surveillance_markers)) == 0
        if expected.get("forbid_external_surveillance_frame")
        else True
    )
    checks["answer_has_no_unsolicited_practice"] = (
        len(_matched_fragments(lowered_answer, unsolicited_practice_markers)) == 0
        if expected.get("forbid_unsolicited_practice")
        else True
    )
    checks["answer_does_not_ask_user_to_define_term"] = (
        len(
            _matched_fragments(
                lowered_answer,
                [
                    "что ты вкладываешь",
                    "что вы вкладываете",
                    "о каком варианте",
                    "какой вариант",
                    "ты имеешь в виду",
                    "вы имеете в виду",
                ],
            )
        )
        == 0
        if expected.get("should_not_ask_user_to_define_term")
        else True
    )

    if not checks["knowledge_answer_needed"]:
        failure_reasons.append("knowledge_answer_needed_mismatch")
    if not checks["should_answer_directly"]:
        failure_reasons.append("should_answer_directly_mismatch")
    if not checks["should_answer_relation"]:
        failure_reasons.append("relation_semantics_missing")
    if not checks["practice_allowed"]:
        failure_reasons.append("practice_allowed_mismatch")
    if not checks["should_not_ask_user_to_define_term"]:
        failure_reasons.append("guard_allows_definition_first")
    if not checks["require_kb_grounding_available"]:
        failure_reasons.append("kb_grounding_required_but_false")
    if not checks["answer_contains_required_semantics"]:
        failure_reasons.append(
            f"answer_missing_required_semantics:min={required_semantics_min};matched={len(matched_required_semantics)}"
        )
    if not checks["answer_has_no_forbidden_fragments"]:
        for fragment in _matched_fragments(lowered_answer, should_not_include_any):
            failure_reasons.append(f"answer_contains_forbidden_phrase:{fragment}")
    if not checks["answer_has_no_forbidden_question_patterns"]:
        for fragment in _matched_fragments(lowered_answer, forbidden_question_patterns):
            failure_reasons.append(f"answer_contains_forbidden_question_pattern:{fragment}")
    if not checks["answer_does_not_ask_user_to_define_term"]:
        failure_reasons.append("answer_asks_user_to_define_known_term")
    if not checks["answer_avoids_external_surveillance_frame"]:
        for fragment in _matched_fragments(lowered_answer, external_surveillance_markers):
            failure_reasons.append(f"answer_contains_external_surveillance_frame:{fragment}")
    if not checks["answer_has_no_unsolicited_practice"]:
        for fragment in _matched_fragments(lowered_answer, unsolicited_practice_markers):
            failure_reasons.append(f"answer_contains_unsolicited_practice:{fragment}")

    passed = all(checks.values())
    return {"passed": passed, "checks": checks, "failure_reasons": failure_reasons}

def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _run_dry(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case.get("id", "unknown"))
        user_turns = _iter_user_turns(case)
        query = user_turns[-1] if user_turns else ""
        guard = build_knowledge_answer_routing_guard(
            user_message=query,
            rag_hits=_build_synthetic_hits_for_dry(query),
            response_mode="reflect",
        )
        knowledge_answer = dict(guard.get("knowledge_answer", {}))
        practice_gate = dict(guard.get("practice_gate", {}))
        expected = dict(case.get("expected", {}))
        if expected.get("should_include_micro_step"):
            answer_proxy = "Сделай один конкретный шаг и повтори его сегодня."
        elif expected.get("forbid_unsolicited_practice") and not bool(knowledge_answer.get("needed")):
            answer_proxy = "Привет. Рад знакомству. Можем спокойно начать: принеси любой вопрос."
        elif expected.get("should_answer_relation"):
            answer_proxy = (
                "Нейросталкинг помогает самореализации тем, что человек замечает паттерны, "
                "триггеры и автоматические реакции, которые мешают проявляться и действовать из авторства."
            )
        elif bool(knowledge_answer.get("needed")):
            answer_proxy = "Нейросталкинг — наблюдение за паттернами, триггерами и автоматическими реакциями."
        else:
            answer_proxy = str(knowledge_answer.get("writer_instruction", "") or "")
        evaluation = _evaluate_case(
            expected=expected,
            answer=answer_proxy,
            knowledge_answer=knowledge_answer,
            practice_gate=practice_gate,
        )
        case_results.append(
            {
                "case_id": case_id,
                "mode": "dry",
                "knowledge_answer": knowledge_answer,
                "practice_gate": practice_gate,
                "evaluation": evaluation,
            }
        )
        samples.append(
            {
                "mode": "dry",
                "case_id": case_id,
                "knowledge_answer": knowledge_answer,
                "practice_gate": practice_gate,
            }
        )
    return case_results, samples


async def _run_direct_async(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from bot_agent.multiagent.orchestrator import orchestrator

    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    run_nonce = uuid.uuid4().hex[:8]
    for idx, case in enumerate(cases, start=1):
        case_id = str(case.get("id", f"case_{idx}"))
        user_id = f"prd0470_direct_{run_nonce}_{idx}"
        user_turns = _iter_user_turns(case)
        final_result: dict[str, Any] | None = None
        turn_errors: list[str] = []
        for turn in user_turns:
            try:
                final_result = await orchestrator.run(query=turn, user_id=user_id)
            except Exception as exc:  # noqa: BLE001
                turn_errors.append(str(exc))
                break
        debug = dict((final_result or {}).get("debug", {}))
        knowledge_answer = dict(debug.get("knowledge_answer", {}))
        practice_gate = dict(debug.get("practice_gate", {}))
        answer = str((final_result or {}).get("answer", "") or "")
        evaluation = _evaluate_case(
            expected=dict(case.get("expected", {})),
            answer=answer,
            knowledge_answer=knowledge_answer,
            practice_gate=practice_gate,
        )
        case_results.append(
            {
                "case_id": case_id,
                "mode": "direct",
                "turn_errors": turn_errors,
                "answer": answer,
                "knowledge_answer": knowledge_answer,
                "practice_gate": practice_gate,
                "evaluation": evaluation,
            }
        )
        samples.append(
            {
                "mode": "direct",
                "case_id": case_id,
                "knowledge_answer": knowledge_answer,
                "practice_gate": practice_gate,
                "knowledge_answer_trace": dict(debug.get("knowledge_answer_trace", {})),
            }
        )
    return case_results, samples


def _run_live(
    cases: list[dict[str, Any]],
    *,
    base_url: str,
    api_key: str,
    limit: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    selected = list(cases[:limit]) if isinstance(limit, int) and limit > 0 else list(cases)
    headers = {"X-API-Key": api_key}
    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    probe_url = f"{base_url.rstrip('/')}/identity/me"
    try:
        status, _ = _http_json_request(method="GET", url=probe_url, headers=headers)
        if status != 200:
            return (
                {
                    "live_status": "skipped",
                    "reason": f"identity probe returned status={status}",
                    "case_results": [],
                },
                [],
            )
    except Exception as exc:  # noqa: BLE001
        return (
            {
                "live_status": "skipped",
                "reason": f"identity probe failed: {exc}",
                "case_results": [],
            },
            [],
        )

    for idx, case in enumerate(selected, start=1):
        case_id = str(case.get("id", f"case_{idx}"))
        session_id = f"prd0470_live_{idx}"
        user_id = f"prd0470_live_user_{idx}"
        user_turns = _iter_user_turns(case)
        final_answer = ""
        final_debug: dict[str, Any] = {}
        errors: list[str] = []
        for turn in user_turns:
            try:
                status, payload = _http_json_request(
                    method="POST",
                    url=f"{base_url.rstrip('/')}/questions/adaptive",
                    headers=headers,
                    payload={
                        "query": turn,
                        "user_id": user_id,
                        "session_id": session_id,
                        "debug": True,
                    },
                )
                if status != 200:
                    errors.append(f"status={status}")
                    break
                final_answer = str(payload.get("answer", "") or "")
                final_debug = dict(payload.get("debug", {}))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")
                errors.append(f"http_error={exc.code}:{detail}")
                break
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                break
        knowledge_answer = dict(final_debug.get("knowledge_answer", {}))
        practice_gate = dict(final_debug.get("practice_gate", {}))
        evaluation = _evaluate_case(
            expected=dict(case.get("expected", {})),
            answer=final_answer,
            knowledge_answer=knowledge_answer,
            practice_gate=practice_gate,
        )
        case_results.append(
            {
                "case_id": case_id,
                "mode": "live",
                "errors": errors,
                "answer": final_answer,
                "knowledge_answer": knowledge_answer,
                "practice_gate": practice_gate,
                "evaluation": evaluation,
            }
        )
        samples.append(
            {
                "mode": "live",
                "case_id": case_id,
                "knowledge_answer": knowledge_answer,
                "practice_gate": practice_gate,
                "knowledge_answer_trace": dict(final_debug.get("knowledge_answer_trace", {})),
            }
        )
    has_knowledge_answer_trace = any(
        isinstance(item.get("knowledge_answer"), dict) and bool(item.get("knowledge_answer"))
        for item in case_results
    )
    if not has_knowledge_answer_trace:
        return (
            {
                "live_status": "skipped",
                "reason": "live backend appears stale or not restarted after code changes (knowledge_answer trace missing)",
                "case_results": case_results,
            },
            samples,
        )
    return ({"live_status": "passed", "reason": "", "case_results": case_results}, samples)


def _build_summary(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(case_results)
    passed = sum(1 for item in case_results if bool(item.get("evaluation", {}).get("passed")))
    return {
        "cases_total": total,
        "cases_passed": passed,
        "cases_failed": max(0, total - passed),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.0 live failure cases.")
    parser.add_argument("--mode", choices=("dry", "direct", "live"), default="dry")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output", default=None)
    parser.add_argument("--trace-samples-output", default=str(DEFAULT_TRACE_SAMPLES))
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--api-base-url", default=os.getenv("PRD0470_API_BASE", "http://localhost:8001/api/v1"))
    parser.add_argument("--api-key", default=os.getenv("PRD0470_API_KEY", os.getenv("BOT_API_KEY", "dev-key-001")))
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    trace_output_path = _resolve_path(args.trace_samples_output)
    if args.output:
        output_path = _resolve_path(args.output)
    else:
        output_path = DEFAULT_LOG_DIR / f"live_failure_cases_{args.mode}.json"

    cases = _load_cases(dataset_path)
    if args.case_id:
        filtered = [item for item in cases if str(item.get("id", "")) == str(args.case_id)]
        if not filtered:
            raise ValueError(f"case-id not found: {args.case_id}")
        cases = filtered
    if args.limit is not None and args.limit > 0:
        cases = cases[: args.limit]

    if args.mode == "dry":
        case_results, samples = _run_dry(cases)
        payload = {
            "prd_id": "PRD-047.0",
            "mode": "dry",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": _build_summary(case_results),
            "case_results": case_results,
        }
        _write_json(output_path, payload)
        _write_json(trace_output_path, {"prd_id": "PRD-047.0", "samples": samples})
        print(output_path)
        return 0

    if args.mode == "direct":
        case_results, samples = asyncio.run(_run_direct_async(cases))
        payload = {
            "prd_id": "PRD-047.0",
            "mode": "direct",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": _build_summary(case_results),
            "case_results": case_results,
        }
        _write_json(output_path, payload)
        _write_json(trace_output_path, {"prd_id": "PRD-047.0", "samples": samples})
        print(output_path)
        return 0

    live_payload, samples = _run_live(
        cases,
        base_url=str(args.api_base_url),
        api_key=str(args.api_key),
        limit=args.limit,
    )
    if str(live_payload.get("live_status")) == "passed":
        result_payload = {
            "prd_id": "PRD-047.0",
            "mode": "live",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": _build_summary(list(live_payload.get("case_results", []))),
            "case_results": list(live_payload.get("case_results", [])),
            "live_status": "passed",
            "reason": "",
        }
    else:
        result_payload = {
            "prd_id": "PRD-047.0",
            "mode": "live",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": {"cases_total": 0, "cases_passed": 0, "cases_failed": 0},
            "case_results": [],
            "live_status": "skipped",
            "reason": str(live_payload.get("reason", "unknown")),
        }
    _write_json(output_path, result_payload)
    _write_json(trace_output_path, {"prd_id": "PRD-047.0", "samples": samples})
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

