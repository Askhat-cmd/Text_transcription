from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1
from bot_agent.multiagent.latest_turn_constraints import build_latest_turn_constraints_v1


def _build_directive(user_message: str) -> dict:
    return build_final_answer_directive_v1(
        user_message=user_message,
        dialogue_policy={"profile": "mvp_free_dialogue"},
        dialogue_pragmatics={},
        response_planner={"answer_shape": "compact_direct", "practice_policy": "allowed_explicit_request"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=SimpleNamespace(safety_active=False),
        state_snapshot=SimpleNamespace(safety_flag=False),
    ).to_dict()


def test_latest_turn_constraints_extract_only_explicit_latest_turn_markers() -> None:
    payload = build_latest_turn_constraints_v1(
        "Не давай практику, не своди все к дыханию, скажи проще и без внутренней БД."
    )

    assert payload["no_practice"] is True
    assert payload["no_breathing_only"] is True
    assert payload["simplify"] is True
    assert payload["long_term_perspective"] is False
    assert payload["no_internal_db"] is True
    assert payload["active_constraints"] == [
        "no_practice",
        "no_breathing_only",
        "simplify",
        "no_internal_db",
    ]
    assert payload["source"] == "latest_user_turn_explicit_text"


def test_final_answer_directive_hardens_no_practice_and_simplify_requests() -> None:
    user_message = "Не давай практику. Скажи проще и без лекции."
    payload = _build_directive(user_message)

    latest = payload["latest_turn_constraints_v1"]
    assert latest["no_practice"] is True
    assert latest["simplify"] is True
    assert payload["practice_policy"] == "forbidden_explicit_latest_turn"
    assert payload["depth"] == "short"
    assert payload["answer_shape"] == "direct_answer"
    assert payload["question_policy"] == "optional_none"
    assert payload["must_answer"] == user_message
    assert any("practice" in item.lower() for item in payload["hard_boundaries"])


def test_latest_turn_constraints_detect_no_practice_with_intermediate_words() -> None:
    payload = build_latest_turn_constraints_v1(
        "Всё, не хочу сейчас практику и упражнения. Мне тяжело, просто поддержи меня."
    )

    assert payload["no_practice"] is True
    assert "no_practice" in payload["active_constraints"]


def test_final_answer_directive_adds_long_term_and_non_breathing_guidance() -> None:
    payload = _build_directive(
        "Что делать в долгосрочной перспективе и не своди ответ только к дыханию?"
    )

    latest = payload["latest_turn_constraints_v1"]
    assert latest["long_term_perspective"] is True
    assert latest["no_breathing_only"] is True
    assert "start_with_long_term_frame" in payload["soft_guidance"]
    assert "name_2_to_3_long_term_directions" in payload["soft_guidance"]
    assert any("breathing" in item.lower() for item in payload["hard_boundaries"])
    assert any("moment-only" in item.lower() for item in payload["hard_boundaries"])
