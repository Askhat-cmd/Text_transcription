from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bot_psychologist.eval.prd_047_26_schema import (
    CONTROLLED_FAILURE_CLASSES,
    PRD_ID,
)


INTERNAL_LEAK_MARKERS = [
    "writer_kb_payload",
    "writer_kb_payload_v1",
    "overlay_shadow",
    "source_ref",
    "candidate_id",
]
RAW_KB_DUMP_MARKERS = [
    "chunk_id",
    "source_ref",
    "allowed_writer_use_candidate",
    "use_when_candidates",
]
LIVING_TONE_WARNING_MARKERS = [
    "определение",
    "критический период",
    "нейропластичность",
]
CLARIFYING_QUESTION_MARKERS = [
    "что ты имеешь в виду",
    "что для тебя",
    "как ты это понимаешь",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _md(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines])


def _normalize(text: str) -> str:
    return " ".join(str(text or "").lower().replace("\r\n", "\n").split())


def _contains_any(text: str, markers: list[str]) -> bool:
    normalized = _normalize(text)
    return any(_normalize(marker) in normalized for marker in markers if str(marker).strip())


def _numbered_list_count(text: str) -> int:
    count = 0
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped[:2].isdigit() or stripped[:2] in {"1.", "2.", "3.", "4.", "5."}:
            count += 1
    return count


def _expected_signal_bool(case: dict[str, Any], key: str, default: bool = False) -> bool:
    trace = dict(case.get("expected_trace_signals", {}) or {})
    return bool(trace.get(key, default))


def _find_missing_fields(export: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    required_top = {
        "assistant_answer": export.get("assistant_answer"),
        "active_runtime_path": export.get("active_runtime_path"),
        "retrieval_query_build_trace_v1": export.get("retrieval_query_build_trace_v1"),
        "writer_kb_payload_trace": export.get("writer_kb_payload_trace"),
        "overlay_shadow_trace": export.get("overlay_shadow_trace"),
        "final_answer_directive_v1": export.get("final_answer_directive_v1"),
        "validator": export.get("validator"),
    }
    for key, value in required_top.items():
        if value is None or value == {} or value == [] or value == "":
            missing.append(key)
    live_evidence = dict(export.get("live_turn_evidence", {}) or {})
    dialogue = dict(live_evidence.get("dialogue", {}) or {})
    if not dialogue.get("dialogue_act_resolution"):
        missing.append("live_turn_evidence.dialogue.dialogue_act_resolution")
    if not dialogue.get("answer_obligation_resolution"):
        missing.append("live_turn_evidence.dialogue.answer_obligation_resolution")
    state_thread = dict(live_evidence.get("state_thread", {}) or {})
    if not state_thread.get("response_mode"):
        missing.append("live_turn_evidence.state_thread.response_mode")
    return missing


def classify_live_case(case: dict[str, Any], export: dict[str, Any]) -> dict[str, Any]:
    answer = str(export.get("assistant_answer", "") or "")
    answer_normalized = _normalize(answer)
    case_type = str(case.get("case_type", "") or "")
    retrieval_trace = dict(export.get("retrieval_query_build_trace_v1", {}) or {})
    payload_trace = dict(export.get("writer_kb_payload_trace", {}) or {})
    overlay_trace = dict(export.get("overlay_shadow_trace", {}) or {})
    live_evidence = dict(export.get("live_turn_evidence", {}) or {})
    dialogue = dict(live_evidence.get("dialogue", {}) or {})
    dialogue_act = str(dict(dialogue.get("dialogue_act_resolution", {}) or {}).get("dialogue_act", "") or "")
    answer_obligation = str(
        dict(dialogue.get("answer_obligation_resolution", {}) or {}).get("answer_obligation", "") or ""
    )
    response_mode = str(dict(live_evidence.get("state_thread", {}) or {}).get("response_mode", "") or "")
    evaluator = dict(export.get("evaluator", {}) or {})
    validator = dict(export.get("validator", {}) or {})
    final_answer_directive = dict(export.get("final_answer_directive_v1", {}) or {})

    expected_keywords = [_normalize(item) for item in list(case.get("expected_keywords", []) or []) if str(item).strip()]
    forbidden_keywords = [_normalize(item) for item in list(case.get("forbidden_keywords", []) or []) if str(item).strip()]
    expected_dialogue_acts = {str(item) for item in list(case.get("expected_dialogue_acts", []) or []) if str(item).strip()}
    expected_obligations = {
        str(item) for item in list(case.get("expected_answer_obligations", []) or []) if str(item).strip()
    }
    allowed_response_modes = {str(item) for item in list(case.get("allowed_response_modes", []) or []) if str(item).strip()}

    missing_fields = _find_missing_fields(export)
    failure_classes: list[str] = []
    notes: list[str] = []

    should_answer_directly = bool(dict(case.get("expected_answer_shape", {}) or {}).get("should_answer_directly", False))
    should_not_dump_raw_kb = bool(
        dict(case.get("expected_answer_shape", {}) or {}).get("should_not_dump_raw_kb", False)
    )
    should_preserve_living_tone = bool(
        dict(case.get("expected_answer_shape", {}) or {}).get("should_preserve_living_tone", False)
    )

    expected_payload = _expected_signal_bool(case, "writer_kb_payload_expected", False)
    case_type_allows_kb_payload = case_type in {"direct_kb_answer", "elliptical_followup", "practice_request"}
    payload_primary = (
        str(payload_trace.get("primary_path", "") or "") == "writer_kb_payload_v1"
        and not bool(payload_trace.get("fallback_is_primary", False))
        and int(payload_trace.get("payload_chunk_count", 0) or 0) > 0
    )
    overlay_apply_detected = any(
        bool(overlay_trace.get(flag, False))
        for flag in ("used_for_writer", "used_for_retrieval_execution", "used_for_final_answer")
    )
    overlay_noise = bool(overlay_trace.get("would_help", False)) and not bool(case.get("overlay_shadow_expected", False))
    answer_shape = str(final_answer_directive.get("answer_shape", "") or "")
    answer_is_summary = answer_shape == "structured_summary" or case_type == "summary_request"

    if missing_fields:
        failure_classes.append("trace_missing_evidence")
        notes.append("missing_fields_detected")
    if overlay_apply_detected:
        failure_classes.append("overlay_shadow_noise")
        notes.append("overlay_apply_detected")
    if str(retrieval_trace.get("primary_path", "") or "") != "current_turn_focus_v1":
        failure_classes.append("retrieval_query_error")
        notes.append("retrieval_primary_not_current_turn_focus")
    if bool(retrieval_trace.get("previous_user_query_included", False)) and case_type != "elliptical_followup":
        failure_classes.append("retrieval_query_error")
        notes.append("unexpected_previous_query_included")
    if bool(retrieval_trace.get("query_truncated_mid_word", False)) or int(
        retrieval_trace.get("duplicate_fragment_count", 0) or 0
    ) > 0:
        failure_classes.append("retrieval_query_error")
        notes.append("query_shape_regression")
    if expected_payload and not payload_primary:
        failure_classes.append("kb_payload_error")
        notes.append("expected_payload_missing_or_fallback_primary")
    elif (
        not expected_payload
        and int(payload_trace.get("payload_chunk_count", 0) or 0) > 0
        and not case_type_allows_kb_payload
    ):
        notes.append("payload_present_on_non_kb_case")
    if expected_dialogue_acts and dialogue_act not in expected_dialogue_acts:
        failure_classes.append("dialogue_act_error")
        notes.append(f"dialogue_act={dialogue_act}")
    if expected_obligations and answer_obligation not in expected_obligations:
        failure_classes.append("answer_obligation_error")
        notes.append(f"answer_obligation={answer_obligation}")
    if allowed_response_modes and response_mode not in allowed_response_modes:
        failure_classes.append("response_mode_error")
        notes.append(f"response_mode={response_mode}")
    if overlay_noise:
        failure_classes.append("overlay_shadow_noise")
        notes.append("overlay_would_help_without_apply")

    expected_keywords_found = [item for item in expected_keywords if item in answer_normalized]
    forbidden_keywords_found = [item for item in forbidden_keywords if item in answer_normalized]
    internal_leak_detected = _contains_any(answer, INTERNAL_LEAK_MARKERS)
    raw_kb_dump_detected = ("```" in answer) or _contains_any(answer, RAW_KB_DUMP_MARKERS)
    reask_detected = _contains_any(answer, CLARIFYING_QUESTION_MARKERS)
    living_tone_warning = False

    if should_answer_directly:
        if len(answer.strip()) < 40:
            failure_classes.append("writer_style_regression")
            notes.append("answer_too_short")
        if reask_detected and case_type in {"direct_kb_answer", "elliptical_followup", "summary_request"}:
            failure_classes.append("writer_instruction_error")
            notes.append("clarifying_question_detected")
    if should_not_dump_raw_kb and raw_kb_dump_detected:
        failure_classes.append("writer_instruction_error")
        notes.append("raw_kb_dump_detected")
    if internal_leak_detected:
        failure_classes.append("writer_instruction_error")
        notes.append("internal_marker_leak_detected")
    if forbidden_keywords_found:
        failure_classes.append("writer_style_regression")
        notes.append("forbidden_keywords_found")
    if expected_keywords and not expected_keywords_found and case_type not in {"support", "overlay_noise_probe", "summary_request"}:
        failure_classes.append("writer_style_regression")
        notes.append("expected_keywords_missing")
    if should_preserve_living_tone and case_type in {"support", "overlay_noise_probe"}:
        if _numbered_list_count(answer) >= 3 or (len(answer) > 1600 and _contains_any(answer, LIVING_TONE_WARNING_MARKERS)):
            living_tone_warning = True
            failure_classes.append("writer_style_regression")
            notes.append("support_answer_too_textbook")

    fit_status = str(evaluator.get("fit_status", "") or "")
    if fit_status in {"pass", "warning"} and any(
        item in failure_classes
        for item in {
            "writer_style_regression",
            "writer_instruction_error",
            "kb_payload_error",
        }
    ):
        failure_classes.append("evaluator_false_pass")
        notes.append("evaluator_did_not_flag_quality_problem")

    if not failure_classes:
        failure_classes.append("no_issue_detected")

    deduped_failure_classes: list[str] = []
    for item in failure_classes:
        if item in CONTROLLED_FAILURE_CLASSES and item not in deduped_failure_classes:
            deduped_failure_classes.append(item)
    if "no_issue_detected" in deduped_failure_classes and len(deduped_failure_classes) > 1:
        deduped_failure_classes.remove("no_issue_detected")

    missing_core_fields = {
        "assistant_answer",
        "active_runtime_path",
        "retrieval_query_build_trace_v1",
        "writer_kb_payload_trace",
        "overlay_shadow_trace",
        "final_answer_directive_v1",
        "live_turn_evidence.dialogue.dialogue_act_resolution",
        "live_turn_evidence.dialogue.answer_obligation_resolution",
        "live_turn_evidence.state_thread.response_mode",
    }
    trace_missing_is_blocking = bool(set(missing_fields) & missing_core_fields)
    blocking_classes = {
        "runtime_transport_error",
        "writer_instruction_error",
        "retrieval_query_error",
    }

    status = "ok"
    if any(item in blocking_classes for item in deduped_failure_classes) or trace_missing_is_blocking:
        status = "blocked"
    elif any(item != "no_issue_detected" for item in deduped_failure_classes):
        status = "warning"
    if bool(validator.get("is_blocked", False)) and status == "ok":
        status = "warning"
        notes.append("validator_blocked_but_triage_ok")

    direct_answer_success = not any(
        item in deduped_failure_classes
        for item in {
            "writer_style_regression",
            "writer_instruction_error",
            "retrieval_query_error",
            "kb_payload_error",
            "runtime_transport_error",
        }
    )
    if trace_missing_is_blocking:
        direct_answer_success = False
    if answer_is_summary and "kb_payload_error" in deduped_failure_classes:
        direct_answer_success = True

    return {
        "status": status,
        "failure_classes": deduped_failure_classes,
        "missing_fields": missing_fields,
        "notes": notes,
        "direct_answer_success": direct_answer_success and not internal_leak_detected and not raw_kb_dump_detected,
        "living_tone_warning": living_tone_warning,
        "overlay_false_positive": overlay_noise,
        "overlay_missing_where_expected": bool(case.get("overlay_shadow_expected", False))
        and not bool(overlay_trace.get("would_help", False)),
        "internal_leak_detected": internal_leak_detected,
        "raw_kb_dump_detected": raw_kb_dump_detected,
        "unsafe_practice_detected": bool(export.get("unsafe_practice_detected", False)),
        "diagnostic_overclaim_detected": bool(export.get("diagnostic_overclaim_detected", False)),
        "expected_keywords_found": expected_keywords_found,
        "forbidden_keywords_found": forbidden_keywords_found,
        "observed_dialogue_act": dialogue_act,
        "observed_answer_obligation": answer_obligation,
        "observed_response_mode": response_mode,
        "observed_answer_shape": answer_shape,
        "expected_dialogue_acts": sorted(expected_dialogue_acts),
        "expected_answer_obligations": sorted(expected_obligations),
        "allowed_response_modes": sorted(allowed_response_modes),
        "writer_payload_chunk_count": int(payload_trace.get("payload_chunk_count", 0) or 0),
        "overlay_shadow_match_count": int(overlay_trace.get("match_count", 0) or 0),
        "safe_for_local_dev_only": True,
    }


def build_triage_report(
    *,
    cases: list[dict[str, Any]],
    live_results: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    case_map = {str(case.get("case_id", "") or ""): case for case in cases}
    exports = [dict(item) for item in list(live_results.get("cases", []) or []) if isinstance(item, dict)]
    triaged_cases: list[dict[str, Any]] = []
    counter = Counter()

    for export in exports:
        case_id = str(export.get("case_id", "") or "")
        case = case_map.get(case_id, {})
        triage = classify_live_case(case, export)
        export["triage"] = triage
        triaged_cases.append(export)
        counter[f"{triage['status']}_case_count"] += 1
        if triage["direct_answer_success"]:
            counter["direct_answer_success_count"] += 1
        if triage["living_tone_warning"]:
            counter["living_tone_warning_count"] += 1
        if triage["overlay_false_positive"]:
            counter["overlay_false_positive_count"] += 1
        if triage["overlay_missing_where_expected"]:
            counter["overlay_missing_where_expected_count"] += 1
        if triage["internal_leak_detected"]:
            counter["internal_leak_count"] += 1
        if triage["raw_kb_dump_detected"]:
            counter["raw_kb_dump_count"] += 1
        if triage["unsafe_practice_detected"]:
            counter["unsafe_practice_count"] += 1
        if triage["diagnostic_overclaim_detected"]:
            counter["diagnostic_overclaim_count"] += 1
        for failure_class in triage["failure_classes"]:
            counter[f"{failure_class}_count"] += 1

    executed_case_count = len(triaged_cases)
    direct_answer_success_rate = round(counter["direct_answer_success_count"] / executed_case_count, 4) if executed_case_count else 0.0
    warning_case_count = counter["warning_case_count"]
    blocked_case_count = counter["blocked_case_count"]

    if counter["dialogue_act_error_count"] >= 2 or counter["answer_obligation_error_count"] >= 2 or counter["evaluator_false_pass_count"] >= 2:
        db_track_readiness = "not_ready"
        recommended_next_prd = "PRD-047.26-HF1 - Dialogue Act / Answer Obligation Repair v1"
    elif counter["overlay_false_positive_count"] >= 3 or counter["overlay_missing_where_expected_count"] >= 3:
        db_track_readiness = "ready_with_warning"
        recommended_next_prd = "PRD-047.26-HF1 - Overlay Shadow Noise Reduction / Evidence Repair v1"
    elif blocked_case_count > 0 or direct_answer_success_rate < 0.75:
        db_track_readiness = "not_ready"
        recommended_next_prd = "PRD-047.26-HF1 - Evaluator False-Pass Repair v1"
    elif warning_case_count > 0:
        db_track_readiness = "ready_with_warning"
        recommended_next_prd = "PRD-047.27 - Mechanism-Aware DB / Semantic Chunk Cards v2"
    else:
        db_track_readiness = "ready"
        recommended_next_prd = "PRD-047.27 - Mechanism-Aware DB / Semantic Chunk Cards v2"

    if counter["runtime_transport_error_count"] > 0 or counter["internal_leak_count"] > 0 or counter["raw_kb_dump_count"] > 0:
        status = "blocked"
    elif blocked_case_count > 0 or warning_case_count > 0 or counter["overlay_false_positive_count"] > 0 or db_track_readiness == "not_ready":
        status = "passed_with_warning"
    else:
        status = "passed"

    report = {
        "prd_id": PRD_ID,
        "schema_version": "prd_047_26_live_quality_triage_report_v1",
        "created_at": _utc_now(),
        "status": status,
        "executed_case_count": executed_case_count,
        "passed_case_count": counter["ok_case_count"],
        "warning_case_count": warning_case_count,
        "blocked_case_count": blocked_case_count,
        "direct_answer_success_rate": direct_answer_success_rate,
        "living_tone_warning_count": counter["living_tone_warning_count"],
        "overlay_false_positive_count": counter["overlay_false_positive_count"],
        "overlay_missing_where_expected_count": counter["overlay_missing_where_expected_count"],
        "dialogue_act_error_count": counter["dialogue_act_error_count"],
        "answer_obligation_error_count": counter["answer_obligation_error_count"],
        "response_mode_error_count": counter["response_mode_error_count"],
        "retrieval_query_error_count": counter["retrieval_query_error_count"],
        "kb_payload_error_count": counter["kb_payload_error_count"],
        "writer_style_regression_count": counter["writer_style_regression_count"],
        "evaluator_false_pass_count": counter["evaluator_false_pass_count"],
        "trace_missing_evidence_count": counter["trace_missing_evidence_count"],
        "writer_instruction_error_count": counter["writer_instruction_error_count"],
        "runtime_transport_error_count": counter["runtime_transport_error_count"],
        "db_track_readiness": db_track_readiness,
        "recommended_next_prd": recommended_next_prd,
        "internal_leak_count": counter["internal_leak_count"],
        "raw_kb_dump_count": counter["raw_kb_dump_count"],
        "unsafe_practice_count": counter["unsafe_practice_count"],
        "diagnostic_overclaim_count": counter["diagnostic_overclaim_count"],
        "case_results": triaged_cases,
    }
    _write_json(out_dir / "live_quality_triage_report.json", report)
    lines = [
        f"- status: `{status}`",
        f"- executed_case_count: `{executed_case_count}`",
        f"- passed_case_count: `{counter['ok_case_count']}`",
        f"- warning_case_count: `{warning_case_count}`",
        f"- blocked_case_count: `{blocked_case_count}`",
        f"- direct_answer_success_rate: `{direct_answer_success_rate}`",
        f"- overlay_false_positive_count: `{counter['overlay_false_positive_count']}`",
        f"- overlay_missing_where_expected_count: `{counter['overlay_missing_where_expected_count']}`",
        f"- dialogue_act_error_count: `{counter['dialogue_act_error_count']}`",
        f"- answer_obligation_error_count: `{counter['answer_obligation_error_count']}`",
        f"- response_mode_error_count: `{counter['response_mode_error_count']}`",
        f"- retrieval_query_error_count: `{counter['retrieval_query_error_count']}`",
        f"- kb_payload_error_count: `{counter['kb_payload_error_count']}`",
        f"- writer_style_regression_count: `{counter['writer_style_regression_count']}`",
        f"- evaluator_false_pass_count: `{counter['evaluator_false_pass_count']}`",
        f"- trace_missing_evidence_count: `{counter['trace_missing_evidence_count']}`",
        f"- db_track_readiness: `{db_track_readiness}`",
        f"- recommended_next_prd: `{recommended_next_prd}`",
        "",
        "## Case Distribution",
        *[
            f"- `{item['case_id']}`: status=`{item['triage']['status']}` failure_classes=`{', '.join(item['triage']['failure_classes'])}`"
            for item in triaged_cases
        ],
    ]
    _write_text(out_dir / "live_quality_triage_report.md", _md("PRD-047.26 Live Quality Triage Report", lines))
    return report


__all__ = ["build_triage_report", "classify_live_case"]
