"""Contracts for PRD-046.1.35-HF2 creator live RAG delivery calibration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PRD_ID = "PRD-046.1.35-HF2"
SOURCE_PRD_ID = "PRD-046.1.35-HF1"


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
    actual_live_turn: bool = False
    turn_id: str = ""
    session_id_hash: str = ""
    user_id_hash: str = ""
    is_creator: bool = False
    timestamp_utc: str = ""
    input_preview_sanitized: str = ""
    input_hash: str = ""
    answer_received: bool = False
    answer_preview_sanitized: str = ""
    answer_hash: str = ""
    diagnostic_center_runtime_mode: str = "unknown"
    diagnostic_center_active_for_creator: bool = False
    normal_user_path_unchanged: bool = False
    raw_provider_payload_committed: bool = False
    raw_private_logs_committed: bool = False
    trace_sanitized: bool = True

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "creator_live_turn_proof_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.actual_live_turn = _as_bool(self.actual_live_turn, False)
        self.turn_id = _as_str(self.turn_id)
        self.session_id_hash = _as_str(self.session_id_hash)
        self.user_id_hash = _as_str(self.user_id_hash)
        self.is_creator = _as_bool(self.is_creator, False)
        self.timestamp_utc = _as_str(self.timestamp_utc)
        self.input_preview_sanitized = _as_str(self.input_preview_sanitized)
        self.input_hash = _as_str(self.input_hash)
        self.answer_received = _as_bool(self.answer_received, False)
        self.answer_preview_sanitized = _as_str(self.answer_preview_sanitized)
        self.answer_hash = _as_str(self.answer_hash)
        self.diagnostic_center_runtime_mode = _as_str(self.diagnostic_center_runtime_mode, "unknown")
        self.diagnostic_center_active_for_creator = _as_bool(self.diagnostic_center_active_for_creator, False)
        self.normal_user_path_unchanged = _as_bool(self.normal_user_path_unchanged, False)
        self.raw_provider_payload_committed = _as_bool(self.raw_provider_payload_committed, False)
        self.raw_private_logs_committed = _as_bool(self.raw_private_logs_committed, False)
        self.trace_sanitized = _as_bool(self.trace_sanitized, True)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class RagToWriterDeliveryProof:
    schema_version: str = "rag_to_writer_delivery_proof_v1"
    prd_id: str = PRD_ID
    query: str = ""
    botdb_query_attempted: bool = False
    botdb_http_status: int = 0
    botdb_chunks_returned: int = 0
    botdb_query_route_fallback_used: bool = False
    botdb_error_class: str | None = None
    retriever_source_attempted: str = "api"
    retriever_source_used: str = "none"
    retriever_raw_hits_count: int = 0
    retriever_raw_scores: list[float] = field(default_factory=list)
    rag_min_score: float = 0.45
    rag_filtered_hits_count: int = 0
    rag_filtered_by_score_count: int = 0
    rag_salvaged_hits_count: int = 0
    score_policy_mode: str = "empty"
    score_policy_reasons: list[str] = field(default_factory=list)
    memory_semantic_hits_count: int = 0
    knowledge_policy_input_hits_count: int = 0
    knowledge_policy_included_writer_count: int = 0
    knowledge_policy_included_diagnostic_count: int = 0
    knowledge_policy_internal_only_count: int = 0
    knowledge_policy_dropped_count: int = 0
    knowledge_policy_drop_reasons: list[str] = field(default_factory=list)
    context_assembly_knowledge_hits_count: int = 0
    context_assembly_drop_reasons: list[str] = field(default_factory=list)
    writer_prompt_knowledge_hits_count: int = 0
    writer_prompt_contains_knowledge_block: bool = False
    writer_final_answer_used_knowledge: str = "not_evaluable"
    delivery_status: str = "blocked"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "rag_to_writer_delivery_proof_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.query = _as_str(self.query)
        self.botdb_query_attempted = _as_bool(self.botdb_query_attempted, False)
        self.botdb_http_status = _as_int(self.botdb_http_status, 0)
        self.botdb_chunks_returned = _as_int(self.botdb_chunks_returned, 0)
        self.botdb_query_route_fallback_used = _as_bool(self.botdb_query_route_fallback_used, False)
        self.botdb_error_class = None if self.botdb_error_class is None else _as_str(self.botdb_error_class)
        self.retriever_source_attempted = _as_str(self.retriever_source_attempted, "api")
        self.retriever_source_used = _as_str(self.retriever_source_used, "none")
        self.retriever_raw_hits_count = _as_int(self.retriever_raw_hits_count, 0)
        self.retriever_raw_scores = [_as_float(item, 0.0) for item in _safe_list(self.retriever_raw_scores)]
        self.rag_min_score = _as_float(self.rag_min_score, 0.45)
        self.rag_filtered_hits_count = _as_int(self.rag_filtered_hits_count, 0)
        self.rag_filtered_by_score_count = _as_int(self.rag_filtered_by_score_count, 0)
        self.rag_salvaged_hits_count = _as_int(self.rag_salvaged_hits_count, 0)
        self.score_policy_mode = _as_str(self.score_policy_mode, "empty")
        self.score_policy_reasons = [str(item) for item in _safe_list(self.score_policy_reasons)]
        self.memory_semantic_hits_count = _as_int(self.memory_semantic_hits_count, 0)
        self.knowledge_policy_input_hits_count = _as_int(self.knowledge_policy_input_hits_count, 0)
        self.knowledge_policy_included_writer_count = _as_int(self.knowledge_policy_included_writer_count, 0)
        self.knowledge_policy_included_diagnostic_count = _as_int(self.knowledge_policy_included_diagnostic_count, 0)
        self.knowledge_policy_internal_only_count = _as_int(self.knowledge_policy_internal_only_count, 0)
        self.knowledge_policy_dropped_count = _as_int(self.knowledge_policy_dropped_count, 0)
        self.knowledge_policy_drop_reasons = [str(item) for item in _safe_list(self.knowledge_policy_drop_reasons)]
        self.context_assembly_knowledge_hits_count = _as_int(self.context_assembly_knowledge_hits_count, 0)
        self.context_assembly_drop_reasons = [str(item) for item in _safe_list(self.context_assembly_drop_reasons)]
        self.writer_prompt_knowledge_hits_count = _as_int(self.writer_prompt_knowledge_hits_count, 0)
        self.writer_prompt_contains_knowledge_block = _as_bool(self.writer_prompt_contains_knowledge_block, False)
        self.writer_final_answer_used_knowledge = _as_str(self.writer_final_answer_used_knowledge, "not_evaluable")
        self.delivery_status = _as_str(self.delivery_status, "blocked")

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.__dict__)
        payload["retriever_raw_scores"] = [float(x) for x in self.retriever_raw_scores]
        return payload


@dataclass
class HF2Scorecard:
    schema_version: str = "creator_live_rag_delivery_hf2_scorecard_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "hf2_blocked_score_filtering_unresolved"

    source_gate: str = "blocked"
    botdb_query_gate: str = "blocked"
    rag_score_policy_gate: str = "blocked"
    memory_retrieval_gate: str = "blocked"
    knowledge_policy_gate: str = "blocked"
    context_assembly_gate: str = "blocked"
    writer_prompt_delivery_gate: str = "blocked"
    creator_live_turn_gate: str = "blocked"
    trace_alignment_gate: str = "blocked"
    normal_user_no_effect_gate: str = "blocked"
    trace_sanitization_gate: str = "blocked"
    provider_budget_gate: str = "blocked"
    no_mutation_proof: str = "blocked"
    artifact_encoding_hygiene: str = "blocked"

    botdb_chunks_returned: int = 0
    rag_raw_hits_count: int = 0
    rag_raw_scores: list[float] = field(default_factory=list)
    rag_min_score: float = 0.45
    rag_filtered_hits_count: int = 0
    rag_filtered_by_score_count: int = 0
    rag_salvaged_hits_count: int = 0
    score_policy_mode: str = "empty"
    knowledge_policy_input_hits_count: int = 0
    knowledge_policy_included_writer_count: int = 0
    knowledge_policy_dropped_count: int = 0
    knowledge_policy_drop_reasons: list[str] = field(default_factory=list)
    context_assembly_knowledge_hits_count: int = 0
    writer_prompt_knowledge_hits_count: int = 0
    web_trace_chunks_in_writer_count: int = 0

    actual_live_turn_evidence_count: int = 0
    broad_rollout_allowed: bool = False
    production_ready: bool = False
    normal_user_activation_allowed: bool = False
    all_users_mode_enabled: bool = False
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_prd_recommendation: str = ""

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "creator_live_rag_delivery_hf2_scorecard_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "hf2_blocked_score_filtering_unresolved")
        self.source_gate = _as_str(self.source_gate, "blocked")
        self.botdb_query_gate = _as_str(self.botdb_query_gate, "blocked")
        self.rag_score_policy_gate = _as_str(self.rag_score_policy_gate, "blocked")
        self.memory_retrieval_gate = _as_str(self.memory_retrieval_gate, "blocked")
        self.knowledge_policy_gate = _as_str(self.knowledge_policy_gate, "blocked")
        self.context_assembly_gate = _as_str(self.context_assembly_gate, "blocked")
        self.writer_prompt_delivery_gate = _as_str(self.writer_prompt_delivery_gate, "blocked")
        self.creator_live_turn_gate = _as_str(self.creator_live_turn_gate, "blocked")
        self.trace_alignment_gate = _as_str(self.trace_alignment_gate, "blocked")
        self.normal_user_no_effect_gate = _as_str(self.normal_user_no_effect_gate, "blocked")
        self.trace_sanitization_gate = _as_str(self.trace_sanitization_gate, "blocked")
        self.provider_budget_gate = _as_str(self.provider_budget_gate, "blocked")
        self.no_mutation_proof = _as_str(self.no_mutation_proof, "blocked")
        self.artifact_encoding_hygiene = _as_str(self.artifact_encoding_hygiene, "blocked")
        self.botdb_chunks_returned = _as_int(self.botdb_chunks_returned, 0)
        self.rag_raw_hits_count = _as_int(self.rag_raw_hits_count, 0)
        self.rag_raw_scores = [_as_float(item, 0.0) for item in _safe_list(self.rag_raw_scores)]
        self.rag_min_score = _as_float(self.rag_min_score, 0.45)
        self.rag_filtered_hits_count = _as_int(self.rag_filtered_hits_count, 0)
        self.rag_filtered_by_score_count = _as_int(self.rag_filtered_by_score_count, 0)
        self.rag_salvaged_hits_count = _as_int(self.rag_salvaged_hits_count, 0)
        self.score_policy_mode = _as_str(self.score_policy_mode, "empty")
        self.knowledge_policy_input_hits_count = _as_int(self.knowledge_policy_input_hits_count, 0)
        self.knowledge_policy_included_writer_count = _as_int(self.knowledge_policy_included_writer_count, 0)
        self.knowledge_policy_dropped_count = _as_int(self.knowledge_policy_dropped_count, 0)
        self.knowledge_policy_drop_reasons = [str(item) for item in _safe_list(self.knowledge_policy_drop_reasons)]
        self.context_assembly_knowledge_hits_count = _as_int(self.context_assembly_knowledge_hits_count, 0)
        self.writer_prompt_knowledge_hits_count = _as_int(self.writer_prompt_knowledge_hits_count, 0)
        self.web_trace_chunks_in_writer_count = _as_int(self.web_trace_chunks_in_writer_count, 0)
        self.actual_live_turn_evidence_count = _as_int(self.actual_live_turn_evidence_count, 0)
        self.broad_rollout_allowed = _as_bool(self.broad_rollout_allowed, False)
        self.production_ready = _as_bool(self.production_ready, False)
        self.normal_user_activation_allowed = _as_bool(self.normal_user_activation_allowed, False)
        self.all_users_mode_enabled = _as_bool(self.all_users_mode_enabled, False)
        self.blockers = [str(item) for item in _safe_list(self.blockers)]
        self.warnings = [str(item) for item in _safe_list(self.warnings)]
        self.next_prd_recommendation = _as_str(self.next_prd_recommendation)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class HF2Decision:
    schema_version: str = "creator_live_rag_delivery_hf2_decision_v1"
    prd_id: str = PRD_ID
    final_status: str = "blocked"
    decision: str = "hf2_blocked_score_filtering_unresolved"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "creator_live_rag_delivery_hf2_decision_v1")
        self.prd_id = _as_str(self.prd_id, PRD_ID)
        self.final_status = _as_str(self.final_status, "blocked")
        self.decision = _as_str(self.decision, "hf2_blocked_score_filtering_unresolved")
        self.blockers = [str(item) for item in _safe_list(self.blockers)]
        self.warnings = [str(item) for item in _safe_list(self.warnings)]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


__all__ = [
    "PRD_ID",
    "SOURCE_PRD_ID",
    "CreatorLiveTurnProof",
    "RagToWriterDeliveryProof",
    "HF2Scorecard",
    "HF2Decision",
]
