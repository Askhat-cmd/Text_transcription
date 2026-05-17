"""Planner Bridge v1 contracts (shadow-only, non-user-facing)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_STATUS = {"candidate", "limited", "blocked"}
_ACTIVATION = {"shadow_only"}
_DEPTH = {"none", "low", "low_to_medium", "medium", "high"}
_KB_USAGE = {"none", "internal_lens_only", "practice_candidate_only"}


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


@dataclass
class PlannerBridgeGuardrails:
    apply_to_writer: bool = False
    apply_to_writer_contract: bool = False
    activation_mode: str = "shadow_only"
    user_path_effect: str = "none"

    def __post_init__(self) -> None:
        self.apply_to_writer = False
        self.apply_to_writer_contract = False
        if self.activation_mode not in _ACTIVATION:
            self.activation_mode = "shadow_only"
        self.user_path_effect = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "apply_to_writer": False,
            "apply_to_writer_contract": False,
            "activation_mode": self.activation_mode,
            "user_path_effect": "none",
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerBridgeGuardrails":
        return cls(
            apply_to_writer=bool(payload.get("apply_to_writer", False)),
            apply_to_writer_contract=bool(payload.get("apply_to_writer_contract", False)),
            activation_mode=str(payload.get("activation_mode", "shadow_only")),
            user_path_effect=str(payload.get("user_path_effect", "none")),
        )


@dataclass
class PlannerBridgeTrace:
    version: str = "planner_bridge_trace_v1"
    builder: str = "planner_bridge_candidate_v1"
    divergence_severity: str = "compatible"
    rules_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    expected_divergence: bool = False

    def __post_init__(self) -> None:
        self.version = _as_str(self.version, "planner_bridge_trace_v1")
        self.builder = _as_str(self.builder, "planner_bridge_candidate_v1")
        self.divergence_severity = _as_str(self.divergence_severity, "compatible")
        self.rules_applied = _as_list(self.rules_applied)
        self.warnings = _as_list(self.warnings)
        self.expected_divergence = bool(self.expected_divergence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "builder": self.builder,
            "divergence_severity": self.divergence_severity,
            "rules_applied": list(self.rules_applied),
            "warnings": list(self.warnings),
            "expected_divergence": bool(self.expected_divergence),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerBridgeTrace":
        return cls(
            version=str(payload.get("version", "planner_bridge_trace_v1")),
            builder=str(payload.get("builder", "planner_bridge_candidate_v1")),
            divergence_severity=str(payload.get("divergence_severity", "compatible")),
            rules_applied=list(payload.get("rules_applied", [])),
            warnings=list(payload.get("warnings", [])),
            expected_divergence=bool(payload.get("expected_divergence", False)),
        )


@dataclass
class PlannerBridgeInput:
    diagnostic_center_output: dict[str, Any] = field(default_factory=dict)
    divergence: dict[str, Any] = field(default_factory=dict)
    divergence_severity: str = "compatible"
    state_snapshot: dict[str, Any] = field(default_factory=dict)
    thread_state: dict[str, Any] = field(default_factory=dict)
    diagnostic_card: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.diagnostic_center_output, dict):
            self.diagnostic_center_output = {}
        if not isinstance(self.divergence, dict):
            self.divergence = {}
        if not isinstance(self.state_snapshot, dict):
            self.state_snapshot = {}
        if not isinstance(self.thread_state, dict):
            self.thread_state = {}
        if not isinstance(self.diagnostic_card, dict):
            self.diagnostic_card = {}
        self.divergence_severity = _as_str(self.divergence_severity, "compatible")

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagnostic_center_output": dict(self.diagnostic_center_output),
            "divergence": dict(self.divergence),
            "divergence_severity": self.divergence_severity,
            "state_snapshot": dict(self.state_snapshot),
            "thread_state": dict(self.thread_state),
            "diagnostic_card": dict(self.diagnostic_card),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerBridgeInput":
        return cls(
            diagnostic_center_output=dict(payload.get("diagnostic_center_output", {}))
            if isinstance(payload.get("diagnostic_center_output"), dict)
            else {},
            divergence=dict(payload.get("divergence", {}))
            if isinstance(payload.get("divergence"), dict)
            else {},
            divergence_severity=str(payload.get("divergence_severity", "compatible")),
            state_snapshot=dict(payload.get("state_snapshot", {}))
            if isinstance(payload.get("state_snapshot"), dict)
            else {},
            thread_state=dict(payload.get("thread_state", {}))
            if isinstance(payload.get("thread_state"), dict)
            else {},
            diagnostic_card=dict(payload.get("diagnostic_card", {}))
            if isinstance(payload.get("diagnostic_card"), dict)
            else {},
        )


@dataclass
class PlannerBridgeOutput:
    schema_version: str = "planner_bridge_output_v1"
    status: str = "candidate"
    activation_mode: str = "shadow_only"
    apply_to_writer: bool = False
    apply_to_writer_contract: bool = False
    response_goal_candidate: str = ""
    response_mode_candidate: str = ""
    depth_limit: str = "low_to_medium"
    max_questions: int = 1
    max_concepts: int = 1
    must_do_candidates: list[str] = field(default_factory=list)
    must_not_do_candidates: list[str] = field(default_factory=list)
    safety_constraints: list[str] = field(default_factory=list)
    kb_constraints: dict[str, Any] = field(
        default_factory=lambda: {
            "kb_usage_mode": "none",
            "must_not_quote_source": True,
        }
    )
    confidence: float = 0.0
    blocked_reasons: list[str] = field(default_factory=list)
    guardrails: PlannerBridgeGuardrails = field(default_factory=PlannerBridgeGuardrails)
    trace: PlannerBridgeTrace = field(default_factory=PlannerBridgeTrace)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "planner_bridge_output_v1")
        if self.status not in _STATUS:
            self.status = "candidate"
        if self.activation_mode not in _ACTIVATION:
            self.activation_mode = "shadow_only"
        self.apply_to_writer = False
        self.apply_to_writer_contract = False
        self.response_goal_candidate = _as_str(self.response_goal_candidate, "")
        self.response_mode_candidate = _as_str(self.response_mode_candidate, "")
        if self.depth_limit not in _DEPTH:
            self.depth_limit = "low_to_medium"
        try:
            self.max_questions = max(0, int(self.max_questions))
        except (TypeError, ValueError):
            self.max_questions = 1
        try:
            self.max_concepts = max(0, int(self.max_concepts))
        except (TypeError, ValueError):
            self.max_concepts = 1
        self.must_do_candidates = _as_list(self.must_do_candidates)[:6]
        self.must_not_do_candidates = _as_list(self.must_not_do_candidates)[:8]
        self.safety_constraints = _as_list(self.safety_constraints)
        if not isinstance(self.kb_constraints, dict):
            self.kb_constraints = {}
        kb_mode = _as_str(self.kb_constraints.get("kb_usage_mode"), "none")
        if kb_mode not in _KB_USAGE:
            kb_mode = "none"
        self.kb_constraints = {
            "kb_usage_mode": kb_mode,
            "must_not_quote_source": bool(self.kb_constraints.get("must_not_quote_source", True)),
        }
        try:
            self.confidence = max(0.0, min(1.0, float(self.confidence)))
        except (TypeError, ValueError):
            self.confidence = 0.0
        self.blocked_reasons = _as_list(self.blocked_reasons)
        if not isinstance(self.guardrails, PlannerBridgeGuardrails):
            self.guardrails = PlannerBridgeGuardrails.from_dict(
                self.guardrails if isinstance(self.guardrails, dict) else {}
            )
        if not isinstance(self.trace, PlannerBridgeTrace):
            self.trace = PlannerBridgeTrace.from_dict(
                self.trace if isinstance(self.trace, dict) else {}
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "activation_mode": "shadow_only",
            "apply_to_writer": False,
            "apply_to_writer_contract": False,
            "response_goal_candidate": self.response_goal_candidate,
            "response_mode_candidate": self.response_mode_candidate,
            "depth_limit": self.depth_limit,
            "max_questions": int(self.max_questions),
            "max_concepts": int(self.max_concepts),
            "must_do_candidates": list(self.must_do_candidates),
            "must_not_do_candidates": list(self.must_not_do_candidates),
            "safety_constraints": list(self.safety_constraints),
            "kb_constraints": dict(self.kb_constraints),
            "confidence": float(self.confidence),
            "blocked_reasons": list(self.blocked_reasons),
            "guardrails": self.guardrails.to_dict(),
            "trace": self.trace.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerBridgeOutput":
        guardrails_raw = payload.get("guardrails")
        trace_raw = payload.get("trace")
        return cls(
            schema_version=str(payload.get("schema_version", "planner_bridge_output_v1")),
            status=str(payload.get("status", "candidate")),
            activation_mode=str(payload.get("activation_mode", "shadow_only")),
            apply_to_writer=bool(payload.get("apply_to_writer", False)),
            apply_to_writer_contract=bool(payload.get("apply_to_writer_contract", False)),
            response_goal_candidate=str(payload.get("response_goal_candidate", "")),
            response_mode_candidate=str(payload.get("response_mode_candidate", "")),
            depth_limit=str(payload.get("depth_limit", "low_to_medium")),
            max_questions=int(payload.get("max_questions", 1) or 1),
            max_concepts=int(payload.get("max_concepts", 1) or 1),
            must_do_candidates=list(payload.get("must_do_candidates", [])),
            must_not_do_candidates=list(payload.get("must_not_do_candidates", [])),
            safety_constraints=list(payload.get("safety_constraints", [])),
            kb_constraints=dict(payload.get("kb_constraints", {}))
            if isinstance(payload.get("kb_constraints"), dict)
            else {},
            confidence=float(payload.get("confidence", 0.0) or 0.0),
            blocked_reasons=list(payload.get("blocked_reasons", [])),
            guardrails=PlannerBridgeGuardrails.from_dict(guardrails_raw)
            if isinstance(guardrails_raw, dict)
            else PlannerBridgeGuardrails(),
            trace=PlannerBridgeTrace.from_dict(trace_raw)
            if isinstance(trace_raw, dict)
            else PlannerBridgeTrace(),
        )
