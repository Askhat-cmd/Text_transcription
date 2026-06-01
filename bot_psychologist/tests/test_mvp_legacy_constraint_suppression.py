from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1


def test_mvp_directive_suppresses_legacy_constraints() -> None:
    payload = build_final_answer_directive_v1(
        user_message="объясни подробно",
        dialogue_policy={"profile": "mvp_free_dialogue"},
        dialogue_pragmatics={},
        response_planner={"practice_policy": "forbidden"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=SimpleNamespace(safety_active=False),
        state_snapshot=SimpleNamespace(safety_flag=False),
    ).to_dict()

    suppressed = payload["suppressed_legacy_constraints"]
    assert "writer_move.max_sentences=5" in suppressed
    assert "response_planner.response_depth=short" in suppressed
    assert payload["planner_role"] == "advisory_context_only"

