from __future__ import annotations

import importlib
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_lr_01_rollback_flag_false_uses_multiagent_shim(monkeypatch) -> None:
    answer_module = importlib.import_module("bot_agent.answer_adaptive")

    called = {"adapter": False}

    def _adapter_guard(**_kwargs) -> dict:
        called["adapter"] = True
        return {
            "status": "ok",
            "answer": "multiagent-response",
            "metadata": {"runtime": "multiagent"},
            "debug": {},
        }

    monkeypatch.setattr(answer_module, "run_multiagent_adaptive_sync", _adapter_guard, raising=True)
    monkeypatch.setattr(
        answer_module.feature_flags,
        "enabled",
        lambda name: False if name == "MULTIAGENT_ENABLED" else False,
        raising=True,
    )
    monkeypatch.setattr(
        answer_module,
        "_runtime_prepare_adaptive_run_context",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("legacy cascade must not be called")),
        raising=True,
    )

    result = answer_module.answer_question_adaptive(query="привет", user_id="u1")

    assert result["answer"] == "multiagent-response"
    assert called["adapter"] is True
    assert result["metadata"]["runtime_entrypoint"] == "answer_adaptive_deprecated_shim"
    assert result["metadata"]["legacy_fallback_used"] is False
    assert result["metadata"]["legacy_fallback_blocked"] is True


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
