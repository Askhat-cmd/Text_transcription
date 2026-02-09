"""Rule-based routing for bot response modes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class DecisionResult:
    """Outcome of decision table evaluation."""

    rule_id: int
    route: str
    reason: str
    confidence: float
    forbid: List[str] = field(default_factory=list)


class DecisionTable:
    """
    Evaluate dialogue signals and pick bot mode.

    Priority is top-to-bottom: first matching rule wins.
    """

    @staticmethod
    def evaluate(signals: Dict[str, Any]) -> DecisionResult:
        confidence = float(signals.get("confidence", 0.5))
        emotion_load = str(signals.get("emotion_load", "low"))
        contradiction = bool(signals.get("contradiction", False))
        explicit_ask = bool(signals.get("explicit_ask", False))
        ask_type = str(signals.get("ask_type", ""))
        insight_signal = bool(signals.get("insight_signal", False))
        validation_needed = bool(signals.get("validation_needed", False))
        thinking_due = bool(signals.get("thinking_due", False))
        cooldown_ok = bool(signals.get("intervention_cooldown_ok", True))
        stage = str(signals.get("user_stage", "surface"))

        rules: List[DecisionResult] = [
            DecisionResult(
                rule_id=1,
                route="CLARIFICATION",
                reason="low confidence",
                confidence=confidence,
                forbid=["explain", "advise_directly"],
            ),
            DecisionResult(
                rule_id=2,
                route="INTEGRATION",
                reason="insight signal detected",
                confidence=confidence,
                forbid=["deepen_further", "add_more", "analyze", "explain_why"],
            ),
            DecisionResult(
                rule_id=3,
                route="INTERVENTION",
                reason="explicit action request",
                confidence=confidence,
                forbid=["lecture", "overload"],
            ),
            DecisionResult(
                rule_id=4,
                route="VALIDATION",
                reason="high emotional load",
                confidence=confidence,
                forbid=["push_action"],
            ),
            DecisionResult(
                rule_id=5,
                route="THINKING",
                reason="contradiction/high complexity",
                confidence=confidence,
                forbid=["fast_advice"],
            ),
            DecisionResult(
                rule_id=6,
                route="VALIDATION",
                reason="explicit validation request",
                confidence=confidence,
                forbid=["interpretation_overreach"],
            ),
            DecisionResult(
                rule_id=7,
                route="THINKING",
                reason="thinking interval due",
                confidence=confidence,
                forbid=["surface_response"],
            ),
            DecisionResult(
                rule_id=8,
                route="CLARIFICATION",
                reason="stage too early for intervention",
                confidence=confidence,
                forbid=["deep_intervention"],
            ),
            DecisionResult(
                rule_id=9,
                route="INTERVENTION",
                reason="action ask and confidence medium/high",
                confidence=confidence,
                forbid=["too_many_options"],
            ),
            DecisionResult(
                rule_id=10,
                route="PRESENCE",
                reason="default pacing",
                confidence=confidence,
                forbid=[],
            ),
        ]

        if confidence < 0.4:
            return rules[0]
        if insight_signal:
            return rules[1]
        if explicit_ask and ask_type == "action" and cooldown_ok and stage in {"exploration", "integration"}:
            return rules[2]
        if emotion_load == "high" and not explicit_ask:
            return rules[3]
        if contradiction and confidence >= 0.55:
            return rules[4]
        if validation_needed:
            return rules[5]
        if thinking_due:
            return rules[6]
        if explicit_ask and ask_type == "action" and stage == "surface":
            return rules[7]
        if explicit_ask and ask_type == "action" and confidence >= 0.5 and cooldown_ok:
            return rules[8]
        return rules[9]
