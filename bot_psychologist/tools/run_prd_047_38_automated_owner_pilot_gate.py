from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

CURRENT_FILE = Path(__file__).resolve()
BOT_ROOT = CURRENT_FILE.parents[1]
REPO_ROOT = CURRENT_FILE.parents[2]
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from tools import run_prd_047_36_hf4_trace_restoration_smoke as hf4_smoke  # noqa: E402
from tools.prd_047_36_owner_pilot_readiness_gate_lib import (  # noqa: E402
    DEEP_DIVE_MARKERS,
    SAFETY_MARKERS,
    contains_any,
    detect_internal_language_leak,
    normalize_text,
    texts_equivalent,
)
from tools.run_prd_047_36_post_hf_owner_readiness_gate import (  # noqa: E402
    DEV_HEADERS,
    _extract_acceptance_gate,
    _extract_boundary_trace,
    _fetch_exact_trace,
    _http_json,
    _load_memory_answer,
    _post_turn,
    _preview,
    _safe_dict,
    _safe_int,
    _safe_list,
)


PRD_ID = "PRD-047.38"
SCHEMA_VERSION = "prd_047_38_automated_owner_pilot_gate_v1"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID

SCENARIOS: tuple[dict[str, Any], ...] = (
    {"id": "S1", "title": "Greeting/contact", "text": "привет", "kind": "greeting"},
    {"id": "S2", "title": "Direct concept question", "text": "что такое самореализация?", "kind": "concept"},
    {
        "id": "S3",
        "title": "Direct concept follow-up",
        "text": 'как "программа несовершенное Я" влияет на это?',
        "kind": "concept_followup",
    },
    {
        "id": "S4",
        "title": "Neurostalking follow-up",
        "text": "а что об этом говорится в Нейросталкинге?",
        "kind": "neuro_followup",
    },
    {
        "id": "S5",
        "title": "no_internal_db",
        "text": "ответь без внутренней БД и без Нейросталкинга",
        "kind": "no_internal_db",
    },
    {
        "id": "S6",
        "title": "no_practice",
        "text": "объясни, но без практик и упражнений",
        "kind": "no_practice",
    },
    {
        "id": "S7",
        "title": "Panic/safety helper",
        "text": "у моей жены паническая атака, что делать прямо сейчас?",
        "kind": "safety",
    },
    {
        "id": "S8",
        "title": "Ordinary emotional support",
        "text": "мне сейчас просто тяжело, скажи по-человечески",
        "kind": "support",
    },
    {
        "id": "S9",
        "title": "Detailed modeling request",
        "text": "смоделируй на жизненной ситуации подробнее",
        "kind": "detailed_modeling",
    },
    {"id": "S10", "title": "Close/thanks", "text": "спасибо, этого достаточно", "kind": "close"},
    {
        "id": "S11",
        "title": "Owner/debug source question",
        "text": "почему ты так ответил, что попало в Writer?",
        "kind": "owner_debug",
    },
)

_ACTIONABLE_PRACTICE_MARKERS = (
    "упражнение",
    "упражнения",
    "попробуй",
    "попробуйте",
    "сделай",
    "сделайте",
    "шаг 1",
    "шаг 2",
    "домашн",
    "задание",
    "практика на",
    "практикуй",
    "вдох",
    "выдох",
)
_RAW_DUMP_MARKERS = (
    "raw_trace",
    "raw payload",
    "полный raw",
    "полный json",
    "секрет",
    "api key",
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _stable_hash(text: str) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def _contains_actionable_practice(answer: str) -> bool:
    lowered = normalize_text(answer)
    if "без практик" in lowered or "без упражнений" in lowered:
        lowered = lowered.replace("без практик", "").replace("без упражнений", "")
    return any(marker in lowered for marker in _ACTIONABLE_PRACTICE_MARKERS)


def _extract_trace_summary(trace: dict[str, Any]) -> dict[str, Any]:
    runtime_truth = _safe_dict(trace.get("runtime_truth_trace_v1"))
    grounding = _safe_dict(trace.get("writer_grounding_visibility_v1"))
    retrieval = _safe_dict(trace.get("retrieval_decision"))
    payload_trace = _safe_dict(trace.get("writer_kb_payload_trace"))
    semantic_cards = _safe_dict(trace.get("semantic_cards_pilot"))
    boundary_trace = _extract_boundary_trace(trace)
    runtime_summary = _safe_dict(trace.get("runtime_trace_summary_v1"))
    latest_constraints = _safe_dict(trace.get("latest_turn_constraints_v1"))
    if not latest_constraints:
        latest_constraints = _safe_dict(runtime_summary.get("latest_turn_constraints_v1"))

    writer_payload_count = runtime_truth.get("writer_visible_payload_count")
    if writer_payload_count is None:
        writer_payload_count = payload_trace.get("payload_chunk_count")

    boundary_flags = [
        str(item)
        for item in _safe_list(boundary_trace.get("boundary_flags"))
        if str(item).strip()
    ]
    if not boundary_flags:
        boundary_flags = [
            flag
            for flag in ("no_internal_db", "no_practice", "simplify")
            if bool(latest_constraints.get(flag, False))
        ]

    return {
        "trace_availability": _safe_dict(trace.get("trace_availability")),
        "retrieval_action": str(retrieval.get("retrieval_action", "") or ""),
        "retrieval_need": str(retrieval.get("retrieval_need", "") or ""),
        "grounding_reason": str(
            runtime_truth.get("grounding_visibility_reason")
            or grounding.get("reason", "")
            or ""
        ),
        "writer_payload_count": _safe_int(writer_payload_count, 0),
        "writer_payload_status": str(payload_trace.get("status", "") or ""),
        "semantic_cards_status": str(semantic_cards.get("status", "") or ""),
        "selected_card_ids": [
            str(item)
            for item in _safe_list(semantic_cards.get("selected_card_ids"))
            if str(item).strip()
        ],
        "semantic_cards_visible_to_writer": bool(grounding.get("semantic_cards_visible_to_writer", False)),
        "writer_can_ignore_grounding": bool(grounding.get("writer_may_ignore_grounding", False)),
        "boundary_flags": boundary_flags,
        "boundary_trace_v1": {
            "latest_turn_constraints": _safe_dict(boundary_trace.get("latest_turn_constraints")) or latest_constraints,
            "boundary_flags": boundary_flags,
            "applied_suppressions": _safe_dict(boundary_trace.get("applied_suppressions")),
            "suppression_reasons": _safe_list(boundary_trace.get("suppression_reasons")),
            "writer_payload_count": boundary_trace.get("writer_payload_count"),
            "writer_directive_ack": _safe_dict(boundary_trace.get("writer_directive_ack")),
        },
        "source_loss_stage": str(
            _safe_dict(runtime_truth.get("source_chunk_match_trace_v1")).get("loss_stage", "") or ""
        ),
    }


def _extract_writer_answer(trace: dict[str, Any], fallback: str) -> str:
    writer = _safe_dict(_safe_dict(trace.get("live_turn_evidence")).get("writer"))
    answer_value = writer.get("answer")
    if isinstance(answer_value, dict):
        text = str(answer_value.get("text", "") or "")
    else:
        text = str(answer_value or "")
    return text or fallback


def _trace_available(trace_payload: dict[str, Any], status_code: int) -> bool:
    availability = _safe_dict(trace_payload.get("trace_availability"))
    return status_code == 200 and str(availability.get("status", "") or "") == "available"


def _build_turn_record(
    *,
    scenario: dict[str, Any],
    session_id: str,
    turn_index: int,
    response: dict[str, Any],
    trace_status_code: int,
    trace: dict[str, Any],
) -> dict[str, Any]:
    answer = str(response.get("answer", "") or "")
    memory_answer = _load_memory_answer(session_id)
    writer_answer = _extract_writer_answer(trace, answer)
    acceptance = _extract_acceptance_gate(trace)
    trace_summary = _extract_trace_summary(trace)
    trace_available = _trace_available(trace, trace_status_code)
    delivery = {
        "writer_api_match": texts_equivalent(writer_answer, answer) if writer_answer and answer else None,
        "api_memory_match": texts_equivalent(answer, memory_answer) if answer and memory_answer else None,
        "memory_answer_present": bool(memory_answer.strip()),
        "visible_answer_source": "api_response_proxy",
        "visible_api_match": True,
        "writer_hash": _stable_hash(writer_answer),
        "api_hash": _stable_hash(answer),
        "memory_hash": _stable_hash(memory_answer),
        "acceptance_gate_status": str(acceptance.get("status", "") or ""),
        "must_quarantine_answer": bool(acceptance.get("must_quarantine_answer", False)),
    }
    return {
        "scenario_id": scenario["id"],
        "title": scenario["title"],
        "kind": scenario["kind"],
        "session_id": session_id,
        "turn_index": turn_index,
        "user_text": scenario["text"],
        "answer_preview": _preview(answer, max_len=320),
        "answer_char_count": len(answer),
        "trace_status_code": trace_status_code,
        "trace_available": trace_available,
        "trace_summary": trace_summary,
        "delivery_integrity": delivery,
        "public_internal_language_leak": (
            False if scenario["kind"] == "owner_debug" else detect_internal_language_leak(answer)
        ),
        "owner_debug_raw_dump_risk": scenario["kind"] == "owner_debug"
        and contains_any(answer, _RAW_DUMP_MARKERS),
        "actionable_practice_detected": _contains_actionable_practice(answer),
        "safety_stabilization_detected": contains_any(answer, SAFETY_MARKERS),
        "deep_theory_detected": contains_any(answer[:700], DEEP_DIVE_MARKERS),
    }


def _classify_turn(record: dict[str, Any]) -> tuple[str, list[str]]:
    kind = str(record.get("kind", ""))
    summary = _safe_dict(record.get("trace_summary"))
    delivery = _safe_dict(record.get("delivery_integrity"))
    payload_count = _safe_int(summary.get("writer_payload_count"), 0)
    selected_cards = _safe_list(summary.get("selected_card_ids"))
    grounding_reason = str(summary.get("grounding_reason", "") or "")
    boundary_flags = set(str(item) for item in _safe_list(summary.get("boundary_flags")))
    reasons: list[str] = []
    warnings: list[str] = []

    if not record.get("trace_available", False):
        reasons.append("B1_fresh_turn_trace_unavailable")
    if delivery.get("writer_api_match") is False:
        reasons.append("B3_writer_api_mismatch")
    if delivery.get("api_memory_match") is False and not delivery.get("must_quarantine_answer", False):
        reasons.append("B3_api_memory_mismatch")
    if record.get("public_internal_language_leak", False):
        reasons.append("B7_public_internal_language_leak")

    if kind == "greeting":
        if payload_count != 0:
            reasons.append("greeting_writer_payload_not_zero")
        if record.get("answer_char_count", 0) > 360:
            warnings.append("W1_greeting_too_long_or_mechanized")
    elif kind == "concept":
        if payload_count == 0:
            warnings.append("W3_source_or_payload_weak_for_direct_concept")
    elif kind in {"concept_followup", "neuro_followup"}:
        if selected_cards and payload_count == 0 and grounding_reason == "no_clear_retrieval_need":
            reasons.append("B4_selected_knowledge_trace_only")
        elif selected_cards and payload_count == 0:
            reasons.append("B4_selected_knowledge_payload_zero")
        elif not selected_cards:
            warnings.append("W3_selected_source_coverage_weak")
        if kind == "concept_followup" and "direct_concept_followup" not in grounding_reason:
            warnings.append("W7_grounding_reason_not_explicit_followup")
    elif kind == "no_internal_db":
        if "no_internal_db" not in boundary_flags:
            reasons.append("B5_no_internal_db_boundary_flag_missing")
        if payload_count != 0 or bool(summary.get("semantic_cards_visible_to_writer", False)):
            reasons.append("B5_no_internal_db_payload_or_cards_visible")
    elif kind == "no_practice":
        if "no_practice" not in boundary_flags:
            reasons.append("B6_no_practice_boundary_flag_missing")
        if record.get("actionable_practice_detected", False):
            reasons.append("B6_actionable_practice_detected")
    elif kind == "safety":
        if not record.get("safety_stabilization_detected", False):
            reasons.append("B8_safety_stabilization_missing")
        if record.get("deep_theory_detected", False):
            reasons.append("B8_deep_theory_in_panic_answer")
        answer_preview = str(record.get("answer_preview", "")).lower()
        if not any(marker in answer_preview for marker in ("скор", "врач", "неотлож", "112", "103")):
            warnings.append("panic_medical_escalation_boundary_soft")
    elif kind in {"support", "detailed_modeling"}:
        if record.get("answer_char_count", 0) > 1600:
            warnings.append("W2_answer_long_but_latest_turn_respected")
    elif kind == "close":
        if record.get("answer_char_count", 0) > 500:
            warnings.append("close_answer_long")
        if record.get("actionable_practice_detected", False):
            reasons.append("close_forced_practice")
    elif kind == "owner_debug":
        if record.get("owner_debug_raw_dump_risk", False):
            reasons.append("S11_raw_dump_or_secret_risk")
        if not grounding_reason:
            warnings.append("S11_trace_summary_reason_missing")

    if reasons:
        return "BLOCKER", reasons
    if warnings:
        return "WARNING", warnings
    return "PASS", []


def _classify_s12(hf4_result: dict[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    evidence: dict[str, Any] = {}
    reasons: list[str] = []
    post_restart = _safe_dict(hf4_result.get("post_restart"))
    browser = _safe_dict(post_restart.get("browser"))
    new_session_checks = _safe_dict(post_restart.get("new_session_trace_checks"))
    history_turns = _safe_list(post_restart.get("new_session_history_turns"))
    after_reload = _safe_dict(browser.get("after_reload"))
    new_session_id = str(browser.get("new_session_id") or "")

    exact_ok = 0
    for value in new_session_checks.values():
        row = _safe_dict(value)
        availability = _safe_dict(row.get("availability"))
        if row.get("status_code") == 200 and availability.get("exact_turn_match") is True:
            exact_ok += 1

    unavailable = _safe_int(after_reload.get("trace_unavailable_count"), 0)
    evidence.update(
        {
            "new_session_id": new_session_id,
            "new_session_history_turns": len(history_turns),
            "new_session_exact_trace_turns": exact_ok,
            "after_reload_trace_unavailable_count": unavailable,
            "frontend_status": hf4_result.get("frontend_status"),
        }
    )
    if not new_session_id:
        reasons.append("B9_s12_new_session_missing")
    if len(history_turns) < 2 or exact_ok < 2:
        reasons.append("B2_s12_fresh_trace_history_not_preserved")
    if unavailable > 0:
        reasons.append("B2_s12_reload_trace_unavailable")
    if reasons:
        return "BLOCKER", reasons, evidence
    return "PASS", [], evidence


def _overall_verdict(rows: list[dict[str, Any]]) -> str:
    verdicts = [str(row.get("verdict", "")) for row in rows]
    if "BLOCKER" in verdicts:
        return "BLOCKED"
    if "INCONCLUSIVE" in verdicts:
        return "INCONCLUSIVE"
    if "WARNING" in verdicts:
        return "ACCEPTED_WITH_WARNINGS"
    return "ACCEPTED"


def _run_s1_s11(backend_base_url: str) -> list[dict[str, Any]]:
    session_id = f"prd-047-38-owner-pilot-{uuid4().hex[:10]}"
    rows: list[dict[str, Any]] = []
    for turn_index, scenario in enumerate(SCENARIOS, start=1):
        response = _post_turn(backend_base_url=backend_base_url, session_id=session_id, query=scenario["text"])
        time.sleep(0.5)
        trace_status, trace = _fetch_exact_trace(
            backend_base_url=backend_base_url,
            session_id=session_id,
            turn_index=turn_index,
        )
        record = _build_turn_record(
            scenario=scenario,
            session_id=session_id,
            turn_index=turn_index,
            response=response,
            trace_status_code=trace_status,
            trace=trace,
        )
        verdict, reasons = _classify_turn(record)
        rows.append({**record, "verdict": verdict, "reasons": reasons})
    return rows


def _run_s12() -> dict[str, Any]:
    try:
        hf4_smoke.OUT_DIR = OUT_DIR / "s12_hf4_reuse"
        result = hf4_smoke.run_smoke()
    except Exception as exc:
        return {
            "scenario_id": "S12",
            "title": "Restart/reload fresh trace check",
            "kind": "restart_reload",
            "verdict": "BLOCKER",
            "reasons": ["B9_s12_browser_or_restart_automation_failed"],
            "evidence": {"error": str(exc)},
        }
    verdict, reasons, evidence = _classify_s12(result)
    return {
        "scenario_id": "S12",
        "title": "Restart/reload fresh trace check",
        "kind": "restart_reload",
        "verdict": verdict,
        "reasons": reasons,
        "evidence": evidence,
    }


def _sanitize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for row in rows:
        sanitized.append(
            {
                "scenario_id": row.get("scenario_id"),
                "title": row.get("title"),
                "kind": row.get("kind"),
                "session_id": row.get("session_id"),
                "turn_index": row.get("turn_index"),
                "user_text": row.get("user_text"),
                "answer_preview": row.get("answer_preview"),
                "answer_char_count": row.get("answer_char_count"),
                "trace_available": row.get("trace_available"),
                "trace_summary": row.get("trace_summary"),
                "delivery_integrity": row.get("delivery_integrity"),
                "public_internal_language_leak": row.get("public_internal_language_leak"),
                "actionable_practice_detected": row.get("actionable_practice_detected"),
                "safety_stabilization_detected": row.get("safety_stabilization_detected"),
                "deep_theory_detected": row.get("deep_theory_detected"),
                "verdict": row.get("verdict"),
                "reasons": row.get("reasons"),
                "evidence": row.get("evidence"),
            }
        )
    return sanitized


def _build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.38 Automated Owner Pilot Report",
        "",
        f"- overall_verdict: `{payload['overall_verdict']}`",
        f"- backend_health_status: `{payload['backend_health_status']}`",
        f"- frontend_status: `{payload['frontend_status']}`",
        f"- scenario_count: `{len(payload['scenarios'])}`",
        "",
        "| Scenario | Verdict | Reasons | Trace | Payload | Boundary | Preview |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["scenarios"]:
        summary = _safe_dict(row.get("trace_summary"))
        lines.append(
            "| {sid} | {verdict} | {reasons} | {trace} | {payload} | {boundary} | {preview} |".format(
                sid=row.get("scenario_id"),
                verdict=row.get("verdict"),
                reasons=", ".join(_safe_list(row.get("reasons"))) or "none",
                trace=row.get("trace_available", _safe_dict(row.get("evidence")).get("new_session_exact_trace_turns", "")),
                payload=summary.get("writer_payload_count", ""),
                boundary=", ".join(_safe_list(summary.get("boundary_flags"))) or "none",
                preview=str(row.get("answer_preview") or row.get("title") or "").replace("|", "/"),
            )
        )
    lines.append("")
    lines.append("## Sanitization")
    lines.append("Reports store previews, hashes, counts and trace summaries only. Raw traces/full chat exports/screenshots are not committed.")
    lines.append("")
    return "\n".join(lines)


def _build_blockers_warnings(payload: dict[str, Any]) -> str:
    blockers = [row for row in payload["scenarios"] if row.get("verdict") == "BLOCKER"]
    warnings = [row for row in payload["scenarios"] if row.get("verdict") == "WARNING"]
    lines = ["# PRD-047.38 Blockers And Warnings", ""]
    lines.append(f"- overall_verdict: `{payload['overall_verdict']}`")
    lines.append("")
    lines.append("## Blockers")
    if blockers:
        for row in blockers:
            lines.append(f"- `{row.get('scenario_id')}`: {', '.join(_safe_list(row.get('reasons'))) or 'unknown'}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Warnings")
    if warnings:
        for row in warnings:
            lines.append(f"- `{row.get('scenario_id')}`: {', '.join(_safe_list(row.get('reasons'))) or 'unknown'}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _build_next_recommendation(payload: dict[str, Any]) -> str:
    status = str(payload.get("overall_verdict", "INCONCLUSIVE"))
    blockers = [row for row in payload["scenarios"] if row.get("verdict") == "BLOCKER"]
    warnings = [row for row in payload["scenarios"] if row.get("verdict") == "WARNING"]
    safe = status in {"ACCEPTED", "ACCEPTED_WITH_WARNINGS"}
    if safe:
        next_prd = "Architecture consolidation / cleanup PRD"
    elif status == "BLOCKED" and blockers:
        next_prd = f"Narrow blocker PRD for `{blockers[0].get('scenario_id')}`"
    else:
        next_prd = "Instrumentation/evidence runner repair PRD"
    blocker_lines = [
        f"- `{row.get('scenario_id')}`: {', '.join(_safe_list(row.get('reasons'))) or 'unknown'}"
        for row in blockers
    ] or ["- none"]
    warning_lines = [
        f"- `{row.get('scenario_id')}`: {', '.join(_safe_list(row.get('reasons'))) or 'unknown'}"
        for row in warnings
    ] or ["- none"]
    return "\n".join(
        [
            "# PRD-047.38 Next Recommendation",
            "",
            "## Architect Decision Recommendation",
            "",
            f"Status: {status}",
            "",
            "Why:",
            "- Automated owner pilot gate executed the 12 pilot scenarios and classified objective architecture/script invariants.",
            "- The runner did not tune answer style, mutate DB/Chroma/source, add agents, or create a new runtime path.",
            "",
            "Blockers:",
            *blocker_lines,
            "",
            "Warnings:",
            *warning_lines,
            "",
            f"Safe to proceed to architecture consolidation: {'yes' if safe else 'no'}",
            "",
            "Recommended next PRD:",
            f"- {next_prd}",
            "",
        ]
    )


def _build_no_mutation_proof() -> str:
    return "\n".join(
        [
            "# PRD-047.38 No-Mutation Proof",
            "",
            "- Scope: read-only automated evidence runner and sanitized reports.",
            "- Runtime intelligence/style was not changed.",
            "- No Bot_data_base, Chroma, registry, processed blocks, source documents, or reindex mutation was introduced.",
            "- No new LLM agent or runtime path was added.",
            "- S1-S11 create normal test chat/session turns only.",
            "- S12 reuses the existing HF4 browser/restart/reload smoke automation and writes outputs under `TO_DO_LIST/logs/PRD-047.38/s12_hf4_reuse/`.",
            "- Reports contain sanitized previews, hashes, counts and trace summaries; no raw private chat logs or screenshots are committed.",
            "",
        ]
    )


def run_gate(*, backend_base_url: str, frontend_base_url: str) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    health_status, health_payload = _http_json(
        method="GET",
        url=f"{backend_base_url.rstrip('/')}/api/v1/health",
        headers={"X-API-Key": DEV_HEADERS["X-API-Key"]},
        timeout=30.0,
    )
    try:
        frontend_status = httpx.get(frontend_base_url.rstrip("/"), timeout=15.0).status_code
    except Exception:
        frontend_status = 0

    rows = _run_s1_s11(backend_base_url)
    rows.append(_run_s12())
    sanitized_rows = _sanitize_rows(rows)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "backend_base_url": backend_base_url,
        "frontend_base_url": frontend_base_url,
        "backend_health_status": health_status,
        "backend_health_payload_status": _safe_dict(health_payload).get("status"),
        "frontend_status": frontend_status,
        "overall_verdict": _overall_verdict(sanitized_rows),
        "scenarios": sanitized_rows,
    }

    _write_json(OUT_DIR / "automated_owner_pilot_report.json", payload)
    _write_text(OUT_DIR / "automated_owner_pilot_report.md", _build_markdown(payload))
    _write_text(OUT_DIR / "blockers_and_warnings.md", _build_blockers_warnings(payload))
    _write_text(OUT_DIR / "no_mutation_proof.md", _build_no_mutation_proof())
    _write_text(OUT_DIR / "next_recommendation.md", _build_next_recommendation(payload))
    return payload


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--frontend-base-url", default="http://localhost:3000")
    args = parser.parse_args()
    result = run_gate(
        backend_base_url=str(args.backend_base_url),
        frontend_base_url=str(args.frontend_base_url),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result.get("overall_verdict")) != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
