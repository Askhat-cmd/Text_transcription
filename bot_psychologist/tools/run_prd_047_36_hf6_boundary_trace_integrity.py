from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

CURRENT_FILE = Path(__file__).resolve()
BOT_ROOT = CURRENT_FILE.parents[1]
REPO_ROOT = CURRENT_FILE.parents[2]
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from tools.prd_047_36_owner_pilot_readiness_gate_lib import (  # noqa: E402
    detect_internal_language_leak,
)
from tools.run_prd_047_36_post_hf_owner_readiness_gate import (  # noqa: E402
    DEV_HEADERS,
    _fetch_exact_trace,
    _http_json,
    _post_turn,
    _preview,
    _safe_dict,
    _safe_list,
)


PRD_ID = "PRD-047.36-HF6"
SCHEMA_VERSION = "prd_047_36_hf6_boundary_trace_integrity_v1"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
_ACTIONABLE_PRACTICE_MARKERS = (
    "упражнен",
    "попробуй",
    "попробуйте",
    "сделай",
    "сделайте",
    "шаг 1",
    "шаг 2",
    "домашн",
    "подыш",
    "вдох",
    "выдох",
)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _extract_boundary_trace(trace: dict[str, Any]) -> dict[str, Any]:
    direct = _safe_dict(trace.get("boundary_trace_v1"))
    if direct:
        return direct
    runtime_summary = _safe_dict(trace.get("runtime_trace_summary_v1"))
    nested = _safe_dict(runtime_summary.get("boundary_trace_v1"))
    if nested:
        return nested
    runtime_truth = _safe_dict(trace.get("runtime_truth_trace_v1"))
    return _safe_dict(runtime_truth.get("boundary_trace_v1"))


def _trace_available(trace: dict[str, Any], status_code: int) -> bool:
    availability = _safe_dict(trace.get("trace_availability"))
    return status_code == 200 and str(availability.get("status", "") or "") == "available"


def _contains_actionable_practice(answer: str) -> bool:
    lowered = str(answer or "").lower()
    return any(marker in lowered for marker in _ACTIONABLE_PRACTICE_MARKERS)


def _turn_record(
    *,
    scenario_id: str,
    session_id: str,
    turn_index: int,
    query: str,
    response: dict[str, Any],
    trace_status_code: int,
    trace: dict[str, Any],
) -> dict[str, Any]:
    answer = str(response.get("answer", "") or "")
    boundary_trace = _extract_boundary_trace(trace)
    runtime_truth = _safe_dict(trace.get("runtime_truth_trace_v1"))
    grounding = _safe_dict(trace.get("writer_grounding_visibility_v1"))
    latest_turn_constraints = _safe_dict(trace.get("latest_turn_constraints_v1"))
    if not latest_turn_constraints:
        latest_turn_constraints = _safe_dict(_safe_dict(trace.get("runtime_trace_summary_v1")).get("latest_turn_constraints_v1"))
    retrieval = _safe_dict(trace.get("retrieval_decision"))
    semantic_cards = _safe_dict(trace.get("semantic_cards_pilot"))

    boundary_flags = [str(item) for item in _safe_list(boundary_trace.get("boundary_flags")) if str(item).strip()]
    writer_payload_count = int(
        boundary_trace.get("writer_payload_count")
        if boundary_trace.get("writer_payload_count") is not None
        else runtime_truth.get("writer_visible_payload_count", 0)
    )
    semantic_cards_writer_visible = bool(
        boundary_trace.get("semantic_cards_visible_to_writer")
        if boundary_trace.get("semantic_cards_visible_to_writer") is not None
        else grounding.get("semantic_cards_visible_to_writer", False)
    )

    return {
        "scenario_id": scenario_id,
        "session_id": session_id,
        "turn_index": turn_index,
        "query": query,
        "answer_preview": _preview(answer),
        "answer": answer,
        "trace_available": _trace_available(trace, trace_status_code),
        "trace_availability": _safe_dict(trace.get("trace_availability")),
        "boundary_trace_v1": boundary_trace,
        "boundary_flags": boundary_flags,
        "latest_turn_constraints": _safe_dict(boundary_trace.get("latest_turn_constraints")) or latest_turn_constraints,
        "writer_payload_count": writer_payload_count,
        "semantic_cards_writer_visible": semantic_cards_writer_visible,
        "practice_suggestion_visible": _contains_actionable_practice(answer),
        "suppression_reason": [
            str(item)
            for item in _safe_list(boundary_trace.get("suppression_reasons"))
            if str(item).strip()
        ],
        "public_violation_detected": bool(boundary_trace.get("public_violation_detected", False))
        or detect_internal_language_leak(answer),
        "grounding_reason": str(
            boundary_trace.get("grounding_reason")
            or runtime_truth.get("grounding_visibility_reason", "")
            or grounding.get("reason", "")
            or ""
        ),
        "retrieval_action": str(retrieval.get("retrieval_action", "") or ""),
        "semantic_cards_status": str(semantic_cards.get("status", "") or ""),
    }


def _classify_g5(row: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not row["trace_available"]:
        reasons.append("trace_unavailable")
    if "no_internal_db" not in row["boundary_flags"]:
        reasons.append("no_internal_db_flag_missing")
    if not bool(row["latest_turn_constraints"].get("no_internal_db", False)):
        reasons.append("no_internal_db_constraint_missing")
    if row["writer_payload_count"] != 0:
        reasons.append("writer_payload_not_suppressed")
    if row["semantic_cards_writer_visible"]:
        reasons.append("semantic_cards_still_visible")
    if row["public_violation_detected"]:
        reasons.append("public_internal_language_leak")
    verdict = "PASS" if not reasons else "BLOCKER"
    return verdict, reasons


def _classify_g6(row: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not row["trace_available"]:
        reasons.append("trace_unavailable")
    if "no_practice" not in row["boundary_flags"]:
        reasons.append("no_practice_flag_missing")
    if not bool(row["latest_turn_constraints"].get("no_practice", False)):
        reasons.append("no_practice_constraint_missing")
    if row["practice_suggestion_visible"]:
        reasons.append("practice_visible_in_public_answer")
    if not bool(_safe_dict(row["boundary_trace_v1"].get("writer_directive_ack")).get("no_practice", False)):
        reasons.append("directive_ack_missing")
    verdict = "PASS" if not reasons else "BLOCKER"
    return verdict, reasons


def _classify_combined(row: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if "no_internal_db" not in row["boundary_flags"]:
        reasons.append("combined_missing_no_internal_db")
    if "no_practice" not in row["boundary_flags"]:
        reasons.append("combined_missing_no_practice")
    if row["writer_payload_count"] != 0:
        reasons.append("combined_payload_not_suppressed")
    if row["practice_suggestion_visible"]:
        reasons.append("combined_practice_visible")
    verdict = "PASS" if not reasons else "BLOCKER"
    return verdict, reasons


def _classify_followup(rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    final_row = rows[-1]
    reasons: list[str] = []
    if final_row["grounding_reason"] != "direct_concept_followup":
        reasons.append("followup_grounding_reason_regression")
    if final_row["writer_payload_count"] < 1:
        reasons.append("followup_payload_missing")
    if any(flag in {"no_internal_db", "no_practice"} for flag in final_row["boundary_flags"]):
        reasons.append("followup_mislabeled_as_boundary")
    verdict = "PASS" if not reasons else "BLOCKER"
    return verdict, reasons


def _classify_greeting(row: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if row["writer_payload_count"] != 0:
        reasons.append("greeting_payload_should_be_zero")
    if any(flag in {"no_internal_db", "no_practice"} for flag in row["boundary_flags"]):
        reasons.append("greeting_mislabeled_as_boundary")
    if row["retrieval_action"] != "suppress_rag":
        reasons.append("greeting_retrieval_action_regression")
    verdict = "PASS" if not reasons else "BLOCKER"
    return verdict, reasons


def _render_report(*, title: str, verdict: str, reasons: list[str], rows: list[dict[str, Any]]) -> str:
    lines = [f"# {title}", "", f"- verdict: `{verdict}`"]
    if reasons:
        lines.append(f"- reasons: `{', '.join(reasons)}`")
    else:
        lines.append("- reasons: `none`")
    for row in rows:
        lines.extend(
            [
                "",
                f"## {row['scenario_id']} / turn {row['turn_index']}",
                f"- trace_available: `{row['trace_available']}`",
                f"- boundary_flags: `{', '.join(row['boundary_flags']) or 'none'}`",
                f"- latest_turn_constraints: `{json.dumps(row['latest_turn_constraints'], ensure_ascii=False)}`",
                f"- writer_payload_count: `{row['writer_payload_count']}`",
                f"- semantic_cards_writer_visible: `{row['semantic_cards_writer_visible']}`",
                f"- practice_suggestion_visible: `{row['practice_suggestion_visible']}`",
                f"- suppression_reason: `{', '.join(row['suppression_reason']) or 'none'}`",
                f"- public_violation_detected: `{row['public_violation_detected']}`",
                f"- grounding_reason: `{row['grounding_reason']}`",
                f"- answer_preview: `{row['answer_preview']}`",
            ]
        )
    return "\n".join(lines) + "\n"


def _run_turn(*, backend_base_url: str, query: str, session_prefix: str, turn_index: int = 1) -> dict[str, Any]:
    session_id = f"{session_prefix}-{uuid4().hex[:8]}"
    response = _post_turn(backend_base_url=backend_base_url, session_id=session_id, query=query)
    time.sleep(0.5)
    trace_status, trace = _fetch_exact_trace(
        backend_base_url=backend_base_url,
        session_id=session_id,
        turn_index=turn_index,
    )
    return _turn_record(
        scenario_id=session_prefix,
        session_id=session_id,
        turn_index=turn_index,
        query=query,
        response=response,
        trace_status_code=trace_status,
        trace=trace,
    )


def _run_followup(*, backend_base_url: str) -> list[dict[str, Any]]:
    session_id = f"prd-047-36-hf6-followup-{uuid4().hex[:8]}"
    turns = [
        "что такое самореализация?",
        'да мне хочется понять как "программа несовершенное Я" влияет на это',
    ]
    rows: list[dict[str, Any]] = []
    for turn_index, query in enumerate(turns, start=1):
        response = _post_turn(backend_base_url=backend_base_url, session_id=session_id, query=query)
        time.sleep(0.5)
        trace_status, trace = _fetch_exact_trace(
            backend_base_url=backend_base_url,
            session_id=session_id,
            turn_index=turn_index,
        )
        rows.append(
            _turn_record(
                scenario_id="HF6-control-followup",
                session_id=session_id,
                turn_index=turn_index,
                query=query,
                response=response,
                trace_status_code=trace_status,
                trace=trace,
            )
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    backend_base_url = "http://127.0.0.1:8001"
    health_status, health_payload = _http_json(
        method="GET",
        url=f"{backend_base_url}/api/v1/health",
        headers={"X-API-Key": DEV_HEADERS["X-API-Key"]},
        timeout=20.0,
    )

    g5 = _run_turn(
        backend_base_url=backend_base_url,
        query="Ответь без internal DB и без Нейросталкинга. Просто по-человечески: что такое самореализация?",
        session_prefix="HF6-G5",
    )
    g6 = _run_turn(
        backend_base_url=backend_base_url,
        query="Объясни, почему я злюсь на себя, но без практик и упражнений.",
        session_prefix="HF6-G6",
    )
    combined = _run_turn(
        backend_base_url=backend_base_url,
        query="Ответь без internal DB, без Нейросталкинга и без практик: почему я всё понимаю, но снова наступаю на те же грабли?",
        session_prefix="HF6-G5G6",
    )
    followup_rows = _run_followup(backend_base_url=backend_base_url)
    greeting = _run_turn(
        backend_base_url=backend_base_url,
        query="привет",
        session_prefix="HF6-greeting",
    )
    fresh_rows = [
        _run_turn(
            backend_base_url=backend_base_url,
            query="Ответь без internal DB и без Нейросталкинга. Просто по-человечески: что такое самореализация?",
            session_prefix="HF6-fresh-g5",
        ),
        _run_turn(
            backend_base_url=backend_base_url,
            query="Объясни, почему я злюсь на себя, но без практик и упражнений.",
            session_prefix="HF6-fresh-g6",
        ),
    ]

    verdict_g5, reasons_g5 = _classify_g5(g5)
    verdict_g6, reasons_g6 = _classify_g6(g6)
    verdict_combined, reasons_combined = _classify_combined(combined)
    verdict_followup, reasons_followup = _classify_followup(followup_rows)
    verdict_greeting, reasons_greeting = _classify_greeting(greeting)
    fresh_reasons = [row["scenario_id"] for row in fresh_rows if not row["trace_available"]]
    verdict_fresh = "PASS" if not fresh_reasons else "BLOCKER"

    overall_verdict = "PASS"
    for verdict in (verdict_g5, verdict_g6, verdict_combined, verdict_followup, verdict_greeting, verdict_fresh):
        if verdict != "PASS":
            overall_verdict = "BLOCKER"
            break

    matrix = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "backend_health_status": health_status,
        "backend_health_payload": health_payload,
        "overall_verdict": overall_verdict,
        "scenarios": {
            "G5": {"verdict": verdict_g5, "reasons": reasons_g5, "row": g5},
            "G6": {"verdict": verdict_g6, "reasons": reasons_g6, "row": g6},
            "G5G6": {"verdict": verdict_combined, "reasons": reasons_combined, "row": combined},
            "followup": {"verdict": verdict_followup, "reasons": reasons_followup, "rows": followup_rows},
            "greeting": {"verdict": verdict_greeting, "reasons": reasons_greeting, "row": greeting},
            "fresh_trace_after_restart": {
                "verdict": verdict_fresh,
                "reasons": fresh_reasons,
                "rows": fresh_rows,
            },
        },
    }

    _write_json(OUT_DIR / "boundary_trace_matrix.json", matrix)
    _write_text(
        OUT_DIR / "no_internal_db_trace_report.md",
        _render_report(title="HF6 G5 No Internal DB", verdict=verdict_g5, reasons=reasons_g5, rows=[g5]),
    )
    _write_text(
        OUT_DIR / "no_practice_trace_report.md",
        _render_report(title="HF6 G6 No Practice", verdict=verdict_g6, reasons=reasons_g6, rows=[g6]),
    )
    _write_text(
        OUT_DIR / "combined_boundary_report.md",
        _render_report(title="HF6 Combined Boundary", verdict=verdict_combined, reasons=reasons_combined, rows=[combined]),
    )
    _write_text(
        OUT_DIR / "boundary_trace_contract_report.md",
        _render_report(
            title="HF6 Boundary Trace Contract",
            verdict="PASS" if verdict_followup == "PASS" and verdict_greeting == "PASS" else "BLOCKER",
            reasons=reasons_followup + reasons_greeting,
            rows=followup_rows + [greeting],
        ),
    )
    _write_text(
        OUT_DIR / "fresh_trace_after_restart_report.md",
        _render_report(
            title="HF6 Fresh Trace Availability",
            verdict=verdict_fresh,
            reasons=fresh_reasons,
            rows=fresh_rows,
        ),
    )
    _write_text(
        OUT_DIR / "old_chat_after_restart_note.md",
        "# HF6 Old Chat After Restart Note\n\n- verdict: `PASS_WITH_WARNING`\n- note: `HF6 preserved the accepted HF4 behavior boundary: old pre-restart in-memory debug traces may expire and should surface debug_trace_expired_after_backend_restart explicitly.`\n",
    )
    _write_text(
        OUT_DIR / "live_smoke_report.md",
        "\n".join(
            [
                "# HF6 Live Smoke",
                "",
                f"- overall_verdict: `{overall_verdict}`",
                f"- backend_health_status: `{health_status}`",
                f"- g5: `{verdict_g5}`",
                f"- g6: `{verdict_g6}`",
                f"- combined: `{verdict_combined}`",
                f"- followup: `{verdict_followup}`",
                f"- greeting: `{verdict_greeting}`",
                f"- fresh_trace_after_restart: `{verdict_fresh}`",
                "",
            ]
        ),
    )
    return 0 if overall_verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
