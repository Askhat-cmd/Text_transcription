"""Composition layer for routing with confidence and stage guard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..retrieval import ConfidenceScorer
from .decision_table import DecisionResult, DecisionTable


@dataclass
class RoutingResult:
    """Final routing output for response mode selection."""

    mode: str
    track: str
    tone: str
    decision: DecisionResult
    confidence_score: float
    confidence_level: str
    stage: str


class DecisionGate:
    """Unified router that combines scoring and decision table."""

    def __init__(self, scorer: ConfidenceScorer | None = None) -> None:
        self.scorer = scorer or ConfidenceScorer()

    @staticmethod
    def _derive_track_tone(mode: str) -> tuple[str, str]:
        mode_norm = str(mode or "").upper()
        if mode_norm in {"CLARIFICATION", "THINKING"}:
            return "reflective", "technical"
        if mode_norm == "INTERVENTION":
            return "practice", "empathic"
        if mode_norm in {"VALIDATION", "PRESENCE"}:
            return "direct", "empathic"
        return "direct", "minimal"

    def route(self, signals: Dict, user_stage: str = "surface") -> RoutingResult:
        confidence_result = self.scorer.score(signals)

        enriched_signals = dict(signals)
        enriched_signals["confidence"] = confidence_result.score
        enriched_signals["user_stage"] = user_stage

        decision = DecisionTable.evaluate(enriched_signals)
        mode = decision.route
        track, tone = self._derive_track_tone(mode)

        return RoutingResult(
            mode=mode,
            track=track,
            tone=tone,
            decision=decision,
            confidence_score=confidence_result.score,
            confidence_level=confidence_result.level,
            stage=user_stage,
        )
