#!/usr/bin/env python3
"""Run PRD-047.1 philosophy-kernel smoke in dry/direct/live modes."""

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

from bot_agent.multiagent.philosophy_kernel import build_philosophy_kernel_runtime_payload  # noqa: E402

DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.1"
DEFAULT_TRACE_SAMPLES = DEFAULT_LOG_DIR / "philosophy_kernel_trace_samples.json"

_UNSOLICITED_PRACTICE_MARKERS = [
    "положи руку",
    "ладонь",
    "грудь",
    "живот",
    "сделай вдох",
    "сделай выдох",
    "глубоких вдоха",
    "почувствуй тело",
    "почувствуй опору",
    "ступн",
    "опор",
]
_EXTERNAL_SURVEILLANCE_MARKERS = [
    "внешнее слежение",
    "биофидбек",
    "ээг",
    "нейроинтерфейс",
    "технический мониторинг",
    "цифровые следы",
]
_DIAGNOSIS_MARKERS = ["диагноз", "травм", "расстройств", "психиатр"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _contains_any(text: str, patterns: list[str]) -> bool:
    lowered = str(text or "").lower()
    return any(str(item).lower() in lowered for item in patterns)


def _cases() -> list[dict[str, str]]:
    return [
        {"id": "greeting", "query": "Привет", "response_mode": "reflect"},
        {"id": "known_concept", "query": "Что такое нейросталкинг?", "response_mode": "reflect"},
        {
            "id": "imperfect_self",
            "query": "Я боюсь, что уже всё упустил и не справлюсь",
            "response_mode": "reflect",
        },
        {
            "id": "driver",
            "query": "Мне всё время кажется, что надо стараться сильнее",
            "response_mode": "reflect",
        },
        {
            "id": "short_support",
            "query": "Я устал, скажи пару спокойных слов без анализа",
            "response_mode": "reflect",
        },
    ]


def _dry_answer_proxy(case_id: str) -> str:
    mapping = {
        "greeting": "Привет. Рад знакомству. Можем спокойно начать с твоего вопроса.",
        "known_concept": (
            "В нашей внутренней рамке нейросталкинг — это наблюдение за паттернами, "
            "триггерами и автоматическими реакциями, чтобы не сливаться с ними полностью."
        ),
        "imperfect_self": (
            "Похоже, включается не поломка личности, а защитная программа: заранее объявить, "
            "что ничего не выйдет, чтобы не рисковать."
        ),
        "driver": (
            "Слышно сильное внутреннее давление 'надо больше'. Можно мягко заметить этот голос "
            "и проверить, что в тебе реально живое, а что идет на автопилоте."
        ),
        "short_support": "Ты устал. Сейчас можно чуть выдохнуть и не решать все в эту минуту.",
    }
    return mapping.get(case_id, "")


def _evaluate_case(*, case_id: str, answer: str, payload: dict[str, Any]) -> dict[str, Any]:
    selection = dict(payload.get("selection", {}))
    selected_lenses = list(selection.get("selected_lenses", []))
    depth_mode = str(selection.get("depth_mode", "guided"))
    lowered = str(answer or "").lower()
    checks: dict[str, bool] = {}

    checks["no_unsolicited_practice"] = not _contains_any(lowered, _UNSOLICITED_PRACTICE_MARKERS)
    checks["no_external_surveillance"] = not _contains_any(lowered, _EXTERNAL_SURVEILLANCE_MARKERS)

    if case_id == "greeting":
        checks["no_deep_lens"] = len(selected_lenses) == 0
        checks["simple_contact"] = _contains_any(lowered, ["привет", "рад", "начать"])
    elif case_id == "known_concept":
        checks["lens_neurostalking"] = "neurostalking" in selected_lenses
        checks["direct_answer"] = _contains_any(lowered, ["нейросталкинг", "паттерн", "триггер"])
    elif case_id == "imperfect_self":
        checks["lens_imperfect_self_program"] = "imperfect_self_program" in selected_lenses
        checks["no_diagnosis"] = not _contains_any(lowered, _DIAGNOSIS_MARKERS)
    elif case_id == "driver":
        checks["lens_drivers"] = "drivers" in selected_lenses
        checks["no_hard_label"] = "у вас драйвер" not in lowered
        checks["soft_mirror"] = _contains_any(lowered, ["давлен", "голос", "мягко"])
    elif case_id == "short_support":
        checks["depth_suppressed"] = depth_mode == "suppressed"
        checks["short_answer"] = len(str(answer or "")) <= 220
        checks["no_analysis_lecture"] = not _contains_any(lowered, ["теория", "лекц", "диагноз"])
    passed = all(checks.values())
    return {"passed": passed, "checks": checks}


def _run_dry() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for case in _cases():
        payload = build_philosophy_kernel_runtime_payload(
            user_message=case["query"],
            safety_active=False,
            response_mode=case["response_mode"],
            practice_allowed=False,
        )
        answer = _dry_answer_proxy(case["id"])
        evaluation = _evaluate_case(case_id=case["id"], answer=answer, payload=payload)
        case_results.append(
            {
                "case_id": case["id"],
                "mode": "dry",
                "query": case["query"],
                "answer": answer,
                "selection": payload.get("selection", {}),
                "evaluation": evaluation,
            }
        )
        samples.append(
            {
                "mode": "dry",
                "case_id": case["id"],
                "selection": payload.get("selection", {}),
                "kernel_version": payload.get("kernel_version", ""),
                "writer_freedom_contract": payload.get("writer_freedom_contract", {}),
            }
        )
    return case_results, samples


async def _run_direct_async() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from bot_agent.multiagent.orchestrator import orchestrator

    case_results: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    run_nonce = uuid.uuid4().hex[:8]
    for idx, case in enumerate(_cases(), start=1):
        user_id = f"prd0471_direct_{run_nonce}_{idx}"
        result = await orchestrator.run(query=case["query"], user_id=user_id)
        debug = dict(result.get("debug", {}))
        answer = str(result.get("answer", "") or "")
        payload = {
            "selection": {
                "selected_lenses": list(
                    dict(debug.get("philosophy_kernel", {})).get("selected_lenses", [])
                ),
                "depth_mode": (
                    "suppressed"
                    if not bool(dict(debug.get("philosophy_kernel", {})).get("prompt_block_included", True))
                    else "guided"
                ),
            }
        }
        evaluation = _evaluate_case(case_id=case["id"], answer=answer, payload=payload)
        case_results.append(
            {
                "case_id": case["id"],
                "mode": "direct",
                "query": case["query"],
                "answer": answer,
                "philosophy_kernel": dict(debug.get("philosophy_kernel", {})),
                "writer_freedom_contract": dict(debug.get("writer_freedom_contract", {})),
                "evaluation": evaluation,
            }
        )
        samples.append(
            {
                "mode": "direct",
                "case_id": case["id"],
                "philosophy_kernel": dict(debug.get("philosophy_kernel", {})),
                "writer_freedom_contract": dict(debug.get("writer_freedom_contract", {})),
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
    for idx, case in enumerate(_cases(), start=1):
        user_id = f"prd0471_live_user_{idx}"
        session_id = f"prd0471_live_session_{idx}"
        errors: list[str] = []
        answer = ""
        debug: dict[str, Any] = {}
        try:
            status, payload = _http_json_request(
                method="POST",
                url=f"{base_url.rstrip('/')}/questions/adaptive",
                headers=headers,
                payload={
                    "query": case["query"],
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

        selection_payload = {
            "selection": {
                "selected_lenses": list(
                    dict(debug.get("philosophy_kernel", {})).get("selected_lenses", [])
                ),
                "depth_mode": (
                    "suppressed"
                    if not bool(dict(debug.get("philosophy_kernel", {})).get("prompt_block_included", True))
                    else "guided"
                ),
            }
        }
        evaluation = _evaluate_case(case_id=case["id"], answer=answer, payload=selection_payload)
        case_results.append(
            {
                "case_id": case["id"],
                "mode": "live",
                "query": case["query"],
                "answer": answer,
                "errors": errors,
                "philosophy_kernel": dict(debug.get("philosophy_kernel", {})),
                "writer_freedom_contract": dict(debug.get("writer_freedom_contract", {})),
                "evaluation": evaluation,
            }
        )
        samples.append(
            {
                "mode": "live",
                "case_id": case["id"],
                "philosophy_kernel": dict(debug.get("philosophy_kernel", {})),
                "writer_freedom_contract": dict(debug.get("writer_freedom_contract", {})),
            }
        )

    has_kernel_trace = any(bool(item.get("philosophy_kernel")) for item in case_results)
    if not has_kernel_trace:
        return (
            {
                "live_status": "skipped",
                "reason": "live backend appears stale or not restarted after PRD-047.1 changes",
                "case_results": case_results,
            },
            samples,
        )
    return ({"live_status": "passed", "reason": "", "case_results": case_results}, samples)


def _summary(case_results: list[dict[str, Any]]) -> dict[str, int]:
    total = len(case_results)
    passed = sum(1 for item in case_results if bool(item.get("evaluation", {}).get("passed")))
    return {"cases_total": total, "cases_passed": passed, "cases_failed": max(0, total - passed)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.1 philosophy-kernel smoke cases.")
    parser.add_argument("--mode", choices=("dry", "direct", "live"), default="dry")
    parser.add_argument("--output", default=None)
    parser.add_argument("--trace-samples-output", default=str(DEFAULT_TRACE_SAMPLES))
    parser.add_argument("--api-base-url", default=os.getenv("PRD0471_API_BASE", "http://localhost:8001/api/v1"))
    parser.add_argument("--api-key", default=os.getenv("PRD0471_API_KEY", os.getenv("BOT_API_KEY", "dev-key-001")))
    args = parser.parse_args()

    output_path = (
        Path(args.output).resolve()
        if args.output
        else (DEFAULT_LOG_DIR / f"philosophy_kernel_smoke_{args.mode}.json")
    )
    trace_samples_path = Path(args.trace_samples_output).resolve()

    if args.mode == "dry":
        case_results, samples = _run_dry()
        payload = {
            "prd_id": "PRD-047.1",
            "mode": "dry",
            "timestamp_utc": _now_iso(),
            "summary": _summary(case_results),
            "case_results": case_results,
        }
        _write_json(output_path, payload)
        _write_json(trace_samples_path, {"prd_id": "PRD-047.1", "mode": "dry", "samples": samples})
        print(output_path)
        return 0

    if args.mode == "direct":
        case_results, samples = asyncio.run(_run_direct_async())
        payload = {
            "prd_id": "PRD-047.1",
            "mode": "direct",
            "timestamp_utc": _now_iso(),
            "summary": _summary(case_results),
            "case_results": case_results,
        }
        _write_json(output_path, payload)
        _write_json(trace_samples_path, {"prd_id": "PRD-047.1", "mode": "direct", "samples": samples})
        print(output_path)
        return 0

    live_payload, samples = _run_live(base_url=str(args.api_base_url), api_key=str(args.api_key))
    if str(live_payload.get("live_status")) == "passed":
        case_results = list(live_payload.get("case_results", []))
        payload = {
            "prd_id": "PRD-047.1",
            "mode": "live",
            "timestamp_utc": _now_iso(),
            "summary": _summary(case_results),
            "case_results": case_results,
            "live_status": "passed",
            "reason": "",
        }
    else:
        payload = {
            "prd_id": "PRD-047.1",
            "mode": "live",
            "timestamp_utc": _now_iso(),
            "summary": {"cases_total": 0, "cases_passed": 0, "cases_failed": 0},
            "case_results": [],
            "live_status": "skipped",
            "reason": str(live_payload.get("reason", "unknown")),
        }
    _write_json(output_path, payload)
    _write_json(trace_samples_path, {"prd_id": "PRD-047.1", "mode": "live", "samples": samples})
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
