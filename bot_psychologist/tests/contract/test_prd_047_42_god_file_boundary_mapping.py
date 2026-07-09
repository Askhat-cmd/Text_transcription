from __future__ import annotations

from datetime import datetime, timezone
import importlib
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.main import app
from api.session_store import get_session_store
from bot_agent.config import config
from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.contracts.memory_bundle import (
    MemoryBundle,
    SemanticHit,
    UserProfile,
)
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.runtime_config import RuntimeConfig


ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}


@pytest.fixture()
def admin_client(tmp_path, monkeypatch):
    override_path = tmp_path / "admin_overrides.json"
    monkeypatch.setattr(RuntimeConfig, "OVERRIDES_PATH", override_path, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache_mtime", 0.0, raising=False)
    monkeypatch.setattr(RuntimeConfig, "_cache", {}, raising=False)
    monkeypatch.setattr(config, "OVERRIDES_PATH", override_path, raising=False)
    monkeypatch.setattr(config, "WARMUP_ON_START", False, raising=False)

    store = get_session_store()
    monkeypatch.setattr(store, "_sessions", {}, raising=False)
    monkeypatch.setattr(store, "_blobs", {}, raising=False)

    with TestClient(app, base_url="http://localhost") as client:
        yield client


def _thread_state() -> ThreadState:
    return ThreadState(
        thread_id="th_047_42",
        user_id="u_047_42",
        core_direction="контроль и перегруз",
        phase="clarify",
        response_mode="reflect",
        response_goal="direct_answer",
        nervous_state="window",
        openness="open",
        ok_position="I+W+",
        pattern_core="control_then_freeze",
        active_frame={"current_need": "простое объяснение"},
        must_avoid=["диагноз"],
        open_loops=["что со мной происходит"],
        safety_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _contract(*, user_message: str = "объясни по-человечески, без практик") -> WriterContract:
    bundle = MemoryBundle(
        conversation_context="USER: Мне тяжело. ASSISTANT: Я рядом.",
        user_profile=UserProfile(patterns=["control"], values=["clarity"]),
        semantic_hits=[
            SemanticHit(chunk_id="c1", content="Нейросталкинг — наблюдение автоматических реакций.", source="kb", score=0.92),
            SemanticHit(chunk_id="c2", content="Контроль может сжимать внимание до действия.", source="kb", score=0.87),
        ],
        has_relevant_knowledge=True,
        context_turns=2,
        recent_turns=[
            {"role": "user", "content": "что такое нейросталкинг?"},
            {"role": "assistant", "content": "это наблюдение реакции"},
        ],
    )
    return WriterContract(
        user_message=user_message,
        thread_state=_thread_state(),
        memory_bundle=bundle,
        knowledge_answer_guard={
            "knowledge_answer": {"should_answer_directly": True, "concept": "нейросталкинг"},
            "practice_gate": {"practice_allowed": False, "is_greeting": False},
        },
        philosophy_kernel={
            "kernel_version": "philosophy_kernel_v1",
            "selection": {"selected_lenses": ["mechanism", "protection"]},
            "prompt_compactness": {"max_kernel_chars": 1800},
        },
        writer_freedom_contract={
            "version": "writer_freedom_contract_v1",
            "freedom_level": "guided",
            "mode_hint": "reflect",
            "question_limit": 1,
            "practice_requires_gate": True,
            "hard_boundaries": ["safety", "no_unsolicited_practice"],
        },
        active_line={
            "version": "active_line_v1",
            "user_intent": "known_concept_question",
            "should_offer_practice": False,
            "practice_suppression_active": True,
        },
        response_planner={
            "version": "response_planner_v1",
            "enabled": True,
            "next_move": "answer_known_concept",
            "answer_shape": "compact_direct",
            "question_policy": "none",
            "practice_policy": "forbidden",
        },
        dialogue_policy={
            "profile": "safe_guided",
            "profile_preset": "safe_guided",
            "context_budget_chars": 2800,
            "explicit_answer_need": True,
            "answer_obligation_resolution": {
                "answer_obligation": "answer_knowledge_question",
                "answer_shape": "structured_explanation",
                "depth": "medium",
                "question_policy": "none",
                "source": ["latest_turn"],
            },
        },
        dialogue_pragmatics={"version": "dialogue_pragmatics_v1", "should_answer_directly": True},
        retrieval_decision={
            "retrieval_decision_version": "contextual_retrieval_gating_v1",
            "retrieval_action": "include_rag",
            "rag_candidates_count": 2,
            "rag_included_count": 2,
            "rag_included_reason": "direct_concept_followup",
            "writer_can_ignore_rag": True,
            "composer": {
                "version": "contextual_retrieval_query_composer_v1",
                "query_source": "current_turn",
                "composed_query": "что такое нейросталкинг",
                "retrieval_need": "direct_knowledge",
                "retrieval_action": "include_rag",
                "writer_can_ignore_rag": True,
            },
        },
        final_answer_directive={
            "version": "final_answer_directive_v1",
            "current_user_request": user_message,
            "must_answer_source": "latest_turn",
            "answer_target": "latest_turn",
            "writer_contact_mode": "structured_answer",
            "no_practice_unless_requested": True,
            "latest_turn_constraints_v1": {"active_constraints": ["no_practice"]},
        },
    )


def test_writer_contract_to_prompt_context_snapshot_surface() -> None:
    ctx = _contract().to_prompt_context()

    assert ctx["fresh_chat_context_policy_version"] == "fresh_chat_context_policy_v1"
    assert ctx["response_planner_next_move"] == "answer_known_concept"
    assert ctx["answer_obligation"] == "answer_knowledge_question"
    assert ctx["retrieval_action"] == "include_rag"
    assert ctx["final_answer_writer_contact_mode"] == "structured_answer"
    assert isinstance(ctx["semantic_hits"], list)
    assert ctx["writer_context_rag_candidates_count"] >= 0
    assert "latest user request are mandatory" in ctx["writer_grounding_authority_note"]


def test_writer_agent_resolve_runtime_settings_snapshot_safe_guided(monkeypatch) -> None:
    writer_agent_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")

    def fake_value(key: str, default: str | None = None) -> str | None:
        mapping = {
            "MULTIAGENT_MAX_TOKENS": "700",
            "WRITER_MAX_TOKENS": "700",
            "MULTIAGENT_LLM_TIMEOUT": "11.5",
        }
        return mapping.get(key, default)

    monkeypatch.setattr(writer_agent_module.feature_flags, "value", fake_value)
    monkeypatch.setattr(writer_agent_module, "get_temperature_for_agent", lambda _agent: 0.42)

    settings = WriterAgent(model="gpt-4o-mini")._resolve_runtime_settings("safe_guided")

    assert settings == {
        "model": "gpt-4o-mini",
        "timeout": 11.5,
        "max_tokens": 700,
        "temperature": 0.42,
    }


def test_writer_agent_resolve_runtime_settings_snapshot_mvp_floor(monkeypatch) -> None:
    writer_agent_module = importlib.import_module("bot_agent.multiagent.agents.writer_agent")

    def fake_value(key: str, default: str | None = None) -> str | None:
        mapping = {
            "MULTIAGENT_MAX_TOKENS": "500",
            "WRITER_MAX_TOKENS": "500",
            "MULTIAGENT_LLM_TIMEOUT": "9.0",
        }
        return mapping.get(key, default)

    monkeypatch.setattr(writer_agent_module.feature_flags, "value", fake_value)
    monkeypatch.setattr(writer_agent_module, "get_temperature_for_agent", lambda _agent: 0.33)

    settings = WriterAgent(model="gpt-4o-mini")._resolve_runtime_settings("mvp_free_dialogue")

    assert settings["model"] == "gpt-4o-mini"
    assert settings["timeout"] == 9.0
    assert settings["temperature"] == 0.33
    assert settings["max_tokens"] == 2500


def test_writer_agent_compliance_literal_markdown_echo_snapshot() -> None:
    agent = WriterAgent(model="gpt-5-mini")
    requested = "**Заголовок**\n\n- пункт один\n- пункт два"
    contract = _contract(
        user_message=f"Верни без объяснений и без изменений следующий markdown-блок: {requested}"
    )

    result = agent._enforce_answer_compliance("Я слышу тебя.", contract)

    assert result == requested
    assert agent.last_debug["final_answer_shape"] == "literal_markdown_echo"
    assert agent.last_debug["format_request_repair_applied"] is True


def test_writer_agent_compliance_no_practice_contact_snapshot() -> None:
    agent = WriterAgent(model="gpt-5-mini")
    contract = _contract(user_message="Мне тяжело, без практик, просто скажи по-человечески.")
    contract.dialogue_policy = {
        "profile": "mvp_free_dialogue",
        "answer_obligation_resolution": {"answer_obligation": "answer_latest_turn"},
    }
    contract.response_planner = {
        "enabled": True,
        "next_move": "give_direct_step",
        "answer_shape": "one_step",
        "question_policy": "none",
        "practice_policy": "forbidden",
    }

    result = agent._enforce_answer_compliance(
        "Понял. Тебе тяжело. Если захочешь дальше, можем придумать один шаг.",
        contract,
    )

    assert "Если захочешь дальше" not in result
    assert "один шаг" not in result.lower()
    assert agent.last_debug["final_answer_shape"] == "sanitized_direct_no_forced_practice"


def test_admin_runtime_effective_snapshot_surface(admin_client) -> None:
    response = admin_client.get("/api/admin/runtime/effective", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["schema_version"] == "10.5.1"
    assert payload["active_runtime"] == "multiagent"
    assert payload["pipeline_mode"] == "multiagent_only"
    assert payload["effective_config"]["schema_version"] == "effective_config_registry_v1"
    assert payload["effective_config"]["flag_count"] == 103
    assert payload["dialogue_policy"]["version"] == "unified_dialogue_policy_v2"


def test_admin_orchestrator_config_snapshot_surface(admin_client) -> None:
    response = admin_client.get("/api/admin/orchestrator/config", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["pipeline_mode"] == "multiagent_only"
    assert payload["runtime_entrypoint"] == "multiagent_adapter"
    assert payload["legacy"]["cascade_status"] == "physically_removed"
    assert payload["compatibility"]["legacy_modes_selectable"] is False


def test_admin_prompt_stack_usage_deprecated_snapshot_surface(admin_client) -> None:
    response = admin_client.get("/api/admin/prompts/stack-v2/usage", headers=ADMIN_HEADERS)
    assert response.status_code == 410
    payload = response.json()

    assert "deprecated" in payload["detail"].lower()
    assert "no longer provided" in payload["detail"].lower()
