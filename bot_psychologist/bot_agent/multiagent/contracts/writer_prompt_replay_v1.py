"""Writer prompt replay contracts (offline-only, non-mutating)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_ALLOWED_KB_USAGE = {"none", "internal_lens_only", "practice_candidate_only"}
_ALLOWED_QUALITY_STATUS = {"passed", "needs_review", "blocked"}


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


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


@dataclass
class WriterPromptReplayInput:
    baseline_prompt_context: dict[str, Any] = field(default_factory=dict)
    writer_contract_pilot: dict[str, Any] = field(default_factory=dict)
    diagnostic_card: dict[str, Any] = field(default_factory=dict)
    thread_state: dict[str, Any] = field(default_factory=dict)
    state_snapshot: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.baseline_prompt_context = _safe_dict(self.baseline_prompt_context)
        self.writer_contract_pilot = _safe_dict(self.writer_contract_pilot)
        self.diagnostic_card = _safe_dict(self.diagnostic_card)
        self.thread_state = _safe_dict(self.thread_state)
        self.state_snapshot = _safe_dict(self.state_snapshot)

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_prompt_context": dict(self.baseline_prompt_context),
            "writer_contract_pilot": dict(self.writer_contract_pilot),
            "diagnostic_card": dict(self.diagnostic_card),
            "thread_state": dict(self.thread_state),
            "state_snapshot": dict(self.state_snapshot),
        }


@dataclass
class WriterPromptReplayCandidateContext:
    schema_version: str = "writer_prompt_replay_candidate_context_v1"
    activation_mode: str = "offline_replay_only"
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "writer_prompt_replay_candidate_context_v1")
        self.activation_mode = "offline_replay_only"
        self.payload = _safe_dict(self.payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "activation_mode": "offline_replay_only",
            "payload": dict(self.payload),
        }


@dataclass
class WriterPromptReplayComparison:
    schema_version: str = "writer_prompt_replay_comparison_v1"
    added_fields_count: int = 0
    removed_fields_count: int = 0
    changed_fields_count: int = 0
    baseline_serialized_chars: int = 0
    candidate_serialized_chars: int = 0
    size_delta_chars: int = 0
    size_delta_ratio: float = 0.0
    forbidden_field_hits: list[str] = field(default_factory=list)
    conflict_rules: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "writer_prompt_replay_comparison_v1")
        self.added_fields_count = _as_int(self.added_fields_count)
        self.removed_fields_count = _as_int(self.removed_fields_count)
        self.changed_fields_count = _as_int(self.changed_fields_count)
        self.baseline_serialized_chars = _as_int(self.baseline_serialized_chars)
        self.candidate_serialized_chars = _as_int(self.candidate_serialized_chars)
        self.size_delta_chars = _as_int(self.size_delta_chars)
        self.size_delta_ratio = _as_float(self.size_delta_ratio, 0.0)
        self.forbidden_field_hits = _as_list(self.forbidden_field_hits)
        self.conflict_rules = _as_list(self.conflict_rules)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "added_fields_count": self.added_fields_count,
            "removed_fields_count": self.removed_fields_count,
            "changed_fields_count": self.changed_fields_count,
            "baseline_serialized_chars": self.baseline_serialized_chars,
            "candidate_serialized_chars": self.candidate_serialized_chars,
            "size_delta_chars": self.size_delta_chars,
            "size_delta_ratio": self.size_delta_ratio,
            "forbidden_field_hits": list(self.forbidden_field_hits),
            "conflict_rules": list(self.conflict_rules),
        }


@dataclass
class WriterPromptReplayQuality:
    schema_version: str = "writer_prompt_replay_quality_v1"
    safety_ok: bool = False
    kb_boundary_ok: bool = False
    constraint_conflict_ok: bool = False
    prompt_bloat_ok: bool = False
    non_mutating_ok: bool = False
    candidate_improves_constraints: bool = False
    quality_status: str = "blocked"

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "writer_prompt_replay_quality_v1")
        self.safety_ok = _as_bool(self.safety_ok, False)
        self.kb_boundary_ok = _as_bool(self.kb_boundary_ok, False)
        self.constraint_conflict_ok = _as_bool(self.constraint_conflict_ok, False)
        self.prompt_bloat_ok = _as_bool(self.prompt_bloat_ok, False)
        self.non_mutating_ok = _as_bool(self.non_mutating_ok, False)
        self.candidate_improves_constraints = _as_bool(self.candidate_improves_constraints, False)
        if self.quality_status not in _ALLOWED_QUALITY_STATUS:
            self.quality_status = "blocked"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "safety_ok": self.safety_ok,
            "kb_boundary_ok": self.kb_boundary_ok,
            "constraint_conflict_ok": self.constraint_conflict_ok,
            "prompt_bloat_ok": self.prompt_bloat_ok,
            "non_mutating_ok": self.non_mutating_ok,
            "candidate_improves_constraints": self.candidate_improves_constraints,
            "quality_status": self.quality_status,
        }


@dataclass
class WriterPromptReplayTrace:
    schema_version: str = "writer_prompt_replay_trace_v1"
    builder: str = "writer_prompt_replay_v1"
    rules_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "writer_prompt_replay_trace_v1")
        self.builder = _as_str(self.builder, "writer_prompt_replay_v1")
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
class WriterPromptReplayResult:
    schema_version: str = "writer_prompt_replay_result_v1"
    activation_mode: str = "offline_replay_only"
    baseline_prompt_context_hash: str = ""
    candidate_prompt_context_hash: str = ""
    baseline_summary: dict[str, Any] = field(default_factory=dict)
    candidate_summary: dict[str, Any] = field(default_factory=dict)
    comparison: WriterPromptReplayComparison = field(default_factory=WriterPromptReplayComparison)
    quality: WriterPromptReplayQuality = field(default_factory=WriterPromptReplayQuality)
    apply_to_writer_contract: bool = False
    apply_to_writer_prompt: bool = False
    apply_to_final_answer: bool = False
    provider_called: bool = False
    blocked_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace: WriterPromptReplayTrace = field(default_factory=WriterPromptReplayTrace)

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "writer_prompt_replay_result_v1")
        self.activation_mode = "offline_replay_only"
        self.baseline_prompt_context_hash = _as_str(self.baseline_prompt_context_hash, "")
        self.candidate_prompt_context_hash = _as_str(self.candidate_prompt_context_hash, "")
        self.baseline_summary = _safe_dict(self.baseline_summary)
        self.candidate_summary = _safe_dict(self.candidate_summary)
        if not isinstance(self.comparison, WriterPromptReplayComparison):
            self.comparison = WriterPromptReplayComparison(**_safe_dict(self.comparison))
        if not isinstance(self.quality, WriterPromptReplayQuality):
            self.quality = WriterPromptReplayQuality(**_safe_dict(self.quality))
        self.apply_to_writer_contract = False
        self.apply_to_writer_prompt = False
        self.apply_to_final_answer = False
        self.provider_called = False
        self.blocked_reasons = _as_list(self.blocked_reasons)
        self.warnings = _as_list(self.warnings)
        if not isinstance(self.trace, WriterPromptReplayTrace):
            self.trace = WriterPromptReplayTrace(**_safe_dict(self.trace))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "activation_mode": "offline_replay_only",
            "baseline_prompt_context_hash": self.baseline_prompt_context_hash,
            "candidate_prompt_context_hash": self.candidate_prompt_context_hash,
            "baseline_summary": dict(self.baseline_summary),
            "candidate_summary": dict(self.candidate_summary),
            "comparison": self.comparison.to_dict(),
            "quality": self.quality.to_dict(),
            "apply_to_writer_contract": False,
            "apply_to_writer_prompt": False,
            "apply_to_final_answer": False,
            "provider_called": False,
            "blocked_reasons": list(self.blocked_reasons),
            "warnings": list(self.warnings),
            "trace": self.trace.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WriterPromptReplayResult":
        return cls(
            schema_version=str(payload.get("schema_version", "writer_prompt_replay_result_v1")),
            activation_mode=str(payload.get("activation_mode", "offline_replay_only")),
            baseline_prompt_context_hash=str(payload.get("baseline_prompt_context_hash", "")),
            candidate_prompt_context_hash=str(payload.get("candidate_prompt_context_hash", "")),
            baseline_summary=_safe_dict(payload.get("baseline_summary")),
            candidate_summary=_safe_dict(payload.get("candidate_summary")),
            comparison=WriterPromptReplayComparison(**_safe_dict(payload.get("comparison"))),
            quality=WriterPromptReplayQuality(**_safe_dict(payload.get("quality"))),
            apply_to_writer_contract=bool(payload.get("apply_to_writer_contract", False)),
            apply_to_writer_prompt=bool(payload.get("apply_to_writer_prompt", False)),
            apply_to_final_answer=bool(payload.get("apply_to_final_answer", False)),
            provider_called=bool(payload.get("provider_called", False)),
            blocked_reasons=_as_list(payload.get("blocked_reasons")),
            warnings=_as_list(payload.get("warnings")),
            trace=WriterPromptReplayTrace(**_safe_dict(payload.get("trace"))),
        )


def normalize_kb_usage_mode(value: str) -> str:
    mode = _as_str(value, "none")
    return mode if mode in _ALLOWED_KB_USAGE else "none"
