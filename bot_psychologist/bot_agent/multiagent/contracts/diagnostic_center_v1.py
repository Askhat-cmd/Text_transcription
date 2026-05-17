"""Diagnostic Center v1 dry-run contracts (internal, non-user-facing)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_NERVOUS_STATE = {"hyper", "window", "hypo", "unknown"}
_INTENT = {
    "contact",
    "vent",
    "clarify",
    "validation",
    "directive",
    "explore",
    "practical_step",
    "crisis",
    "unknown",
}
_OPENNESS = {"open", "mixed", "defensive", "collapsed", "unknown"}
_OK_POSITION = {"I+W+", "I-W+", "I+W-", "I-W-", "unknown"}
_RELATION = {"continue", "branch", "new_thread", "return_to_old", "unknown"}
_PHASE = {"stabilize", "clarify", "explore", "integrate", "unknown"}
_DEPTH = {"none", "low", "low_to_medium", "medium", "medium|high", "high"}
_STATUS = {"ok", "safety_first", "blocked"}
_KB_USAGE = {"internal_lens_only", "disabled"}


def _as_str(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


@dataclass
class DiagnosticLensSignal:
    lens_family: str
    score: float
    source: str = "knowledge_hits"
    rationale: str = ""

    def __post_init__(self) -> None:
        self.lens_family = _as_str(self.lens_family, "unknown")
        self.source = _as_str(self.source, "knowledge_hits")
        self.rationale = _as_str(self.rationale, "")
        try:
            self.score = max(0.0, min(1.0, float(self.score)))
        except (TypeError, ValueError):
            self.score = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "lens_family": self.lens_family,
            "score": float(self.score),
            "source": self.source,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiagnosticLensSignal":
        return cls(
            lens_family=str(payload.get("lens_family", "unknown")),
            score=float(payload.get("score", 0.0) or 0.0),
            source=str(payload.get("source", "knowledge_hits")),
            rationale=str(payload.get("rationale", "")),
        )


@dataclass
class DiagnosticHypothesis:
    pattern_candidate: str
    mechanism_summary: str
    blind_spot_candidate: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.pattern_candidate = _as_str(self.pattern_candidate, "unknown")
        self.mechanism_summary = _as_str(self.mechanism_summary, "")
        self.blind_spot_candidate = _as_str(self.blind_spot_candidate, "")
        self.evidence = _as_list(self.evidence)
        self.counter_evidence = _as_list(self.counter_evidence)
        self.risk_flags = _as_list(self.risk_flags)
        try:
            self.confidence = max(0.0, min(1.0, float(self.confidence)))
        except (TypeError, ValueError):
            self.confidence = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_candidate": self.pattern_candidate,
            "mechanism_summary": self.mechanism_summary,
            "blind_spot_candidate": self.blind_spot_candidate,
            "confidence": float(self.confidence),
            "evidence": list(self.evidence),
            "counter_evidence": list(self.counter_evidence),
            "risk_flags": list(self.risk_flags),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiagnosticHypothesis":
        return cls(
            pattern_candidate=str(payload.get("pattern_candidate", "unknown")),
            mechanism_summary=str(payload.get("mechanism_summary", "")),
            blind_spot_candidate=str(payload.get("blind_spot_candidate", "")),
            confidence=float(payload.get("confidence", 0.0) or 0.0),
            evidence=list(payload.get("evidence", [])),
            counter_evidence=list(payload.get("counter_evidence", [])),
            risk_flags=list(payload.get("risk_flags", [])),
        )


@dataclass
class NextMicroShift:
    response_goal: str
    response_mode: str
    target_micro_shift: str
    must_do: list[str] = field(default_factory=list)
    must_not_do: list[str] = field(default_factory=list)
    depth_allowed: str = "low_to_medium"
    max_questions: int = 1
    max_concepts: int = 1

    def __post_init__(self) -> None:
        self.response_goal = _as_str(self.response_goal, "stabilize_authorship")
        self.response_mode = _as_str(self.response_mode, "reflect_then_one_question")
        self.target_micro_shift = _as_str(self.target_micro_shift, "")
        self.must_do = _as_list(self.must_do)
        self.must_not_do = _as_list(self.must_not_do)
        if self.depth_allowed not in _DEPTH:
            self.depth_allowed = "low_to_medium"
        try:
            self.max_questions = max(0, int(self.max_questions))
        except (TypeError, ValueError):
            self.max_questions = 1
        try:
            self.max_concepts = max(0, int(self.max_concepts))
        except (TypeError, ValueError):
            self.max_concepts = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_goal": self.response_goal,
            "response_mode": self.response_mode,
            "target_micro_shift": self.target_micro_shift,
            "must_do": list(self.must_do),
            "must_not_do": list(self.must_not_do),
            "depth_allowed": self.depth_allowed,
            "max_questions": int(self.max_questions),
            "max_concepts": int(self.max_concepts),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NextMicroShift":
        return cls(
            response_goal=str(payload.get("response_goal", "stabilize_authorship")),
            response_mode=str(payload.get("response_mode", "reflect_then_one_question")),
            target_micro_shift=str(payload.get("target_micro_shift", "")),
            must_do=list(payload.get("must_do", [])),
            must_not_do=list(payload.get("must_not_do", [])),
            depth_allowed=str(payload.get("depth_allowed", "low_to_medium")),
            max_questions=int(payload.get("max_questions", 1) or 1),
            max_concepts=int(payload.get("max_concepts", 1) or 1),
        )


@dataclass
class DiagnosticCenterTrace:
    version: str
    builder: str
    rules_applied: list[str] = field(default_factory=list)
    safety_priority_applied: bool = False
    evidence_sources: list[str] = field(default_factory=list)
    kb_usage_mode: str = "internal_lens_only"
    must_not_quote_source: bool = True

    def __post_init__(self) -> None:
        self.version = _as_str(self.version, "diagnostic_center_trace_v1")
        self.builder = _as_str(self.builder, "diagnostic_center_dry_run_v1")
        self.rules_applied = _as_list(self.rules_applied)
        self.evidence_sources = _as_list(self.evidence_sources)
        if self.kb_usage_mode not in _KB_USAGE:
            self.kb_usage_mode = "internal_lens_only"
        self.must_not_quote_source = bool(self.must_not_quote_source)
        self.safety_priority_applied = bool(self.safety_priority_applied)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "builder": self.builder,
            "rules_applied": list(self.rules_applied),
            "safety_priority_applied": bool(self.safety_priority_applied),
            "evidence_sources": list(self.evidence_sources),
            "kb_usage_mode": self.kb_usage_mode,
            "must_not_quote_source": bool(self.must_not_quote_source),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiagnosticCenterTrace":
        return cls(
            version=str(payload.get("version", "diagnostic_center_trace_v1")),
            builder=str(payload.get("builder", "diagnostic_center_dry_run_v1")),
            rules_applied=list(payload.get("rules_applied", [])),
            safety_priority_applied=bool(payload.get("safety_priority_applied", False)),
            evidence_sources=list(payload.get("evidence_sources", [])),
            kb_usage_mode=str(payload.get("kb_usage_mode", "internal_lens_only")),
            must_not_quote_source=bool(payload.get("must_not_quote_source", True)),
        )


@dataclass
class DiagnosticCenterInput:
    user_message: str
    nervous_state: str = "unknown"
    intent: str = "unknown"
    openness: str = "unknown"
    ok_position: str = "unknown"
    relation_to_thread: str = "unknown"
    phase: str = "unknown"
    safety_flag: bool = False
    response_mode: str = "reflect"
    pattern_core: str = ""
    thread_action: str = ""
    knowledge_hits: list[dict[str, Any]] = field(default_factory=list)
    context_signals: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.user_message = _as_str(self.user_message, "")
        if self.nervous_state not in _NERVOUS_STATE:
            self.nervous_state = "unknown"
        if self.intent not in _INTENT:
            self.intent = "unknown"
        if self.openness not in _OPENNESS:
            self.openness = "unknown"
        if self.ok_position not in _OK_POSITION:
            self.ok_position = "unknown"
        if self.relation_to_thread not in _RELATION:
            self.relation_to_thread = "unknown"
        if self.phase not in _PHASE:
            self.phase = "unknown"
        self.safety_flag = bool(self.safety_flag)
        self.response_mode = _as_str(self.response_mode, "reflect")
        self.pattern_core = _as_str(self.pattern_core, "")
        self.thread_action = _as_str(self.thread_action, "")
        if not isinstance(self.knowledge_hits, list):
            self.knowledge_hits = []
        if not isinstance(self.context_signals, dict):
            self.context_signals = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_message": self.user_message,
            "nervous_state": self.nervous_state,
            "intent": self.intent,
            "openness": self.openness,
            "ok_position": self.ok_position,
            "relation_to_thread": self.relation_to_thread,
            "phase": self.phase,
            "safety_flag": bool(self.safety_flag),
            "response_mode": self.response_mode,
            "pattern_core": self.pattern_core,
            "thread_action": self.thread_action,
            "knowledge_hits": list(self.knowledge_hits),
            "context_signals": dict(self.context_signals),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiagnosticCenterInput":
        return cls(
            user_message=str(payload.get("user_message", "")),
            nervous_state=str(payload.get("nervous_state", "unknown")),
            intent=str(payload.get("intent", "unknown")),
            openness=str(payload.get("openness", "unknown")),
            ok_position=str(payload.get("ok_position", "unknown")),
            relation_to_thread=str(payload.get("relation_to_thread", "unknown")),
            phase=str(payload.get("phase", "unknown")),
            safety_flag=bool(payload.get("safety_flag", False)),
            response_mode=str(payload.get("response_mode", "reflect")),
            pattern_core=str(payload.get("pattern_core", "")),
            thread_action=str(payload.get("thread_action", "")),
            knowledge_hits=list(payload.get("knowledge_hits", [])),
            context_signals=dict(payload.get("context_signals", {}))
            if isinstance(payload.get("context_signals"), dict)
            else {},
        )


@dataclass
class DiagnosticCenterOutput:
    schema_version: str
    status: str
    nervous_state: str
    intent: str
    openness: str
    ok_position: str
    relation_to_thread: str
    phase: str
    working_hypothesis: DiagnosticHypothesis
    lens_signals: list[DiagnosticLensSignal]
    next_micro_shift: NextMicroShift
    trace: DiagnosticCenterTrace
    diagnostic_center_runtime_enabled: bool = False
    user_facing_text_generated: bool = False

    def __post_init__(self) -> None:
        self.schema_version = _as_str(self.schema_version, "diagnostic_center_output_v1")
        if self.status not in _STATUS:
            self.status = "ok"
        if self.nervous_state not in _NERVOUS_STATE:
            self.nervous_state = "unknown"
        if self.intent not in _INTENT:
            self.intent = "unknown"
        if self.openness not in _OPENNESS:
            self.openness = "unknown"
        if self.ok_position not in _OK_POSITION:
            self.ok_position = "unknown"
        if self.relation_to_thread not in _RELATION:
            self.relation_to_thread = "unknown"
        if self.phase not in _PHASE:
            self.phase = "unknown"
        self.diagnostic_center_runtime_enabled = bool(self.diagnostic_center_runtime_enabled)
        self.user_facing_text_generated = bool(self.user_facing_text_generated)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "nervous_state": self.nervous_state,
            "intent": self.intent,
            "openness": self.openness,
            "ok_position": self.ok_position,
            "relation_to_thread": self.relation_to_thread,
            "phase": self.phase,
            "working_hypothesis": self.working_hypothesis.to_dict(),
            "lens_signals": [item.to_dict() for item in self.lens_signals],
            "next_micro_shift": self.next_micro_shift.to_dict(),
            "trace": self.trace.to_dict(),
            "diagnostic_center_runtime_enabled": self.diagnostic_center_runtime_enabled,
            "user_facing_text_generated": self.user_facing_text_generated,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiagnosticCenterOutput":
        hypothesis_raw = payload.get("working_hypothesis")
        shift_raw = payload.get("next_micro_shift")
        trace_raw = payload.get("trace")
        lens_raw = payload.get("lens_signals", [])
        lens_signals = [
            DiagnosticLensSignal.from_dict(item)
            for item in lens_raw
            if isinstance(item, dict)
        ]
        return cls(
            schema_version=str(payload.get("schema_version", "diagnostic_center_output_v1")),
            status=str(payload.get("status", "ok")),
            nervous_state=str(payload.get("nervous_state", "unknown")),
            intent=str(payload.get("intent", "unknown")),
            openness=str(payload.get("openness", "unknown")),
            ok_position=str(payload.get("ok_position", "unknown")),
            relation_to_thread=str(payload.get("relation_to_thread", "unknown")),
            phase=str(payload.get("phase", "unknown")),
            working_hypothesis=DiagnosticHypothesis.from_dict(hypothesis_raw)
            if isinstance(hypothesis_raw, dict)
            else DiagnosticHypothesis(
                pattern_candidate="unknown",
                mechanism_summary="",
                blind_spot_candidate="",
                confidence=0.0,
            ),
            lens_signals=lens_signals,
            next_micro_shift=NextMicroShift.from_dict(shift_raw)
            if isinstance(shift_raw, dict)
            else NextMicroShift(
                response_goal="stabilize_authorship",
                response_mode="reflect_then_one_question",
                target_micro_shift="",
            ),
            trace=DiagnosticCenterTrace.from_dict(trace_raw)
            if isinstance(trace_raw, dict)
            else DiagnosticCenterTrace(
                version="diagnostic_center_trace_v1",
                builder="diagnostic_center_dry_run_v1",
            ),
            diagnostic_center_runtime_enabled=bool(payload.get("diagnostic_center_runtime_enabled", False)),
            user_facing_text_generated=bool(payload.get("user_facing_text_generated", False)),
        )
