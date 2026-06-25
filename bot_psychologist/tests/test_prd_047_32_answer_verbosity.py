from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.dialogue_policy import build_effective_dialogue_policy


def _state() -> SimpleNamespace:
    return SimpleNamespace(safety_flag=False)


def _thread() -> SimpleNamespace:
    return SimpleNamespace(safety_active=False, response_mode="reflect")


def test_ordinary_support_turn_gets_compact_answer_shape_hint() -> None:
    policy = build_effective_dialogue_policy(
        profile="mvp_free_dialogue",
        user_message="Мне тяжело, просто поддержи без анализа.",
        state_snapshot=_state(),
        thread_state=_thread(),
        knowledge_answer_guard={"knowledge_answer": {"needed": False}},
    )

    human_like = policy["human_like_answer_policy"]

    assert policy["compact_support_answer"] is True
    assert human_like["support_answer_compactness"] == "ordinary_support_compact"
    assert human_like["preferred_shape"] == "one_main_point_one_optional_next_step"
    assert human_like["target_length_chars"] == "450_1100"
    assert human_like["avoid_mechanism_heavy_default"] is True
    assert human_like["prefer_direct_answer_first"] is True
    assert human_like["prefer_single_main_mechanism"] is True
    assert human_like["max_list_items"] == 3
    assert human_like["default_depth"] == "short_to_medium"
    assert human_like["allow_long_answers"] is False
    assert human_like["allow_multiple_options"] is False


def test_direct_detailed_question_can_still_receive_detailed_answer() -> None:
    policy = build_effective_dialogue_policy(
        profile="mvp_free_dialogue",
        user_message="Объясни подробно, как применять это в жизни, с примерами.",
        state_snapshot=_state(),
        thread_state=_thread(),
        knowledge_answer_guard={"knowledge_answer": {"needed": False}},
    )

    human_like = policy["human_like_answer_policy"]

    assert policy["compact_support_answer"] is False
    assert human_like["support_answer_compactness"] == "adaptive"
    assert human_like["default_depth"] == "medium_to_long"
    assert human_like["allow_long_answers"] is True
    assert human_like["allow_multiple_options"] is True
    assert human_like["avoid_mechanism_heavy_default"] is False


def test_no_practice_explanation_does_not_become_practice_first() -> None:
    policy = build_effective_dialogue_policy(
        profile="mvp_free_dialogue",
        user_message="Не давай практику, просто объясни словами.",
        state_snapshot=_state(),
        thread_state=_thread(),
        knowledge_answer_guard={"knowledge_answer": {"needed": False}},
    )

    human_like = policy["human_like_answer_policy"]

    assert human_like["do_not_force_practice_frame"] is True
    assert human_like["support_answer_compactness"] == "ordinary_support_compact"
    assert human_like["allow_long_answers"] is False
    assert human_like["avoid_mechanism_heavy_default"] is True
    assert human_like["prefer_direct_answer_first"] is True
