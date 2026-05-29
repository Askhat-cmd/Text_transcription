from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.dialogue_policy import build_effective_dialogue_policy


def _state(**kwargs):
    base = {"safety_flag": False}
    base.update(kwargs)
    return SimpleNamespace(**base)


def _thread(**kwargs):
    base = {"safety_active": False, "response_mode": "reflect"}
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_mvp_profile_is_advisory_with_explicit_depth_request() -> None:
    payload = build_effective_dialogue_policy(
        profile="mvp_free_dialogue",
        user_message="объясни подробно и по пунктам, добавь примеры",
        state_snapshot=_state(),
        thread_state=_thread(),
        knowledge_answer_guard={"knowledge_answer": {"needed": True, "concept": "нейросталкинг"}},
    )
    assert payload["profile"] == "mvp_free_dialogue"
    assert payload["planner_authority"] == "advisory"
    assert payload["diagnostic_card_authority"] == "advisory"
    assert payload["writer_move_authority"] == "advisory"
    assert payload["user_explicit_request_priority"] == "highest_after_safety"
    assert payload["answer_depth"] == "long"
    assert payload["allow_numbered_lists"] is True
    assert payload["allow_examples"] is True
    assert payload["context_budget_chars"] >= 6000


def test_safety_stays_top_priority_even_in_mvp_profile() -> None:
    payload = build_effective_dialogue_policy(
        profile="mvp_free_dialogue",
        user_message="объясни подробно",
        state_snapshot=_state(safety_flag=True),
        thread_state=_thread(),
        knowledge_answer_guard={},
    )
    assert payload["writer_autonomy"] == "guarded_safety"
    assert payload["answer_depth"] == "short"


def test_practice_overview_does_not_force_one_step() -> None:
    payload = build_effective_dialogue_policy(
        profile="mvp_free_dialogue",
        user_message="скажи, какие практики в нейросталкинге предлагаются",
        state_snapshot=_state(),
        thread_state=_thread(),
        knowledge_answer_guard={},
    )
    assert payload["practice_overview_requested"] is True
    assert payload["allow_practice_catalog"] is True
    assert payload["must_not_force_one_step"] is True


def test_explicit_one_step_keeps_short_depth() -> None:
    payload = build_effective_dialogue_policy(
        profile="mvp_free_dialogue",
        user_message="дай один конкретный шаг прямо сейчас",
        state_snapshot=_state(),
        thread_state=_thread(),
        knowledge_answer_guard={},
    )
    assert payload["explicit_one_step_requested"] is True
    assert payload["answer_depth"] == "short"
