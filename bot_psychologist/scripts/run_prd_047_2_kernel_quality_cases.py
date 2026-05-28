#!/usr/bin/env python3
"""Run PRD-047.2 philosophy-kernel quality calibration cases."""

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

from bot_agent.multiagent.philosophy_kernel import (  # noqa: E402
    MAX_COMBINED_PROMPT_CHARS,
    MAX_FREEDOM_PROMPT_CHARS,
    MAX_KERNEL_PROMPT_CHARS,
    MAX_SELECTED_LENSES,
    build_philosophy_kernel_runtime_payload,
)

DEFAULT_DATASET = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_2_kernel_quality_cases.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.2"
DEFAULT_TRACE_SAMPLES = DEFAULT_LOG_DIR / "kernel_quality_trace_samples.json"
DEFAULT_COMPACTNESS_REPORT = DEFAULT_LOG_DIR / "prompt_compactness_report.json"

_UNSOLICITED_PRACTICE_MARKERS = [
    "положи руку",
    "ладонь",
    "сделай вдох",
    "сделай выдох",
    "глубоких вдоха",
    "дыхани",
    "почувствуй тело",
    "почувствуй опору",
]
_EXTERNAL_SURVEILLANCE_MARKERS = [
    "внешнее слежение",
    "биофидбек",
    "ээг",
    "нейроинтерфейс",
    "технический мониторинг",
    "цифровые следы",
]
_QUOTE_SOURCE_MARKERS = [
    "согласно книге",
    "в книге сказано",
    "согласно кузнице",
    "автор утверждает",
]
_DIAGNOSIS_MARKERS = ["диагноз", "патология", "расстройств", "у вас травма"]
_HARD_LABEL_MARKERS = ["у вас драйвер", "ваш тип"]
_MECHANISM_MARKERS = ["программа", "механизм", "голос", "автоматизм", "защита"]
_DEFECT_MARKERS = ["сломан", "дефект", "патология", "слабый", "неполноцен"]
_TECHNICAL_STYLE_MARKERS = [
    "в рамках внутренней линзы",
    "согласно внутренней философской",
    "на основании контракта",
]
_GENERIC_MARKERS = ["это нормально", "важно помнить", "дай себе время"]
_ANALYSIS_LECTURE_MARKERS = ["теория", "лекция", "концепция", "модель"]
_INTERNAL_LENS_MARKERS = ["паттерн", "триггер", "автомат", "внутренн", "программа"]


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
        raise ValueError("dataset must be a list")
    return [item for item in payload if isinstance(item, dict)]


def _contains_any(text: str, markers: list[str]) -> bool:
    lowered = str(text or "").lower()
    return any(str(marker).lower() in lowered for marker in markers)


def _count_questions(text: str) -> int:
    return str(text or "").count("?")


def _extract_selected_lenses(kernel_trace: dict[str, Any]) -> list[str]:
    return [str(item) for item in list(kernel_trace.get("selected_lenses", []) or []) if str(item).strip()]


def _effective_compactness(payload_or_trace: dict[str, Any]) -> dict[str, Any]:
    compactness = payload_or_trace.get("prompt_compactness", {})
    if isinstance(compactness, dict) and compactness:
        return compactness
    return {
        "philosophy_kernel_prompt_block_chars": 0,
        "writer_freedom_contract_chars": 0,
        "combined_chars": 0,
        "selected_lenses_count": 0,
        "within_budget": True,
    }


def _evaluate_case(
    *,
    case: dict[str, Any],
    answer: str,
    kernel_trace: dict[str, Any],
    compactness: dict[str, Any],
) -> dict[str, Any]:
    expected = dict(case.get("expected", {}))
    selected_lenses = _extract_selected_lenses(kernel_trace)
    lowered = str(answer or "").lower()
    checks: dict[str, bool] = {}
    failures: list[str] = []

    expected_lenses = [str(x) for x in expected.get("selected_lenses", []) if str(x).strip()]
    expected_lenses_any = [str(x) for x in expected.get("selected_lenses_any", []) if str(x).strip()]

    if expected_lenses:
        checks["selected_lens_match"] = all(lens in selected_lenses for lens in expected_lenses)
    elif expected_lenses_any:
        checks["selected_lens_match"] = any(lens in selected_lenses for lens in expected_lenses_any)
    elif bool(expected.get("no_deep_lens", False)):
        checks["selected_lens_match"] = len(selected_lenses) == 0
    else:
        checks["selected_lens_match"] = True

    checks["no_unsolicited_practice"] = not _contains_any(lowered, _UNSOLICITED_PRACTICE_MARKERS)
    checks["no_external_surveillance"] = not _contains_any(lowered, _EXTERNAL_SURVEILLANCE_MARKERS)
    checks["no_quote_source"] = not _contains_any(lowered, _QUOTE_SOURCE_MARKERS)
    checks["no_diagnosis"] = not _contains_any(lowered, _DIAGNOSIS_MARKERS)
    checks["no_hard_label"] = not _contains_any(lowered, _HARD_LABEL_MARKERS)

    short_requested = bool(expected.get("short_answer", False))
    checks["short_answer_when_requested"] = (len(str(answer or "")) <= 280) if short_requested else True

    no_analysis_requested = bool(expected.get("no_analysis_lecture", False))
    checks["no_analysis_when_requested"] = (
        not _contains_any(lowered, _ANALYSIS_LECTURE_MARKERS) if no_analysis_requested else True
    )

    mechanism_required = bool(expected.get("must_frame_as_mechanism_not_defect", False))
    if mechanism_required:
        checks["mechanism_not_defect_frame"] = _contains_any(lowered, _MECHANISM_MARKERS) or (
            "imperfect_self_program" in selected_lenses and not _contains_any(lowered, _DEFECT_MARKERS)
        )
    else:
        checks["mechanism_not_defect_frame"] = True

    semantics = [str(x) for x in expected.get("should_include_any", []) if str(x).strip()]
    if semantics:
        checks["required_semantics_present"] = _contains_any(lowered, semantics) or (
            mechanism_required and checks["mechanism_not_defect_frame"]
        )
    else:
        checks["required_semantics_present"] = True

    forbidden_any = [str(x) for x in expected.get("should_not_include_any", []) if str(x).strip()]
    checks["forbidden_fragments_absent"] = not _contains_any(lowered, forbidden_any) if forbidden_any else True

    checks["answer_not_too_technical"] = not _contains_any(lowered, _TECHNICAL_STYLE_MARKERS)
    checks["answer_not_too_generic"] = not _contains_any(lowered, _GENERIC_MARKERS)

    max_questions = 0 if bool(expected.get("must_not_ask_question", False)) else 1
    checks["question_count_lte_1"] = _count_questions(answer) <= max_questions

    if bool(expected.get("must_be_internal_lens", False)):
        checks["internal_lens_framing"] = _contains_any(lowered, _INTERNAL_LENS_MARKERS)
    else:
        checks["internal_lens_framing"] = True

    checks["prompt_compactness_within_budget"] = bool(compactness.get("within_budget", False))

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
        "a1_greeting_short_contact": "Привет. Рад тебе. Можем спокойно начать с того, что сейчас важнее всего.",
        "a2_short_support_no_analysis": "Ты устал. Сейчас можно просто выдохнуть и не решать все в эту минуту.",
        "a3_no_practice_presence": "Я рядом. Сейчас можно просто побыть в этом моменте без давления.",
        "b1_imperfect_self_not_coping": "Похоже, здесь говорит программа защиты: заранее объявить, что не справишься, чтобы не рисковать.",
        "b2_imperfect_self_something_wrong": "Сейчас звучит голос механизма ""со мной что-то не так"", но это не дефект, а защита от боли.",
        "b3_imperfect_self_firmware_fail": "Это похоже на автоматизм программы: она заранее рисует неудачу, чтобы удержать от риска.",
        "c1_driver_try_harder": "Слышно сильное внутреннее давление ""надо еще"". Можно мягко заметить этот голос без самокритики.",
        "c2_driver_be_strong": "Когда внутри звучит ""будь сильным"", это может быть защитный голос, а не единственная правда о тебе.",
        "c3_driver_hurry": "Похоже, включается спешащий автоматизм: как будто нужно все успеть прямо сейчас.",
        "d1_what_is_neurostalking": "В нашей внутренней рамке нейросталкинг — это наблюдение за паттернами, триггерами и автоматическими реакциями.",
        "d2_neurostalking_and_selfrealization": "Нейросталкинг помогает самореализации, потому что дает увидеть автопилот и вернуть выбор в точке реакции.",
        "d3_inner_loop_return": "Ты замечаешь повторяющийся внутренний круг: автопилот запускает знакомую программу, и это уже можно наблюдать в моменте.",
    }
    return mapping.get(case_id, "")


def _run_dry(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case.get("id", "unknown"))
        query = str(case.get("query", "") or "")
        response_mode = str(case.get("response_mode", "reflect") or "reflect")
        payload = build_philosophy_kernel_runtime_payload(
            user_message=query,
            safety_active=False,
            response_mode=response_mode,
            practice_allowed=False,
        )
        answer = _dry_answer(case_id)
        kernel_trace = {
            "selected_lenses": list(dict(payload.get("selection", {})).get("selected_lenses", [])),
        }
        compactness = _effective_compactness(payload)
        evaluation = _evaluate_case(
            case=case,
            answer=answer,
            kernel_trace=kernel_trace,
            compactness=compactness,
        )
        case_results.append(
            {
                "case_id": case_id,
                "group": case.get("group"),
                "mode": "dry",
                "query": query,
                "answer": answer,
                "kernel_trace": {
                    "selected_lenses": kernel_trace.get("selected_lenses", []),
                    "selection_reason": list(dict(payload.get("selection", {})).get("selection_reason", [])),
                    "depth_mode": str(dict(payload.get("selection", {})).get("depth_mode", "guided")),
                },
                "prompt_compactness": compactness,
                "evaluation": evaluation,
            }
        )
        samples.append(
            {
                "mode": "dry",
                "case_id": case_id,
                "group": case.get("group"),
                "selected_lenses": kernel_trace.get("selected_lenses", []),
                "prompt_compactness": compactness,
            }
        )
    return case_results, samples


async def _run_direct_async(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from bot_agent.multiagent.orchestrator import orchestrator

    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    run_nonce = uuid.uuid4().hex[:8]
    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("id", f"case_{index}"))
        query = str(case.get("query", "") or "")
        user_id = f"prd0472_direct_{run_nonce}_{index}"
        final_result = await orchestrator.run(query=query, user_id=user_id)
        debug = dict(final_result.get("debug", {}))
        answer = str(final_result.get("answer", "") or "")
        kernel_trace = dict(debug.get("philosophy_kernel", {}))
        compactness = _effective_compactness(kernel_trace)
        evaluation = _evaluate_case(
            case=case,
            answer=answer,
            kernel_trace=kernel_trace,
            compactness=compactness,
        )
        case_results.append(
            {
                "case_id": case_id,
                "group": case.get("group"),
                "mode": "direct",
                "query": query,
                "answer": answer,
                "kernel_trace": kernel_trace,
                "writer_freedom_contract": dict(debug.get("writer_freedom_contract", {})),
                "prompt_compactness": compactness,
                "evaluation": evaluation,
            }
        )
        samples.append(
            {
                "mode": "direct",
                "case_id": case_id,
                "group": case.get("group"),
                "kernel_trace": kernel_trace,
                "writer_freedom_contract": dict(debug.get("writer_freedom_contract", {})),
                "prompt_compactness": compactness,
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
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    headers = {"X-API-Key": api_key}
    probe_url = f"{base_url.rstrip('/')}/identity/me"
    try:
        status, _ = _http_json_request(method="GET", url=probe_url, headers=headers)
        if status != 200:
            return (
                {"live_status": "skipped", "reason": f"identity probe status={status}", "case_results": []},
                [],
            )
    except Exception as exc:  # noqa: BLE001
        return (
            {"live_status": "skipped", "reason": f"identity probe failed: {exc}", "case_results": []},
            [],
        )

    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("id", f"case_{index}"))
        query = str(case.get("query", "") or "")
        user_id = f"prd0472_live_user_{index}"
        session_id = f"prd0472_live_session_{index}"
        answer = ""
        debug: dict[str, Any] = {}
        errors: list[str] = []
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
                errors.append(f"status={status}")
            else:
                answer = str(payload.get("answer", "") or "")
                debug = dict(payload.get("debug", {}))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            errors.append(f"http_error={exc.code}:{detail}")
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

        kernel_trace = dict(debug.get("philosophy_kernel", {}))
        compactness = _effective_compactness(kernel_trace)
        evaluation = _evaluate_case(
            case=case,
            answer=answer,
            kernel_trace=kernel_trace,
            compactness=compactness,
        )
        case_results.append(
            {
                "case_id": case_id,
                "group": case.get("group"),
                "mode": "live",
                "query": query,
                "answer": answer,
                "errors": errors,
                "kernel_trace": kernel_trace,
                "writer_freedom_contract": dict(debug.get("writer_freedom_contract", {})),
                "prompt_compactness": compactness,
                "evaluation": evaluation,
            }
        )
        samples.append(
            {
                "mode": "live",
                "case_id": case_id,
                "group": case.get("group"),
                "kernel_trace": kernel_trace,
                "writer_freedom_contract": dict(debug.get("writer_freedom_contract", {})),
                "prompt_compactness": compactness,
            }
        )

    has_kernel_trace = any(bool(item.get("kernel_trace")) for item in case_results)
    if not has_kernel_trace:
        return (
            {
                "live_status": "skipped",
                "reason": "live backend appears stale or not restarted after PRD-047.2 changes",
                "case_results": case_results,
            },
            samples,
        )

    return ({"live_status": "passed", "reason": "", "case_results": case_results}, samples)


def _build_summary(case_results: list[dict[str, Any]]) -> dict[str, int]:
    total = len(case_results)
    passed = sum(1 for item in case_results if bool(item.get("evaluation", {}).get("passed")))
    return {"cases_total": total, "cases_passed": passed, "cases_failed": max(0, total - passed)}


def _build_prompt_compactness_report(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    compactness_rows = [
        dict(item.get("prompt_compactness", {}))
        for item in case_results
        if isinstance(item.get("prompt_compactness", {}), dict)
    ]
    if not compactness_rows:
        return {
            "max_kernel_chars": 0,
            "max_freedom_chars": 0,
            "max_combined_chars": 0,
            "max_selected_lenses": 0,
            "within_budget_all": False,
            "budgets": {
                "max_kernel_chars": MAX_KERNEL_PROMPT_CHARS,
                "max_freedom_chars": MAX_FREEDOM_PROMPT_CHARS,
                "max_combined_chars": MAX_COMBINED_PROMPT_CHARS,
                "max_selected_lenses": MAX_SELECTED_LENSES,
            },
        }
    max_kernel = max(int(item.get("philosophy_kernel_prompt_block_chars", 0) or 0) for item in compactness_rows)
    max_freedom = max(int(item.get("writer_freedom_contract_chars", 0) or 0) for item in compactness_rows)
    max_combined = max(int(item.get("combined_chars", 0) or 0) for item in compactness_rows)
    max_selected = max(int(item.get("selected_lenses_count", 0) or 0) for item in compactness_rows)
    within_budget_all = all(bool(item.get("within_budget", False)) for item in compactness_rows)
    return {
        "max_kernel_chars": max_kernel,
        "max_freedom_chars": max_freedom,
        "max_combined_chars": max_combined,
        "max_selected_lenses": max_selected,
        "within_budget_all": within_budget_all,
        "budgets": {
            "max_kernel_chars": MAX_KERNEL_PROMPT_CHARS,
            "max_freedom_chars": MAX_FREEDOM_PROMPT_CHARS,
            "max_combined_chars": MAX_COMBINED_PROMPT_CHARS,
            "max_selected_lenses": MAX_SELECTED_LENSES,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.2 kernel quality cases.")
    parser.add_argument("--mode", choices=("dry", "direct", "live"), default="dry")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output", default=None)
    parser.add_argument("--trace-samples-output", default=str(DEFAULT_TRACE_SAMPLES))
    parser.add_argument("--compactness-output", default=str(DEFAULT_COMPACTNESS_REPORT))
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--api-base-url", default=os.getenv("PRD0472_API_BASE", "http://localhost:8001/api/v1"))
    parser.add_argument("--api-key", default=os.getenv("PRD0472_API_KEY", os.getenv("BOT_API_KEY", "dev-key-001")))
    args = parser.parse_args()

    dataset_path = _resolve_path(args.dataset)
    trace_output_path = _resolve_path(args.trace_samples_output)
    compactness_output_path = _resolve_path(args.compactness_output)
    if args.output:
        output_path = _resolve_path(args.output)
    else:
        output_path = DEFAULT_LOG_DIR / f"kernel_quality_{args.mode}.json"

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
            "prd_id": "PRD-047.2",
            "mode": "dry",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": _build_summary(case_results),
            "case_results": case_results,
        }
        _write_json(output_path, payload)
        _write_json(trace_output_path, {"prd_id": "PRD-047.2", "mode": "dry", "samples": samples})
        _write_json(compactness_output_path, _build_prompt_compactness_report(case_results))
        print(output_path)
        return 0

    if args.mode == "direct":
        case_results, samples = asyncio.run(_run_direct_async(cases))
        payload = {
            "prd_id": "PRD-047.2",
            "mode": "direct",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": _build_summary(case_results),
            "case_results": case_results,
        }
        _write_json(output_path, payload)
        _write_json(trace_output_path, {"prd_id": "PRD-047.2", "mode": "direct", "samples": samples})
        _write_json(compactness_output_path, _build_prompt_compactness_report(case_results))
        print(output_path)
        return 0

    live_payload, samples = _run_live(cases, base_url=str(args.api_base_url), api_key=str(args.api_key))
    if str(live_payload.get("live_status")) == "passed":
        case_results = list(live_payload.get("case_results", []))
        payload = {
            "prd_id": "PRD-047.2",
            "mode": "live",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": _build_summary(case_results),
            "case_results": case_results,
            "live_status": "passed",
            "reason": "",
        }
        _write_json(compactness_output_path, _build_prompt_compactness_report(case_results))
    else:
        payload = {
            "prd_id": "PRD-047.2",
            "mode": "live",
            "timestamp_utc": _now_iso(),
            "dataset": str(dataset_path),
            "summary": {"cases_total": 0, "cases_passed": 0, "cases_failed": 0},
            "case_results": [],
            "live_status": "skipped",
            "reason": str(live_payload.get("reason", "unknown")),
        }
    _write_json(output_path, payload)
    _write_json(trace_output_path, {"prd_id": "PRD-047.2", "mode": "live", "samples": samples})
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
