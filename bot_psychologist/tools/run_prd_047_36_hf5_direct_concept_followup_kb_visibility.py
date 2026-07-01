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
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.36-HF5"
API_BASE = "http://127.0.0.1:8001"
API_KEY = "dev-key-001"
DEVICE_FINGERPRINT = "prd-047-36-hf5-smoke"

_INTERNAL_LEAK_MARKERS = (
    "в базе",
    "во внутренней базе",
    "внутренней бд",
    "semantic card",
    "semantic cards",
    "чанк",
    "чанки",
    "trace",
    "трейс",
    "карточк",
)


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


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _answer_preview(answer: str, max_len: int = 320) -> str:
    normalized = " ".join(str(answer or "").split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3].rstrip() + "..."


def _contains_internal_language(answer: str) -> bool:
    lowered = str(answer or "").lower()
    return any(marker in lowered for marker in _INTERNAL_LEAK_MARKERS)


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
            "X-Device-Fingerprint": DEVICE_FINGERPRINT,
        },
        timeout=240,
    )


def _fetch_trace(session: str, turn_index: int) -> dict[str, Any]:
    encoded_session = urllib.parse.quote(session, safe="")
    return _request_json(
        f"{API_BASE}/api/debug/session/{encoded_session}/multiagent-trace?turn_index={turn_index}",
        headers={"X-API-Key": API_KEY},
        timeout=90,
    )


def _selected_reason_map(candidate_scores: list[Any], selected_ids: list[str]) -> dict[str, list[str]]:
    selected = set(selected_ids)
    reason_map: dict[str, list[str]] = {}
    for item in candidate_scores:
        row = _safe_dict(item)
        card_id = str(row.get("card_id", "") or "")
        if not card_id or card_id not in selected:
            continue
        reasons = [str(reason).strip() for reason in _safe_list(row.get("reasons")) if str(reason).strip()]
        reason_map[card_id] = reasons
    return reason_map


def _turn_summary(
    *,
    scenario_id: str,
    scenario_label: str,
    session: str,
    turn_index: int,
    query: str,
    response: dict[str, Any],
    trace: dict[str, Any],
) -> dict[str, Any]:
    answer = str(response.get("answer", "") or "")
    runtime_truth = _safe_dict(trace.get("runtime_truth_trace_v1"))
    grounding = _safe_dict(trace.get("writer_grounding_visibility_v1"))
    payload_trace = _safe_dict(trace.get("writer_kb_payload_trace"))
    semantic_cards = _safe_dict(trace.get("semantic_cards_pilot"))
    retrieval = _safe_dict(trace.get("retrieval_decision"))
    composer = _safe_dict(
        retrieval.get("contextual_retrieval_query_composer") or retrieval.get("composer")
    )
    latest_turn_constraints = _safe_dict(trace.get("latest_turn_constraints_v1"))
    runtime_summary = _safe_dict(trace.get("runtime_trace_summary_v1"))
    candidate_scores = _safe_list(semantic_cards.get("candidate_scores"))
    selected_card_ids = [str(item) for item in _safe_list(semantic_cards.get("selected_card_ids")) if str(item).strip()]
    selected_reason_map = _selected_reason_map(candidate_scores, selected_card_ids)

    return {
        "scenario_id": scenario_id,
        "scenario_label": scenario_label,
        "session": session,
        "turn_index": turn_index,
        "query": query,
        "answer_length": len(answer),
        "answer_preview": _answer_preview(answer),
        "contains_internal_language": _contains_internal_language(answer),
        "retrieval_action": str(retrieval.get("retrieval_action", "") or ""),
        "retrieval_need": str(retrieval.get("retrieval_need", "") or ""),
        "rag_suppressed_reason": str(retrieval.get("rag_suppressed_reason", "") or ""),
        "composer_reason": str(composer.get("reason", "") or ""),
        "composer_evidence": [str(item) for item in _safe_list(composer.get("evidence")) if str(item).strip()],
        "inherited_topic": str(composer.get("inherited_topic", "") or ""),
        "grounding_reason": str(
            runtime_truth.get("grounding_visibility_reason")
            or grounding.get("reason", "")
            or ""
        ),
        "writer_payload_count": int(
            runtime_truth.get("writer_visible_payload_count")
            if runtime_truth.get("writer_visible_payload_count") is not None
            else payload_trace.get("payload_chunk_count", 0)
        ),
        "writer_visible_payload_ids": [
            str(item) for item in _safe_list(runtime_truth.get("writer_visible_payload_ids")) if str(item).strip()
        ],
        "writer_payload_status": str(payload_trace.get("status", "") or ""),
        "writer_payload_primary_path": str(payload_trace.get("primary_path", "") or ""),
        "selected_card_status": str(semantic_cards.get("status", "") or ""),
        "selected_card_count": int(semantic_cards.get("selected_card_count", 0) or 0),
        "selected_card_ids": selected_card_ids,
        "selected_card_reasons": selected_reason_map,
        "selected_knowledge_should_flow": bool(grounding.get("selected_knowledge_should_flow", False)),
        "selected_knowledge_recovery_applied": bool(grounding.get("selected_knowledge_recovery_applied", False)),
        "retrieval_gate_recovery_applied": bool(grounding.get("retrieval_gate_recovery_applied", False)),
        "no_internal_db": bool(grounding.get("no_internal_db", False) or latest_turn_constraints.get("no_internal_db", False)),
        "writer_can_ignore_grounding": bool(grounding.get("writer_may_ignore_grounding", False)),
        "semantic_cards_visible_to_writer": bool(grounding.get("semantic_cards_visible_to_writer", False)),
        "kb_visible_to_writer": bool(grounding.get("kb_visible_to_writer", False)),
        "latest_turn_constraints_v1": latest_turn_constraints,
        "runtime_truth_trace_v1": {
            "writer_visible_payload_count": int(runtime_truth.get("writer_visible_payload_count", 0) or 0),
            "filtered_out_for_writer_count": int(runtime_truth.get("filtered_out_for_writer_count", 0) or 0),
            "retrieved_candidates_count": int(runtime_truth.get("retrieved_candidates_count", 0) or 0),
            "grounding_visibility_reason": str(runtime_truth.get("grounding_visibility_reason", "") or ""),
            "payload_decision_reason": str(runtime_truth.get("payload_decision_reason", "") or ""),
        },
        "runtime_trace_summary_v1": runtime_summary,
    }


def _evaluate_row(row: dict[str, Any]) -> dict[str, Any]:
    scenario_id = str(row.get("scenario_id", "") or "")
    payload = int(row.get("writer_payload_count", 0) or 0)
    leak = bool(row.get("contains_internal_language", False))
    selected_ids = [str(item) for item in _safe_list(row.get("selected_card_ids")) if str(item).strip()]
    grounding_reason = str(row.get("grounding_reason", "") or "")
    retrieval_action = str(row.get("retrieval_action", "") or "")
    no_internal_db = bool(row.get("no_internal_db", False))
    selected_status = str(row.get("selected_card_status", "") or "")
    tags: list[str] = []
    verdict = "PASS"

    if leak:
        verdict = "BLOCKER"
        tags.append("public_internal_language_leak")

    if scenario_id == "S-HF5-1":
        if payload != 0:
            verdict = "BLOCKER"
        if payload != 0:
            tags.append("direct_concept_followup_payload_missing")
        if retrieval_action not in {"suppress_rag", "trace_only"}:
            verdict = "PASS_WITH_WARNING" if verdict == "PASS" else verdict
    elif scenario_id == "S-HF5-2":
        if payload < 1:
            verdict = "BLOCKER"
            tags.append("direct_concept_followup_payload_missing")
    elif scenario_id == "S-HF5-3":
        if "program_imperfect_self_v1" not in selected_ids:
            verdict = "PASS_WITH_WARNING" if verdict == "PASS" else verdict
        if payload < 1:
            verdict = "BLOCKER"
            tags.append("direct_concept_followup_payload_missing")
        if selected_status == "trace_only":
            verdict = "BLOCKER"
            tags.append("selected_knowledge_trace_only")
        if grounding_reason == "no_clear_retrieval_need":
            verdict = "BLOCKER"
            tags.append("no_clear_retrieval_need_over_suppression")
    elif scenario_id == "S-HF5-4":
        if payload < 1 and selected_ids:
            verdict = "BLOCKER"
            tags.append("direct_concept_followup_payload_missing")
        elif payload < 1:
            verdict = "PASS_WITH_WARNING" if verdict == "PASS" else verdict
        if grounding_reason == "no_clear_retrieval_need" and selected_ids:
            verdict = "BLOCKER"
            tags.append("no_clear_retrieval_need_over_suppression")
    elif scenario_id == "S-HF5-5":
        if payload < 1 and selected_ids:
            verdict = "BLOCKER"
            tags.append("direct_concept_followup_payload_missing")
        elif payload < 1 and not grounding_reason:
            verdict = "PASS_WITH_WARNING" if verdict == "PASS" else verdict
    elif scenario_id == "S-HF5-6":
        if not no_internal_db:
            verdict = "BLOCKER"
        if payload != 0 or grounding_reason != "latest_turn_no_internal_db":
            verdict = "BLOCKER"
            tags.append("hard_blocker_valid_suppression")
        else:
            tags.append("no_internal_db_preserved")

    if selected_status == "trace_only" and scenario_id in {"S-HF5-3", "S-HF5-4", "S-HF5-5"}:
        tags.append("selected_knowledge_trace_only")
    if grounding_reason == "no_clear_retrieval_need" and scenario_id in {"S-HF5-3", "S-HF5-4", "S-HF5-5"}:
        tags.append("no_clear_retrieval_need_over_suppression")

    return {
        "verdict": verdict,
        "tags": sorted(set(tags)),
    }


def run_smoke() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_prefix = f"prd-047-36-hf5-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    rows: list[dict[str, Any]] = []

    greeting_session = f"{run_prefix}-greeting"
    greeting_query = "привет!"
    greeting_response = _post_turn(greeting_session, greeting_query)
    time.sleep(0.5)
    greeting_trace = _fetch_trace(greeting_session, 1)
    rows.append(
        _turn_summary(
            scenario_id="S-HF5-1",
            scenario_label="baseline_greeting_should_not_pull_kb",
            session=greeting_session,
            turn_index=1,
            query=greeting_query,
            response=greeting_response,
            trace=greeting_trace,
        )
    )

    concept_session = f"{run_prefix}-concept"
    concept_turns = [
        ("S-HF5-2", "direct_concept_question", "что такое самореализация?"),
        (
            "S-HF5-3",
            "chat12_direct_concept_followup",
            'да мне хочется понять как "программа несовершенное Я" влияет на это',
        ),
        (
            "S-HF5-4",
            "neurostalking_followup",
            "а что об этом говорится в Нейросталкинге?",
        ),
        (
            "S-HF5-5",
            "detailed_modeling_after_grounded_followup",
            "Можешь смоделировать на какой нибудь жизненной ситуации более подробно объяснив каждый нюанс",
        ),
    ]
    for turn_index, (scenario_id, scenario_label, query) in enumerate(concept_turns, start=1):
        response = _post_turn(concept_session, query)
        time.sleep(0.5)
        trace = _fetch_trace(concept_session, turn_index)
        rows.append(
            _turn_summary(
                scenario_id=scenario_id,
                scenario_label=scenario_label,
                session=concept_session,
                turn_index=turn_index,
                query=query,
                response=response,
                trace=trace,
            )
        )

    boundary_session = f"{run_prefix}-boundary"
    boundary_seed = "что такое самореализация?"
    _post_turn(boundary_session, boundary_seed)
    time.sleep(0.5)
    boundary_query = "Ответь без внутренней БД и без Нейросталкинга. Просто по-человечески: как программа несовершенное Я влияет на самореализацию?"
    boundary_response = _post_turn(boundary_session, boundary_query)
    time.sleep(0.5)
    boundary_trace = _fetch_trace(boundary_session, 2)
    rows.append(
        _turn_summary(
            scenario_id="S-HF5-6",
            scenario_label="no_internal_db_boundary_wins",
            session=boundary_session,
            turn_index=2,
            query=boundary_query,
            response=boundary_response,
            trace=boundary_trace,
        )
    )

    verdict_counts = {"PASS": 0, "PASS_WITH_WARNING": 0, "BLOCKER": 0}
    evaluated_rows: list[dict[str, Any]] = []
    for row in rows:
        evaluation = _evaluate_row(row)
        verdict = str(evaluation.get("verdict", "PASS") or "PASS")
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        evaluated_rows.append({**row, **evaluation})
        print(
            f"{row['scenario_id']} payload={row['writer_payload_count']} "
            f"grounding={row['grounding_reason']} selected={row['selected_card_ids']} "
            f"verdict={verdict}"
        )
        sys.stdout.flush()

    overall_verdict = "PASS"
    if verdict_counts.get("BLOCKER", 0):
        overall_verdict = "BLOCKER"
    elif verdict_counts.get("PASS_WITH_WARNING", 0):
        overall_verdict = "PASS_WITH_WARNING"

    return {
        "created_at": datetime.now().isoformat(),
        "backend_health": _health(),
        "overall_verdict": overall_verdict,
        "verdict_counts": verdict_counts,
        "results": evaluated_rows,
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    payload = run_smoke()
    out_path = OUT_DIR / "live_smoke_result.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
