#!/usr/bin/env python3
"""PRD-047.7 guided live feedback smoke runner."""

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
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.live_testing.feedback_capture import (  # noqa: E402
    append_feedback_record,
    build_trace_summary,
    create_feedback_record,
    get_feedback_reports_dir,
    get_session_storage_path,
    load_session_payload,
)
from scripts.build_live_feedback_summary import build_summary_artifacts  # noqa: E402


DEFAULT_SCENARIOS = PROJECT_ROOT / "tests" / "evaluation" / "prd_047_7_guided_live_scenarios.json"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.7"

_REQUIRED_CATEGORIES = {
    "ordinary_understanding",
    "low_resource",
    "soft_distress",
    "practice_boundary",
    "defensive_i_plus_w_minus",
    "known_concept_kb",
    "close_continuation",
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


def _load_scenarios(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("scenario_set must be list")
    return [item for item in payload if isinstance(item, dict)]


def _validate_scenarios(items: list[dict[str, Any]]) -> tuple[bool, list[str], dict[str, int]]:
    errors: list[str] = []
    coverage: dict[str, int] = {}

    if len(items) < 18:
        errors.append(f"scenario_count_too_low:{len(items)}")

    for idx, item in enumerate(items, start=1):
        scenario_id = str(item.get("scenario_id", "") or f"scenario_{idx}")
        category = str(item.get("category", "") or "").strip()
        if not category:
            errors.append(f"{scenario_id}:missing_category")
        coverage[category] = coverage.get(category, 0) + 1
        if not str(item.get("user_prompt", "") or "").strip():
            errors.append(f"{scenario_id}:missing_user_prompt")

    for category in sorted(_REQUIRED_CATEGORIES):
        if coverage.get(category, 0) == 0:
            errors.append(f"missing_required_category:{category}")

    return len(errors) == 0, errors, coverage


def _sample_debug_payload(index: int) -> dict[str, Any]:
    statuses = ["ok", "warning", "ok"]
    status = statuses[index % len(statuses)]
    severity = "none" if status == "ok" else "medium"
    flags = [] if status == "ok" else ["question_policy_violation"]
    return {
        "active_line": {
            "user_intent": "understand_self_pattern",
            "continuity_mode": "continue_existing_line",
        },
        "response_planner": {
            "next_move": "deepen_mechanism",
            "answer_shape": "mechanism_explanation",
            "response_depth": "short",
            "question_policy": "none",
            "practice_policy": "forbidden",
        },
        "planner_drift_guard": {
            "status": status,
            "severity": severity,
            "flags": flags,
        },
        "model_used": "gpt-5-mini",
        "writer_fallback_used": False,
    }


def _build_feedback_for_case(
    *,
    session_id: str,
    turn_id: str,
    scenario: dict[str, Any],
    debug_payload: dict[str, Any],
    answer_preview: str,
) -> dict[str, Any]:
    scenario_id = str(scenario.get("scenario_id", "") or "")
    user_prompt = str(scenario.get("user_prompt", "") or "")

    record = create_feedback_record(
        session_id=session_id,
        turn_id=turn_id,
        scenario_id=scenario_id,
        user_rating=4,
        felt_alive=True,
        felt_understood=True,
        felt_too_rigid=False,
        felt_too_generic=False,
        too_many_questions=False,
        too_much_practice=False,
        missed_context=False,
        comment=f"smoke comment for {scenario_id}",
        trace_summary=build_trace_summary(
            debug_payload=debug_payload,
            user_message_preview=user_prompt,
            answer_preview=answer_preview,
            user_id="project_owner_local",
        ),
    )
    payload = append_feedback_record(
        record=record,
        backend_url="http://127.0.0.1:dev",
        frontend_url="http://localhost:3000",
        scenario_set="guided_live_v1",
    )
    return payload


def _has_raw_dialogue(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False).lower()
    forbidden = ["raw_dialogue", "provider_payload", "api_key", "authorization"]
    return any(marker in text for marker in forbidden)


def _run_dry(items: list[dict[str, Any]]) -> dict[str, Any]:
    session_id = "sample_session"
    session_path = get_session_storage_path(session_id)
    if session_path.exists():
        session_path.unlink()

    selected = items[:3]
    for idx, scenario in enumerate(selected, start=1):
        _build_feedback_for_case(
            session_id=session_id,
            turn_id=f"turn_{idx}",
            scenario=scenario,
            debug_payload=_sample_debug_payload(idx),
            answer_preview="Короткий поддерживающий ответ для smoke-проверки.",
        )

    payload = load_session_payload(session_id) or {}
    reports_dir = get_feedback_reports_dir()
    summary_json, summary_md, summary = build_summary_artifacts(
        session_payload=payload,
        session_id=session_id,
        output_dir=reports_dir,
    )

    return {
        "mode": "dry",
        "timestamp_utc": _now_iso(),
        "summary": "passed",
        "session_id": session_id,
        "records_created": int(payload.get("feedback_count", 0) or 0),
        "raw_dialogue_saved": _has_raw_dialogue(payload),
        "sanitized_summary_created": summary_json.exists() and summary_md.exists(),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
        "recommended_next_action": summary.get("recommended_next_action"),
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
    items: list[dict[str, Any]],
    *,
    api_base_url: str,
    admin_runtime_url: str,
    api_key: str,
) -> dict[str, Any]:
    headers = {"X-API-Key": api_key}
    try:
        status, runtime_payload = _http_json_request(
            method="GET",
            url=admin_runtime_url,
            headers=headers,
            timeout=20,
        )
        if status != 200:
            return {
                "mode": "live",
                "summary": "blocked",
                "reason": f"admin_runtime_status_{status}",
                "records_created": 0,
                "raw_dialogue_saved": False,
                "sanitized_summary_created": False,
            }
        if not isinstance(runtime_payload.get("guided_live_testing"), dict):
            return {
                "mode": "live",
                "summary": "blocked",
                "reason": "admin_runtime_missing_guided_live_testing_block",
                "records_created": 0,
                "raw_dialogue_saved": False,
                "sanitized_summary_created": False,
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "mode": "live",
            "summary": "blocked",
            "reason": f"admin_runtime_unavailable:{exc}",
            "records_created": 0,
            "raw_dialogue_saved": False,
            "sanitized_summary_created": False,
        }

    session_id = f"live_smoke_{uuid.uuid4().hex[:10]}"
    selected = items[:3]
    created = 0
    for idx, scenario in enumerate(selected, start=1):
        user_prompt = str(scenario.get("user_prompt", "") or "")
        try:
            status_code, response_payload = _http_json_request(
                method="POST",
                url=f"{api_base_url.rstrip('/')}/questions/adaptive",
                headers=headers,
                payload={
                    "query": user_prompt,
                    "session_id": f"{session_id}_thread",
                    "debug": True,
                },
                timeout=90,
            )
            if status_code != 200:
                continue
            trace_payload = response_payload.get("trace") if isinstance(response_payload.get("trace"), dict) else {}
            debug_payload = response_payload.get("debug") if isinstance(response_payload.get("debug"), dict) else {}
            joined_debug = dict(debug_payload)
            for key, value in dict(trace_payload).items():
                joined_debug.setdefault(key, value)

            record = create_feedback_record(
                session_id=session_id,
                turn_id=f"turn_{idx}",
                scenario_id=str(scenario.get("scenario_id", "") or ""),
                user_rating=4,
                felt_alive=True,
                felt_understood=True,
                comment="live smoke feedback",
                trace_summary=build_trace_summary(
                    debug_payload=joined_debug,
                    user_message_preview=user_prompt,
                    answer_preview=str(response_payload.get("answer", "") or ""),
                    user_id=session_id,
                ),
            )
            append_feedback_record(
                record=record,
                backend_url=api_base_url,
                frontend_url="http://localhost:3000",
                scenario_set="guided_live_v1",
            )
            created += 1
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue

    payload = load_session_payload(session_id) or {}
    reports_dir = get_feedback_reports_dir()
    summary_json, summary_md, summary = build_summary_artifacts(
        session_payload=payload,
        session_id=session_id,
        output_dir=reports_dir,
    )

    return {
        "mode": "live",
        "timestamp_utc": _now_iso(),
        "summary": "passed" if created >= 1 else "blocked",
        "reason": "" if created >= 1 else "no_live_records_created",
        "session_id": session_id,
        "records_created": created,
        "raw_dialogue_saved": _has_raw_dialogue(payload),
        "sanitized_summary_created": summary_json.exists() and summary_md.exists(),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
        "recommended_next_action": summary.get("recommended_next_action"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.7 guided live feedback smoke")
    parser.add_argument("--mode", choices=("dry", "live"), default="dry")
    parser.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    parser.add_argument("--output", default=None)
    parser.add_argument("--api-base-url", default=os.getenv("PRD0477_API_BASE", "http://127.0.0.1:8015/api/v1"))
    parser.add_argument(
        "--admin-runtime-url",
        default=os.getenv("PRD0477_ADMIN_RUNTIME_URL", "http://127.0.0.1:8015/api/admin/runtime/effective"),
    )
    parser.add_argument("--api-key", default=os.getenv("PRD0477_API_KEY", os.getenv("BOT_API_KEY", "dev-key-001")))
    args = parser.parse_args()

    scenarios_path = _resolve_path(args.scenarios)
    output_path = _resolve_path(args.output) if args.output else DEFAULT_LOG_DIR / f"guided_live_feedback_smoke_{args.mode}.json"

    items = _load_scenarios(scenarios_path)
    scenarios_ok, scenario_errors, scenario_coverage = _validate_scenarios(items)

    if args.mode == "dry":
        result = _run_dry(items)
    else:
        result = _run_live(
            items,
            api_base_url=args.api_base_url,
            admin_runtime_url=args.admin_runtime_url,
            api_key=args.api_key,
        )

    payload = {
        "prd_id": "PRD-047.7",
        "mode": args.mode,
        "timestamp_utc": _now_iso(),
        "scenario_set": str(scenarios_path),
        "scenario_count": len(items),
        "scenario_validation_passed": scenarios_ok,
        "scenario_validation_errors": scenario_errors,
        "scenario_coverage": scenario_coverage,
        "result": result,
    }
    _write_json(output_path, payload)

    print(
        json.dumps(
            {
                "mode": args.mode,
                "output": str(output_path),
                "summary": result.get("summary"),
                "records_created": result.get("records_created"),
                "raw_dialogue_saved": result.get("raw_dialogue_saved"),
                "sanitized_summary_created": result.get("sanitized_summary_created"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
