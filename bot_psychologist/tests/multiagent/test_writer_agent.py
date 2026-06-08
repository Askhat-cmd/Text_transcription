from __future__ import annotations

import importlib
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract


class _FakeCompletions:
    def __init__(self, payload: str = "", should_fail: bool = False) -> None:
        self.payload = payload
        self.should_fail = should_fail
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.should_fail:
            raise RuntimeError("llm failed")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.payload))],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=30, total_tokens=130),
        )


class _FakeResponses:
    def __init__(self, payload: str = "", should_fail: bool = False) -> None:
        self.payload = payload
        self.should_fail = should_fail
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.should_fail:
            raise RuntimeError("llm failed")
        return SimpleNamespace(
            output_text=self.payload,
            usage=SimpleNamespace(input_tokens=90, output_tokens=40, total_tokens=130),
        )


class _FakeClient:
    def __init__(self, payload: str = "", should_fail: bool = False) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(payload=payload, should_fail=should_fail))
        self.responses = _FakeResponses(payload=payload, should_fail=should_fail)


def _thread(
    *,
    mode: str = "reflect",
    safety_active: bool = False,
    must_avoid: list[str] | None = None,
    open_loops: list[str] | None = None,
) -> ThreadState:
    return ThreadState(
        thread_id="th_1",
        user_id="u1",
        core_direction="тревога перед встречей",
        phase="clarify",
        response_mode=mode,  # type: ignore[arg-type]
        response_goal="поддержка",
        nervous_state="window",
        openness="open",
        ok_position="I+W+",
        must_avoid=list(must_avoid or []),
        open_loops=list(open_loops or []),
        safety_active=safety_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _contract(
    *,
    mode: str = "reflect",
    safety_active: bool = False,
    message: str = "привет",
    must_avoid: list[str] | None = None,
    open_loops: list[str] | None = None,
    conversation_context: str = "u: hi\na: hello",
    hits: list[SemanticHit] | None = None,
) -> WriterContract:
    bundle = MemoryBundle(
        conversation_context=conversation_context,
        user_profile=UserProfile(patterns=["avoidance"], values=["honesty"]),
        semantic_hits=list(hits or []),
        has_relevant_knowledge=bool(hits),
        context_turns=3,
    )
    return WriterContract(
        user_message=message,
        thread_state=_thread(
            mode=mode,
            safety_active=safety_active,
            must_avoid=must_avoid,
            open_loops=open_loops,
        ),
        memory_bundle=bundle,
    )


def _mvp_contract(*, message: str, dialogue_policy: dict | None = None, response_planner: dict | None = None) -> WriterContract:
    contract = _contract(message=message)
    contract.dialogue_policy = {
        "profile": "mvp_free_dialogue",
        **(dialogue_policy or {}),
    }
    contract.response_planner = {
        "enabled": True,
        "next_move": "deepen_mechanism",
        "answer_shape": "expanded_explanation",
        "response_depth": "long",
        "question_policy": "optional_none",
        "practice_policy": "forbidden",
        "revoicing_policy": "suppressed",
        **(response_planner or {}),
    }
    return contract


@pytest.mark.asyncio
async def test_write_returns_non_empty() -> None:
    agent = WriterAgent(client=_FakeClient("готовый ответ"), model="gpt-5-mini")
    result = await agent.write(_contract())
    assert isinstance(result, str)
    assert result.strip() != ""


@pytest.mark.asyncio
async def test_safety_fallback_on_error_sets_debug() -> None:
    agent = WriterAgent(client=_FakeClient("x", should_fail=True), model="gpt-5-mini")
    result = await agent.write(_contract(mode="safe_override", safety_active=True))
    assert "здесь" in result.lower()
    assert agent.last_debug.get("error")
    assert agent.last_debug.get("fallback_used") is True


@pytest.mark.asyncio
async def test_static_fallback_validate_on_error() -> None:
    agent = WriterAgent(client=_FakeClient("x", should_fail=True), model="gpt-5-mini")
    result = await agent.write(_contract(mode="validate", safety_active=False))
    assert "слышу" in result.lower()
    assert agent.last_debug.get("fallback_used") is True


@pytest.mark.asyncio
async def test_writer_gpt5_uses_responses_api() -> None:
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract())

    assert len(client.responses.calls) == 1
    assert len(client.chat.completions.calls) == 0
    req = client.responses.calls[0]
    assert req["model"] == "gpt-5-mini"
    assert req["max_output_tokens"] == 600
    assert "temperature" not in req
    assert "max_tokens" not in req
    assert agent.last_debug["api_mode"] == "responses"


@pytest.mark.asyncio
async def test_writer_gpt4o_uses_chat_api_with_temperature() -> None:
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-4o-mini")
    await agent._call_llm(_contract())

    assert len(client.chat.completions.calls) == 1
    assert len(client.responses.calls) == 0
    req = client.chat.completions.calls[0]
    assert req["model"] == "gpt-4o-mini"
    assert req["temperature"] == pytest.approx(0.7, abs=1e-9)
    assert req["max_tokens"] == 600
    assert agent.last_debug["api_mode"] == "chat_completions"


@pytest.mark.asyncio
async def test_prompt_contains_must_avoid_for_responses_path() -> None:
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract(must_avoid=["оценка", "диагноз"]))

    user_input = str(client.responses.calls[0]["input"])
    assert "оценка" in user_input
    assert "диагноз" in user_input


@pytest.mark.asyncio
async def test_prompt_contains_open_loops_for_responses_path() -> None:
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract(open_loops=["почему я так реагирую"]))

    user_input = str(client.responses.calls[0]["input"])
    assert "почему я так реагирую" in user_input


@pytest.mark.asyncio
async def test_conversation_context_truncated() -> None:
    old_part = "legacy_context " * 260
    tail = "RECENT FULL TURNS:\nUSER#turn_9: last user turn\nASSISTANT#turn_9: last assistant turn"
    long_ctx = old_part + "\n" + tail
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract(conversation_context=long_ctx))

    user_input = str(client.responses.calls[0]["input"])
    assert "[older context omitted:" in user_input
    assert "USER#turn_9: last user turn" in user_input
    assert "ASSISTANT#turn_9: last assistant turn" in user_input


@pytest.mark.asyncio
async def test_semantic_hits_limit_to_two() -> None:
    hits = [
        SemanticHit(chunk_id="1", content="hit_1", source="s", score=0.9),
        SemanticHit(chunk_id="2", content="hit_2", source="s", score=0.8),
        SemanticHit(chunk_id="3", content="hit_3", source="s", score=0.7),
    ]
    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-5-mini")
    await agent._call_llm(_contract(hits=hits))

    user_input = str(client.responses.calls[0]["input"])
    assert "hit_1" in user_input
    assert "hit_2" in user_input
    assert "hit_3" not in user_input


def test_model_from_agent_llm_config_dynamic() -> None:
    from bot_agent.multiagent.agents.agent_llm_config import reset_model_for_agent, set_model_for_agent

    writer_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")
    set_model_for_agent("writer", "gpt-4.1-mini")
    try:
        agent = writer_module.WriterAgent(client=_FakeClient("ok"))
        assert agent._resolve_model() == "gpt-4.1-mini"
    finally:
        reset_model_for_agent("writer")


@pytest.mark.asyncio
async def test_hot_swap_model_without_recreate_instance() -> None:
    from bot_agent.multiagent.agents.agent_llm_config import reset_model_for_agent, set_model_for_agent

    client = _FakeClient("ok")
    agent = WriterAgent(client=client)

    set_model_for_agent("writer", "gpt-5-mini")
    await agent._call_llm(_contract())
    assert agent.last_debug["api_mode"] == "responses"

    set_model_for_agent("writer", "gpt-4o-mini")
    await agent._call_llm(_contract())
    assert agent.last_debug["api_mode"] == "chat_completions"

    reset_model_for_agent("writer")


@pytest.mark.asyncio
async def test_hot_swap_temperature_without_recreate_instance() -> None:
    from bot_agent.multiagent.agents.agent_llm_config import (
        reset_temperature_for_agent,
        set_temperature_for_agent,
    )

    client = _FakeClient("ok")
    agent = WriterAgent(client=client, model="gpt-4o-mini")

    set_temperature_for_agent("writer", 0.33)
    await agent._call_llm(_contract())
    assert client.chat.completions.calls[-1]["temperature"] == pytest.approx(0.33, abs=1e-9)

    set_temperature_for_agent("writer", 1.1)
    await agent._call_llm(_contract())
    assert client.chat.completions.calls[-1]["temperature"] == pytest.approx(1.1, abs=1e-9)

    reset_temperature_for_agent("writer")


def test_detect_language_ru() -> None:
    assert WriterAgent._detect_language("Привет, как ты?") == "ru"


def test_detect_language_en() -> None:
    assert WriterAgent._detect_language("Hello there, how are you?") == "en"


def test_mvp_sarcasm_triggers_repair_answer_shape() -> None:
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")
    contract = _mvp_contract(
        message="спасибо что ты не дал мне никаких ответов",
        dialogue_policy={
            "sarcasm_or_negative_feedback": True,
            "explicit_answer_need": True,
        },
    )
    result = agent._enforce_answer_compliance("Спасибо за сообщение, чем еще помочь?", contract)
    assert "исправляюсь" in result.lower()
    assert agent.last_debug.get("final_answer_shape") == "repair_plus_direct_answer"


def test_mvp_summary_request_returns_structured_summary() -> None:
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")
    contract = _mvp_contract(
        message="обобщи весь разговор",
        dialogue_policy={"summary_request": True},
    )
    result = agent._enforce_answer_compliance("Давай сделаем один шаг прямо сейчас.", contract)
    assert "итог" in result.lower()
    assert "1." in result
    assert agent.last_debug.get("final_answer_shape") == "structured_summary"


def test_mvp_direct_concrete_request_returns_variants() -> None:
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")
    contract = _mvp_contract(
        message="назови конкретно, какая черта во мне может цепляться",
        dialogue_policy={"direct_concrete_request": True},
    )
    result = agent._enforce_answer_compliance("Давай исследуем это мягко.", contract)
    assert "гиперконтроль" in result.lower()
    assert "самообесценивание" in result.lower()
    assert agent.last_debug.get("final_answer_shape") == "direct_answer_with_variants"


def test_mvp_formula_stub_defers_to_acceptance_gate_without_static_answer() -> None:
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")
    contract = _mvp_contract(
        message="в разговоре с начальником я опять сжимаюсь и ухожу в молчание, объясни по моей ситуации без практик",
        dialogue_policy={
            "explicit_answer_need": True,
            "application_request": True,
        },
    )
    response_text = (
        "Сейчас полезнее не упражнение, а прямое объяснение: автоматический контроль может перегружать "
        "внимание еще до действия, поэтому энергия уходит в внутренний спор."
    )
    result = agent._enforce_answer_compliance(response_text, contract)
    assert result == response_text
    assert agent.last_debug.get("final_answer_shape") == "template_repair_deferred_to_gate"
    evaluator = agent.last_debug.get("answer_fit_evaluator") or {}
    assert evaluator.get("fit_status") == "fail"
    assert agent.last_debug.get("answer_fit_repair_applied") is True
    assert agent.last_debug.get("template_leakage_repair_deferred_to_gate") is True


def test_literal_markdown_echo_request_is_preserved() -> None:
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")
    requested_markdown = "**Жирный заголовок**\n\nПервый абзац.\n\n- Пункт один\n- Пункт два"
    contract = _mvp_contract(
        message=f"Верни без объяснений и без изменений следующий markdown-блок: {requested_markdown}",
        dialogue_policy={"explicit_answer_need": True},
    )
    result = agent._enforce_answer_compliance("Я слышу тебя. Расскажи больше, если хочешь.", contract)
    assert result == requested_markdown
    assert agent.last_debug.get("format_request_repair_applied") is True
    assert agent.last_debug.get("final_answer_shape") == "literal_markdown_echo"


def test_mvp_answer_last_offer_rewrites_repeated_offer_into_direct_answer() -> None:
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")
    contract = _mvp_contract(
        message="да",
        dialogue_policy={
            "answer_obligation_resolution": {
                "answer_obligation": "answer_last_offer",
            },
            "last_assistant_offer": {
                "is_open": True,
                "offer_text_summary": "Да - могу так сделать. Сначала покажу адаптацию для Красного, Оранжевого и Зеленого уровней.",
            },
        },
    )
    result = agent._enforce_answer_compliance(
        "Да - могу так сделать. Предлагаю такой план, прежде чем давать полную инструкцию.",
        contract,
    )
    assert "красный уровень" in result.lower()
    assert "оранжевый уровень" in result.lower()
    assert "зеленый уровень" in result.lower()
    assert agent.last_debug.get("final_answer_shape") == "answer_last_offer_repair"


def test_mvp_answer_last_offer_skips_second_confirmation_and_returns_levels() -> None:
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")
    contract = _mvp_contract(
        message="да",
        dialogue_policy={
            "answer_obligation_resolution": {
                "answer_obligation": "answer_last_offer",
            },
            "last_assistant_offer": {
                "is_open": True,
                "offer_text_summary": "Потом покажу адаптацию под Красный, Оранжевый и Зеленый уровни.",
            },
        },
    )
    result = agent._enforce_answer_compliance(
        "После подтверждения я пришлю адаптацию в выбранном формате.",
        contract,
    )
    assert "красный уровень" in result.lower()
    assert "оранжевый уровень" in result.lower()
    assert "зеленый уровень" in result.lower()
    assert agent.last_debug.get("final_answer_shape") == "answer_last_offer_repair"


def test_mvp_answer_last_offer_uses_last_direct_question_when_offer_summary_is_truncated() -> None:
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")
    contract = _mvp_contract(
        message="да",
        dialogue_policy={
            "answer_obligation_resolution": {
                "answer_obligation": "answer_last_offer",
            },
            "last_assistant_offer": {
                "is_open": True,
                "offer_text_summary": "Хорошо - сначала выберем формат, потом продолжим.",
            },
            "unanswered_question_state": {
                "last_direct_user_question": "Покажешь потом адаптацию под Красный, Оранжевый и Зеленый уровни?",
            },
        },
    )
    result = agent._enforce_answer_compliance(
        "Какой формат предпочитаешь дальше?",
        contract,
    )
    assert "красный уровень" in result.lower()
    assert "оранжевый уровень" in result.lower()
    assert "зеленый уровень" in result.lower()
    assert agent.last_debug.get("final_answer_shape") == "answer_last_offer_repair"


def test_mvp_repair_complaint_answers_saved_neurostalking_question() -> None:
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")
    contract = _mvp_contract(
        message="ты не ответил мне на вопрос",
        dialogue_policy={
            "answer_obligation_resolution": {
                "answer_obligation": "repair_and_answer_last_question",
            },
            "unanswered_question_state": {
                "last_direct_user_question": "что такое нейросталкинг?",
            },
        },
    )
    contract.dialogue_pragmatics = {"repair_user_dissatisfaction": True}
    result = agent._enforce_answer_compliance("Ладно, тогда уточню иначе.", contract)
    assert "ты прав" in result.lower()
    assert "нейросталкинг" in result.lower()
    assert "триггер" in result.lower()
    assert agent.last_debug.get("final_answer_shape") in {
        "repair_plus_direct_answer",
        "repair_answer_last_question_repair",
    }


def test_mvp_preserves_substantive_knowledge_answer_when_practice_is_forbidden() -> None:
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")
    contract = _mvp_contract(
        message="повторю вопрос, что такое нейросталкинг, и как его применять?",
        dialogue_policy={
            "application_request": True,
            "answer_obligation_resolution": {
                "answer_obligation": "answer_knowledge_question",
            },
        },
    )
    response_text = (
        "Нейросталкинг - это внутреннее наблюдение за триггерами, паттернами и автоматическими реакциями, "
        "чтобы не сливаться с ними и возвращать себе выбор.\n\n"
        "Применять его можно так: замечать, что запускает реакцию, видеть привычную последовательность "
        "\"триггер -> мысль -> тело -> действие\" и выбирать более точный ответ вместо автопилота.\n\n"
        "Если хочешь, могу потом разобрать это на твоем примере."
    )
    result = agent._enforce_answer_compliance(response_text, contract)
    assert "нейросталкинг" in result.lower()
    assert "применять" in result.lower()
    assert "если хочешь" not in result.lower()


def test_mvp_preserves_offer_outline_for_later_confirmation_flow() -> None:
    agent = WriterAgent(client=_FakeClient("ok"), model="gpt-5-mini")
    contract = _mvp_contract(
        message="Можешь сначала предложить, а не отвечать целиком: покажешь потом, как адаптировать технику под Красный, Оранжевый и Зеленый уровни?",
        dialogue_policy={
            "application_request": True,
            "answer_obligation_resolution": {
                "answer_obligation": "answer_direct_question",
            },
        },
        response_planner={
            "next_move": "continue_active_line",
            "answer_shape": "mechanism_explanation",
            "question_policy": "optional_none",
            "practice_policy": "forbidden",
        },
    )
    response_text = (
        "Сначала предложу саму идею, а затем отдельно покажу адаптацию под Красный, Оранжевый и Зеленый уровни.\n\n"
        "Короткая схема такая: намерение, минимальный запуск и наблюдение результата.\n\n"
        "Если хочешь, следующим сообщением сразу разложу это по трем уровням."
    )
    result = agent._enforce_answer_compliance(response_text, contract)
    assert "красный" in result.lower()
    assert "оранжевый" in result.lower()
    assert "зеленый" in result.lower()
    assert "следующим сообщением" not in result.lower()
    assert agent.last_debug.get("final_answer_shape") in {
        "sanitized_direct_no_forced_practice",
        "preserved_application_answer",
    }
