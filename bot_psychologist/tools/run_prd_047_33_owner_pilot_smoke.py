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
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.33"
API_BASE = "http://127.0.0.1:8001"
API_KEY = "dev-key-001"

CASES = [
    {
        "label": "A_greeting_memory_lite",
        "session_key": "owner-pilot-main",
        "query": "Привет! Я- Олег!",
    },
    {
        "label": "B_ordinary_explanation_resistance",
        "session_key": "owner-pilot-main",
        "query": "Как преодолеть свое сопротивление? Некоторые вещи я вообще не хочу делать. Например есть люди, которые мне неприятны, но я вынужден с ними общаться.",
    },
    {
        "label": "C_concrete_anger_boss",
        "session_key": "owner-pilot-main",
        "query": "А если на меня накатывает гнев во время разговора, когда я вижу, что мне нагло врут, но это мой начальник!",
    },
    {
        "label": "D_explicit_long_term_practice",
        "session_key": "owner-pilot-main",
        "query": "Скажи, а есть ли какая-нибудь практика, которая в долгосрочной перспективе научит меня не реагировать так остро на враньё?",
    },
    {
        "label": "E_no_practice_explanation_only",
        "session_key": "owner-pilot-main",
        "query": "Не давай практику. Просто объясни, почему меня так цепляет, когда человек врёт.",
    },
    {
        "label": "F_no_internal_db",
        "session_key": "owner-pilot-main",
        "query": "Ответь своими словами, без внутренней БД: что мне делать, если я злюсь, но не могу прямо спорить с начальником?",
    },
    {
        "label": "G_direct_kb_source_request",
        "session_key": "owner-pilot-main",
        "query": "Что во внутренней базе говорится про программу «несовершенное Я» и пять драйверов?",
    },
    {
        "label": "H_simple_support_presence",
        "session_key": "owner-pilot-support",
        "query": "Мне сейчас просто тяжело. Не хочу разбирать, просто скажи что-нибудь по-человечески.",
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


def _fetch_trace(session: str, turn_index: int) -> dict[str, Any]:
    encoded_session = urllib.parse.quote(session, safe="")
    url = f"{API_BASE}/api/debug/session/{encoded_session}/multiagent-trace?turn_index={turn_index}"
    return _request_json(url, headers={"X-API-Key": API_KEY}, timeout=60)


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
            "X-Device-Fingerprint": "prd-047-33-live-fp",
        },
        timeout=220,
    )


def _health() -> dict[str, Any]:
    return _request_json(f"{API_BASE}/api/v1/health", timeout=20)


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _looks_methodical(answer_text: str) -> tuple[bool, list[str]]:
    lowered = str(answer_text or "").lower()
    reasons: list[str] = []
    if len(answer_text) > 1400:
        reasons.append("answer_length_gt_1400")
    if answer_text.count("\n- ") > 2 or answer_text.count("\n1") > 0:
        reasons.append("list_like_structure")
    mechanism_hits = sum(
        1
        for token in ("механизм", "1)", "2)", "3)", "что происходит", "почему это важно", "что с этим делать")
        if token in lowered
    )
    if mechanism_hits >= 2:
        reasons.append("mechanism_lecture_pattern")
    return bool(reasons), reasons


def _summarize(
    case: dict[str, str],
    session: str,
    turn_index: int,
    response: dict[str, Any],
    trace: dict[str, Any],
) -> dict[str, Any]:
    answer = str(response.get("answer") or "")
    runtime_summary = _safe_dict(trace.get("runtime_trace_summary_v1"))
    truth = _safe_dict(trace.get("runtime_truth_trace_v1"))
    writer_payload = _safe_dict(trace.get("writer_kb_payload_trace"))
    directive = _safe_dict(trace.get("final_answer_directive"))
    methodical_warning, methodical_reasons = _looks_methodical(answer)
    selected_profile = str(
        runtime_summary.get("selected_answer_shape_profile")
        or directive.get("answer_shape_profile")
        or "unknown"
    )
    payload_count = (
        truth.get("writer_visible_payload_count")
        if truth.get("writer_visible_payload_count") is not None
        else writer_payload.get("payload_chunk_count", 0)
    )
    return {
        "label": case["label"],
        "session": session,
        "turn_index": turn_index,
        "query": case["query"],
        "status": response.get("status"),
        "answer_length": len(answer),
        "answer_preview": answer[:280],
        "selected_answer_shape_profile": selected_profile,
        "writer_payload_count": int(payload_count or 0),
        "runtime_truth_trace_present": bool(truth),
        "dialogue_act": truth.get("dialogue_act") or trace.get("dialogue_act"),
        "answer_obligation": truth.get("answer_obligation") or directive.get("answer_obligation"),
        "grounding_visibility_reason": truth.get("grounding_visibility_reason"),
        "planner_shadow_status": truth.get("planner_shadow_status") or runtime_summary.get("planner_shadow_status"),
        "methodical_warning": methodical_warning,
        "methodical_warning_reasons": methodical_reasons,
        "pass_hint": "warning" if methodical_warning else "passed",
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_prefix = f"prd-047-33-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    turn_by_session: dict[str, int] = {}
    results: list[dict[str, Any]] = []
    for case in CASES:
        session = f"{run_prefix}-{case['session_key']}"
        turn_by_session[session] = turn_by_session.get(session, 0) + 1
        turn_index = turn_by_session[session]
        response = _post_turn(session=session, query=case["query"])
        time.sleep(0.5)
        trace = _fetch_trace(session=session, turn_index=turn_index)
        summary = _summarize(case, session, turn_index, response, trace)
        results.append(summary)
        print(
            f"{case['label']}: len={summary['answer_length']} "
            f"profile={summary['selected_answer_shape_profile']} "
            f"payload={summary['writer_payload_count']} "
            f"methodical={summary['methodical_warning']}"
        )
        sys.stdout.flush()

    report = {
        "created_at": datetime.now().isoformat(),
        "backend_health": _health(),
        "results": results,
    }
    out_path = OUT_DIR / "live_owner_pilot_raw.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
