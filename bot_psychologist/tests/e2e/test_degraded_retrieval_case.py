from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from tests.phase8_runtime_support import build_diagnostics, setup_phase8_runtime


def test_degraded_retrieval_case(monkeypatch) -> None:
    def _diagnostics(**_kwargs):
        return build_diagnostics(
            interaction_mode="coaching",
            nervous_system_state="window",
            request_function="understand",
            core_theme="degraded_mode",
        )

    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=1,
        informational_branch_enabled=True,
        diagnostics_builder=_diagnostics,
        answer_text="Работа в деградированном режиме.",
    )
    monkeypatch.setattr(adaptive, "get_retriever", lambda: (_ for _ in ()).throw(RuntimeError("retriever down")))

    result = adaptive.answer_question_adaptive(
        query="Помоги разобраться, даже если retrieval недоступен.",
        user_id="e2e_degraded_retrieval",
        debug=True,
    )

    assert result["status"] in {"success", "partial"}
    assert result["debug_trace"]["retrieval_degraded_reason"] == "retriever_init_failed"

