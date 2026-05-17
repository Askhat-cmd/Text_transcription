from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.planner_bridge_v1 import PlannerBridgeOutput


def test_planner_bridge_contract_enforces_shadow_only_guardrails() -> None:
    output = PlannerBridgeOutput.from_dict(
        {
            "status": "candidate",
            "activation_mode": "active",
            "apply_to_writer": True,
            "apply_to_writer_contract": True,
            "must_do_candidates": ["a", "a", "b"],
            "must_not_do_candidates": ["x"] * 12,
        }
    ).to_dict()
    assert output["activation_mode"] == "shadow_only"
    assert output["apply_to_writer"] is False
    assert output["apply_to_writer_contract"] is False
    assert output["guardrails"]["apply_to_writer"] is False
    assert output["guardrails"]["apply_to_writer_contract"] is False
    assert len(output["must_do_candidates"]) <= 6
    assert len(output["must_not_do_candidates"]) <= 8


def test_planner_bridge_contract_roundtrip() -> None:
    payload = {
        "schema_version": "planner_bridge_output_v1",
        "status": "limited",
        "activation_mode": "shadow_only",
        "response_goal_candidate": "clarify",
        "response_mode_candidate": "reflect_then_one_question",
        "depth_limit": "low",
        "max_questions": 0,
        "max_concepts": 1,
        "must_do_candidates": ["validate_feeling"],
        "must_not_do_candidates": ["quote_kb_directly"],
        "safety_constraints": ["safety_first"],
        "kb_constraints": {"kb_usage_mode": "internal_lens_only", "must_not_quote_source": True},
        "confidence": 0.72,
        "blocked_reasons": [],
    }
    out = PlannerBridgeOutput.from_dict(payload).to_dict()
    assert out["schema_version"] == "planner_bridge_output_v1"
    assert out["status"] == "limited"
    assert out["depth_limit"] == "low"
    assert out["kb_constraints"]["must_not_quote_source"] is True

