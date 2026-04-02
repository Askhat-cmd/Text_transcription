from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from tests.phase8_runtime_support import build_diagnostics, setup_phase8_runtime


def test_degraded_mode_without_retrieval(monkeypatch) -> None:
    def _diagnostics(*, query, state_analysis, informational_mode_hint=False):
        return build_diagnostics(interaction_mode="coaching", request_function="understand")

    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=1,
        informational_branch_enabled=True,
        diagnostics_builder=_diagnostics,
        answer_text="Работаю в деградированном режиме без retrieval.",
    )

    monkeypatch.setattr(adaptive, "get_retriever", lambda: (_ for _ in ()).throw(RuntimeError("retriever down")))

    result = adaptive.answer_question_adaptive(
        query="Помоги понять, что со мной сейчас.",
        user_id="phase9_degraded",
        debug=True,
    )

    assert result["status"] in {"success", "partial"}
    assert result["sources"] == []
    trace = result["debug_trace"]
    assert trace.get("retrieval_degraded_reason") == "retriever_init_failed"
    retrieval_stage = next(stage for stage in trace["pipeline_stages"] if stage["name"] == "retrieval")
    assert retrieval_stage["skipped"] is True
