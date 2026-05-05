from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive


def test_multiagent_exception_does_not_trigger_legacy_cascade(monkeypatch) -> None:
    def _raise_adapter(**_kwargs):
        raise RuntimeError("forced adapter failure")

    def _legacy_guard(**_kwargs):
        raise AssertionError("legacy cascade must not be called")

    monkeypatch.setattr(adaptive, "run_multiagent_adaptive_sync", _raise_adapter, raising=True)
    monkeypatch.setattr(adaptive, "_runtime_prepare_adaptive_run_context", _legacy_guard, raising=True)

    result = adaptive.answer_question_adaptive(
        query="force adapter error",
        user_id="e2e_adapter_error",
        debug=True,
    )

    assert result["status"] == "error"
    assert result["metadata"]["runtime"] == "multiagent"
    assert result["metadata"]["legacy_fallback_used"] is False
    assert result["metadata"]["legacy_fallback_blocked"] is True
    assert "forced adapter failure" in result["metadata"]["pipeline_error"]
