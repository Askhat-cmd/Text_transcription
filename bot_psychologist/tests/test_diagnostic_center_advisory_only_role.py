from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1


def _directive(profile: str) -> dict:
    return build_final_answer_directive_v1(
        user_message="что такое нейросталкинг?",
        dialogue_policy={"profile": profile},
        dialogue_pragmatics={},
        response_planner={},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=SimpleNamespace(safety_active=False),
        state_snapshot=SimpleNamespace(safety_flag=False),
    ).to_dict()


def test_mvp_role_is_advisory_only() -> None:
    payload = _directive("mvp_free_dialogue")
    assert payload["diagnostic_center_role"] == "advisory_context_only"
    assert payload["planner_role"] == "advisory_context_only"


def test_safe_guided_role_is_legacy_guided() -> None:
    payload = _directive("safe_guided")
    assert payload["diagnostic_center_role"] == "guided_legacy"
    assert payload["planner_role"] == "guided_legacy"

