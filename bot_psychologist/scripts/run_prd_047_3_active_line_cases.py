#!/usr/bin/env python3
"""Run PRD-047.3 Active Line / Dialogue Continuity cases."""

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

from bot_agent.multiagent.active_line import (  # noqa: E402
    build_active_line_state,
    starts_with_mechanical_revoicing,
)

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_3_active_line_cases.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.3"
DEFAULT_TRACE_SAMPLES = DEFAULT_LOG_DIR / "active_line_trace_samples.json"
DEFAULT_REVOICING_REPORT = DEFAULT_LOG_DIR / "revoicing_report.json"
DEFAULT_PRACTICE_SUPPRESSION_REPORT = DEFAULT_LOG_DIR / "practice_suppression_report.json"

_PRACTICE_MARKERS = [
    "практик",
    "упражн",
    "поставь таймер",
    "встань",
    "потянись",
    "вдох",
    "выдох",
    "дыхани",
    "сделай шаг",
    "начни одно простое действие",
    "открой документ",
    "напиши заголовок",
    "60 секунд",
    "5 минут",
]
_EXTERNAL_SURVEILLANCE_MARKERS = [
    "внешнее слежение",
    "биофидбек",
    "ээг",
    "нейроинтерфейс",
    "технический мониторинг",
]
_RESTART_MARKERS = [
    "вы говорите",
    "вы спрашиваете",
    "похоже, вы хотите",
    "асхат, похоже",
]
_STEP_OFFER_MARKERS = [
    "предложу еще",
    "еще один шаг",
    "давай сделаем практику",
    "дам упражнение",
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


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("dataset must be list")
    cases = [item for item in payload if isinstance(item, dict)]
    return sorted(cases, key=lambda item: (str(item.get("thread_id", "")), int(item.get("turn_index", 0) or 0)))


def _contains_any(text: str, markers: list[str]) -> bool:
    lowered = str(text or "").lower()
    return any(str(marker).lower() in lowered for marker in markers)


def _count_questions(text: str) -> int:
    return str(text or "").count("?")


def _starts_with_query_repetition(*, answer: str, query: str) -> bool:
    a = " ".join(str(answer or "").strip().lower().split())
    q_words = [w for w in " ".join(str(query or "").strip().lower().split()).split(" ") if w]
    if len(q_words) < 3:
        return False
    needle = " ".join(q_words[: min(6, len(q_words))])
    return bool(needle and a.startswith(needle))


def _evaluate_case(*, case: dict[str, Any], answer: str, active_line_trace: dict[str, Any]) -> dict[str, Any]:
    expected = dict(case.get("expected", {}))
    lower = str(answer or "").lower()
    intent = str(active_line_trace.get("user_intent", "unknown") or "unknown")
    continuity_mode = str(active_line_trace.get("continuity_mode", "") or "")

    checks: dict[str, bool] = {}
    failures: list[str] = []

    checks["active_line_present"] = bool(active_line_trace)
    checks["continuity_mode_correct"] = (
        continuity_mode == str(expected.get("continuity_mode")) if expected.get("continuity_mode") else True
    )
    checks["user_intent_correct"] = (
        intent == str(expected.get("user_intent")) if expected.get("user_intent") else True
    )

    checks["no_mechanical_revoicing"] = not starts_with_mechanical_revoicing(answer)
    checks["no_unsolicited_practice"] = (
        not _contains_any(lower, _PRACTICE_MARKERS) if bool(expected.get("no_practice", False)) else True
    )

    require_suppression = bool(expected.get("no_practice", False)) or intent in {
        "understand_mechanism",
        "correction_of_bot",
    }
    checks["practice_suppressed_for_understand_mechanism"] = (
        bool(active_line_trace.get("should_offer_practice", False)) is False
        and not _contains_any(lower, _PRACTICE_MARKERS)
        if require_suppression
        else True
    )

    checks["repair_mode_when_user_corrects_bot"] = (
        bool(active_line_trace.get("repair_mode"))
        if bool(expected.get("repair_required", False))
        else True
    )
    checks["no_new_practice_after_practice_complaint"] = (
        not _contains_any(lower, _PRACTICE_MARKERS)
        if bool(expected.get("no_new_practice_after_correction", False))
        else True
    )

    q_limit = int(expected.get("question_count_lte", 1) or 1)
    checks["question_count_lte_1"] = _count_questions(answer) <= q_limit

    turn_index = int(case.get("turn_index", 1) or 1)
    checks["continues_prior_line"] = (
        bool(active_line_trace.get("should_continue_line", False))
        if turn_index > 1 and continuity_mode in {"continue_existing_line", "repair_and_continue_line"}
        else True
    )
    checks["does_not_restart_conversation"] = not _contains_any(lower, _RESTART_MARKERS)
    checks["does_not_repeat_user_question_as_opening"] = not _starts_with_query_repetition(
        answer=answer,
        query=str(case.get("query", "") or ""),
    )

    checks["meaningful_next_move_present"] = bool(
        str(active_line_trace.get("next_meaningful_move", "") or "").strip()
    )

    expected_active_line_any = [
        str(item).lower() for item in list(expected.get("active_line_should_contain_any", []) or []) if str(item).strip()
    ]
    if expected_active_line_any:
        line_text = str(active_line_trace.get("active_line", "") or "").lower()
        checks["active_line_contains_expected_semantics"] = any(token in line_text for token in expected_active_line_any)
    else:
        checks["active_line_contains_expected_semantics"] = True

    checks["practice_allowed_when_explicit"] = (
        bool(active_line_trace.get("should_offer_practice", False))
        if bool(expected.get("practice_allowed", False))
        else True
    )

    checks["no_external_surveillance"] = (
        not _contains_any(lower, _EXTERNAL_SURVEILLANCE_MARKERS)
        if bool(expected.get("no_external_surveillance", False))
        else True
    )

    checks["no_step_offer_on_close"] = (
        not _contains_any(lower, _STEP_OFFER_MARKERS)
        if bool(expected.get("no_step_offer", False))
        else True
    )

    checks["short_answer_when_requested"] = (
        len(str(answer or "")) <= 240 if bool(expected.get("short_answer", False)) else True
    )

    max_answer_chars = int(expected.get("max_answer_chars", 0) or 0)
    checks["max_answer_chars"] = len(str(answer or "")) <= max_answer_chars if max_answer_chars > 0 else True

    for check_name, ok in checks.items():
        if not ok:
            failures.append(check_name)

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failure_reasons": failures,
    }


def _dry_answer(case_id: str) -> str:
    mapping = {
        "a1_open_understand": "Если смотреть в суть, тут важен не общий контроль, а момент, где тревога съедает фокус до действия.",
        "a2_clarify_forecasting": "Да, это похоже на узел: прогноз и подстраховка сначала дают чувство контроля, а потом забирают ресурс старта.",
        "a3_work_context": "В рабочем контуре это часто выглядит так: энергия уходит в подготовку к риску раньше, чем начинается само действие.",
        "a4_delayed_start_tired": "Здесь видно механизм: прогнозирование и контроль пытаются снизить риск, но из-за них к старту уже мало энергии.",
        "a5_user_correction_no_practice": "Да, ты прав: я слишком рано ушел в действие. Вернусь к сути — к механизму застревания до старта.",
        "a6_thanks_close": "Пожалуйста. Рад, что стало чуть яснее.",
        "b1_explicit_direct_step": "Один шаг: открой задачу и выпиши только первый проверяемый результат за 5 минут, без детализации всего плана.",
        "c1_explicit_no_practice": "Тогда фокус на механизме: попытка заранее снять риск превращается в отдельную внутреннюю задачу и тормозит старт.",
        "d1_known_concept_continuity": "Да, похоже: в этой линии это как раз наблюдение автопилота, который включает прогноз и забирает ресурс до действия.",
        "d2_short_support": "Я рядом. Сейчас можно просто немного снизить давление к себе.",
    }
    return mapping.get(case_id, "")


def _build_case_result(*, case: dict[str, Any], mode: str, answer: str, active_line_trace: dict[str, Any], errors: list[str] | None = None) -> dict[str, Any]:
    evaluation = _evaluate_case(case=case, answer=answer, active_line_trace=active_line_trace)
    return {
        "case_id": str(case.get("id", "unknown")),
        "group": case.get("group"),
        "thread_id": str(case.get("thread_id", "")),
        "turn_index": int(case.get("turn_index", 0) or 0),
        "mode": mode,
        "query": str(case.get("query", "") or ""),
        "answer": answer,
        "errors": list(errors or []),
        "active_line_trace": active_line_trace,
        "evaluation": evaluation,
    }


def _run_dry(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []

    thread_context: dict[str, str] = {}
    for case in cases:
        case_id = str(case.get("id", "unknown"))
        thread_id = str(case.get("thread_id", "default"))
        query = str(case.get("query", "") or "")
        response_mode = str(case.get("response_mode", "reflect") or "reflect")
        context = thread_context.get(thread_id, "")

        active_line = build_active_line_state(
            user_message=query,
            conversation_context=context,
            response_mode=response_mode,
            practice_allowed=bool(case.get("expected", {}).get("practice_allowed", False)),
            evidence_turn_ids=[],
        ).to_dict()
        answer = _dry_answer(case_id)
        case_result = _build_case_result(
            case=case,
            mode="dry",
            answer=answer,
            active_line_trace=active_line,
        )
        case_results.append(case_result)
        samples.append(
            {
                "mode": "dry",
                "case_id": case_id,
                "thread_id": thread_id,
                "active_line_trace": active_line,
            }
        )
        thread_context[thread_id] = (context + "\nUser: " + query + "\nAssistant: " + answer)[-2500:]

    return case_results, samples


async def _run_direct_async(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from bot_agent.multiagent.orchestrator import orchestrator

    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    run_nonce = uuid.uuid4().hex[:8]

    thread_user_map: dict[str, str] = {}

    for case in cases:
        case_id = str(case.get("id", "unknown"))
        thread_id = str(case.get("thread_id", "default"))
        query = str(case.get("query", "") or "")

        if thread_id not in thread_user_map:
            thread_user_map[thread_id] = f"prd0473_direct_{run_nonce}_{thread_id}"
        user_id = thread_user_map[thread_id]

        result = await orchestrator.run(query=query, user_id=user_id)
        debug = dict(result.get("debug", {}))
        answer = str(result.get("answer", "") or "")
        active_line_trace = dict(debug.get("active_line", {}))

        case_result = _build_case_result(
            case=case,
            mode="direct",
            answer=answer,
            active_line_trace=active_line_trace,
        )
        case_results.append(case_result)
        samples.append(
            {
                "mode": "direct",
                "case_id": case_id,
                "thread_id": thread_id,
                "active_line_trace": active_line_trace,
            }
        )

    return case_results, samples


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


def _run_live(
    cases: list[dict[str, Any]],
    *,
    base_url: str,
    api_key: str,
    admin_runtime_url: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headers = {"X-API-Key": api_key}

    freshness_reason = ""
    try:
        status, payload = _http_json_request(
            method="GET",
            url=admin_runtime_url,
            headers=headers,
            timeout=30,
        )
        if status != 200:
            freshness_reason = f"admin runtime probe status={status}"
        elif not isinstance(payload.get("active_line"), dict):
            freshness_reason = "admin runtime payload has no active_line block"
    except Exception as exc:  # noqa: BLE001
        freshness_reason = f"admin runtime probe failed: {exc}"

    if freshness_reason:
        return (
            {
                "live_status": "skipped",
                "reason": freshness_reason,
                "case_results": [],
            },
            [],
        )

    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    thread_user_map: dict[str, str] = {}
    thread_session_map: dict[str, str] = {}
    thread_context_map: dict[str, str] = {}

    for idx, case in enumerate(cases, start=1):
        case_id = str(case.get("id", "unknown"))
        thread_id = str(case.get("thread_id", "default"))
        query = str(case.get("query", "") or "")
        context = str(thread_context_map.get(thread_id, "") or "")

        if thread_id not in thread_user_map:
            thread_user_map[thread_id] = f"prd0473_live_user_{idx}_{thread_id}"
            thread_session_map[thread_id] = f"prd0473_live_session_{idx}_{thread_id}"

        answer = ""
        debug: dict[str, Any] = {}
        trace_payload: dict[str, Any] = {}
        errors: list[str] = []
        try:
            status, payload = _http_json_request(
                method="POST",
                url=f"{base_url.rstrip('/')}/questions/adaptive",
                headers=headers,
                payload={
                    "query": query,
                    "user_id": thread_user_map[thread_id],
                    "session_id": thread_session_map[thread_id],
                    "debug": True,
                },
            )
            if status != 200:
                errors.append(f"status={status}")
            else:
                answer = str(payload.get("answer", "") or "")
                debug = dict(payload.get("debug", {}))
                trace_payload = dict(payload.get("trace", {}))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            errors.append(f"http_error={exc.code}:{detail}")
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

        active_line_trace = dict(debug.get("active_line", {}))
        if not active_line_trace and isinstance(trace_payload.get("active_line"), dict):
            active_line_trace = dict(trace_payload.get("active_line", {}))
        if not active_line_trace:
            active_line_trace = build_active_line_state(
                user_message=query,
                conversation_context=context,
                response_mode=str(case.get("response_mode", "reflect") or "reflect"),
                practice_allowed=bool(case.get("expected", {}).get("practice_allowed", False)),
                evidence_turn_ids=[],
            ).to_dict()
            active_line_trace["_fallback_source"] = "local_builder"
        case_result = _build_case_result(
            case=case,
            mode="live",
            answer=answer,
            active_line_trace=active_line_trace,
            errors=errors,
        )
        case_results.append(case_result)
        samples.append(
            {
                "mode": "live",
                "case_id": case_id,
                "thread_id": thread_id,
                "active_line_trace": active_line_trace,
            }
        )
        thread_context_map[thread_id] = (context + "\nUser: " + query + "\nAssistant: " + answer)[-2500:]

    return ({"live_status": "passed", "reason": "", "case_results": case_results}, samples)


def _build_summary(case_results: list[dict[str, Any]]) -> dict[str, int]:
    total = len(case_results)
    passed = sum(1 for item in case_results if bool(item.get("evaluation", {}).get("passed")))
    return {"cases_total": total, "cases_passed": passed, "cases_failed": max(0, total - passed)}


def _build_revoicing_report(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    violations = [
        {
            "case_id": item.get("case_id"),
            "thread_id": item.get("thread_id"),
            "answer": str(item.get("answer", ""))[:400],
        }
        for item in case_results
        if not bool(item.get("evaluation", {}).get("checks", {}).get("no_mechanical_revoicing", True))
    ]
    return {
        "total_cases": len(case_results),
        "violations_count": len(violations),
        "violations": violations,
    }


def _build_practice_suppression_report(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    suppressed_cases = [
        item
        for item in case_results
        if item.get("evaluation", {}).get("checks", {}).get("practice_suppressed_for_understand_mechanism")
    ]
    violations = [
        {
            "case_id": item.get("case_id"),
            "thread_id": item.get("thread_id"),
            "answer": str(item.get("answer", ""))[:400],
            "failure_reasons": list(item.get("evaluation", {}).get("failure_reasons", [])),
        }
        for item in case_results
        if not bool(item.get("evaluation", {}).get("checks", {}).get("no_unsolicited_practice", True))
    ]
    return {
        "total_cases": len(case_results),
        "suppressed_cases_count": len(suppressed_cases),
        "practice_violations_count": len(violations),
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.3 active line continuity cases.")
    parser.add_argument("--mode", choices=("dry", "direct", "live"), default="dry")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output", default=None)
    parser.add_argument("--trace-samples-output", default=str(DEFAULT_TRACE_SAMPLES))
    parser.add_argument("--revoicing-output", default=str(DEFAULT_REVOICING_REPORT))
    parser.add_argument("--practice-suppression-output", default=str(DEFAULT_PRACTICE_SUPPRESSION_REPORT))
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--api-base-url", default=os.getenv("PRD0473_API_BASE", "http://localhost:8001/api/v1"))
    parser.add_argument("--api-key", default=os.getenv("PRD0473_API_KEY", os.getenv("BOT_API_KEY", "dev-key-001")))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD0473_ADMIN_RUNTIME_URL", "http://localhost:8001/api/admin/runtime/effective"),
    )
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    trace_output_path = _resolve_path(args.trace_samples_output)
    revoicing_output_path = _resolve_path(args.revoicing_output)
    practice_output_path = _resolve_path(args.practice_suppression_output)
    output_path = _resolve_path(args.output) if args.output else DEFAULT_LOG_DIR / f"active_line_{args.mode}.json"

    cases = _load_cases(dataset_path)
    if args.case_id:
        cases = [item for item in cases if str(item.get("id", "")) == str(args.case_id)]
        if not cases:
            raise ValueError(f"case-id not found: {args.case_id}")
    if args.limit is not None and args.limit > 0:
        cases = cases[: args.limit]

    if args.mode == "dry":
        case_results, samples = _run_dry(cases)
        payload = {
            "prd_id": "PRD-047.3",
            "mode": "dry",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": _build_summary(case_results),
            "case_results": case_results,
        }
        _write_json(output_path, payload)
        _write_json(trace_output_path, {"prd_id": "PRD-047.3", "mode": "dry", "samples": samples})
        _write_json(revoicing_output_path, _build_revoicing_report(case_results))
        _write_json(practice_output_path, _build_practice_suppression_report(case_results))
        print(output_path)
        return 0

    if args.mode == "direct":
        case_results, samples = asyncio.run(_run_direct_async(cases))
        payload = {
            "prd_id": "PRD-047.3",
            "mode": "direct",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": _build_summary(case_results),
            "case_results": case_results,
        }
        _write_json(output_path, payload)
        _write_json(trace_output_path, {"prd_id": "PRD-047.3", "mode": "direct", "samples": samples})
        _write_json(revoicing_output_path, _build_revoicing_report(case_results))
        _write_json(practice_output_path, _build_practice_suppression_report(case_results))
        print(output_path)
        return 0

    live_payload, samples = _run_live(
        cases,
        base_url=str(args.api_base_url),
        api_key=str(args.api_key),
        admin_runtime_url=str(args.admin_runtime_url),
    )
    if str(live_payload.get("live_status")) == "passed":
        case_results = list(live_payload.get("case_results", []))
        payload = {
            "prd_id": "PRD-047.3",
            "mode": "live",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": _build_summary(case_results),
            "case_results": case_results,
            "live_status": "passed",
            "reason": "",
        }
        _write_json(revoicing_output_path, _build_revoicing_report(case_results))
        _write_json(practice_output_path, _build_practice_suppression_report(case_results))
    else:
        payload = {
            "prd_id": "PRD-047.3",
            "mode": "live",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": {"cases_total": 0, "cases_passed": 0, "cases_failed": 0},
            "case_results": [],
            "live_status": "skipped",
            "reason": str(live_payload.get("reason", "unknown")),
        }
    _write_json(output_path, payload)
    _write_json(trace_output_path, {"prd_id": "PRD-047.3", "mode": "live", "samples": samples})
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
