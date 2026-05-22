"""Contracts for PRD-046.1.35-HF3 creator live RAG evidence sync."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PRD_ID = "PRD-046.1.35-HF3"
SOURCE_PRD_ID = "PRD-046.1.35-HF2"


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


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


@dataclass
class CreatorLiveTurnProof:
    schema_version: str = "creator_live_turn_proof_v1"
    prd_id: str = PRD_ID
    query_id: str = ""
    query: str = ""
    actual_live_turn: bool = False
    turn_id: str = ""
    session_id_hash: str = ""
    user_id_hash: str = ""
    answer_received: bool = False
    trace_available: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "creator_live_turn_proof_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.query_id = _as_str(self.query_id)
        self.query = _as_str(self.query)
        self.actual_live_turn = _as_bool(self.actual_live_turn, False)
        self.turn_id = _as_str(self.turn_id)
        self.session_id_hash = _as_str(self.session_id_hash)
        self.user_id_hash = _as_str(self.user_id_hash)
        self.answer_received = _as_bool(self.answer_received, False)
        self.trace_available = _as_bool(self.trace_available, False)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class HF3Scorecard:
    schema_version: str = "creator_live_rag_delivery_hf3_scorecard_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "hf3_blocked_runtime_reload_or_trace_mismatch"

    source_gate: str = "blocked"
    runtime_reload_gate: str = "blocked"
    botdb_query_gate: str = "blocked"
    memory_retrieval_gate: str = "blocked"
    knowledge_policy_gate: str = "blocked"
    context_assembly_gate: str = "blocked"
    writer_prompt_delivery_gate: str = "blocked"
    web_trace_alignment_gate: str = "blocked"

    writer_kb_truncation_gate: str = "warning"
    truncation_detected: bool = True
    truncation_blocker: bool = False
    kb_context_v2_backlog: bool = True

    creator_live_turn_gate: str = "blocked"
    normal_user_no_effect_gate: str = "blocked"
    trace_sanitization_gate: str = "blocked"
    provider_budget_gate: str = "blocked"
    no_mutation_proof: str = "blocked"
    artifact_encoding_hygiene: str = "blocked"

    botdb_chunks_returned: int = 0
    rag_raw_hits_count: int = 0
    rag_filtered_hits_count: int = 0
    rag_salvaged_hits_count: int = 0
    knowledge_policy_input_hits_count: int = 0
    knowledge_policy_included_writer_count: int = 0
    context_assembly_knowledge_hits_count: int = 0
    writer_prompt_knowledge_hits_count: int = 0
    web_trace_chunks_in_writer_count: int = 0
    has_relevant_knowledge: bool = False
    writer_prompt_contains_knowledge_rag_hits: bool = False
    actual_live_turn_evidence_count: int = 0

    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    all_users_mode_enabled: bool = False

    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_prd_recommendation: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "creator_live_rag_delivery_hf3_scorecard_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "hf3_blocked_runtime_reload_or_trace_mismatch")
        for field_name in (
            "source_gate",
            "runtime_reload_gate",
            "botdb_query_gate",
            "memory_retrieval_gate",
            "knowledge_policy_gate",
            "context_assembly_gate",
            "writer_prompt_delivery_gate",
            "web_trace_alignment_gate",
            "writer_kb_truncation_gate",
            "creator_live_turn_gate",
            "normal_user_no_effect_gate",
            "trace_sanitization_gate",
            "provider_budget_gate",
            "no_mutation_proof",
            "artifact_encoding_hygiene",
        ):
            setattr(self, field_name, _as_str(getattr(self, field_name), "blocked"))

        self.truncation_detected = _as_bool(self.truncation_detected, True)
        self.truncation_blocker = _as_bool(self.truncation_blocker, False)
        self.kb_context_v2_backlog = _as_bool(self.kb_context_v2_backlog, True)

        for field_name in (
            "botdb_chunks_returned",
            "rag_raw_hits_count",
            "rag_filtered_hits_count",
            "rag_salvaged_hits_count",
            "knowledge_policy_input_hits_count",
            "knowledge_policy_included_writer_count",
            "context_assembly_knowledge_hits_count",
            "writer_prompt_knowledge_hits_count",
            "web_trace_chunks_in_writer_count",
            "actual_live_turn_evidence_count",
        ):
            setattr(self, field_name, _as_int(getattr(self, field_name), 0))

        self.has_relevant_knowledge = _as_bool(self.has_relevant_knowledge, False)
        self.writer_prompt_contains_knowledge_rag_hits = _as_bool(self.writer_prompt_contains_knowledge_rag_hits, False)
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
class HF3Decision:
    schema_version: str = "creator_live_rag_delivery_hf3_decision_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "hf3_blocked_runtime_reload_or_trace_mismatch"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "creator_live_rag_delivery_hf3_decision_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "hf3_blocked_runtime_reload_or_trace_mismatch")
        self.blockers = [str(x) for x in _safe_list(self.blockers)]
        self.warnings = [str(x) for x in _safe_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


__all__ = [
    "PRD_ID",
    "SOURCE_PRD_ID",
    "CreatorLiveTurnProof",
    "HF3Scorecard",
    "HF3Decision",
]
