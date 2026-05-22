"""Contracts for PRD-046.1.35-HF4 creator live behavior calibration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PRD_ID = "PRD-046.1.35-HF4"
SOURCE_PRD_ID = "PRD-046.1.35-HF3"


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


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


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


@dataclass
class HF4Scorecard:
    schema_version: str = "creator_live_behavior_hf4_scorecard_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "hf4_blocked_example_request_routing_failed"

    source_gate: str = "blocked"
    example_request_routing_gate: str = "blocked"
    anti_regulate_loop_gate: str = "blocked"
    practice_rejection_memory_gate: str = "blocked"
    writer_move_calibration_gate: str = "blocked"
    creator_live_behavior_smoke_gate: str = "blocked"
    writer_chunks_display_gate: str = "blocked"
    rag_regression_gate: str = "blocked"
    normal_user_no_effect_gate: str = "blocked"
    trace_sanitization_gate: str = "blocked"
    provider_budget_gate: str = "blocked"
    no_mutation_proof: str = "blocked"
    artifact_encoding_hygiene: str = "blocked"

    example_cases_total: int = 0
    example_cases_passed: int = 0
    practice_suppressed_after_rejection_count: int = 0
    unexpected_regulate_first_count: int = 0
    unexpected_body_action_count: int = 0
    true_regulate_case_passed: bool = False

    writer_chunks_count: int = 0
    writer_chunks_non_empty_preview_count: int = 0
    writer_chunks_empty_preview_count: int = 0

    botdb_chunks_returned: int = 0
    knowledge_policy_included_writer_count: int = 0
    context_assembly_knowledge_hits_count: int = 0
    writer_prompt_knowledge_hits_count: int = 0

    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    all_users_mode_enabled: bool = False

    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_prd_recommendation: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "creator_live_behavior_hf4_scorecard_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "hf4_blocked_example_request_routing_failed")
        for field_name in (
            "source_gate",
            "example_request_routing_gate",
            "anti_regulate_loop_gate",
            "practice_rejection_memory_gate",
            "writer_move_calibration_gate",
            "creator_live_behavior_smoke_gate",
            "writer_chunks_display_gate",
            "rag_regression_gate",
            "normal_user_no_effect_gate",
            "trace_sanitization_gate",
            "provider_budget_gate",
            "no_mutation_proof",
            "artifact_encoding_hygiene",
        ):
            setattr(self, field_name, _as_str(getattr(self, field_name), "blocked"))

        for field_name in (
            "example_cases_total",
            "example_cases_passed",
            "practice_suppressed_after_rejection_count",
            "unexpected_regulate_first_count",
            "unexpected_body_action_count",
            "writer_chunks_count",
            "writer_chunks_non_empty_preview_count",
            "writer_chunks_empty_preview_count",
            "botdb_chunks_returned",
            "knowledge_policy_included_writer_count",
            "context_assembly_knowledge_hits_count",
            "writer_prompt_knowledge_hits_count",
        ):
            setattr(self, field_name, _as_int(getattr(self, field_name), 0))

        self.true_regulate_case_passed = _as_bool(self.true_regulate_case_passed, False)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.all_users_mode_enabled = _as_bool(self.all_users_mode_enabled, False)
        self.blockers = [str(x) for x in _safe_list(self.blockers)]
        self.warnings = [str(x) for x in _safe_list(self.warnings)]
        self.next_prd_recommendation = _as_str(self.next_prd_recommendation)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class HF4Decision:
    schema_version: str = "creator_live_behavior_hf4_decision_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "hf4_blocked_example_request_routing_failed"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "creator_live_behavior_hf4_decision_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "hf4_blocked_example_request_routing_failed")
        self.blockers = [str(x) for x in _safe_list(self.blockers)]
        self.warnings = [str(x) for x in _safe_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


__all__ = [
    "PRD_ID",
    "SOURCE_PRD_ID",
    "HF4Scorecard",
    "HF4Decision",
]

