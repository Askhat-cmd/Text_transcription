"""Prompt-constraint pilot runtime decision contracts (default-off, limited apply)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_ALLOWED_MODES = {"disabled", "shadow_only", "test_apply"}


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class PromptConstraintPilotRuntimeInput:
    user_id: str = ""
    writer_prompt_replay_result: dict[str, Any] = field(default_factory=dict)
    writer_contract_pilot: dict[str, Any] = field(default_factory=dict)
    state_snapshot: dict[str, Any] = field(default_factory=dict)
    thread_state: dict[str, Any] = field(default_factory=dict)
    feature_flag_snapshot: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.user_id = _as_str(self.user_id, "")
        self.writer_prompt_replay_result = _safe_dict(self.writer_prompt_replay_result)
        self.writer_contract_pilot = _safe_dict(self.writer_contract_pilot)
        self.state_snapshot = _safe_dict(self.state_snapshot)
        self.thread_state = _safe_dict(self.thread_state)
        self.feature_flag_snapshot = _safe_dict(self.feature_flag_snapshot)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "writer_prompt_replay_result": dict(self.writer_prompt_replay_result),
            "writer_contract_pilot": dict(self.writer_contract_pilot),
            "state_snapshot": dict(self.state_snapshot),
            "thread_state": dict(self.thread_state),
            "feature_flag_snapshot": dict(self.feature_flag_snapshot),
        }


@dataclass
class PromptConstraintPilotRuntimeTrace:
    schema_version: str = "prompt_constraint_pilot_runtime_trace_v1"
    builder: str = "prompt_constraint_pilot_runtime_v1"
    rules_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_pilot_runtime_trace_v1")
        self.builder = _as_str(self.builder, "prompt_constraint_pilot_runtime_v1")
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
class PromptConstraintPilotRuntimeDecision:
    schema_version: str = "prompt_constraint_pilot_runtime_decision_v1"
    activation_mode: str = "disabled"
    apply_to_writer_prompt: bool = False
    apply_to_writer_contract: bool = False
    apply_to_final_answer: bool = False
    rollback_active: bool = True
    eligible_user: bool = False
    feature_flag_snapshot: dict[str, Any] = field(default_factory=dict)
    candidate_constraints: dict[str, Any] = field(default_factory=dict)
    blocked_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace: PromptConstraintPilotRuntimeTrace = field(default_factory=PromptConstraintPilotRuntimeTrace)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "prompt_constraint_pilot_runtime_decision_v1")
        if self.activation_mode not in _ALLOWED_MODES:
            self.activation_mode = "disabled"
        self.rollback_active = _as_bool(self.rollback_active, True)
        self.eligible_user = _as_bool(self.eligible_user, False)
        self.feature_flag_snapshot = _safe_dict(self.feature_flag_snapshot)
        self.candidate_constraints = _safe_dict(self.candidate_constraints)
        self.blocked_reasons = _as_list(self.blocked_reasons)
        self.warnings = _as_list(self.warnings)
        if not isinstance(self.trace, PromptConstraintPilotRuntimeTrace):
            self.trace = PromptConstraintPilotRuntimeTrace(**_safe_dict(self.trace))

        # hard invariants for PRD-046.1.6
        self.apply_to_writer_contract = False
        self.apply_to_final_answer = False

        if self.rollback_active:
            self.activation_mode = "disabled"
            self.apply_to_writer_prompt = False
        elif self.activation_mode != "test_apply":
            self.apply_to_writer_prompt = False
        else:
            self.apply_to_writer_prompt = bool(self.apply_to_writer_prompt)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "activation_mode": self.activation_mode,
            "apply_to_writer_prompt": bool(self.apply_to_writer_prompt),
            "apply_to_writer_contract": False,
            "apply_to_final_answer": False,
            "rollback_active": bool(self.rollback_active),
            "eligible_user": bool(self.eligible_user),
            "feature_flag_snapshot": dict(self.feature_flag_snapshot),
            "candidate_constraints": dict(self.candidate_constraints),
            "blocked_reasons": list(self.blocked_reasons),
            "warnings": list(self.warnings),
            "trace": self.trace.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PromptConstraintPilotRuntimeDecision":
        return cls(
            schema_version=str(payload.get("schema_version", "prompt_constraint_pilot_runtime_decision_v1")),
            activation_mode=str(payload.get("activation_mode", "disabled")),
            apply_to_writer_prompt=bool(payload.get("apply_to_writer_prompt", False)),
            apply_to_writer_contract=bool(payload.get("apply_to_writer_contract", False)),
            apply_to_final_answer=bool(payload.get("apply_to_final_answer", False)),
            rollback_active=bool(payload.get("rollback_active", True)),
            eligible_user=bool(payload.get("eligible_user", False)),
            feature_flag_snapshot=_safe_dict(payload.get("feature_flag_snapshot")),
            candidate_constraints=_safe_dict(payload.get("candidate_constraints")),
            blocked_reasons=_as_list(payload.get("blocked_reasons")),
            warnings=_as_list(payload.get("warnings")),
            trace=PromptConstraintPilotRuntimeTrace(**_safe_dict(payload.get("trace"))),
        )
