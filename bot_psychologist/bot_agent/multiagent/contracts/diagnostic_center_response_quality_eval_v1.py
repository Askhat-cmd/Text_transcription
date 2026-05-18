"""Contracts for PRD-046.1.17 response quality eval pack."""

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
class ResponseQualityExpectedState:
    nervous_state: str = "window"
    intent: str = "explore"
    openness: str = "open"
    ok_position: str = "I+W+"

    def __post_init__(self) -> None:
        self.nervous_state = _as_str(self.nervous_state, "window")
        self.intent = _as_str(self.intent, "explore")
        self.openness = _as_str(self.openness, "open")
        self.ok_position = _as_str(self.ok_position, "I+W+")

    def to_dict(self) -> dict[str, Any]:
        return {
            "nervous_state": self.nervous_state,
            "intent": self.intent,
            "openness": self.openness,
            "ok_position": self.ok_position,
        }


@dataclass
class ResponseQualityScenario:
    scenario_id: str = ""
    title: str = ""
    scenario_group: str = ""
    user_message: str = ""
    recent_context: list[str] = field(default_factory=list)
    expected_state: dict[str, Any] = field(default_factory=dict)
    thread: dict[str, Any] = field(default_factory=dict)
    manager_expectation: dict[str, Any] = field(default_factory=dict)
    kb_boundary_expectation: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.scenario_id = _as_str(self.scenario_id, "")
        self.title = _as_str(self.title, "")
        self.scenario_group = _as_str(self.scenario_group, "")
        self.user_message = _as_str(self.user_message, "")
        self.recent_context = [str(item) for item in _as_list(self.recent_context)]
        self.expected_state = _safe_dict(self.expected_state)
        self.thread = _safe_dict(self.thread)
        self.manager_expectation = _safe_dict(self.manager_expectation)
        self.kb_boundary_expectation = _safe_dict(self.kb_boundary_expectation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "scenario_group": self.scenario_group,
            "user_message": self.user_message,
            "recent_context": list(self.recent_context),
            "expected_state": dict(self.expected_state),
            "thread": dict(self.thread),
            "manager_expectation": dict(self.manager_expectation),
            "kb_boundary_expectation": dict(self.kb_boundary_expectation),
        }


@dataclass
class ResponseQualityRubric:
    dimension: str = ""
    description: str = ""
    score_range: list[int] = field(default_factory=lambda: [0, 1, 2])
    pass_threshold: int = 1
    hard_fail_conditions: list[str] = field(default_factory=list)
    positive_markers: list[str] = field(default_factory=list)
    negative_markers: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.dimension = _as_str(self.dimension, "")
        self.description = _as_str(self.description, "")
        self.score_range = [_as_int(item, 0) for item in _as_list(self.score_range)]
        self.pass_threshold = _as_int(self.pass_threshold, 1)
        self.hard_fail_conditions = [str(item) for item in _as_list(self.hard_fail_conditions)]
        self.positive_markers = [str(item) for item in _as_list(self.positive_markers)]
        self.negative_markers = [str(item) for item in _as_list(self.negative_markers)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "description": self.description,
            "score_range": list(self.score_range),
            "pass_threshold": self.pass_threshold,
            "hard_fail_conditions": list(self.hard_fail_conditions),
            "positive_markers": list(self.positive_markers),
            "negative_markers": list(self.negative_markers),
        }


@dataclass
class ResponseQualityDimensionScore:
    dimension: str = ""
    score: int = 0
    passed: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        self.dimension = _as_str(self.dimension, "")
        self.score = _as_int(self.score, 0)
        self.passed = _as_bool(self.passed, False)
        self.notes = _as_str(self.notes, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "passed": self.passed,
            "notes": self.notes,
        }


@dataclass
class ResponseQualityEvalResult:
    scenario_id: str = ""
    candidate_id: str = ""
    candidate_type: str = "weak"
    dimension_scores: dict[str, Any] = field(default_factory=dict)
    hard_fail_detected: bool = False
    final_status: str = "failed"
    failed_dimensions: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.scenario_id = _as_str(self.scenario_id, "")
        self.candidate_id = _as_str(self.candidate_id, "")
        self.candidate_type = _as_str(self.candidate_type, "weak")
        self.dimension_scores = _safe_dict(self.dimension_scores)
        self.hard_fail_detected = _as_bool(self.hard_fail_detected, False)
        self.final_status = _as_str(self.final_status, "failed")
        self.failed_dimensions = [str(item) for item in _as_list(self.failed_dimensions)]
        self.reasons = [str(item) for item in _as_list(self.reasons)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "candidate_id": self.candidate_id,
            "candidate_type": self.candidate_type,
            "dimension_scores": dict(self.dimension_scores),
            "hard_fail_detected": self.hard_fail_detected,
            "final_status": self.final_status,
            "failed_dimensions": list(self.failed_dimensions),
            "reasons": list(self.reasons),
        }


@dataclass
class ResponseQualityWeakCase:
    scenario_id: str = ""
    dimension: str = ""
    candidate_id: str = ""
    failure_reason: str = ""
    recommended_fix_type: str = "rubric_calibration"
    severity: str = "low"

    def __post_init__(self) -> None:
        self.scenario_id = _as_str(self.scenario_id, "")
        self.dimension = _as_str(self.dimension, "")
        self.candidate_id = _as_str(self.candidate_id, "")
        self.failure_reason = _as_str(self.failure_reason, "")
        self.recommended_fix_type = _as_str(self.recommended_fix_type, "rubric_calibration")
        self.severity = _as_str(self.severity, "low")

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "dimension": self.dimension,
            "candidate_id": self.candidate_id,
            "failure_reason": self.failure_reason,
            "recommended_fix_type": self.recommended_fix_type,
            "severity": self.severity,
        }


@dataclass
class ResponseQualityScorecard:
    prd_id: str = "PRD-046.1.17"
    final_status: str = "failed"
    decision: str = "blocked_source_gate_failed"
    scenario_count: int = 0
    required_scenario_groups_present: bool = False
    rubric_dimension_count: int = 0
    all_required_dimensions_present: bool = False
    acceptable_candidate_pass_rate: float = 0.0
    weak_candidate_detection_rate: float = 0.0
    hard_fail_detection_rate: float = 0.0

    def __post_init__(self) -> None:
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.17")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "blocked_source_gate_failed")
        self.scenario_count = _as_int(self.scenario_count, 0)
        self.required_scenario_groups_present = _as_bool(self.required_scenario_groups_present, False)
        self.rubric_dimension_count = _as_int(self.rubric_dimension_count, 0)
        self.all_required_dimensions_present = _as_bool(self.all_required_dimensions_present, False)
        self.acceptable_candidate_pass_rate = _as_float(self.acceptable_candidate_pass_rate, 0.0)
        self.weak_candidate_detection_rate = _as_float(self.weak_candidate_detection_rate, 0.0)
        self.hard_fail_detection_rate = _as_float(self.hard_fail_detection_rate, 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prd_id": self.prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "scenario_count": self.scenario_count,
            "required_scenario_groups_present": self.required_scenario_groups_present,
            "rubric_dimension_count": self.rubric_dimension_count,
            "all_required_dimensions_present": self.all_required_dimensions_present,
            "acceptable_candidate_pass_rate": self.acceptable_candidate_pass_rate,
            "weak_candidate_detection_rate": self.weak_candidate_detection_rate,
            "hard_fail_detection_rate": self.hard_fail_detection_rate,
        }


@dataclass
class ResponseQualityGateDecision:
    schema_version: str = "diagnostic_center_response_quality_eval_decision_v1"
    prd_id: str = "PRD-046.1.17"
    final_status: str = "failed"
    decision: str = "blocked_source_gate_failed"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_response_quality_eval_decision_v1")
        self.prd_id = _as_str(self.prd_id, "PRD-046.1.17")
        self.final_status = _as_str(self.final_status, "failed")
        self.decision = _as_str(self.decision, "blocked_source_gate_failed")
        self.blockers = [str(item) for item in _as_list(self.blockers)]
        self.warnings = [str(item) for item in _as_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prd_id": self.prd_id,
            "final_status": self.final_status,
            "decision": self.decision,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }
