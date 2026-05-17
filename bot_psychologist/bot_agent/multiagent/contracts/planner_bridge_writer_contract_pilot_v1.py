"""Writer-contract pilot overlay contracts (shadow-only, non-mutating)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_DEPTH = {"none", "low", "low_to_medium", "medium", "high"}
_RISK = {"none", "low", "medium", "high"}
_READINESS = {"not_ready", "pilot_ready", "blocked"}


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int = 0, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class PlannerBridgeWriterContractPilotInput:
    writer_contract: dict[str, Any] = field(default_factory=dict)
    planner_bridge_compliance_shadow: dict[str, Any] = field(default_factory=dict)
    diagnostic_card: dict[str, Any] = field(default_factory=dict)
    thread_state: dict[str, Any] = field(default_factory=dict)
    state_snapshot: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.writer_contract = _safe_dict(self.writer_contract)
        self.planner_bridge_compliance_shadow = _safe_dict(self.planner_bridge_compliance_shadow)
        self.diagnostic_card = _safe_dict(self.diagnostic_card)
        self.thread_state = _safe_dict(self.thread_state)
        self.state_snapshot = _safe_dict(self.state_snapshot)

    def to_dict(self) -> dict[str, Any]:
        return {
            "writer_contract": dict(self.writer_contract),
            "planner_bridge_compliance_shadow": dict(self.planner_bridge_compliance_shadow),
            "diagnostic_card": dict(self.diagnostic_card),
            "thread_state": dict(self.thread_state),
            "state_snapshot": dict(self.state_snapshot),
        }


@dataclass
class PlannerBridgeWriterContractPilotOverlay:
    schema_version: str = "planner_bridge_writer_contract_pilot_overlay_v1"
    activation_mode: str = "pilot_shadow_only"
    apply_to_writer_contract: bool = False
    apply_to_writer_prompt: bool = False
    apply_to_final_answer: bool = False
    candidate_constraints: dict[str, Any] = field(default_factory=dict)
    merge_policy: dict[str, Any] = field(default_factory=dict)
    risk_assessment: dict[str, Any] = field(default_factory=dict)
    guardrails: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(
            self.schema_version,
            "planner_bridge_writer_contract_pilot_overlay_v1",
        )
        self.activation_mode = "pilot_shadow_only"
        self.apply_to_writer_contract = False
        self.apply_to_writer_prompt = False
        self.apply_to_final_answer = False

        candidate = _safe_dict(self.candidate_constraints)
        depth_limit = _as_str(candidate.get("depth_limit"), "low_to_medium")
        if depth_limit not in _DEPTH:
            depth_limit = "low_to_medium"
        self.candidate_constraints = {
            "response_goal": _as_str(candidate.get("response_goal"), ""),
            "response_mode": _as_str(candidate.get("response_mode"), "reflect"),
            "depth_limit": depth_limit,
            "max_questions": _as_int(candidate.get("max_questions"), default=0, minimum=0),
            "max_concepts": _as_int(candidate.get("max_concepts"), default=1, minimum=1),
            "must_do": _as_list(candidate.get("must_do")),
            "must_not_do": _as_list(candidate.get("must_not_do")),
            "kb_usage_mode": _as_str(candidate.get("kb_usage_mode"), "none"),
            "must_not_quote_source": bool(candidate.get("must_not_quote_source", True)),
        }

        merge = _safe_dict(self.merge_policy)
        self.merge_policy = {
            "mode": "non_mutating_compare_only",
            "allowed_fields": _as_list(merge.get("allowed_fields")),
            "blocked_fields": _as_list(merge.get("blocked_fields")),
        }

        risk = _safe_dict(self.risk_assessment)
        safety_risk = _as_str(risk.get("safety_risk"), "none")
        contract_risk = _as_str(risk.get("contract_conflict_risk"), "none")
        kb_risk = _as_str(risk.get("kb_boundary_risk"), "none")
        activation_readiness = _as_str(risk.get("activation_readiness"), "not_ready")
        if safety_risk not in _RISK:
            safety_risk = "none"
        if contract_risk not in _RISK:
            contract_risk = "none"
        if kb_risk not in _RISK:
            kb_risk = "none"
        if activation_readiness not in _READINESS:
            activation_readiness = "not_ready"
        self.risk_assessment = {
            "safety_risk": safety_risk,
            "contract_conflict_risk": contract_risk,
            "kb_boundary_risk": kb_risk,
            "activation_readiness": activation_readiness,
        }

        guardrails = _safe_dict(self.guardrails)
        self.guardrails = {
            "writer_contract_changed": _as_bool(guardrails.get("writer_contract_changed"), False),
            "writer_prompt_changed": _as_bool(guardrails.get("writer_prompt_changed"), False),
            "final_answer_changed": _as_bool(guardrails.get("final_answer_changed"), False),
            "provider_called": _as_bool(guardrails.get("provider_called"), False),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "activation_mode": "pilot_shadow_only",
            "apply_to_writer_contract": False,
            "apply_to_writer_prompt": False,
            "apply_to_final_answer": False,
            "candidate_constraints": dict(self.candidate_constraints),
            "merge_policy": dict(self.merge_policy),
            "risk_assessment": dict(self.risk_assessment),
            "guardrails": dict(self.guardrails),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerBridgeWriterContractPilotOverlay":
        return cls(
            schema_version=str(
                payload.get("schema_version", "planner_bridge_writer_contract_pilot_overlay_v1")
            ),
            activation_mode=str(payload.get("activation_mode", "pilot_shadow_only")),
            apply_to_writer_contract=bool(payload.get("apply_to_writer_contract", False)),
            apply_to_writer_prompt=bool(payload.get("apply_to_writer_prompt", False)),
            apply_to_final_answer=bool(payload.get("apply_to_final_answer", False)),
            candidate_constraints=_safe_dict(payload.get("candidate_constraints")),
            merge_policy=_safe_dict(payload.get("merge_policy")),
            risk_assessment=_safe_dict(payload.get("risk_assessment")),
            guardrails=_safe_dict(payload.get("guardrails")),
        )


@dataclass
class PlannerBridgeWriterContractPilotTrace:
    schema_version: str = "planner_bridge_writer_contract_pilot_trace_v1"
    builder: str = "planner_bridge_writer_contract_pilot_v1"
    rules_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(
            self.schema_version,
            "planner_bridge_writer_contract_pilot_trace_v1",
        )
        self.builder = _as_str(self.builder, "planner_bridge_writer_contract_pilot_v1")
        self.rules_applied = _as_list(self.rules_applied)
        self.warnings = _as_list(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "builder": self.builder,
            "rules_applied": list(self.rules_applied),
            "warnings": list(self.warnings),
        }


@dataclass
class PlannerBridgeWriterContractPilotResult:
    schema_version: str = "planner_bridge_writer_contract_pilot_result_v1"
    overlay: PlannerBridgeWriterContractPilotOverlay = field(
        default_factory=PlannerBridgeWriterContractPilotOverlay
    )
    writer_contract_hash_before_pilot: str = ""
    writer_contract_hash_after_pilot: str = ""
    writer_contract_changed_by_pilot: bool = False
    blocked_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace: PlannerBridgeWriterContractPilotTrace = field(
        default_factory=PlannerBridgeWriterContractPilotTrace
    )

    def __post_init__(self) -> None:
        self.schema_version = _as_str(
            self.schema_version,
            "planner_bridge_writer_contract_pilot_result_v1",
        )
        if not isinstance(self.overlay, PlannerBridgeWriterContractPilotOverlay):
            self.overlay = PlannerBridgeWriterContractPilotOverlay.from_dict(
                self.overlay if isinstance(self.overlay, dict) else {}
            )
        self.writer_contract_hash_before_pilot = _as_str(self.writer_contract_hash_before_pilot, "")
        self.writer_contract_hash_after_pilot = _as_str(self.writer_contract_hash_after_pilot, "")
        self.writer_contract_changed_by_pilot = bool(self.writer_contract_changed_by_pilot)
        self.blocked_reasons = _as_list(self.blocked_reasons)
        self.warnings = _as_list(self.warnings)
        if not isinstance(self.trace, PlannerBridgeWriterContractPilotTrace):
            self.trace = PlannerBridgeWriterContractPilotTrace(
                **(self.trace if isinstance(self.trace, dict) else {})
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "overlay": self.overlay.to_dict(),
            "writer_contract_hash_before_pilot": self.writer_contract_hash_before_pilot,
            "writer_contract_hash_after_pilot": self.writer_contract_hash_after_pilot,
            "writer_contract_changed_by_pilot": self.writer_contract_changed_by_pilot,
            "blocked_reasons": list(self.blocked_reasons),
            "warnings": list(self.warnings),
            "trace": self.trace.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerBridgeWriterContractPilotResult":
        return cls(
            schema_version=str(payload.get("schema_version", "planner_bridge_writer_contract_pilot_result_v1")),
            overlay=PlannerBridgeWriterContractPilotOverlay.from_dict(
                _safe_dict(payload.get("overlay"))
            ),
            writer_contract_hash_before_pilot=str(payload.get("writer_contract_hash_before_pilot", "")),
            writer_contract_hash_after_pilot=str(payload.get("writer_contract_hash_after_pilot", "")),
            writer_contract_changed_by_pilot=bool(payload.get("writer_contract_changed_by_pilot", False)),
            blocked_reasons=_as_list(payload.get("blocked_reasons")),
            warnings=_as_list(payload.get("warnings")),
            trace=PlannerBridgeWriterContractPilotTrace(**_safe_dict(payload.get("trace"))),
        )
