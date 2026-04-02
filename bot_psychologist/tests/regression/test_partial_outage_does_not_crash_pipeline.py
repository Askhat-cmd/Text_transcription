from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from tests.phase8_runtime_support import setup_phase8_runtime


class _FailingGenerator:
    def __init__(self):
        self.answerer = type(
            "Answerer",
            (),
            {
                "build_system_prompt": staticmethod(lambda: "SYSTEM"),
                "build_context_prompt": staticmethod(lambda *args, **kwargs: "USER"),
            },
        )()

    def generate(self, *args, **kwargs):
        raise RuntimeError("llm subsystem outage")


def test_partial_outage_does_not_crash_pipeline(monkeypatch) -> None:
    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=1,
        informational_branch_enabled=True,
    )

    monkeypatch.setattr(adaptive, "get_retriever", lambda: (_ for _ in ()).throw(RuntimeError("retriever down")))
    monkeypatch.setattr(adaptive, "ResponseGenerator", lambda: _FailingGenerator())

    result = adaptive.answer_question_adaptive(
        query="Мне нужна помощь, но система может быть нестабильна.",
        user_id="phase9_partial_outage",
        debug=True,
    )

    assert isinstance(result, dict)
    assert result["status"] in {"error", "partial"}
    assert "processing_time_seconds" in result
    assert "metadata" in result
    assert "debug_trace" in result
