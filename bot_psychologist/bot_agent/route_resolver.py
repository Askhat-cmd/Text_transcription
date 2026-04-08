"""Deterministic route resolver for Neo MindBot Phase 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .diagnostics_classifier import DiagnosticsV1


ROUTES = {
    "safe_override",
    "regulate",
    "reflect",
    "practice",
    "inform",
    "contact_hold",
}


@dataclass(frozen=True)
class RouteDecision:
    rule_id: int
    reason: str
    forbid: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class RouteResolution:
    route: str
    mode: str
    decision: RouteDecision
    confidence_score: float
    confidence_level: str
    track: str = "direct"
    tone: str = "minimal"
    stage: str = "runtime"

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "track": self.track,
            "tone": self.tone,
        }


def _confidence_level(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def _route_to_track_tone(route: str, mode: str) -> tuple[str, str]:
    """Return Neo routing package (`track`, `tone`) for a resolved route."""
    route_norm = str(route or "").strip().lower()

    if route_norm == "practice":
        return "practice", "empathic"
    if route_norm in {"reflect", "inform"}:
        return "reflective", "technical"
    if route_norm in {"safe_override", "regulate", "contact_hold"}:
        return "direct", "empathic"

    mode_norm = str(mode or "").strip().upper()
    if mode_norm in {"CLARIFICATION", "THINKING"}:
        return "reflective", "technical"
    if mode_norm in {"INTERVENTION"}:
        return "practice", "empathic"
    return "direct", "minimal"


class RouteResolver:
    """Single deterministic route resolver (one route per turn)."""

    def resolve(
        self,
        diagnostics: DiagnosticsV1,
        *,
        safety_override: bool = False,
        practice_candidate_score: float = 0.0,
        user_stage: str = "surface",
    ) -> RouteResolution:
        score = self._base_confidence(diagnostics)

        if safety_override:
            track, tone = _route_to_track_tone("safe_override", "VALIDATION")
            return RouteResolution(
                route="safe_override",
                mode="VALIDATION",
                track=track,
                tone=tone,
                decision=RouteDecision(
                    rule_id=1,
                    reason="safety override active",
                    forbid=["directive_advice", "deep_analysis"],
                ),
                confidence_score=0.95,
                confidence_level="high",
                stage=user_stage,
            )

        if diagnostics.interaction_mode == "informational":
            track, tone = _route_to_track_tone("inform", "CLARIFICATION")
            return RouteResolution(
                route="inform",
                mode="CLARIFICATION",
                track=track,
                tone=tone,
                decision=RouteDecision(
                    rule_id=2,
                    reason="interaction mode informational",
                    forbid=["forced_coaching", "practice_push"],
                ),
                confidence_score=max(score, 0.72),
                confidence_level=_confidence_level(max(score, 0.72)),
                stage=user_stage,
            )

        if diagnostics.nervous_system_state in {"hyper", "hypo"}:
            track, tone = _route_to_track_tone("regulate", "VALIDATION")
            return RouteResolution(
                route="regulate",
                mode="VALIDATION",
                track=track,
                tone=tone,
                decision=RouteDecision(
                    rule_id=3,
                    reason=f"nervous system state={diagnostics.nervous_system_state}",
                    forbid=["intense_interpretation"],
                ),
                confidence_score=max(score, 0.7),
                confidence_level=_confidence_level(max(score, 0.7)),
                stage=user_stage,
            )

        if diagnostics.request_function == "contact":
            track, tone = _route_to_track_tone("contact_hold", "PRESENCE")
            return RouteResolution(
                route="contact_hold",
                mode="PRESENCE",
                track=track,
                tone=tone,
                decision=RouteDecision(
                    rule_id=4,
                    reason="request function contact",
                    forbid=["over_structuring", "push_action"],
                ),
                confidence_score=max(score, 0.68),
                confidence_level=_confidence_level(max(score, 0.68)),
                stage=user_stage,
            )

        if diagnostics.request_function == "solution" or practice_candidate_score >= 0.62:
            track, tone = _route_to_track_tone("practice", "INTERVENTION")
            return RouteResolution(
                route="practice",
                mode="INTERVENTION",
                track=track,
                tone=tone,
                decision=RouteDecision(
                    rule_id=5,
                    reason="explicit solution request or strong practice candidate",
                    forbid=["too_many_options"],
                ),
                confidence_score=max(score, 0.66),
                confidence_level=_confidence_level(max(score, 0.66)),
                stage=user_stage,
            )

        if (
            diagnostics.request_function in {"understand", "explore", "validation"}
            and diagnostics.nervous_system_state == "window"
        ):
            track, tone = _route_to_track_tone("reflect", "THINKING")
            return RouteResolution(
                route="reflect",
                mode="THINKING",
                track=track,
                tone=tone,
                decision=RouteDecision(
                    rule_id=6,
                    reason="window + understanding/exploration request",
                    forbid=["directive_pressure"],
                ),
                confidence_score=max(score, 0.64),
                confidence_level=_confidence_level(max(score, 0.64)),
                stage=user_stage,
            )

        track, tone = _route_to_track_tone("reflect", "PRESENCE")
        return RouteResolution(
            route="reflect",
            mode="PRESENCE",
            track=track,
            tone=tone,
            decision=RouteDecision(
                rule_id=7,
                reason="safe fallback route",
                forbid=[],
            ),
            confidence_score=max(score, 0.55),
            confidence_level=_confidence_level(max(score, 0.55)),
            stage=user_stage,
        )

    @staticmethod
    def _base_confidence(diagnostics: DiagnosticsV1) -> float:
        conf = diagnostics.confidence
        score = (
            float(conf.interaction_mode)
            + float(conf.nervous_system_state)
            + float(conf.request_function)
        ) / 3.0
        return max(0.0, min(1.0, score))


route_resolver = RouteResolver()
