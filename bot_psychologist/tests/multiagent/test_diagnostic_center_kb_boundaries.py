from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_v1 import DiagnosticCenterInput
from bot_agent.multiagent.diagnostic_center_v1_builder import build_diagnostic_center_output_v1


def test_kb_usage_mode_is_internal_lens_only_and_no_quote() -> None:
    payload = DiagnosticCenterInput(
        user_message="я опять недостаточно постарался",
        nervous_state="window",
        intent="validation",
        openness="mixed",
        ok_position="I-W+",
        relation_to_thread="continue",
        phase="clarify",
        safety_flag=False,
        response_mode="reflect",
        knowledge_hits=[
            {"lens_family": "insufficient_self", "score": 0.91},
            {"lens_family": "perfectionism_like", "score": 0.74},
        ],
    )
    out = build_diagnostic_center_output_v1(payload).to_dict()
    assert out["trace"]["kb_usage_mode"] == "internal_lens_only"
    assert out["trace"]["must_not_quote_source"] is True
    assert out["lens_signals"]
    assert out["user_facing_text_generated"] is False


def test_branch_relation_keeps_internal_rule_and_branch_trace() -> None:
    payload = DiagnosticCenterInput(
        user_message="на работе то же самое",
        nervous_state="window",
        intent="clarify",
        openness="mixed",
        ok_position="I-W+",
        relation_to_thread="branch",
        phase="clarify",
        safety_flag=False,
        response_mode="reflect",
        pattern_core="external_confirmation_loop",
    )
    out = build_diagnostic_center_output_v1(payload).to_dict()
    assert out["relation_to_thread"] == "branch"
    assert "branch_continuity_rule" in out["trace"]["rules_applied"]
    assert out["trace"]["must_not_quote_source"] is True
