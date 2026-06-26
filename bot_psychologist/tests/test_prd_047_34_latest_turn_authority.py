from __future__ import annotations

from types import SimpleNamespace

from bot_agent.multiagent.answer_obligation_resolver import (
    build_answer_obligation_resolver_v1,
)
from bot_agent.multiagent.dialogue_act_resolver import build_dialogue_act_resolution_v1
from bot_agent.multiagent.final_answer_directive import build_final_answer_directive_v1
from bot_agent.multiagent.legacy_advisory_sanitizer import sanitize_legacy_advisory_for_writer
from bot_agent.multiagent.runtime_trace_summary import build_runtime_trace_summary_v1


def _state(*, safety_flag: bool = False) -> SimpleNamespace:
    return SimpleNamespace(safety_flag=safety_flag)


def _thread(*, safety_active: bool = False) -> SimpleNamespace:
    return SimpleNamespace(safety_active=safety_active)


def _base_policy(**overrides: object) -> dict[str, object]:
    policy: dict[str, object] = {
        "profile": "mvp_free_dialogue",
        "profile_preset": "free_dialogue_default",
        "dialogue_style_state": {
            "tone": "neutral",
            "length_preference": "adaptive",
            "complexity_preference": "normal",
            "avoid": [],
        },
        "last_assistant_offer": {},
        "unanswered_question_state": {},
        "dialogue_act_resolution": {},
    }
    policy.update(overrides)
    return policy


def test_chat5_latest_human_turn_demotes_previous_kb_task() -> None:
    user_message = (
        "Мне сейчас просто тяжело. Не хочу разбирать, просто скажи что-нибудь по-человечески."
    )
    act = build_dialogue_act_resolution_v1(
        user_message=user_message,
        dialogue_pragmatics={},
        last_assistant_offer={},
        knowledge_answer_guard={},
    )
    assert act["dialogue_act"] == "support_request"

    obligation = build_answer_obligation_resolver_v1(
        dialogue_act_resolution=act,
        last_assistant_offer={},
        unanswered_question_state={
            "last_direct_user_question": "Что во внутренней базе говорится про программу «несовершенное Я» и пять драйверов?",
            "answer_required": True,
            "answer_status": "pending",
        },
        dialogue_style_state={"tone": "neutral", "length_preference": "adaptive", "avoid": []},
        dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    )
    assert obligation["answer_obligation"] == "answer_latest_turn"

    directive = build_final_answer_directive_v1(
        user_message=user_message,
        dialogue_policy=_base_policy(
            compact_support_answer=True,
            dialogue_act_resolution=act,
            unanswered_question_state={
                "last_direct_user_question": "Что во внутренней базе говорится про программу «несовершенное Я» и пять драйверов?",
                "answer_required": True,
                "answer_status": "pending",
            },
        ),
        dialogue_pragmatics={},
        response_planner={"answer_shape": "compact_direct", "question_policy": "none", "practice_policy": "forbidden"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={"retrieval_action": "trace_only", "rag_included_for_writer": [], "rag_included_count": 0},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution=obligation,
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["must_answer"] == user_message
    assert directive["must_answer_source"] == "latest_turn"
    assert directive["previous_must_answer_demoted"] is True
    assert directive["previous_must_answer"].startswith("Что во внутренней базе")
    assert directive["answer_target"] == "latest_turn"
    assert directive["answer_shape_profile"] == "free_writer_contact"
    assert directive["writer_contact_mode"] == "free_writer_contact"

    summary = build_runtime_trace_summary_v1(
        entrypoint="multiagent_adapter",
        final_answer_directive=directive,
        writer_debug={
            "writer_grounding_visibility_v1": {
                "reason": "non_kb_emotional_support_turn",
                "kb_visible_to_writer": False,
                "semantic_cards_visible_to_writer": False,
            }
        },
        overlay_shadow={},
        user_message=user_message,
        dialogue_act_resolution=act,
    )
    authority = summary["latest_turn_authority_v1"]

    assert authority["must_answer_source"] == "latest_turn"
    assert authority["previous_must_answer_demoted"] is True
    assert authority["writer_contact_mode"] == "free_writer_contact"
    assert authority["kb_payload_expected"] == "0"


def test_support_after_practice_latest_turn_wins_and_practice_stays_forbidden() -> None:
    user_message = "Всё, не хочу сейчас практику и анализ. Мне тяжело, просто поддержи меня."
    act = build_dialogue_act_resolution_v1(
        user_message=user_message,
        dialogue_pragmatics={},
        last_assistant_offer={},
        knowledge_answer_guard={},
    )

    directive = build_final_answer_directive_v1(
        user_message=user_message,
        dialogue_policy=_base_policy(
            compact_support_answer=True,
            dialogue_act_resolution=act,
            unanswered_question_state={
                "last_direct_user_question": "Дай практику, чтобы не быть реактивным.",
                "answer_required": True,
                "answer_status": "pending",
            },
        ),
        dialogue_pragmatics={},
        response_planner={"answer_shape": "one_step", "question_policy": "none", "practice_policy": "allowed_if_explicit"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={"retrieval_action": "trace_only"},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution=build_answer_obligation_resolver_v1(
            dialogue_act_resolution=act,
            last_assistant_offer={},
            unanswered_question_state={
                "last_direct_user_question": "Дай практику, чтобы не быть реактивным.",
                "answer_required": True,
            },
            dialogue_style_state={"tone": "neutral", "length_preference": "adaptive", "avoid": []},
            dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
        ),
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["must_answer"] == user_message
    assert directive["previous_must_answer_demoted"] is True
    assert directive["latest_turn_constraints_v1"]["no_practice"] is True
    assert directive["practice_policy"].startswith("forbidden")
    assert directive["writer_contact_mode"] == "free_writer_contact"


def test_no_practice_sanitizer_removes_step_shaped_legacy_advice() -> None:
    payload = sanitize_legacy_advisory_for_writer(
        {
            "active_line": {
                "active_line": "дать один уместный шаг как продолжение уже понятой линии",
                "practice_suppression_active": True,
            },
            "response_planner": {
                "target_micro_shift": "дать один исполнимый микро-шаг без списка",
            },
            "latest_turn_constraints_v1": {
                "no_practice": True,
            },
            "writer_grounding_visibility_v1": {
                "kb_visible_to_writer": False,
            },
            "knowledge_answer_guard": {
                "practice_gate": {
                    "practice_allowed": False,
                }
            },
        }
    )

    summary = payload["writer_visible_summary"].lower()
    assert "микро-шаг" not in summary
    assert "дать один уместный шаг" not in summary
    assert "do not turn the answer into an exercise" in summary
    assert "lower pressure" in summary
    assert payload["writer_visible_practice_instruction"] == "no_exercise_but_answer_normally"


def test_say_simpler_replaces_previous_topic_with_latest_turn() -> None:
    user_message = "Слишком сложно, скажи проще."
    act = build_dialogue_act_resolution_v1(
        user_message=user_message,
        dialogue_pragmatics={},
        last_assistant_offer={},
        knowledge_answer_guard={},
    )
    assert act["dialogue_act"] == "repair_complaint"

    obligation = build_answer_obligation_resolver_v1(
        dialogue_act_resolution=act,
        last_assistant_offer={},
        unanswered_question_state={
            "last_direct_user_question": "Что такое пять драйверов?",
            "answer_required": True,
            "answer_status": "answered",
        },
        dialogue_style_state={"tone": "neutral", "length_preference": "adaptive", "avoid": []},
        dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
    )
    assert obligation["answer_obligation"] == "answer_latest_turn"

    directive = build_final_answer_directive_v1(
        user_message=user_message,
        dialogue_policy=_base_policy(
            dialogue_act_resolution=act,
            unanswered_question_state={
                "last_direct_user_question": "Что такое пять драйверов?",
                "answer_required": True,
                "answer_status": "answered",
            },
        ),
        dialogue_pragmatics={},
        response_planner={"answer_shape": "structured_explanation", "question_policy": "optional_none", "practice_policy": "forbidden"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution=obligation,
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["must_answer"] == user_message
    assert directive["must_answer_source"] == "latest_turn"
    assert directive["previous_must_answer_demoted"] is True
    assert directive["answer_shape_profile"] == "simplified_direct_answer"


def test_explicit_continuation_keeps_previous_open_loop() -> None:
    user_message = "Расскажи подробнее про второй."
    act = build_dialogue_act_resolution_v1(
        user_message=user_message,
        dialogue_pragmatics={},
        last_assistant_offer={"is_open": True, "offer_type": "explanation"},
        knowledge_answer_guard={},
    )

    directive = build_final_answer_directive_v1(
        user_message=user_message,
        dialogue_policy=_base_policy(
            dialogue_act_resolution=act,
            last_assistant_offer={"is_open": True, "offer_type": "explanation", "offer_text_summary": "Кратко объяснил пять драйверов."},
            unanswered_question_state={
                "last_direct_user_question": "Что такое пять драйверов?",
                "answer_required": True,
                "answer_status": "pending",
            },
        ),
        dialogue_pragmatics={},
        response_planner={"answer_shape": "structured_explanation", "question_policy": "optional_none", "practice_policy": "forbidden"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution=build_answer_obligation_resolver_v1(
            dialogue_act_resolution={"dialogue_act": "continuation_request"},
            last_assistant_offer={"is_open": True, "offer_type": "explanation"},
            unanswered_question_state={
                "last_direct_user_question": "Что такое пять драйверов?",
                "answer_required": True,
                "answer_status": "pending",
            },
            dialogue_style_state={"tone": "neutral", "length_preference": "adaptive", "avoid": []},
            dialogue_policy={"profile": "mvp_free_dialogue", "profile_preset": "free_dialogue_default"},
        ),
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["explicit_continue_previous_detected"] is True
    assert directive["must_answer_source"] == "explicit_continue_previous"
    assert directive["answer_target"] == "previous_open_loop"
    assert directive["must_answer"] == "Что такое пять драйверов?"
    assert directive["previous_must_answer_demoted"] is False


def test_direct_source_path_is_preserved() -> None:
    user_message = "Что во внутренней базе говорится про пять драйверов?"
    directive = build_final_answer_directive_v1(
        user_message=user_message,
        dialogue_policy=_base_policy(dialogue_act_resolution={"dialogue_act": "knowledge_question"}),
        dialogue_pragmatics={},
        response_planner={"answer_shape": "structured_explanation", "question_policy": "optional_none", "practice_policy": "forbidden"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={"direct_source_request": True, "retrieval_action": "query_kb"},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution={
            "dialogue_act": "knowledge_question",
            "answer_obligation": "answer_knowledge_question",
            "answer_shape": "structured_explanation",
            "question_policy": "optional_none",
            "depth": "medium",
        },
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["must_answer_source"] == "direct_source"
    assert directive["writer_contact_mode"] == "direct_kb"
    assert directive["answer_shape_profile"] == "direct_kb_grounded_compact"


def test_no_internal_db_latest_turn_is_preserved() -> None:
    user_message = "Ответь своими словами, без внутренней БД: что мне делать, если я злюсь на начальника?"
    directive = build_final_answer_directive_v1(
        user_message=user_message,
        dialogue_policy=_base_policy(dialogue_act_resolution={"dialogue_act": "direct_question"}),
        dialogue_pragmatics={},
        response_planner={"answer_shape": "direct_answer", "question_policy": "optional_none", "practice_policy": "forbidden"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution={
            "dialogue_act": "direct_question",
            "answer_obligation": "answer_direct_question",
            "answer_shape": "direct_answer",
            "question_policy": "optional_none",
            "depth": "medium",
        },
        unified_dialogue_profile={},
    ).to_dict()

    assert directive["must_answer"] == user_message
    assert directive["must_answer_source"] == "latest_turn"
    assert directive["answer_shape_profile"] == "no_internal_db_compact"


def test_explicit_practice_and_safety_sources_still_win() -> None:
    practice_message = "Дай практику, чтобы не реагировать на ложь начальника."
    practice_directive = build_final_answer_directive_v1(
        user_message=practice_message,
        dialogue_policy=_base_policy(dialogue_act_resolution={"dialogue_act": "practice_request"}),
        dialogue_pragmatics={},
        response_planner={"answer_shape": "one_step", "question_policy": "none", "practice_policy": "allowed_if_explicit"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=_thread(),
        state_snapshot=_state(),
        answer_obligation_resolution={
            "dialogue_act": "practice_request",
            "answer_obligation": "provide_one_bounded_practice",
            "answer_shape": "one_short_practice",
            "question_policy": "none",
            "depth": "short",
        },
        unified_dialogue_profile={},
    ).to_dict()

    safety_message = "Мне очень тревожно, я не могу успокоиться прямо сейчас."
    safety_directive = build_final_answer_directive_v1(
        user_message=safety_message,
        dialogue_policy=_base_policy(dialogue_act_resolution={"dialogue_act": "support_request"}),
        dialogue_pragmatics={},
        response_planner={"answer_shape": "safety_grounding", "question_policy": "none", "practice_policy": "required_for_safety_or_grounding"},
        active_line={},
        diagnostic_card={},
        diagnostic_center_shadow={},
        retrieval_decision={},
        knowledge_answer_guard={},
        thread_state=_thread(safety_active=True),
        state_snapshot=_state(safety_flag=True),
        answer_obligation_resolution={
            "dialogue_act": "support_request",
            "answer_obligation": "answer_latest_turn",
            "answer_shape": "simple_contact",
            "question_policy": "none",
            "depth": "short",
        },
        unified_dialogue_profile={},
    ).to_dict()

    assert practice_directive["must_answer_source"] == "explicit_practice"
    assert practice_directive["writer_contact_mode"] == "bounded_practice"
    assert safety_directive["must_answer_source"] == "safety"
    assert safety_directive["writer_contact_mode"] == "safety"
