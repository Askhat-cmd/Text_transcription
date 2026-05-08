"""Diagnostic Center contract objects for Writer orientation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiagnosticEvidenceRef:
    """Safe reference to one signal used by diagnostic card builder."""

    source: str
    key: str
    value_preview: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "key": self.key,
            "value_preview": self.value_preview,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiagnosticEvidenceRef":
        value_preview = payload.get("value_preview")
        return cls(
            source=str(payload.get("source", "")),
            key=str(payload.get("key", "")),
            value_preview=str(value_preview) if isinstance(value_preview, str) else None,
        )


@dataclass
class DiagnosticCardTrace:
    """Safe trace metadata for deterministic card-building rules."""

    version: str
    builder: str
    rules_applied: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    evidence_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "builder": self.builder,
            "rules_applied": list(self.rules_applied),
            "risk_flags": list(self.risk_flags),
            "evidence_sources": list(self.evidence_sources),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiagnosticCardTrace":
        rules_raw = payload.get("rules_applied", [])
        flags_raw = payload.get("risk_flags", [])
        sources_raw = payload.get("evidence_sources", [])
        return cls(
            version=str(payload.get("version", "diagnostic_card_v1")),
            builder=str(payload.get("builder", "deterministic_rules_v1")),
            rules_applied=[str(item) for item in rules_raw] if isinstance(rules_raw, list) else [],
            risk_flags=[str(item) for item in flags_raw] if isinstance(flags_raw, list) else [],
            evidence_sources=[str(item) for item in sources_raw] if isinstance(sources_raw, list) else [],
        )


@dataclass
class DiagnosticCard:
    """Compact deterministic situation card for Writer."""

    version: str
    situation_label: str
    user_state_summary: str
    thread_line_summary: str
    current_need: str
    suggested_writer_move: str
    avoid_list: list[str] = field(default_factory=list)
    evidence_refs: list[DiagnosticEvidenceRef] = field(default_factory=list)
    confidence: float = 0.5
    risk_flags: list[str] = field(default_factory=list)
    trace: DiagnosticCardTrace = field(
        default_factory=lambda: DiagnosticCardTrace(
            version="diagnostic_card_v1",
            builder="deterministic_rules_v1",
            rules_applied=[],
            risk_flags=[],
            evidence_sources=[],
        )
    )

    def __post_init__(self) -> None:
        try:
            value = float(self.confidence)
        except (TypeError, ValueError):
            value = 0.5
        self.confidence = max(0.0, min(1.0, value))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "situation_label": self.situation_label,
            "user_state_summary": self.user_state_summary,
            "thread_line_summary": self.thread_line_summary,
            "current_need": self.current_need,
            "suggested_writer_move": self.suggested_writer_move,
            "avoid_list": list(self.avoid_list),
            "evidence_refs": [item.to_dict() for item in self.evidence_refs],
            "confidence": float(self.confidence),
            "risk_flags": list(self.risk_flags),
            "trace": self.trace.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiagnosticCard":
        evidence_raw = payload.get("evidence_refs", [])
        evidence_refs = [
            DiagnosticEvidenceRef.from_dict(item)
            for item in evidence_raw
            if isinstance(item, dict)
        ]
        trace_raw = payload.get("trace", {})
        trace = (
            DiagnosticCardTrace.from_dict(trace_raw)
            if isinstance(trace_raw, dict)
            else DiagnosticCardTrace(
                version="diagnostic_card_v1",
                builder="deterministic_rules_v1",
                rules_applied=[],
                risk_flags=[],
                evidence_sources=[],
            )
        )
        avoid_raw = payload.get("avoid_list", [])
        risk_raw = payload.get("risk_flags", [])
        return cls(
            version=str(payload.get("version", "diagnostic_card_v1")),
            situation_label=str(payload.get("situation_label", "generic_support")),
            user_state_summary=str(payload.get("user_state_summary", "")),
            thread_line_summary=str(payload.get("thread_line_summary", "")),
            current_need=str(payload.get("current_need", "")),
            suggested_writer_move=str(payload.get("suggested_writer_move", "validate_briefly")),
            avoid_list=[str(item) for item in avoid_raw] if isinstance(avoid_raw, list) else [],
            evidence_refs=evidence_refs,
            confidence=float(payload.get("confidence", 0.5) or 0.5),
            risk_flags=[str(item) for item in risk_raw] if isinstance(risk_raw, list) else [],
            trace=trace,
        )
