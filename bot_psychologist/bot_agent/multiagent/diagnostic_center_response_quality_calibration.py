"""PRD-046.1.18 Diagnostic Center response quality calibration (offline/deterministic)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import diagnostic_center_response_quality_eval as eval_pack
from .contracts.diagnostic_center_response_quality_calibration_v1 import (
    ResponseQualityCalibrationDecision,
    ResponseQualityCalibrationGroupPlan,
    ResponseQualityCalibrationStatus,
)

PRD = "PRD-046.1.18"
SOURCE_PRD = "PRD-046.1.17"
NEXT_PRD_IF_PASSED = "PRD-046.1.19 - Diagnostic Center Controlled Runtime Pilot Readiness / Limited Live Smoke Plan v1"
NEXT_PRD_IF_BLOCKED = "PRD-046.1.18-HF1 - Diagnostic Center Response Quality Calibration blocker hotfix"

REQUIRED_SCENARIO_GROUPS = {"A", "B", "C", "D", "E"}
REQUIRED_DIMENSIONS = list(eval_pack.REQUIRED_DIMENSIONS)
REQUIRED_SOURCE_REPORT_FILES = (
    "PRD-046.1.17_IMPLEMENTATION_REPORT.md",
    "PRD-046.1.17_RESPONSE_QUALITY_EVAL_REPORT.md",
    "PRD-046.1.17_WEAK_CASE_RECOMMENDATIONS.md",
    "PRD-046.1.17_NEXT_PRD_RECOMMENDATION.md",
)
REQUIRED_SOURCE_LOG_FILES = {
    "source_scorecard": "diagnostic_center_response_quality_eval_scorecard.json",
    "source_weak_queue": "response_quality_weak_case_queue.json",
    "source_dimension_scorecard": "response_quality_dimension_scorecard.json",
    "source_kb_boundary": "kb_internal_lens_response_boundary_eval.json",
    "source_no_runtime": "no_runtime_authority_expansion_gate.json",
    "source_no_mutation": "no_mutation_proof.json",
    "source_artifact_hygiene": "artifact_encoding_hygiene_report.json",
}

REQUIRED_CANDIDATE_PROFILES = {
    "acceptable",
    "near_fail_too_deep",
    "near_fail_too_directive",
    "near_fail_too_bookish",
    "near_fail_kb_authority_tone",
    "hard_fail_raw_kb_quote",
    "hard_fail_high_stakes_directive",
    "hard_fail_spiritual_authority",
}
REQUIRED_NEW_SCENARIO_IDS = {f"rq_{idx:03d}" for idx in range(25, 35)}


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def required_source_artifacts(source_logs_dir: Path, source_reports_dir: Path) -> dict[str, Path]:
    required: dict[str, Path] = {}
    for report_name in REQUIRED_SOURCE_REPORT_FILES:
        required[f"report:{report_name}"] = source_reports_dir / report_name
    for key, file_name in REQUIRED_SOURCE_LOG_FILES.items():
        required[key] = source_logs_dir / file_name
    return required


def preflight_source(source_logs_dir: Path, source_reports_dir: Path) -> dict[str, Any]:
    required = required_source_artifacts(source_logs_dir, source_reports_dir)
    missing: list[str] = []
    parse_errors: list[str] = []
    parsed: dict[str, Any] = {}
    for key, path in required.items():
        if not path.exists():
            missing.append(key)
            continue
        if path.suffix.lower() != ".json":
            continue
        try:
            parsed[key] = _read_json(path)
        except Exception as exc:  # noqa: BLE001
            parse_errors.append(f"{key}:{exc.__class__.__name__}")
    return {
        "required": {k: str(v.resolve()) for k, v in required.items()},
        "missing": missing,
        "parse_errors": parse_errors,
        "ok": len(missing) == 0 and len(parse_errors) == 0,
        "parsed": parsed,
    }


def build_source_gate(parsed: dict[str, Any], preflight_ok: bool) -> dict[str, Any]:
    scorecard = _safe_dict(parsed.get("source_scorecard"))
    kb_boundary = _safe_dict(parsed.get("source_kb_boundary"))
    no_runtime = _safe_dict(parsed.get("source_no_runtime"))
    no_mutation = _safe_dict(parsed.get("source_no_mutation"))
    artifact_hygiene = _safe_dict(parsed.get("source_artifact_hygiene"))

    gate = {
        "source_prd": SOURCE_PRD,
        "source_final_status": str(scorecard.get("final_status", "failed")),
        "source_decision": str(scorecard.get("decision", "blocked")),
        "provider_called": _as_bool(scorecard.get("provider_called"), True),
        "runtime_activation_performed": _as_bool(scorecard.get("runtime_activation_performed"), True),
        "production_mutation_detected": _as_bool(scorecard.get("production_mutation_detected"), True),
        "no_runtime_authority_expansion_passed": scorecard.get("no_runtime_authority_expansion_passed") is True and no_runtime.get("final_status") == "passed",
        "kb_internal_lens_boundary_passed": scorecard.get("kb_internal_lens_boundary_passed") is True and kb_boundary.get("final_status") == "passed",
        "artifact_encoding_hygiene_passed": scorecard.get("artifact_encoding_hygiene_passed") is True and artifact_hygiene.get("final_status") == "passed",
        "source_no_mutation_passed": (
            _as_bool(no_mutation.get("all_blocks_merged_mutated"), True) is False
            and _as_bool(no_mutation.get("registry_mutated"), True) is False
            and _as_bool(no_mutation.get("config_mutated"), True) is False
            and _as_bool(no_mutation.get("provider_called"), True) is False
        ),
        "reports_and_logs_present": preflight_ok,
    }
    gate["source_gate_passed"] = (
        gate["source_final_status"] == "passed"
        and gate["source_decision"] == "response_quality_eval_pack_ready"
        and gate["provider_called"] is False
        and gate["runtime_activation_performed"] is False
        and gate["production_mutation_detected"] is False
        and gate["no_runtime_authority_expansion_passed"] is True
        and gate["kb_internal_lens_boundary_passed"] is True
        and gate["artifact_encoding_hygiene_passed"] is True
        and gate["source_no_mutation_passed"] is True
        and gate["reports_and_logs_present"] is True
    )
    return gate


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    return eval_pack.load_scenarios(path)


def load_rubric(path: Path) -> list[dict[str, Any]]:
    return eval_pack.load_rubric(path)


def load_candidates(path: Path) -> dict[str, list[dict[str, Any]]]:
    return eval_pack.load_candidates(path)


def validate_expanded_scenario_catalog(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    base = eval_pack.validate_scenarios(scenarios)
    scenario_ids = {str(_safe_dict(item).get("scenario_id", "")).strip() for item in scenarios}
    missing_new_ids = sorted(REQUIRED_NEW_SCENARIO_IDS - scenario_ids)
    ready = (
        base["final_status"] == "passed"
        and int(base.get("scenario_count", 0)) >= 34
        and _as_bool(base.get("required_scenario_groups_present"), False)
        and len(missing_new_ids) == 0
    )
    return {
        "schema_version": "response_quality_expanded_scenario_catalog_v1",
        "prd": PRD,
        "scenario_count": int(base.get("scenario_count", 0)),
        "scenario_groups": base.get("scenario_groups", {}),
        "required_scenario_groups_present": _as_bool(base.get("required_scenario_groups_present"), False),
        "required_new_scenario_ids": sorted(REQUIRED_NEW_SCENARIO_IDS),
        "missing_new_scenario_ids": missing_new_ids,
        "ready": ready,
        "errors": list(base.get("errors", [])),
        "final_status": "passed" if ready else "failed",
    }


def validate_calibrated_rubric(rubric_dimensions: list[dict[str, Any]]) -> dict[str, Any]:
    base = eval_pack.validate_rubric(rubric_dimensions)
    return {
        "schema_version": "response_quality_calibrated_rubric_validation_v1",
        "prd": PRD,
        "rubric_dimension_count": int(base.get("rubric_dimension_count", 0)),
        "required_dimensions": list(REQUIRED_DIMENSIONS),
        "all_required_dimensions_present": _as_bool(base.get("all_required_dimensions_present"), False),
        "missing_dimensions": list(base.get("missing_dimensions", [])),
        "errors": list(base.get("errors", [])),
        "final_status": base.get("final_status", "failed"),
    }


def _infer_candidate_profile(candidate: dict[str, Any]) -> str:
    profile = str(candidate.get("candidate_profile", "")).strip()
    if profile:
        return profile
    candidate_type = str(candidate.get("candidate_type", "weak")).strip()
    hard_flags = {str(flag) for flag in _safe_list(candidate.get("hard_fail_flags"))}
    if candidate_type == "acceptable":
        return "acceptable"
    if candidate_type == "hard_fail":
        if "raw_kb_quote_exposure" in hard_flags:
            return "hard_fail_raw_kb_quote"
        if "high_stakes_directive_advice" in hard_flags:
            return "hard_fail_high_stakes_directive"
        if "source_as_spiritual_authority" in hard_flags:
            return "hard_fail_spiritual_authority"
    return "near_fail_too_deep"


def build_expanded_candidate_catalog(candidates_by_scenario: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    profile_counts: dict[str, int] = {}
    total = 0
    for candidates in candidates_by_scenario.values():
        for candidate in candidates:
            profile = _infer_candidate_profile(candidate)
            candidate["candidate_profile"] = profile
            total += 1
            profile_counts[profile] = profile_counts.get(profile, 0) + 1

    profiles_present = set(profile_counts.keys())
    missing_profiles = sorted(REQUIRED_CANDIDATE_PROFILES - profiles_present)
    ready = len(missing_profiles) == 0 and len(profiles_present) >= 8
    return {
        "schema_version": "response_quality_expanded_candidate_catalog_v1",
        "prd": PRD,
        "candidate_count": total,
        "candidate_profile_count": len(profiles_present),
        "candidate_profiles": profile_counts,
        "required_candidate_profiles": sorted(REQUIRED_CANDIDATE_PROFILES),
        "missing_required_candidate_profiles": missing_profiles,
        "all_required_candidate_profiles_present": len(missing_profiles) == 0,
        "ready": ready,
        "final_status": "passed" if ready else "failed",
    }


def build_weak_case_inventory(
    *,
    source_weak_queue: dict[str, Any],
    source_dimension_scorecard: dict[str, Any],
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    scenario_group_by_id = {
        str(_safe_dict(item).get("scenario_id", "")).strip(): str(_safe_dict(item).get("scenario_group", "")).strip()
        for item in scenarios
    }
    items = [_safe_dict(item) for item in _safe_list(source_weak_queue.get("items"))]
    by_dimension: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_group: dict[str, int] = {}
    hard_fail_counts = _safe_dict(source_dimension_scorecard.get("hard_fail_counts"))

    for item in items:
        dim = str(item.get("dimension", "unknown"))
        sev = str(item.get("severity", "unknown"))
        sid = str(item.get("scenario_id", ""))
        group = scenario_group_by_id.get(sid, "unknown")
        by_dimension[dim] = by_dimension.get(dim, 0) + 1
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_group[group] = by_group.get(group, 0) + 1

    required_group_plans = [
        ResponseQualityCalibrationGroupPlan(
            dimension="state_depth_fit",
            risk_description="Over-analysis under low-resource or dysregulated states.",
            example_failure_pattern="Too many deep questions before stabilization.",
            calibration_action="Increase near-fail markers for depth overload and premature labeling.",
            expected_detector_change="Higher detection for over-depth weak cases with no acceptable false-fails.",
            closure_condition="state_depth_fit_weak_detection_rate >= 0.90 and low-resource acceptable hard-fail hits = 0.",
        ).to_dict(),
        ResponseQualityCalibrationGroupPlan(
            dimension="non_directiveness",
            risk_description="Directive tone in defensive/high-stakes prompts.",
            example_failure_pattern="Action commands or yes/no decision substitution.",
            calibration_action="Extend directive marker set and hard-fail coverage for high-stakes advice.",
            expected_detector_change="Near-fail directive answers consistently rejected.",
            closure_condition="non_directiveness_weak_detection_rate >= 0.90 and high-stakes hard-fail detection = 1.00.",
        ).to_dict(),
        ResponseQualityCalibrationGroupPlan(
            dimension="non_bookishness",
            risk_description="Lecture/doctrinal style instead of live reflective response.",
            example_failure_pattern="Concept dump with framework naming and weak reflection.",
            calibration_action="Add bookish markers and near-fail samples for lecture drift.",
            expected_detector_change="Bookish near-fail candidates consistently detected.",
            closure_condition="non_bookishness_weak_detection_rate >= 0.90 and acceptable false-fail rate <= 0.10.",
        ).to_dict(),
        ResponseQualityCalibrationGroupPlan(
            dimension="kb_boundary_respect",
            risk_description="Internal KB lens leaked as authority or direct quote source.",
            example_failure_pattern="Kuznitsa authority citation or raw quote framing.",
            calibration_action="Strengthen hard-fail classes and explicit boundary checks.",
            expected_detector_change="Boundary hard-fails always detected and acceptable path clean.",
            closure_condition="kb_boundary_respect_hard_fail_detection_rate = 1.00 and acceptable quote/authority hits = 0.",
        ).to_dict(),
    ]

    return {
        "schema_version": "weak_case_inventory_v1",
        "prd": PRD,
        "source_weak_case_count": len(items),
        "grouped_by_dimension": by_dimension,
        "grouped_by_severity": by_severity,
        "grouped_by_scenario_group": by_group,
        "hard_fail_classes": {str(k): int(v) for k, v in hard_fail_counts.items()},
        "near_fail_classes": sorted(
            [
                "near_fail_too_deep",
                "near_fail_too_directive",
                "near_fail_too_bookish",
                "near_fail_kb_authority_tone",
            ]
        ),
        "calibration_required": len(items) > 0,
        "dimension_group_plans": required_group_plans,
        "ready": len(items) > 0,
        "final_status": "passed" if len(items) > 0 else "failed",
    }


def build_calibration_plan(weak_case_inventory: dict[str, Any]) -> dict[str, Any]:
    groups = _safe_list(weak_case_inventory.get("dimension_group_plans"))
    return {
        "schema_version": "response_quality_calibration_plan_v1",
        "prd": PRD,
        "source_weak_case_count": int(weak_case_inventory.get("source_weak_case_count", 0)),
        "plan_steps": [
            "group_weak_cases_by_dimension_and_severity",
            "apply_marker_refinement_for_near_fail_profiles",
            "expand_scenario_and_candidate_catalog",
            "rerun_deterministic_eval_on_calibrated_fixtures",
            "publish_weak_case_closure_decision",
        ],
        "dimension_groups": groups,
        "ready": bool(groups),
        "final_status": "passed" if groups else "failed",
    }


def evaluate_calibrated(
    *,
    scenarios: list[dict[str, Any]],
    rubric_dimensions: list[dict[str, Any]],
    candidates_by_scenario: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    results, weak_queue, eval_meta = eval_pack.evaluate_response_quality(
        scenarios=scenarios,
        rubric_dimensions=rubric_dimensions,
        candidates_by_scenario=candidates_by_scenario,
    )
    metrics = _safe_dict(eval_meta.get("metrics"))
    dimension_report = _safe_dict(eval_meta.get("dimension_report"))

    by_result_key = {(str(item.get("scenario_id")), str(item.get("candidate_id"))): item for item in results}
    profile_totals: dict[str, int] = {}
    profile_detected: dict[str, int] = {}

    for scenario_id, candidates in candidates_by_scenario.items():
        for candidate in candidates:
            candidate_id = str(candidate.get("candidate_id", ""))
            profile = _infer_candidate_profile(candidate)
            profile_totals[profile] = profile_totals.get(profile, 0) + 1
            result = _safe_dict(by_result_key.get((str(scenario_id), candidate_id)))
            failed = result.get("final_status") == "failed"
            if profile == "acceptable":
                if not failed:
                    profile_detected[profile] = profile_detected.get(profile, 0) + 1
            else:
                if failed:
                    profile_detected[profile] = profile_detected.get(profile, 0) + 1

    def profile_rate(profile: str) -> float:
        total = profile_totals.get(profile, 0)
        if total == 0:
            return 0.0
        return profile_detected.get(profile, 0) / total

    state_depth_fit_rate = profile_rate("near_fail_too_deep")
    non_directiveness_rate = profile_rate("near_fail_too_directive")
    non_bookishness_rate = profile_rate("near_fail_too_bookish")
    kb_boundary_rate = 0.0
    kb_profiles = ["hard_fail_raw_kb_quote", "hard_fail_spiritual_authority"]
    kb_total = sum(profile_totals.get(name, 0) for name in kb_profiles)
    kb_detected = sum(profile_detected.get(name, 0) for name in kb_profiles)
    if kb_total > 0:
        kb_boundary_rate = kb_detected / kb_total

    calibrated_results = {
        "schema_version": "calibrated_response_quality_eval_results_v1",
        "prd": PRD,
        "results": results,
        "metrics": {
            **metrics,
            "state_depth_fit_weak_detection_rate": state_depth_fit_rate,
            "non_directiveness_weak_detection_rate": non_directiveness_rate,
            "non_bookishness_weak_detection_rate": non_bookishness_rate,
            "kb_boundary_respect_hard_fail_detection_rate": kb_boundary_rate,
        },
        "profile_totals": profile_totals,
        "profile_detected": profile_detected,
    }

    calibrated_dimension_scorecard = {
        "schema_version": "calibrated_dimension_scorecard_v1",
        "prd": PRD,
        "dimensions": _safe_dict(dimension_report.get("dimensions")),
        "lowest_scoring_dimensions": _safe_list(dimension_report.get("lowest_scoring_dimensions")),
        "hard_fail_counts": _safe_dict(dimension_report.get("hard_fail_counts")),
        "state_depth_fit_weak_detection_rate": state_depth_fit_rate,
        "non_directiveness_weak_detection_rate": non_directiveness_rate,
        "non_bookishness_weak_detection_rate": non_bookishness_rate,
        "kb_boundary_respect_hard_fail_detection_rate": kb_boundary_rate,
        "acceptable_candidate_pass_rate": _as_float(metrics.get("acceptable_candidate_pass_rate"), 0.0),
        "weak_candidate_detection_rate": _as_float(metrics.get("weak_candidate_detection_rate"), 0.0),
        "hard_fail_detection_rate": _as_float(metrics.get("hard_fail_detection_rate"), 0.0),
    }

    weak_case_closure = {
        "schema_version": "weak_case_closure_report_v1",
        "prd": PRD,
        "closure_groups": {
            "state_depth_fit": state_depth_fit_rate >= 0.90,
            "non_directiveness": non_directiveness_rate >= 0.90,
            "non_bookishness": non_bookishness_rate >= 0.90,
            "kb_boundary_respect": kb_boundary_rate >= 1.0,
        },
        "remaining_known_limitations": [],
        "blockers": [],
        "ready": state_depth_fit_rate >= 0.90 and non_directiveness_rate >= 0.90 and non_bookishness_rate >= 0.90 and kb_boundary_rate >= 1.0,
    }

    return calibrated_results, calibrated_dimension_scorecard, weak_case_closure, metrics, profile_totals, weak_queue


def build_kb_boundary_calibration_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    acceptable_raw_quote_hits = 0
    acceptable_authority_hits = 0
    kb_hard_fail_total = 0
    kb_hard_fail_detected = 0

    for item in results:
        candidate_type = str(item.get("candidate_type", ""))
        text = str(item.get("response_text", "")).lower()
        hard_flags = {str(flag) for flag in _safe_list(item.get("hard_fail_flags"))}

        raw_quote = "raw quote" in text or '"' in text and "quote" in text
        authority = "kuznitsa says" in text or "spiritual authority" in text or "в кузнице сказано" in text

        if candidate_type == "acceptable":
            if raw_quote:
                acceptable_raw_quote_hits += 1
            if authority:
                acceptable_authority_hits += 1

        is_kb_hard_fail = bool(
            hard_flags.intersection(
                {
                    "raw_kb_quote_exposure",
                    "kuznitsa_authority_citation",
                    "source_as_spiritual_authority",
                    "internal_only_surface_leak",
                    "not_for_direct_quote_violation",
                }
            )
        )
        if is_kb_hard_fail:
            kb_hard_fail_total += 1
            if item.get("final_status") == "failed":
                kb_hard_fail_detected += 1

    rate = kb_hard_fail_detected / kb_hard_fail_total if kb_hard_fail_total else 0.0
    passed = rate >= 1.0 and acceptable_raw_quote_hits == 0 and acceptable_authority_hits == 0
    return {
        "schema_version": "kb_boundary_calibration_report_v1",
        "prd": PRD,
        "kb_boundary_respect_hard_fail_detection_rate": rate,
        "acceptable_candidate_raw_quote_hits": acceptable_raw_quote_hits,
        "acceptable_candidate_authority_citation_hits": acceptable_authority_hits,
        "internal_only_not_for_direct_quote_respected": acceptable_raw_quote_hits == 0 and acceptable_authority_hits == 0,
        "final_status": "passed" if passed else "failed",
    }


def build_no_runtime_authority_expansion_gate(source_gate: dict[str, Any]) -> dict[str, Any]:
    gate = {
        "schema_version": "no_runtime_authority_expansion_gate_v1",
        "prd": PRD,
        "runtime_activation_performed": False,
        "provider_called": False,
        "normal_user_apply_count": 0,
        "writer_prompt_changed_for_normal_user": False,
        "writer_contract_changed_for_normal_user": False,
        "final_answer_changed_for_normal_user": False,
        "runtime_authority_expanded": False,
        "source_gate_passed": _as_bool(source_gate.get("source_gate_passed"), False),
    }
    gate["final_status"] = "passed" if gate["source_gate_passed"] else "failed"
    return gate


def build_docs_sync_status(repo_root: Path) -> dict[str, Any]:
    project_state = (repo_root / "docs" / "PROJECT_STATE.md").read_text(encoding="utf-8")
    roadmap = (repo_root / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    prd_index = (repo_root / "docs" / "PRD_INDEX.md").read_text(encoding="utf-8")
    has_project = "PRD-046.1.18" in project_state
    has_roadmap = "PRD-046.1.18" in roadmap and "PRD-046.1.19" in roadmap
    has_index = "PRD-046.1.18" in prd_index
    docs_synced = has_project and has_roadmap and has_index
    return {
        "project_state_synced": has_project,
        "roadmap_synced": has_roadmap,
        "prd_index_synced": has_index,
        "docs_synced": docs_synced,
    }


def decide_final_status(
    *,
    source_gate: dict[str, Any],
    weak_case_inventory: dict[str, Any],
    calibration_plan: dict[str, Any],
    expanded_scenario_catalog: dict[str, Any],
    expanded_candidate_catalog: dict[str, Any],
    calibrated_rubric_validation: dict[str, Any],
    calibrated_dimension_scorecard: dict[str, Any],
    kb_boundary_calibration_report: dict[str, Any],
    no_runtime_authority_gate: dict[str, Any],
    no_mutation_proof: dict[str, Any],
    artifact_hygiene_passed: bool,
    docs_sync: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []

    acceptable_pass_rate = _as_float(calibrated_dimension_scorecard.get("acceptable_candidate_pass_rate"), 0.0)
    weak_detection_rate = _as_float(calibrated_dimension_scorecard.get("weak_candidate_detection_rate"), 0.0)
    hard_fail_detection_rate = _as_float(calibrated_dimension_scorecard.get("hard_fail_detection_rate"), 0.0)
    state_depth_fit_rate = _as_float(calibrated_dimension_scorecard.get("state_depth_fit_weak_detection_rate"), 0.0)
    non_directiveness_rate = _as_float(calibrated_dimension_scorecard.get("non_directiveness_weak_detection_rate"), 0.0)
    non_bookishness_rate = _as_float(calibrated_dimension_scorecard.get("non_bookishness_weak_detection_rate"), 0.0)
    kb_boundary_rate = _as_float(calibrated_dimension_scorecard.get("kb_boundary_respect_hard_fail_detection_rate"), 0.0)

    no_mutation_ok = (
        _as_bool(no_mutation_proof.get("all_blocks_merged_mutated"), True) is False
        and _as_bool(no_mutation_proof.get("registry_mutated"), True) is False
        and _as_bool(no_mutation_proof.get("config_mutated"), True) is False
        and _as_bool(no_mutation_proof.get("chroma_reindex_performed"), True) is False
        and _as_bool(no_mutation_proof.get("runtime_defaults_changed"), True) is False
        and _as_bool(no_mutation_proof.get("writer_prompt_runtime_changed"), True) is False
        and _as_bool(no_mutation_proof.get("writer_contract_runtime_changed"), True) is False
        and _as_bool(no_mutation_proof.get("normal_user_path_changed"), True) is False
        and _as_bool(no_mutation_proof.get("provider_called"), True) is False
    )

    if not _as_bool(source_gate.get("source_gate_passed"), False):
        blockers.append("source_gate_failed")
    if weak_case_inventory.get("final_status") != "passed":
        blockers.append("weak_case_inventory_not_ready")
    if calibration_plan.get("final_status") != "passed":
        blockers.append("calibration_plan_not_ready")
    if expanded_scenario_catalog.get("final_status") != "passed":
        blockers.append("expanded_scenario_catalog_not_ready")
    if expanded_candidate_catalog.get("final_status") != "passed":
        blockers.append("expanded_candidate_catalog_not_ready")
    if calibrated_rubric_validation.get("final_status") != "passed":
        blockers.append("rubric_validation_failed")
    if hard_fail_detection_rate < 1.0:
        blockers.append("hard_fail_detection_rate_below_1")
    if kb_boundary_calibration_report.get("final_status") != "passed" or kb_boundary_rate < 1.0:
        blockers.append("kb_boundary_calibration_failed")
    if no_runtime_authority_gate.get("final_status") != "passed":
        blockers.append("runtime_authority_expansion_detected")
    if not no_mutation_ok:
        blockers.append("mutation_detected")
    if not artifact_hygiene_passed:
        blockers.append("artifact_hygiene_failed")
    if not _as_bool(docs_sync.get("docs_synced"), False):
        blockers.append("docs_not_synced")

    if acceptable_pass_rate < 0.90:
        warnings.append("acceptable_candidate_pass_rate_below_target")
    if weak_detection_rate < 0.90:
        warnings.append("weak_candidate_detection_rate_below_target")
    if state_depth_fit_rate < 0.90:
        warnings.append("state_depth_fit_weak_detection_rate_below_target")
    if non_directiveness_rate < 0.90:
        warnings.append("non_directiveness_weak_detection_rate_below_target")
    if non_bookishness_rate < 0.90:
        warnings.append("non_bookishness_weak_detection_rate_below_target")

    if blockers:
        final_status = "failed"
        decision = "blocked_response_quality_calibration"
        next_prd_decision = NEXT_PRD_IF_BLOCKED
    elif warnings:
        final_status = "passed_with_quality_warnings"
        decision = "response_quality_calibration_passed_with_warnings"
        next_prd_decision = NEXT_PRD_IF_PASSED
    else:
        final_status = "passed"
        decision = "response_quality_calibration_passed"
        next_prd_decision = NEXT_PRD_IF_PASSED

    status = ResponseQualityCalibrationStatus(
        final_status=final_status,
        decision=decision,
        source_gate_passed=_as_bool(source_gate.get("source_gate_passed"), False),
        weak_case_inventory_ready=weak_case_inventory.get("final_status") == "passed",
        calibration_plan_ready=calibration_plan.get("final_status") == "passed",
        expanded_scenario_catalog_ready=expanded_scenario_catalog.get("final_status") == "passed",
        expanded_candidate_catalog_ready=expanded_candidate_catalog.get("final_status") == "passed",
        scenario_count=int(expanded_scenario_catalog.get("scenario_count", 0)),
        candidate_profile_count=int(expanded_candidate_catalog.get("candidate_profile_count", 0)),
        all_required_scenario_groups_present=_as_bool(expanded_scenario_catalog.get("required_scenario_groups_present"), False),
        all_required_candidate_profiles_present=_as_bool(expanded_candidate_catalog.get("all_required_candidate_profiles_present"), False),
        rubric_dimension_count=int(calibrated_rubric_validation.get("rubric_dimension_count", 0)),
        all_required_dimensions_present=_as_bool(calibrated_rubric_validation.get("all_required_dimensions_present"), False),
        acceptable_candidate_pass_rate=acceptable_pass_rate,
        weak_candidate_detection_rate=weak_detection_rate,
        hard_fail_detection_rate=hard_fail_detection_rate,
        state_depth_fit_weak_detection_rate=state_depth_fit_rate,
        non_directiveness_weak_detection_rate=non_directiveness_rate,
        non_bookishness_weak_detection_rate=non_bookishness_rate,
        kb_boundary_respect_hard_fail_detection_rate=kb_boundary_rate,
    ).to_dict()

    status.update(
        {
            "acceptable_candidate_raw_quote_hits": int(kb_boundary_calibration_report.get("acceptable_candidate_raw_quote_hits", 0)),
            "acceptable_candidate_authority_citation_hits": int(kb_boundary_calibration_report.get("acceptable_candidate_authority_citation_hits", 0)),
            "internal_only_not_for_direct_quote_respected": _as_bool(kb_boundary_calibration_report.get("internal_only_not_for_direct_quote_respected"), False),
            "no_runtime_authority_expansion_passed": no_runtime_authority_gate.get("final_status") == "passed",
            "runtime_activation_performed": False,
            "provider_called": False,
            "normal_user_apply_count": 0,
            "production_mutation_detected": not no_mutation_ok,
            "all_blocks_merged_mutated": _as_bool(no_mutation_proof.get("all_blocks_merged_mutated"), False),
            "registry_mutated": _as_bool(no_mutation_proof.get("registry_mutated"), False),
            "config_mutated": _as_bool(no_mutation_proof.get("config_mutated"), False),
            "chroma_reindex_performed": _as_bool(no_mutation_proof.get("chroma_reindex_performed"), False),
            "runtime_defaults_changed": _as_bool(no_mutation_proof.get("runtime_defaults_changed"), False),
            "artifact_encoding_hygiene_passed": artifact_hygiene_passed,
            "docs_synced": _as_bool(docs_sync.get("docs_synced"), False),
            "next_prd_decision": next_prd_decision,
            "blockers": blockers,
            "warnings": warnings,
        }
    )

    decision_payload = ResponseQualityCalibrationDecision(
        final_status=final_status,
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        next_prd_decision=next_prd_decision,
    ).to_dict()
    return status, decision_payload
