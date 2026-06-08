from __future__ import annotations

import inspect
from datetime import datetime

from bot_agent.multiagent import concrete_answer_fit
from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


class _FakeClient:
    pass


def _contract(message: str) -> WriterContract:
    return WriterContract(
        user_message=message,
        thread_state=ThreadState(
            thread_id="th_hf1",
            user_id="u_hf1",
            core_direction="concrete answer fit",
            phase="clarify",
            response_mode="reflect",
            response_goal="answer",
            nervous_state="window",
            openness="open",
            ok_position="I+W+",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ),
        memory_bundle=MemoryBundle(conversation_context="", context_turns=0),
        dialogue_policy={
            "unified_dialogue_profile": {"profile": "mvp_free_dialogue"},
            "explicit_answer_need": True,
            "application_request": True,
        },
    )


def test_concrete_answer_fit_does_not_export_static_answer_builder() -> None:
    assert not hasattr(concrete_answer_fit, "build_contextual_no_practice_answer")
    assert "build_contextual_no_practice_answer" not in getattr(concrete_answer_fit, "__all__", [])


def test_concrete_answer_fit_source_has_no_user_facing_template_skeleton() -> None:
    source = inspect.getsource(concrete_answer_fit)

    assert "в твоем описании важно не свести все к одному общему механизму" not in source
    assert "Сначала отдели факты от вывода" not in source
    assert "Затем найди центральное убеждение" not in source
    assert "Практический смысл распутывания" not in source


def test_writer_defers_formula_stub_to_gate_instead_of_static_rewrite() -> None:
    agent = WriterAgent(client=_FakeClient(), model="gpt-5-mini")
    response_text = (
        "Сейчас полезнее не упражнение, а прямое объяснение: автоматический контроль "
        "перегружает внимание еще до действия."
    )

    result = agent._enforce_answer_compliance(
        response_text,
        _contract(
            "в разговоре с начальником я сжимаюсь и молчу, объясни по моей ситуации без практик"
        ),
    )

    assert result == response_text
    assert agent.last_debug.get("template_leakage_repair_deferred_to_gate") is True
    assert agent.last_debug.get("final_answer_shape") == "template_repair_deferred_to_gate"
