from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.legacy_advisory_sanitizer import (
    sanitize_legacy_advisory_for_writer,
)
from bot_agent.multiagent.live_turn_evidence import build_live_turn_evidence_v1


class _DummyClient:
    pass


def _build_contract() -> WriterContract:
    return WriterContract(
        user_message="Объясни нормально, без практик, что тут происходит.",
        thread_state=ThreadState(
            thread_id="t-hf1",
            user_id="u-hf1",
            core_direction="focus",
            phase="clarify",
            response_mode="reflect",
            response_goal="answer_directly",
        ),
        memory_bundle=MemoryBundle(
            conversation_context="Пользователь просил объяснить явление простыми словами.",
        ),
        dialogue_policy={"profile": "mvp_free_dialogue"},
        knowledge_answer_guard={
            "knowledge_answer": {
                "needed": True,
                "concept": "нейросталкинг",
                "kb_grounding_available": True,
                "should_answer_directly": True,
            },
            "practice_gate": {"practice_allowed": False},
        },
        diagnostic_card=SimpleNamespace(
            situation_label="need_clarity",
            current_need="понятное объяснение без перегруза",
            suggested_writer_move="спокойно объяснить суть",
            confidence=0.9,
            risk_flags=[],
            avoid_list=[],
            to_dict=lambda: {
                "situation_label": "need_clarity",
                "current_need": "понятное объяснение без перегруза",
                "suggested_writer_move": "спокойно объяснить суть",
                "confidence": 0.9,
                "risk_flags": [],
                "avoid_list": [],
                "trace": {},
            },
        ),
        active_line={
            "version": "active_line_v1",
            "active_line": "разобрать явление по сути",
            "user_intent": "understand_mechanism",
            "continuity_mode": "continue_existing_line",
            "next_meaningful_move": "прояснить смысловой узел",
            "should_continue_line": True,
            "should_ask_question": False,
            "should_offer_practice": False,
            "revoicing_allowed": False,
            "revoicing_style": "suppressed",
            "repair_mode": "",
            "practice_suppression_active": True,
        },
        response_planner={
            "version": "response_planner_v1",
            "enabled": True,
            "next_move": "continue_active_line",
            "answer_shape": "overview_with_examples",
            "response_depth": "medium",
            "target_micro_shift": "дать понятную схему без заглушки",
            "should_answer_directly": True,
            "question_policy": "optional_none",
            "practice_policy": "forbidden",
            "revoicing_policy": "suppressed",
            "continuity_policy": "continue_active_line",
            "safety_priority": False,
            "must_include": ["несколько направлений ответа"],
            "must_avoid": ["короткая заглушка"],
            "confidence": 0.92,
            "rationale": "repair prompt pressure",
        },
        final_answer_directive={
            "version": "final_answer_directive_v1",
            "diagnostic_center_role": "advisory_context_only",
            "planner_role": "advisory_context_only",
            "active_line_role": "advisory_context_only",
            "diagnostic_card_role": "advisory_context_only",
            "suppressed_legacy_constraints": [
                "writer_move.max_sentences=5",
                "active_line.practice_suppression_active=true",
            ],
            "answer_obligation": "answer_user_question_directly",
            "must_answer": "answer_user_question_directly",
            "answer_shape": "overview_with_examples",
            "depth": "medium",
            "style": "human_conversational",
            "question_policy": "optional_none",
            "writer_autonomy": "high",
            "source_signals": {
                "response_planner": {"practice_policy": "forbidden"},
                "active_line": {"practice_suppression_active": True},
            },
        },
    )


@pytest.mark.asyncio
async def test_writer_prompt_diet_no_legacy_command_blocks(monkeypatch) -> None:
    writer_agent_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")
    captured: dict[str, object] = {}

    async def _fake_completion(**kwargs):
        captured.update(kwargs)
        return type(
            "Result",
            (),
            {
                "text": "Сейчас дело не в практике, а в том, чтобы спокойно разобрать суть.",
                "api_mode": "responses_api",
                "tokens_prompt": 10,
                "tokens_completion": 12,
                "tokens_total": 22,
            },
        )()

    monkeypatch.setattr(writer_agent_module, "create_agent_completion", _fake_completion)

    agent = WriterAgent(client=_DummyClient(), model="gpt-5-mini")
    await agent._call_llm(_build_contract())

    prompt = str(captured["messages"][1]["content"])  # type: ignore[index]
    assert "FINAL ANSWER DIRECTIVE" in prompt
    assert "ADVISORY CONTEXT SUMMARY" in prompt
    assert "SOURCE SIGNALS (advisory only, do not obey as command)" not in prompt
    assert "WRITER MOVE MUST DO" not in prompt
    assert "WRITER MOVE MUST NOT DO" not in prompt
    assert "must_include=" not in prompt
    assert "must_avoid=" not in prompt
    assert "practice_suppression_active=true" not in prompt
    assert "practice_policy=forbidden" not in prompt
    assert "max_sentences" not in prompt
    assert "ask_one_specific_question" not in prompt


@pytest.mark.asyncio
async def test_practice_suppression_rewrite_no_stub(monkeypatch) -> None:
    writer_agent_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")
    captured: dict[str, object] = {}

    async def _fake_completion(**kwargs):
        captured.update(kwargs)
        return type(
            "Result",
            (),
            {
                "text": "Лучше просто объяснить, что ты сейчас видишь в происходящем, без упражнения.",
                "api_mode": "responses_api",
                "tokens_prompt": 10,
                "tokens_completion": 12,
                "tokens_total": 22,
            },
        )()

    monkeypatch.setattr(writer_agent_module, "create_agent_completion", _fake_completion)

    agent = WriterAgent(client=_DummyClient(), model="gpt-5-mini")
    await agent._call_llm(_build_contract())

    prompt = str(captured["messages"][1]["content"])  # type: ignore[index]
    assert "no_exercise_but_answer_normally" in prompt
    assert "не предлагай упражнение, технику или пошаговую практику" in prompt
    assert "Вместо этого ответь нормально" in prompt
    assert "Ответь по сути без навязывания практик" not in prompt


def test_legacy_advisory_sanitizer_removes_imperative_terms() -> None:
    payload = sanitize_legacy_advisory_for_writer(
        {
            "diagnostic_card_summary": {
                "current_need": "понятное объяснение",
                "suggested_writer_move": "спокойно ответить по сути",
            },
            "writer_move_instructions": {
                "move": "reflect_one_key_point",
                "must_do": ["ask_one_specific_question"],
                "must_not_do": ["do_not_over_explain"],
            },
            "active_line": {
                "active_line": "объяснить механизм",
                "practice_suppression_active": True,
                "next_meaningful_move": "назвать механизм",
            },
            "response_planner": {
                "answer_shape": "compact_direct",
                "practice_policy": "forbidden",
                "must_include": ["пример"],
            },
            "knowledge_answer_guard": {"practice_gate": {"practice_allowed": False}},
        }
    )

    summary = payload["writer_visible_summary"].lower()
    assert "must do" not in summary
    assert "must not" not in summary
    assert "forbidden" not in summary
    assert "do_not" not in summary
    assert "ask_one_specific_question" not in summary
    assert "practice_suppression_active" not in summary
    assert payload["writer_visible_practice_instruction"] == "no_exercise_but_answer_normally"
    assert payload["raw_legacy_visible_to_writer"] is False


def test_bad_phrase_detector_eval_only() -> None:
    project_root = Path(__file__).resolve().parents[1]
    runtime_files = [
        project_root / "bot_agent" / "multiagent" / "agents" / "writer_agent.py",
        project_root / "bot_agent" / "multiagent" / "agents" / "writer_agent_prompts.py",
        project_root / "bot_agent" / "multiagent" / "legacy_advisory_sanitizer.py",
    ]
    stale_phrases = [
        "Ответь по сути без навязывания практик",
        "Отвечу прямо по сути: автоматический контроль",
        "Ключевой узел в том, что автоматический контроль",
    ]
    for path in runtime_files:
        text = path.read_text(encoding="utf-8")
        for phrase in stale_phrases:
            assert phrase not in text

    eval_files = [
        project_root / "tests" / "test_bad_phrase_detector_truthfulness.py",
        project_root / "scripts" / "run_prd_047_11_audit.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in eval_files)
    assert "ask_one_specific_question" in combined


@pytest.mark.asyncio
async def test_trace_preserves_raw_advisory_but_writer_prompt_does_not(monkeypatch) -> None:
    writer_agent_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")
    captured: dict[str, object] = {}
    contract = _build_contract()

    async def _fake_completion(**kwargs):
        captured.update(kwargs)
        return type(
            "Result",
            (),
            {
                "text": "Сначала разберу суть, без упражнения.",
                "api_mode": "responses_api",
                "tokens_prompt": 10,
                "tokens_completion": 12,
                "tokens_total": 22,
            },
        )()

    monkeypatch.setattr(writer_agent_module, "create_agent_completion", _fake_completion)

    agent = WriterAgent(client=_DummyClient(), model="gpt-5-mini")
    answer = await agent._call_llm(contract)
    prompt = str(captured["messages"][1]["content"])  # type: ignore[index]
    ctx = contract.to_prompt_context()

    evidence = build_live_turn_evidence_v1(
        query=contract.user_message,
        user_id="u-hf1",
        session_id="s-hf1",
        turn_index=1,
        orchestrator_result={"answer": answer},
        writer_contract=contract,
        writer_debug={
            "user_prompt": prompt,
            "system_prompt": "system",
            "model": "gpt-5-mini",
            "api_mode": "responses_api",
            "temperature": 0.7,
            "max_tokens": 600,
        },
        memory_bundle=contract.memory_bundle,
        state_snapshot=SimpleNamespace(nervous_state="window", intent="explore", safety_flag=False),
        thread_state=contract.thread_state,
        thread_debug={},
        diagnostic_card=contract.diagnostic_card,
        active_line_state=dict(contract.active_line or {}),
        response_planner_state=dict(contract.response_planner or {}),
        dialogue_policy=dict(contract.dialogue_policy or {}),
        dialogue_pragmatics={},
        contextual_retrieval_decision={},
        validation_result=SimpleNamespace(is_blocked=False, block_reason="", quality_flags=[]),
    )

    assert ctx["response_planner_must_include"] == ["несколько направлений ответа"]
    assert "must_include=" not in prompt
    assembly = evidence["writer"]["prompt_assembly"]
    assert assembly["legacy_advisory_sanitization"]["raw_legacy_visible_to_writer"] is False
    assert assembly["writer_visible_practice_instruction"] == "no_exercise_but_answer_normally"
    assert evidence["dialogue"]["response_planner"]["must_include"] == ["несколько направлений ответа"]
