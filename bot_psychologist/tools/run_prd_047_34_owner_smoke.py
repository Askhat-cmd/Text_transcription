from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


BOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BOT_ROOT.parent
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.34"
API_BASE = "http://127.0.0.1:8001"
API_KEY = "dev-key-001"

SCENARIOS = [
    {
        "label": "A_chat5_exact_failure",
        "session_key": "chat5-main",
        "turns": [
            "Привет! Я - Олег.",
            "Что во внутренней базе говорится про программу «несовершенное Я» и пять драйверов?",
            "Мне сейчас просто тяжело. Не хочу разбирать, просто скажи что-нибудь по-человечески.",
        ],
    },
    {
        "label": "B_support_after_practice",
        "session_key": "support-after-practice",
        "turns": [
            "Как преодолеть свое сопротивление?",
            "А если я злюсь на начальника, который врёт?",
            "Дай практику, чтобы не быть реактивным.",
            "Всё, не хочу сейчас практику. Мне тяжело, просто скажи по-человечески.",
        ],
    },
    {
        "label": "C_explicit_continuation",
        "session_key": "continue-previous",
        "turns": [
            "Что во внутренней базе говорится про пять драйверов?",
            "Расскажи подробнее про второй драйвер.",
        ],
    },
    {
        "label": "D_no_internal_db_boundary",
        "session_key": "no-internal-db",
        "turns": [
            "Ответь своими словами, без внутренней БД: что мне делать, если я злюсь на начальника?",
        ],
    },
]


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    data = None
    request_headers = dict(headers or {})
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json; charset=utf-8")
    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else {}


def _post_turn(session: str, query: str) -> dict[str, Any]:
    return _request_json(
        f"{API_BASE}/api/v1/questions/adaptive",
        method="POST",
        payload={
            "query": query,
            "session_id": session,
            "debug": True,
            "include_path": False,
            "include_feedback_prompt": False,
        },
        headers={
            "X-API-Key": API_KEY,
            "X-Session-Id": session,
            "X-Device-Fingerprint": "prd-047-34-live-fp",
        },
        timeout=220,
    )


def _fetch_trace(session: str, turn_index: int) -> dict[str, Any]:
    encoded_session = urllib.parse.quote(session, safe="")
    return _request_json(
        f"{API_BASE}/api/debug/session/{encoded_session}/multiagent-trace?turn_index={turn_index}",
        headers={"X-API-Key": API_KEY},
        timeout=60,
    )


def _health() -> dict[str, Any]:
    return _request_json(f"{API_BASE}/api/v1/health", timeout=20)


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _turn_summary(
    *,
    scenario_label: str,
    session: str,
    turn_index: int,
    query: str,
    response: dict[str, Any],
    trace: dict[str, Any],
) -> dict[str, Any]:
    answer = str(response.get("answer") or "")
    runtime_summary = _safe_dict(trace.get("runtime_trace_summary_v1"))
    directive = _safe_dict(trace.get("final_answer_directive"))
    authority = _safe_dict(runtime_summary.get("latest_turn_authority_v1"))
    truth = _safe_dict(trace.get("runtime_truth_trace_v1"))
    payload_trace = _safe_dict(trace.get("writer_kb_payload_trace"))
    return {
        "scenario": scenario_label,
        "session": session,
        "turn_index": turn_index,
        "query": query,
        "answer_length": len(answer),
        "answer_preview": answer[:320],
        "dialogue_act": str(trace.get("dialogue_act") or truth.get("dialogue_act") or ""),
        "answer_obligation": str(
            directive.get("answer_obligation")
            or truth.get("answer_obligation")
            or trace.get("answer_obligation")
            or ""
        ),
        "must_answer": str(directive.get("must_answer", "") or ""),
        "must_answer_source": str(authority.get("must_answer_source") or directive.get("must_answer_source") or ""),
        "previous_must_answer_demoted": bool(
            authority.get("previous_must_answer_demoted", directive.get("previous_must_answer_demoted", False))
        ),
        "previous_must_answer": str(
            authority.get("previous_must_answer") or directive.get("previous_must_answer") or ""
        ),
        "explicit_continue_previous_detected": bool(
            authority.get(
                "explicit_continue_previous_detected",
                directive.get("explicit_continue_previous_detected", False),
            )
        ),
        "answer_target": str(authority.get("answer_target") or directive.get("answer_target") or ""),
        "writer_contact_mode": str(
            authority.get("writer_contact_mode") or directive.get("writer_contact_mode") or ""
        ),
        "answer_shape_profile": str(
            runtime_summary.get("selected_answer_shape_profile")
            or directive.get("answer_shape_profile")
            or ""
        ),
        "writer_payload_count": int(
            truth.get("writer_visible_payload_count")
            if truth.get("writer_visible_payload_count") is not None
            else payload_trace.get("payload_chunk_count", 0)
        ),
        "grounding_reason": str(
            truth.get("grounding_visibility_reason")
            or _safe_dict(trace.get("writer_grounding_visibility_v1")).get("reason", "")
            or ""
        ),
        "latest_turn_authority_v1": authority,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_prefix = f"prd-047-34-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    results: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        session = f"{run_prefix}-{scenario['session_key']}"
        for index, query in enumerate(scenario["turns"], start=1):
            response = _post_turn(session=session, query=query)
            time.sleep(0.5)
            trace = _fetch_trace(session=session, turn_index=index)
            summary = _turn_summary(
                scenario_label=scenario["label"],
                session=session,
                turn_index=index,
                query=query,
                response=response,
                trace=trace,
            )
            results.append(summary)
            print(
                f"{scenario['label']} turn={index}: "
                f"source={summary['must_answer_source']} "
                f"target={summary['answer_target']} "
                f"mode={summary['writer_contact_mode']} "
                f"payload={summary['writer_payload_count']}"
            )
            sys.stdout.flush()

    payload = {
        "created_at": datetime.now().isoformat(),
        "backend_health": _health(),
        "results": results,
    }
    out_path = OUT_DIR / "live_owner_smoke_raw.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
