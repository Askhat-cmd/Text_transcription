from __future__ import annotations

import asyncio
import inspect
import json
import importlib
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.memory_retrieval import MemoryRetrievalAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle, SemanticHit, UserProfile
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.orchestrator import MultiAgentOrchestrator


def _thread(
    *,
    phase: str = "clarify",
    relation: str = "continue",
    core_direction: str = "тревога перед встречей",
    open_loops: list[str] | None = None,
) -> ThreadState:
    return ThreadState(
        thread_id="tm_thread",
        user_id="u1",
        core_direction=core_direction,
        phase=phase,  # type: ignore[arg-type]
        relation_to_thread=relation,  # type: ignore[arg-type]
        open_loops=list(open_loops or []),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _hit(chunk_id: str, score: float, content: str = "text", source: str = "src") -> SemanticHit:
    return SemanticHit(chunk_id=chunk_id, content=content, source=source, score=score)


@pytest.mark.asyncio
async def test_mr_01_bundle_fields(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(return_value="User: hi\n---"))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(return_value=UserProfile()))
    monkeypatch.setattr(agent, "_load_rag", AsyncMock(return_value=[_hit("1", 0.7)]))
    bundle = await agent.assemble(user_message="привет", thread_state=_thread(), user_id="u1")
    assert isinstance(bundle, MemoryBundle)
    assert isinstance(bundle.conversation_context, str)
    assert isinstance(bundle.user_profile, UserProfile)
    assert isinstance(bundle.semantic_hits, list)
    assert isinstance(bundle.retrieved_chunks, list)
    assert isinstance(bundle.has_relevant_knowledge, bool)
    assert isinstance(bundle.context_turns, int)


def test_mr_02_bundle_round_trip() -> None:
    original = MemoryBundle(
        conversation_context="User: hi\nAssistant: hello\n---",
        user_profile=UserProfile(
            patterns=["p1"], triggers=["t1"], values=["v1"], progress_notes=["n1"]
        ),
        semantic_hits=[_hit("h1", 0.9, content="chunk")],
        retrieved_chunks=["chunk"],
        has_relevant_knowledge=True,
        context_turns=6,
    )
    restored = MemoryBundle.from_dict(original.to_dict())
    assert restored.to_dict() == original.to_dict()


def test_mr_03_semantic_hit_fields() -> None:
    hit = _hit("abc", 0.55, content="content", source="book")
    payload = hit.to_dict()
    assert payload["chunk_id"] == "abc"
    assert payload["content"] == "content"
    assert payload["source"] == "book"
    assert payload["score"] == 0.55


def test_mr_04_user_profile_fields() -> None:
    profile = UserProfile(
        patterns=["avoidance"],
        triggers=["criticism"],
        values=["honesty"],
        progress_notes=["started journaling"],
    )
    payload = profile.to_dict()
    assert payload["patterns"] == ["avoidance"]
    assert payload["triggers"] == ["criticism"]
    assert payload["values"] == ["honesty"]
    assert payload["progress_notes"] == ["started journaling"]


def test_mr_05_n_turns_stabilize() -> None:
    assert MemoryRetrievalAgent._resolve_n_turns(_thread(phase="stabilize")) == 3


def test_mr_06_n_turns_integrate() -> None:
    assert MemoryRetrievalAgent._resolve_n_turns(_thread(phase="integrate")) == 10


def test_mr_07_n_turns_new_thread() -> None:
    assert MemoryRetrievalAgent._resolve_n_turns(_thread(relation="new_thread")) == 2


def test_mr_08_n_turns_default_unknown_phase() -> None:
    fake = SimpleNamespace(relation_to_thread="continue", phase="unknown")
    assert MemoryRetrievalAgent._resolve_n_turns(fake) == 6


def test_mr_09_rag_query_with_core() -> None:
    thread = _thread(core_direction="тревога на работе", open_loops=[])
    query = MemoryRetrievalAgent._build_rag_query("хочу разобраться", thread)
    assert "тревога на работе" in query


def test_mr_10_rag_query_with_loop() -> None:
    thread = _thread(open_loops=["почему я так реагирую"])
    query = MemoryRetrievalAgent._build_rag_query("хочу разобраться", thread)
    assert "почему я так реагирую" in query


def test_mr_11_rag_query_short_core_ignored() -> None:
    thread = _thread(core_direction="коротко", open_loops=[])
    query = MemoryRetrievalAgent._build_rag_query("хочу разобраться", thread)
    assert "коротко" not in query


def test_mr_12_rag_query_max_len() -> None:
    long_text = "а" * 1000
    query = MemoryRetrievalAgent._build_rag_query(long_text, _thread())
    assert len(query) <= 300


@pytest.mark.asyncio
async def test_mr_13_rag_score_filter(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(return_value="ctx"))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(return_value=UserProfile()))
    monkeypatch.setattr(
        agent,
        "_load_rag",
        AsyncMock(return_value=[_hit("a", 0.2), _hit("b", 0.5), _hit("c", 0.9)]),
    )
    bundle = await agent.assemble(user_message="q", thread_state=_thread(), user_id="u1")
    ids = [h.chunk_id for h in bundle.semantic_hits]
    assert ids == ["c", "b"]


@pytest.mark.asyncio
async def test_mr_14_rag_sort_desc(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(return_value="ctx"))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(return_value=UserProfile()))
    monkeypatch.setattr(
        agent,
        "_load_rag",
        AsyncMock(return_value=[_hit("x", 0.7), _hit("y", 0.95), _hit("z", 0.8)]),
    )
    bundle = await agent.assemble(user_message="q", thread_state=_thread(), user_id="u1")
    assert [h.chunk_id for h in bundle.semantic_hits] == ["y", "z", "x"]


@pytest.mark.asyncio
async def test_mr_15_has_knowledge_true(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(return_value="ctx"))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(return_value=UserProfile()))
    monkeypatch.setattr(agent, "_load_rag", AsyncMock(return_value=[_hit("x", 0.7)]))
    bundle = await agent.assemble(user_message="q", thread_state=_thread(), user_id="u1")
    assert bundle.has_relevant_knowledge is True


@pytest.mark.asyncio
async def test_mr_16_has_knowledge_false(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(return_value="ctx"))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(return_value=UserProfile()))
    monkeypatch.setattr(agent, "_load_rag", AsyncMock(return_value=[]))
    bundle = await agent.assemble(user_message="q", thread_state=_thread(), user_id="u1")
    assert bundle.has_relevant_knowledge is False


@pytest.mark.asyncio
async def test_mr_17_conv_fail_graceful(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(return_value=UserProfile()))
    monkeypatch.setattr(agent, "_load_rag", AsyncMock(return_value=[_hit("x", 0.7)]))
    bundle = await agent.assemble(user_message="q", thread_state=_thread(), user_id="u1")
    assert bundle.conversation_context == ""


@pytest.mark.asyncio
async def test_mr_18_profile_fail_graceful(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(return_value="ctx"))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(agent, "_load_rag", AsyncMock(return_value=[]))
    bundle = await agent.assemble(user_message="q", thread_state=_thread(), user_id="u1")
    assert bundle.user_profile == UserProfile()


@pytest.mark.asyncio
async def test_mr_19_rag_fail_graceful(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(return_value="ctx"))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(return_value=UserProfile()))
    monkeypatch.setattr(agent, "_load_rag", AsyncMock(side_effect=RuntimeError("boom")))
    bundle = await agent.assemble(user_message="q", thread_state=_thread(), user_id="u1")
    assert bundle.semantic_hits == []


@pytest.mark.asyncio
async def test_mr_20_all_fail_graceful(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(side_effect=RuntimeError("c")))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(side_effect=RuntimeError("p")))
    monkeypatch.setattr(agent, "_load_rag", AsyncMock(side_effect=RuntimeError("r")))
    bundle = await agent.assemble(user_message="q", thread_state=_thread(), user_id="u1")
    assert bundle.conversation_context == ""
    assert bundle.user_profile == UserProfile()
    assert bundle.semantic_hits == []
    assert bundle.has_relevant_knowledge is False


@pytest.mark.asyncio
async def test_mr_21_parallel_gather(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(return_value="ctx"))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(return_value=UserProfile()))
    monkeypatch.setattr(agent, "_load_rag", AsyncMock(return_value=[]))

    import bot_agent.multiagent.agents.memory_retrieval as mr_module

    called = {"gather": False}
    real_gather = asyncio.gather

    async def _wrapped(*args, **kwargs):
        called["gather"] = True
        return await real_gather(*args, **kwargs)

    monkeypatch.setattr(mr_module.asyncio, "gather", _wrapped)
    _ = await agent.assemble(user_message="q", thread_state=_thread(), user_id="u1")
    assert called["gather"] is True


def test_mr_22_no_llm_calls() -> None:
    import bot_agent.multiagent.agents.memory_retrieval as mr_module

    src = inspect.getsource(mr_module)
    assert "openai" not in src.lower()
    assert "chat.completions" not in src.lower()


@pytest.mark.asyncio
async def test_mr_23_update_scaffold() -> None:
    agent = MemoryRetrievalAgent()
    result = await agent.update(
        user_id="u1",
        user_message="msg",
        assistant_response="resp",
        thread_state=_thread(),
    )
    assert result is None


@pytest.mark.asyncio
async def test_mr_24_compat_chunks(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(return_value="ctx"))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(return_value=UserProfile()))
    monkeypatch.setattr(
        agent,
        "_load_rag",
        AsyncMock(return_value=[_hit("x", 0.9, "A"), _hit("y", 0.8, "B")]),
    )
    bundle = await agent.assemble(user_message="q", thread_state=_thread(), user_id="u1")
    assert bundle.retrieved_chunks == ["A", "B"]


@pytest.mark.asyncio
async def test_mr_25_context_turns_set(monkeypatch) -> None:
    agent = MemoryRetrievalAgent()
    monkeypatch.setattr(agent, "_load_conversation", AsyncMock(return_value="ctx"))
    monkeypatch.setattr(agent, "_load_profile", AsyncMock(return_value=UserProfile()))
    monkeypatch.setattr(agent, "_load_rag", AsyncMock(return_value=[]))
    bundle = await agent.assemble(
        user_message="q",
        thread_state=_thread(phase="integrate"),
        user_id="u1",
    )
    assert bundle.context_turns == 10


@pytest.mark.asyncio
async def test_mr_26_orchestrator_integration(monkeypatch) -> None:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")

    analyzer = AsyncMock(
        return_value=StateSnapshot(
            nervous_state="window",
            intent="explore",
            openness="open",
            ok_position="I+W+",
            safety_flag=False,
            confidence=0.8,
        )
    )
    manager = AsyncMock(return_value=_thread())
    assemble = AsyncMock(return_value=MemoryBundle(conversation_context="ctx", context_turns=6))
    update = AsyncMock(return_value=None)

    monkeypatch.setattr(orch_module.state_analyzer_agent, "analyze", analyzer)
    monkeypatch.setattr(orch_module.thread_manager_agent, "update", manager)
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "assemble", assemble)
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "update", update)
    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: None)
    monkeypatch.setattr(orch_module.thread_storage, "load_archived", lambda _u: [])
    monkeypatch.setattr(orch_module.thread_storage, "save_active", lambda _t: None)
    def _consume_task(coro):
        coro.close()
        return None

    monkeypatch.setattr(orch_module.asyncio, "create_task", _consume_task)

    orchestrator = MultiAgentOrchestrator()
    _ = await orchestrator.run(query="привет", user_id="u1")
    assert assemble.await_count == 1


@pytest.mark.asyncio
async def test_mr_27_orchestrator_debug(monkeypatch) -> None:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")

    monkeypatch.setattr(
        orch_module.state_analyzer_agent,
        "analyze",
        AsyncMock(
            return_value=StateSnapshot(
                nervous_state="window",
                intent="explore",
                openness="open",
                ok_position="I+W+",
                safety_flag=False,
                confidence=0.8,
            )
        ),
    )
    monkeypatch.setattr(orch_module.thread_manager_agent, "update", AsyncMock(return_value=_thread()))
    monkeypatch.setattr(
        orch_module.memory_retrieval_agent,
        "assemble",
        AsyncMock(
            return_value=MemoryBundle(
                conversation_context="ctx",
                semantic_hits=[_hit("1", 0.9)],
                has_relevant_knowledge=True,
                context_turns=6,
            )
        ),
    )
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "update", AsyncMock(return_value=None))
    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: None)
    monkeypatch.setattr(orch_module.thread_storage, "load_archived", lambda _u: [])
    monkeypatch.setattr(orch_module.thread_storage, "save_active", lambda _t: None)
    def _consume_task(coro):
        coro.close()
        return None

    monkeypatch.setattr(orch_module.asyncio, "create_task", _consume_task)

    orchestrator = MultiAgentOrchestrator()
    result = await orchestrator.run(query="привет", user_id="u1")
    assert result["debug"]["has_relevant_knowledge"] is True
    assert result["debug"]["context_turns"] == 6
    assert result["debug"]["semantic_hits_count"] == 1


def test_mr_28_fixture_f01() -> None:
    fixtures_path = Path(__file__).parent / "fixtures" / "memory_retrieval_fixtures.json"
    payload = json.loads(fixtures_path.read_text(encoding="utf-8"))
    item = next(x for x in payload if x["id"] == "MR-F01")
    thread = _thread(
        phase=item["thread_phase"],
        relation=item["thread_relation"],
        core_direction=item["core_direction"],
        open_loops=item["open_loops"],
    )
    assert MemoryRetrievalAgent._resolve_n_turns(thread) == item["expected_n_turns"]


def test_mr_29_fixture_f02() -> None:
    fixtures_path = Path(__file__).parent / "fixtures" / "memory_retrieval_fixtures.json"
    payload = json.loads(fixtures_path.read_text(encoding="utf-8"))
    item = next(x for x in payload if x["id"] == "MR-F02")
    thread = _thread(
        phase=item["thread_phase"],
        relation=item["thread_relation"],
        core_direction=item["core_direction"],
        open_loops=item["open_loops"],
    )
    assert MemoryRetrievalAgent._resolve_n_turns(thread) == item["expected_n_turns"]


def test_mr_30_fixture_f03() -> None:
    fixtures_path = Path(__file__).parent / "fixtures" / "memory_retrieval_fixtures.json"
    payload = json.loads(fixtures_path.read_text(encoding="utf-8"))
    item = next(x for x in payload if x["id"] == "MR-F03")
    thread = _thread(
        phase=item["thread_phase"],
        relation=item["thread_relation"],
        core_direction=item["core_direction"],
        open_loops=item["open_loops"],
    )
    assert MemoryRetrievalAgent._resolve_n_turns(thread) == item["expected_n_turns"]


@pytest.mark.asyncio
async def test_mr_31_update_calls_add_turn(monkeypatch) -> None:
    conv_module = importlib.import_module("bot_agent.conversation_memory")
    captured: dict[str, str] = {}

    class _Memory:
        def add_turn(self, *, user_input: str, bot_response: str) -> None:
            captured["user_input"] = user_input
            captured["bot_response"] = bot_response

    monkeypatch.setattr(conv_module, "get_conversation_memory", lambda user_id: _Memory())
    agent = MemoryRetrievalAgent()

    await agent.update(
        user_id="u1",
        user_message="вопрос",
        assistant_response="ответ",
        thread_state=_thread(),
    )

    assert captured == {"user_input": "вопрос", "bot_response": "ответ"}


@pytest.mark.asyncio
async def test_mr_32_update_with_metadata_if_supported(monkeypatch) -> None:
    conv_module = importlib.import_module("bot_agent.conversation_memory")
    captured: dict[str, object] = {}

    class _Memory:
        def add_turn(
            self,
            *,
            user_input: str,
            bot_response: str,
            metadata: dict | None = None,
        ) -> None:
            captured["user_input"] = user_input
            captured["bot_response"] = bot_response
            captured["metadata"] = metadata

    monkeypatch.setattr(conv_module, "get_conversation_memory", lambda user_id: _Memory())
    agent = MemoryRetrievalAgent()
    state = _thread(phase="integrate")

    await agent.update(
        user_id="u1",
        user_message="вопрос",
        assistant_response="ответ",
        thread_state=state,
    )

    assert captured["user_input"] == "вопрос"
    assert captured["bot_response"] == "ответ"
    assert isinstance(captured["metadata"], dict)
    assert captured["metadata"]["phase"] == "integrate"
    assert captured["metadata"]["response_mode"] == state.response_mode
    assert captured["metadata"]["thread_id"] == state.thread_id


@pytest.mark.asyncio
async def test_mr_33_update_error_non_blocking(monkeypatch) -> None:
    conv_module = importlib.import_module("bot_agent.conversation_memory")

    class _Memory:
        def add_turn(self, **kwargs) -> None:
            raise RuntimeError("db unavailable")

    monkeypatch.setattr(conv_module, "get_conversation_memory", lambda user_id: _Memory())
    agent = MemoryRetrievalAgent()

    await agent.update(
        user_id="u1",
        user_message="вопрос",
        assistant_response="ответ",
        thread_state=_thread(),
    )
