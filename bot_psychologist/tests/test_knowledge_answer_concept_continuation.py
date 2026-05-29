from __future__ import annotations

from bot_agent.multiagent.dialogue_policy import apply_active_concept_continuation


def test_followup_expansion_inherits_active_concept_in_mvp() -> None:
    guard, concept = apply_active_concept_continuation(
        user_message="можешь дать более развернутый ответ?",
        dialogue_profile="mvp_free_dialogue",
        knowledge_answer_guard={
            "knowledge_answer": {
                "needed": False,
                "reason": "no_known_concept_question",
                "concept": "",
                "should_answer_directly": False,
            },
            "practice_gate": {"practice_allowed": False},
        },
        thread_active_frame={"active_concept": "нейросталкинг"},
    )
    knowledge = guard["knowledge_answer"]
    assert concept == "нейросталкинг"
    assert knowledge["needed"] is True
    assert knowledge["concept"] == "нейросталкинг"
    assert knowledge["should_answer_directly"] is True
    assert knowledge["reason"] == "followup_expansion_inherits_active_concept"


def test_safe_guided_does_not_force_concept_inheritance() -> None:
    guard, concept = apply_active_concept_continuation(
        user_message="можешь дать более развернутый ответ?",
        dialogue_profile="safe_guided",
        knowledge_answer_guard={"knowledge_answer": {"concept": ""}},
        thread_active_frame={"active_concept": "нейросталкинг"},
    )
    assert concept == "нейросталкинг"
    assert guard["knowledge_answer"]["concept"] == ""

