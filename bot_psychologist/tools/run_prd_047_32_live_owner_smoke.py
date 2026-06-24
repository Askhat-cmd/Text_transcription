from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


BOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BOT_ROOT.parent
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.32"
API_BASE = "http://127.0.0.1:8001"
API_KEY = "dev-key-001"

CASES = [
    {
        "label": "mandatory_1_greeting",
        "session": "prd-047-32-live-owner",
        "query": "Привет",
    },
    {
        "label": "mandatory_2_resistance",
        "session": "prd-047-32-live-owner",
        "query": "Как преодолеть сопротивление, когда я понимаю, что надо делать, но не делаю?",
    },
    {
        "label": "mandatory_3_anger_boss",
        "session": "prd-047-32-live-owner",
        "query": "А если накатывает гнев, начальник врет, и я хочу резко ответить?",
    },
    {
        "label": "mandatory_4_practice",
        "session": "prd-047-32-live-owner",
        "query": "Дай практику, чтобы не быть реактивным",
    },
    {
        "label": "mandatory_5_long_term_practice",
        "session": "prd-047-32-live-owner",
        "query": "В долгосрочной перспективе какую практику применять, чтобы меньше взрываться на начальника?",
    },
    {
        "label": "extra_a_support",
        "session": "prd-047-32-live-owner",
        "query": "Мне тяжело, просто поддержи меня без анализа.",
    },
    {
        "label": "extra_b_no_practice_explain",
        "session": "prd-047-32-live-owner",
        "query": "Не давай практику, объясни словами, что со мной происходит.",
    },
    {
        "label": "extra_c_direct_kb_source",
        "session": "prd-047-32-live-owner",
        "query": "Что во внутренней базе говорится про программу несовершенное Я?",
    },
    {
        "label": "extra_d_no_internal_db",
        "session": "prd-047-32-live-owner",
        "query": "Не используй внутреннюю базу, ответь своими словами: как выдержать злость?",
    },
    {
        "label": "extra_e_new_thread_practice",
        "session": "prd-047-32-live-practice-new",
        "query": "Дай короткую практику, чтобы не быть реактивным, на моем примере.",
    },
]


def _request_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 180) -> dict[str, Any]:
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


def _health() -> dict[str, Any]:
    return _request_json(f"{API_BASE}/api/v1/health", timeout=20)


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
            "X-Device-Fingerprint": "prd-047-32-live-fp",
        },
        timeout=220,
    )


def _safe_get(mapping: dict[str, Any] | None, key: str, default: Any = None) -> Any:
    if not isinstance(mapping, dict):
        return default
    return mapping.get(key, default)


def _summarize(case: dict[str, str], turn_index: int, response: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    truth = trace.get("runtime_truth_trace_v1") if isinstance(trace.get("runtime_truth_trace_v1"), dict) else {}
    answer = str(response.get("answer") or "")
    return {
        "label": case["label"],
        "session": case["session"],
        "turn_index": turn_index,
        "query": case["query"],
        "status": response.get("status"),
        "answer_length": len(answer),
        "answer_preview": answer[:260],
        "trace_version": _safe_get(truth, "trace_version"),
        "dialogue_act": _safe_get(truth, "dialogue_act"),
        "answer_obligation": _safe_get(truth, "answer_obligation"),
        "latest_must_answer": _safe_get(truth, "latest_must_answer"),
        "retrieval_query_source": _safe_get(truth, "retrieval_query_source"),
        "retrieved_candidates_count": _safe_get(truth, "retrieved_candidates_count"),
        "writer_visible_payload_count": _safe_get(truth, "writer_visible_payload_count"),
        "writer_visible_payload_ids": _safe_get(truth, "writer_visible_payload_ids", []),
        "filtered_out_for_writer_count": _safe_get(truth, "filtered_out_for_writer_count"),
        "grounding_visibility_reason": _safe_get(truth, "grounding_visibility_reason"),
        "legacy_fallback_scope": _safe_get(truth, "legacy_fallback_scope"),
        "planner_shadow_status": _safe_get(truth, "planner_shadow_status", trace.get("hybrid_retrieval_planner_status")),
        "planner_fallback_scope": _safe_get(truth, "planner_fallback_scope", trace.get("hybrid_retrieval_fallback_scope")),
        "json_decode_error_affected_production_answer": _safe_get(
            truth,
            "json_decode_error_affected_production_answer",
            trace.get("hybrid_retrieval_production_answer_affected"),
        ),
        "top_level_planner_status": trace.get("hybrid_retrieval_planner_status"),
        "top_level_fallback_scope": trace.get("hybrid_retrieval_fallback_scope"),
        "top_level_production_query_source": trace.get("hybrid_retrieval_production_query_source"),
        "top_level_production_answer_affected": trace.get("hybrid_retrieval_production_answer_affected"),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    turn_by_session: dict[str, int] = {}
    results: list[dict[str, Any]] = []
    for case in CASES:
        session = case["session"]
        turn_by_session[session] = turn_by_session.get(session, 0) + 1
        turn_index = turn_by_session[session]
        response = _post_turn(session=session, query=case["query"])
        time.sleep(0.5)
        try:
            trace = _fetch_trace(session=session, turn_index=turn_index)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            trace = {"trace_fetch_error": str(exc)}
        results.append(_summarize(case, turn_index, response, trace))
        print(f"{case['label']}: answer_length={results[-1]['answer_length']} payload={results[-1]['writer_visible_payload_count']} planner={results[-1]['planner_shadow_status']}")
        sys.stdout.flush()

    report = {
        "created_at": datetime.now().isoformat(),
        "backend_health": _health(),
        "results": results,
    }
    out_path = OUT_DIR / "live_owner_web_chat_trace_raw.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
