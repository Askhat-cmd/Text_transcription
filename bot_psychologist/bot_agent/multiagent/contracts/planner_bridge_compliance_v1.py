"""Planner Bridge vs Writer Move compliance comparison contracts (shadow-only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_OVERALL_STATUS = {
    "compatible",
    "tightens_constraints",
    "expected_divergence",
    "needs_review",
    "blocked",
}
_DEPTH = {"none", "low", "low_to_medium", "medium", "high"}


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


@dataclass
class PlannerBridgeComplianceShadow:
    schema_version: str = "planner_bridge_compliance_shadow_v1"
    activation_mode: str = "shadow_compare_only"
    apply_to_writer: bool = False
    apply_to_writer_contract: bool = False
    writer_prompt_changed: bool = False
    final_answer_changed: bool = False
    existing_writer_move: dict[str, Any] = field(default_factory=dict)
    planner_bridge_candidate: dict[str, Any] = field(default_factory=dict)
    compatibility: dict[str, Any] = field(default_factory=dict)
    candidate_delta: dict[str, Any] = field(default_factory=dict)
    blocked_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "planner_bridge_compliance_shadow_v1")
        self.activation_mode = "shadow_compare_only"
        self.apply_to_writer = False
        self.apply_to_writer_contract = False
        self.writer_prompt_changed = False
        self.final_answer_changed = False

        if not isinstance(self.existing_writer_move, dict):
            self.existing_writer_move = {}
        if not isinstance(self.planner_bridge_candidate, dict):
            self.planner_bridge_candidate = {}
        if not isinstance(self.compatibility, dict):
            self.compatibility = {}
        if not isinstance(self.candidate_delta, dict):
            self.candidate_delta = {}
        if not isinstance(self.trace, dict):
            self.trace = {}

        self.existing_writer_move = {
            "move": _as_str(self.existing_writer_move.get("move"), "validate_briefly"),
            "max_sentences": max(1, _as_int(self.existing_writer_move.get("max_sentences"), 5)),
            "max_questions": max(0, _as_int(self.existing_writer_move.get("max_questions"), 1)),
            "style": _as_str(self.existing_writer_move.get("style"), "brief_supportive"),
            "must_do": _as_list(self.existing_writer_move.get("must_do")),
            "must_not_do": _as_list(self.existing_writer_move.get("must_not_do")),
        }

        depth_limit = _as_str(self.planner_bridge_candidate.get("depth_limit"), "low_to_medium")
        if depth_limit not in _DEPTH:
            depth_limit = "low_to_medium"
        self.planner_bridge_candidate = {
            "status": _as_str(self.planner_bridge_candidate.get("status"), "candidate"),
            "response_goal_candidate": _as_str(
                self.planner_bridge_candidate.get("response_goal_candidate"), ""
            ),
            "response_mode_candidate": _as_str(
                self.planner_bridge_candidate.get("response_mode_candidate"), ""
            ),
            "depth_limit": depth_limit,
            "max_questions": max(0, _as_int(self.planner_bridge_candidate.get("max_questions"), 1)),
            "max_concepts": max(0, _as_int(self.planner_bridge_candidate.get("max_concepts"), 1)),
            "must_do_candidates": _as_list(self.planner_bridge_candidate.get("must_do_candidates")),
            "must_not_do_candidates": _as_list(
                self.planner_bridge_candidate.get("must_not_do_candidates")
            ),
            "kb_constraints": dict(self.planner_bridge_candidate.get("kb_constraints", {}))
            if isinstance(self.planner_bridge_candidate.get("kb_constraints"), dict)
            else {"kb_usage_mode": "none", "must_not_quote_source": True},
        }

        overall_status = _as_str(self.compatibility.get("overall_status"), "needs_review")
        if overall_status not in _OVERALL_STATUS:
            overall_status = "needs_review"
        self.compatibility = {
            "safety_compatible": _as_bool(self.compatibility.get("safety_compatible"), False),
            "depth_compatible": _as_bool(self.compatibility.get("depth_compatible"), False),
            "question_limit_compatible": _as_bool(
                self.compatibility.get("question_limit_compatible"), False
            ),
            "must_not_conflict_count": max(
                0, _as_int(self.compatibility.get("must_not_conflict_count"), 0)
            ),
            "writer_move_candidate_compatible": _as_bool(
                self.compatibility.get("writer_move_candidate_compatible"), False
            ),
            "kb_boundary_compatible": _as_bool(
                self.compatibility.get("kb_boundary_compatible"), False
            ),
            "overall_status": overall_status,
        }

        self.candidate_delta = {
            "tightened_question_limit": _as_bool(
                self.candidate_delta.get("tightened_question_limit"), False
            ),
            "tightened_depth": _as_bool(self.candidate_delta.get("tightened_depth"), False),
            "added_must_not_do": _as_list(self.candidate_delta.get("added_must_not_do")),
            "added_must_do": _as_list(self.candidate_delta.get("added_must_do")),
            "removed_constraints": _as_list(self.candidate_delta.get("removed_constraints")),
        }

        self.blocked_reasons = _as_list(self.blocked_reasons)
        self.warnings = _as_list(self.warnings)
        self.trace = {
            "builder": _as_str(self.trace.get("builder"), "planner_bridge_compliance_shadow_v1"),
            "rules_applied": _as_list(self.trace.get("rules_applied")),
            "source": "shadow_compare_only",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "activation_mode": "shadow_compare_only",
            "apply_to_writer": False,
            "apply_to_writer_contract": False,
            "writer_prompt_changed": False,
            "final_answer_changed": False,
            "existing_writer_move": dict(self.existing_writer_move),
            "planner_bridge_candidate": dict(self.planner_bridge_candidate),
            "compatibility": dict(self.compatibility),
            "candidate_delta": dict(self.candidate_delta),
            "blocked_reasons": list(self.blocked_reasons),
            "warnings": list(self.warnings),
            "trace": dict(self.trace),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannerBridgeComplianceShadow":
        return cls(
            schema_version=str(payload.get("schema_version", "planner_bridge_compliance_shadow_v1")),
            activation_mode=str(payload.get("activation_mode", "shadow_compare_only")),
            apply_to_writer=bool(payload.get("apply_to_writer", False)),
            apply_to_writer_contract=bool(payload.get("apply_to_writer_contract", False)),
            writer_prompt_changed=bool(payload.get("writer_prompt_changed", False)),
            final_answer_changed=bool(payload.get("final_answer_changed", False)),
            existing_writer_move=dict(payload.get("existing_writer_move", {}))
            if isinstance(payload.get("existing_writer_move"), dict)
            else {},
            planner_bridge_candidate=dict(payload.get("planner_bridge_candidate", {}))
            if isinstance(payload.get("planner_bridge_candidate"), dict)
            else {},
            compatibility=dict(payload.get("compatibility", {}))
            if isinstance(payload.get("compatibility"), dict)
            else {},
            candidate_delta=dict(payload.get("candidate_delta", {}))
            if isinstance(payload.get("candidate_delta"), dict)
            else {},
            blocked_reasons=list(payload.get("blocked_reasons", [])),
            warnings=list(payload.get("warnings", [])),
            trace=dict(payload.get("trace", {})) if isinstance(payload.get("trace"), dict) else {},
        )

