"""Contracts for PRD-046.1.18 response quality calibration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class ResponseQualityCalibrationGroupPlan:
    dimension: str = ""
    risk_description: str = ""
    example_failure_pattern: str = ""
    calibration_action: str = ""
    expected_detector_change: str = ""
    closure_condition: str = ""

    def __post_init__(self) -> None:
        self.dimension = _as_str(self.dimension)
        self.risk_description = _as_str(self.risk_description)
        self.example_failure_pattern = _as_str(self.example_failure_pattern)
        self.calibration_action = _as_str(self.calibration_action)
        self.expected_detector_change = _as_str(self.expected_detector_change)
        self.closure_condition = _as_str(self.closure_condition)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "risk_description": self.risk_description,
            "example_failure_pattern": self.example_failure_pattern,
            "calibration_action": self.calibration_action,
            "expected_detector_change": self.expected_detector_change,
            "closure_condition": self.closure_condition,
        }


@dataclass
class ResponseQualityCalibrationStatus:
    final_status: str = "blocked"
    decision: str = "blocked_source_gate_failed"
    source_gate_passed: bool = False
    weak_case_inventory_ready: bool = False
    calibration_plan_ready: bool = False
    expanded_scenario_catalog_ready: bool = False
    expanded_candidate_catalog_ready: bool = False
    scenario_count: int = 0
    candidate_profile_count: int = 0
    all_required_scenario_groups_present: bool = False
    all_required_candidate_profiles_present: bool = False
    rubric_dimension_count: int = 0
    all_required_dimensions_present: bool = False
    acceptable_candidate_pass_rate: float = 0.0
    weak_candidate_detection_rate: float = 0.0
    hard_fail_detection_rate: float = 0.0
    state_depth_fit_weak_detection_rate: float = 0.0
    non_directiveness_weak_detection_rate: float = 0.0
    non_bookishness_weak_detection_rate: float = 0.0
    kb_boundary_respect_hard_fail_detection_rate: float = 0.0

    def __post_init__(self) -> None:
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked_source_gate_failed")
        self.source_gate_passed = _as_bool(self.source_gate_passed)
        self.weak_case_inventory_ready = _as_bool(self.weak_case_inventory_ready)
        self.calibration_plan_ready = _as_bool(self.calibration_plan_ready)
        self.expanded_scenario_catalog_ready = _as_bool(self.expanded_scenario_catalog_ready)
        self.expanded_candidate_catalog_ready = _as_bool(self.expanded_candidate_catalog_ready)
        self.scenario_count = _as_int(self.scenario_count)
        self.candidate_profile_count = _as_int(self.candidate_profile_count)
        self.all_required_scenario_groups_present = _as_bool(self.all_required_scenario_groups_present)
        self.all_required_candidate_profiles_present = _as_bool(self.all_required_candidate_profiles_present)
        self.rubric_dimension_count = _as_int(self.rubric_dimension_count)
        self.all_required_dimensions_present = _as_bool(self.all_required_dimensions_present)
        self.acceptable_candidate_pass_rate = _as_float(self.acceptable_candidate_pass_rate)
        self.weak_candidate_detection_rate = _as_float(self.weak_candidate_detection_rate)
        self.hard_fail_detection_rate = _as_float(self.hard_fail_detection_rate)
        self.state_depth_fit_weak_detection_rate = _as_float(self.state_depth_fit_weak_detection_rate)
        self.non_directiveness_weak_detection_rate = _as_float(self.non_directiveness_weak_detection_rate)
        self.non_bookishness_weak_detection_rate = _as_float(self.non_bookishness_weak_detection_rate)
        self.kb_boundary_respect_hard_fail_detection_rate = _as_float(self.kb_boundary_respect_hard_fail_detection_rate)

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_status": self.final_status,
            "decision": self.decision,
            "source_gate_passed": self.source_gate_passed,
            "weak_case_inventory_ready": self.weak_case_inventory_ready,
            "calibration_plan_ready": self.calibration_plan_ready,
            "expanded_scenario_catalog_ready": self.expanded_scenario_catalog_ready,
            "expanded_candidate_catalog_ready": self.expanded_candidate_catalog_ready,
            "scenario_count": self.scenario_count,
            "candidate_profile_count": self.candidate_profile_count,
            "all_required_scenario_groups_present": self.all_required_scenario_groups_present,
            "all_required_candidate_profiles_present": self.all_required_candidate_profiles_present,
            "rubric_dimension_count": self.rubric_dimension_count,
            "all_required_dimensions_present": self.all_required_dimensions_present,
            "acceptable_candidate_pass_rate": self.acceptable_candidate_pass_rate,
            "weak_candidate_detection_rate": self.weak_candidate_detection_rate,
            "hard_fail_detection_rate": self.hard_fail_detection_rate,
            "state_depth_fit_weak_detection_rate": self.state_depth_fit_weak_detection_rate,
            "non_directiveness_weak_detection_rate": self.non_directiveness_weak_detection_rate,
            "non_bookishness_weak_detection_rate": self.non_bookishness_weak_detection_rate,
            "kb_boundary_respect_hard_fail_detection_rate": self.kb_boundary_respect_hard_fail_detection_rate,
        }


@dataclass
class ResponseQualityCalibrationDecision:
    schema_version: str = "diagnostic_center_response_quality_calibration_decision_v1"
    prd_id: str = "PRD-046.1.18"
    final_status: str = "blocked"
    decision: str = "blocked_source_gate_failed"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_prd_decision: str = "PRD-046.1.18-HF1"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_response_quality_calibration_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.18")
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "blocked_source_gate_failed")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]
        self.next_prd_decision = _as_str(self.next_prd_decision, "PRD-046.1.18-HF1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "next_prd_decision": self.next_prd_decision,
        }


@dataclass
class ResponseQualityCalibrationBundle:
    source_gate: dict[str, Any] = field(default_factory=dict)
    weak_case_inventory: dict[str, Any] = field(default_factory=dict)
    calibration_plan: dict[str, Any] = field(default_factory=dict)
    expanded_scenario_catalog: dict[str, Any] = field(default_factory=dict)
    expanded_candidate_catalog: dict[str, Any] = field(default_factory=dict)
    calibrated_eval_results: dict[str, Any] = field(default_factory=dict)
    weak_case_closure_status: dict[str, Any] = field(default_factory=dict)
    kb_boundary_calibration_status: dict[str, Any] = field(default_factory=dict)
    non_bookishness_calibration_status: dict[str, Any] = field(default_factory=dict)
    non_directiveness_calibration_status: dict[str, Any] = field(default_factory=dict)
    state_depth_fit_calibration_status: dict[str, Any] = field(default_factory=dict)
    no_runtime_authority_expansion_status: dict[str, Any] = field(default_factory=dict)
    no_mutation_status: dict[str, Any] = field(default_factory=dict)
    artifact_hygiene_status: dict[str, Any] = field(default_factory=dict)
    next_prd_decision: str = "PRD-046.1.18-HF1"

    def __post_init__(self) -> None:
        self.source_gate = _safe_dict(self.source_gate)
        self.weak_case_inventory = _safe_dict(self.weak_case_inventory)
        self.calibration_plan = _safe_dict(self.calibration_plan)
        self.expanded_scenario_catalog = _safe_dict(self.expanded_scenario_catalog)
        self.expanded_candidate_catalog = _safe_dict(self.expanded_candidate_catalog)
        self.calibrated_eval_results = _safe_dict(self.calibrated_eval_results)
        self.weak_case_closure_status = _safe_dict(self.weak_case_closure_status)
        self.kb_boundary_calibration_status = _safe_dict(self.kb_boundary_calibration_status)
        self.non_bookishness_calibration_status = _safe_dict(self.non_bookishness_calibration_status)
        self.non_directiveness_calibration_status = _safe_dict(self.non_directiveness_calibration_status)
        self.state_depth_fit_calibration_status = _safe_dict(self.state_depth_fit_calibration_status)
        self.no_runtime_authority_expansion_status = _safe_dict(self.no_runtime_authority_expansion_status)
        self.no_mutation_status = _safe_dict(self.no_mutation_status)
        self.artifact_hygiene_status = _safe_dict(self.artifact_hygiene_status)
        self.next_prd_decision = _as_str(self.next_prd_decision, "PRD-046.1.18-HF1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_gate": dict(self.source_gate),
            "weak_case_inventory": dict(self.weak_case_inventory),
            "calibration_plan": dict(self.calibration_plan),
            "expanded_scenario_catalog": dict(self.expanded_scenario_catalog),
            "expanded_candidate_catalog": dict(self.expanded_candidate_catalog),
            "calibrated_eval_results": dict(self.calibrated_eval_results),
            "weak_case_closure_status": dict(self.weak_case_closure_status),
            "kb_boundary_calibration_status": dict(self.kb_boundary_calibration_status),
            "non_bookishness_calibration_status": dict(self.non_bookishness_calibration_status),
            "non_directiveness_calibration_status": dict(self.non_directiveness_calibration_status),
            "state_depth_fit_calibration_status": dict(self.state_depth_fit_calibration_status),
            "no_runtime_authority_expansion_status": dict(self.no_runtime_authority_expansion_status),
            "no_mutation_status": dict(self.no_mutation_status),
            "artifact_hygiene_status": dict(self.artifact_hygiene_status),
            "next_prd_decision": self.next_prd_decision,
        }
