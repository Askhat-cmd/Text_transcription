from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from bot_agent.diagnostics_classifier import DiagnosticsV1
from tests.phase8_runtime_support import RuntimeHarness, setup_phase8_runtime


def run_adaptive_case(
    monkeypatch,
    *,
    query: str,
    user_id: str,
    diagnostics_builder: Callable[..., DiagnosticsV1],
    answer_text: str = "Тестовый e2e-ответ.",
    turns_count: int = 1,
    informational_branch_enabled: bool = True,
    runtime_setup: Callable[[object], None] | None = None,
) -> tuple[dict, RuntimeHarness]:
    harness = setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=turns_count,
        informational_branch_enabled=informational_branch_enabled,
        diagnostics_builder=diagnostics_builder,
        answer_text=answer_text,
    )
    if runtime_setup is not None:
        runtime_setup(adaptive)
    result = adaptive.answer_question_adaptive(
        query=query,
        user_id=user_id,
        debug=True,
    )
    return result, harness
