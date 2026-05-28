from __future__ import annotations

from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


def _contract(active_line: dict) -> WriterContract:
    thread_state = ThreadState(
        thread_id="t-active-line",
        user_id="u-active-line",
        core_direction="focus",
        phase="clarify",
        response_mode="reflect",
    )
    return WriterContract(
        user_message="Почему ты мне предлагаешь практику? Я хочу разобраться",
        thread_state=thread_state,
        memory_bundle=MemoryBundle(has_relevant_knowledge=False),
        active_line=active_line,
        knowledge_answer_guard={
            "practice_gate": {"practice_allowed": False},
            "knowledge_answer": {"needed": False},
        },
    )


def test_active_line_present_in_prompt_context() -> None:
    ctx = _contract(
        {
            "version": "active_line_v1",
            "active_line": "механизм застревания на старте",
            "user_intent": "understand_mechanism",
            "continuity_mode": "continue_existing_line",
            "next_meaningful_move": "показать механизм",
            "should_continue_line": True,
            "should_ask_question": False,
            "should_offer_practice": False,
            "revoicing_allowed": False,
            "revoicing_style": "suppressed",
            "repair_mode": "",
            "practice_suppression_active": True,
        }
    ).to_prompt_context()

    assert ctx["active_line_version"] == "active_line_v1"
    assert ctx["active_line_user_intent"] == "understand_mechanism"
    assert ctx["active_line_continuity_mode"] == "continue_existing_line"


def test_should_offer_practice_false_propagates_to_prompt_context() -> None:
    ctx = _contract(
        {
            "version": "active_line_v1",
            "active_line": "разбор механизма",
            "user_intent": "understand_mechanism",
            "continuity_mode": "continue_existing_line",
            "next_meaningful_move": "вернуться к механизму",
            "should_continue_line": True,
            "should_ask_question": False,
            "should_offer_practice": False,
            "revoicing_allowed": False,
            "revoicing_style": "suppressed",
            "repair_mode": "",
            "practice_suppression_active": True,
        }
    ).to_prompt_context()

    assert ctx["active_line_should_offer_practice"] is False
    assert ctx["active_line_practice_suppression_active"] is True


def test_revoicing_disallow_propagates_to_prompt_context() -> None:
    ctx = _contract(
        {
            "version": "active_line_v1",
            "active_line": "продолжение линии",
            "user_intent": "understand_mechanism",
            "continuity_mode": "continue_existing_line",
            "next_meaningful_move": "показать узел",
            "should_continue_line": True,
            "should_ask_question": False,
            "should_offer_practice": False,
            "revoicing_allowed": False,
            "revoicing_style": "suppressed",
            "repair_mode": "",
            "practice_suppression_active": True,
        }
    ).to_prompt_context()

    assert ctx["active_line_revoicing_allowed"] is False
    assert ctx["active_line_revoicing_style"] == "suppressed"


def test_repair_mode_propagates_to_prompt_context() -> None:
    ctx = _contract(
        {
            "version": "active_line_v1",
            "active_line": "возврат к механизму",
            "user_intent": "correction_of_bot",
            "continuity_mode": "repair_and_continue_line",
            "next_meaningful_move": "признать сдвиг и вернуться к сути",
            "should_continue_line": True,
            "should_ask_question": False,
            "should_offer_practice": False,
            "revoicing_allowed": False,
            "revoicing_style": "suppressed",
            "repair_mode": "acknowledge_and_return_to_mechanism",
            "practice_suppression_active": True,
        }
    ).to_prompt_context()

    assert ctx["active_line_user_intent"] == "correction_of_bot"
    assert ctx["active_line_repair_mode"] == "acknowledge_and_return_to_mechanism"
