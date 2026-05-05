from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive


def test_legacy_fallback_disabled_when_flag_off(monkeypatch) -> None:
    called = {"adapter": False}

    def _legacy_flags(name: str) -> bool:
        if name == "MULTIAGENT_ENABLED":
            return False
        return False

    def _fake_adapter(**kwargs):
        called["adapter"] = True
        return {
            "status": "ok",
            "answer": "multiagent-shim-response",
            "metadata": {"runtime": "multiagent"},
            "debug": {},
        }

    monkeypatch.setattr(adaptive.feature_flags, "enabled", _legacy_flags, raising=True)
    monkeypatch.setattr(adaptive, "run_multiagent_adaptive_sync", _fake_adapter, raising=True)
    monkeypatch.setattr(
        adaptive,
        "_runtime_prepare_adaptive_run_context",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("legacy cascade must not be called")),
        raising=True,
    )

    result = adaptive.answer_question_adaptive(
        query="verify no legacy fallback when MULTIAGENT_ENABLED is false",
        user_id="e2e_no_legacy",
        debug=True,
    )

    assert called["adapter"] is True
    assert result["status"] == "ok"
    assert result["metadata"]["runtime"] == "multiagent"
    assert result["metadata"]["runtime_entrypoint"] == "answer_adaptive_deprecated_shim"
    assert result["metadata"]["legacy_fallback_used"] is False
    assert result["metadata"]["legacy_fallback_blocked"] is True
