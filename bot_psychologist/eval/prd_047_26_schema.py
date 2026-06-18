from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PRD_ID = "PRD-047.26"

CONTROLLED_CASE_TYPES = {
    "direct_kb_answer",
    "elliptical_followup",
    "summary_request",
    "practice_request",
    "support",
    "overlay_noise_probe",
}

REQUIRED_CASE_TYPES = {
    "direct_kb_answer",
    "elliptical_followup",
    "summary_request",
    "practice_request",
    "support",
    "overlay_noise_probe",
}

CONTROLLED_FAILURE_CLASSES = {
    "dialogue_act_error",
    "answer_obligation_error",
    "response_mode_error",
    "overlay_shadow_noise",
    "retrieval_query_error",
    "kb_payload_error",
    "writer_instruction_error",
    "writer_style_regression",
    "evaluator_false_pass",
    "trace_missing_evidence",
    "runtime_transport_error",
    "no_issue_detected",
}

REQUIRED_EXPORT_FIELDS = {
    "active_runtime_path",
    "retrieval_query_build_trace_v1",
    "writer_kb_payload_trace",
    "overlay_shadow_trace",
    "final_answer_directive_v1",
    "validator",
    "evaluator",
    "triage",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_cases_path() -> Path:
    return repo_root() / "bot_psychologist" / "eval" / "prd_047_26_live_quality_cases.json"


def load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or default_cases_path()
    payload = json.loads(target.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        items = payload.get("cases", [])
        if isinstance(items, list):
            return [dict(item) for item in items if isinstance(item, dict)]
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, dict)]
    return []


def validate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    ids: list[str] = []
    type_counts: dict[str, int] = {}
    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id", "") or "").strip()
        case_type = str(case.get("case_type", "") or "").strip()
        ids.append(case_id)
        if not case_id:
            blockers.append(f"case_{index}_missing_case_id")
        if case_type not in CONTROLLED_CASE_TYPES:
            blockers.append(f"{case_id or f'case_{index}'}_invalid_case_type:{case_type}")
        type_counts[case_type] = type_counts.get(case_type, 0) + 1
        turns = case.get("turns")
        if not isinstance(turns, list) or not turns:
            blockers.append(f"{case_id}_missing_turns")
        expected_shape = case.get("expected_answer_shape")
        expected_trace = case.get("expected_trace_signals")
        failure_candidates = case.get("failure_class_candidates")
        if not isinstance(expected_shape, dict):
            blockers.append(f"{case_id}_missing_expected_answer_shape")
        if not isinstance(expected_trace, dict):
            blockers.append(f"{case_id}_missing_expected_trace_signals")
        if not isinstance(failure_candidates, list) or not failure_candidates:
            blockers.append(f"{case_id}_missing_failure_class_candidates")
        else:
            bad_candidates = [
                str(item) for item in failure_candidates if str(item) not in CONTROLLED_FAILURE_CLASSES
            ]
            if bad_candidates:
                blockers.append(f"{case_id}_invalid_failure_candidates:{','.join(sorted(bad_candidates))}")
        if isinstance(turns, list):
            for turn_number, turn in enumerate(turns, start=1):
                if not isinstance(turn, dict):
                    blockers.append(f"{case_id}_turn_{turn_number}_not_object")
                    continue
                if str(turn.get("role", "") or "").strip() not in {"user", "assistant"}:
                    blockers.append(f"{case_id}_turn_{turn_number}_invalid_role")
                if not str(turn.get("content", "") or "").strip():
                    blockers.append(f"{case_id}_turn_{turn_number}_missing_content")
        if isinstance(expected_shape, dict):
            missing_shape_keys = {
                "should_answer_directly",
                "should_not_reask_definition",
                "should_not_open_new_topic",
                "should_not_dump_raw_kb",
                "should_preserve_living_tone",
            }.difference(expected_shape.keys())
            if missing_shape_keys:
                blockers.append(f"{case_id}_missing_shape_keys:{','.join(sorted(missing_shape_keys))}")
        if isinstance(expected_trace, dict):
            missing_trace_keys = {
                "writer_kb_payload_expected",
                "overlay_apply_must_be_false",
                "legacy_query_builder_must_be_false",
                "current_turn_focus_expected",
            }.difference(expected_trace.keys())
            if missing_trace_keys:
                blockers.append(f"{case_id}_missing_trace_keys:{','.join(sorted(missing_trace_keys))}")
        if not isinstance(case.get("expected_keywords", []), list):
            blockers.append(f"{case_id}_expected_keywords_not_list")
        if not isinstance(case.get("forbidden_keywords", []), list):
            blockers.append(f"{case_id}_forbidden_keywords_not_list")
        if case_type == "direct_kb_answer" and not case.get("expected_dialogue_acts"):
            warnings.append(f"{case_id}_missing_expected_dialogue_acts")

    if len(cases) < 12:
        blockers.append("case_count_below_12")
    duplicates = sorted({item for item in ids if item and ids.count(item) > 1})
    if duplicates:
        blockers.append(f"duplicate_case_ids:{','.join(duplicates)}")
    missing_types = sorted(REQUIRED_CASE_TYPES.difference({item for item, count in type_counts.items() if count > 0}))
    if missing_types:
        blockers.append(f"missing_required_case_types:{','.join(missing_types)}")

    return {
        "schema_version": "prd_047_26_live_quality_cases_schema_v1",
        "prd_id": PRD_ID,
        "case_count": len(cases),
        "type_counts": type_counts,
        "status": "passed" if not blockers else "blocked",
        "warnings": warnings,
        "blockers": blockers,
    }


def required_source_gate_paths() -> list[str]:
    return [
        "TO_DO_LIST/reports/PRD-047.25_IMPLEMENTATION_REPORT.md",
        "TO_DO_LIST/reports/PRD-047.25_NEXT_PRD_RECOMMENDATION.md",
        "TO_DO_LIST/logs/PRD-047.25/live_evidence_results.json",
        "TO_DO_LIST/logs/PRD-047.25/overlay_payload_alignment_report.json",
        "TO_DO_LIST/logs/PRD-047.25/retrieval_query_health_report.json",
        "TO_DO_LIST/logs/PRD-047.25/no_mutation_proof.json",
        "docs/PROJECT_STATE.md",
        "docs/ROADMAP.md",
        "docs/PRD_INDEX.md",
    ]


__all__ = [
    "CONTROLLED_CASE_TYPES",
    "CONTROLLED_FAILURE_CLASSES",
    "PRD_ID",
    "REQUIRED_CASE_TYPES",
    "REQUIRED_EXPORT_FIELDS",
    "default_cases_path",
    "load_cases",
    "repo_root",
    "required_source_gate_paths",
    "validate_cases",
]
