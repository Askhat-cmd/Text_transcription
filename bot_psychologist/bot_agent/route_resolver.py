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
    stage: str = "runtime"

    def as_dict(self) -> dict:
        return {
            "route": self.route,
            "mode": self.mode,
            "rule_id": self.decision.rule_id,
            "reason": self.decision.reason,
            "forbid": list(self.decision.forbid),
            "confidence_score": round(float(self.confidence_score), 3),
            "confidence_level": self.confidence_level,
            "stage": self.stage,
        }


def _confidence_level(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


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
            return RouteResolution(
                route="safe_override",
                mode="VALIDATION",
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
            return RouteResolution(
                route="inform",
                mode="CLARIFICATION",
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
            return RouteResolution(
                route="regulate",
                mode="VALIDATION",
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
            return RouteResolution(
                route="contact_hold",
                mode="PRESENCE",
                decision=RouteDecision(
                    rule_id=4,
                    reason="request function contact",
                    forbid=["over_structuring", "push_action"],
                ),
                confidence_score=max(score, 0.68),
                confidence_level=_confidence_level(max(score, 0.68)),
                stage=user_stage,
            )

        if diagnostics.request_function in {"directive"} or practice_candidate_score >= 0.62:
            return RouteResolution(
                route="practice",
                mode="INTERVENTION",
                decision=RouteDecision(
                    rule_id=5,
                    reason="explicit directive or strong practice candidate",
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
            return RouteResolution(
                route="reflect",
                mode="THINKING",
                decision=RouteDecision(
                    rule_id=6,
                    reason="window + understanding/exploration request",
                    forbid=["directive_pressure"],
                ),
                confidence_score=max(score, 0.64),
                confidence_level=_confidence_level(max(score, 0.64)),
                stage=user_stage,
            )

        return RouteResolution(
            route="reflect",
            mode="PRESENCE",
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

