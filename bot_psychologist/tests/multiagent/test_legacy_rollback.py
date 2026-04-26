from __future__ import annotations

import importlib
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _runtime_ctx() -> dict:
    return {
        "top_k": 3,
        "start_time": 0.0,
        "llm_model_name": "gpt-5-mini",
        "prompt_stack_enabled": True,
        "output_validation_enabled": False,
        "informational_branch_enabled": True,
        "diagnostics_v1_enabled": True,
        "deterministic_route_resolver_enabled": True,
        "pipeline_stages": [],
        "debug_info": {},
        "debug_trace": None,
        "conversation_context": "",
        "memory_context_bundle": None,
        "phase8_signals": {},
        "current_stage": "bootstrap",
    }


def _bootstrap_response() -> dict:
    return {
        "memory": None,
        "memory_context_bundle": None,
        "conversation_context": "",
        "cross_session_context": "",
        "memory_trace_metrics": {},
        "phase8_signals": {},
        "path_level_enum": None,
        "start_command_response": {
            "status": "ok",
            "answer": "legacy-path-response",
        },
    }


def test_lr_01_rollback_flag_false(monkeypatch) -> None:
    answer_module = importlib.import_module("bot_agent.answer_adaptive")
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")

    called = {"run_sync": False}

    def _run_sync_guard(*, query: str, user_id: str) -> dict:
        called["run_sync"] = True
        return {"status": "ok", "answer": "should-not-be-used"}

    monkeypatch.setattr(orch_module.orchestrator, "run_sync", _run_sync_guard)
    monkeypatch.setattr(
        answer_module.feature_flags,
        "enabled",
        lambda name: False if name == "MULTIAGENT_ENABLED" else False,
    )
    monkeypatch.setattr(answer_module, "_runtime_prepare_adaptive_run_context", lambda **kwargs: _runtime_ctx())
    monkeypatch.setattr(
        answer_module,
        "_runtime_run_bootstrap_and_onboarding_guard",
        lambda **kwargs: _bootstrap_response(),
    )

    result = answer_module.answer_question_adaptive(query="привет", user_id="u1")

    assert result["answer"] == "legacy-path-response"
    assert called["run_sync"] is False


def test_lr_02_rollback_no_import_error() -> None:
    module = importlib.import_module("bot_agent.answer_adaptive")
    assert hasattr(module, "answer_question_adaptive")


def test_lr_03_readme_exists() -> None:
    readme_path = Path(__file__).resolve().parents[2] / "bot_agent" / "multiagent" / "README.md"
    assert readme_path.exists()


def test_lr_04_readme_agents_table() -> None:
    readme_path = Path(__file__).resolve().parents[2] / "bot_agent" / "multiagent" / "README.md"
    content = readme_path.read_text(encoding="utf-8")
    for expected in (
        "agents/state_analyzer.py",
        "agents/thread_manager.py",
        "agents/memory_retrieval.py",
        "agents/writer_agent.py",
        "agents/validator_agent.py",
    ):
        assert expected in content


def test_lr_05_deprecated_comments() -> None:
    root = Path(__file__).resolve().parents[2] / "bot_agent"
    modules = [
        root / "route_resolver.py",
        root / "prompt_registry_v2.py",
    ]
    for module_path in modules:
        content = module_path.read_text(encoding="utf-8")
        assert "DEPRECATED since PRD-022 (Epoch 4)." in content
