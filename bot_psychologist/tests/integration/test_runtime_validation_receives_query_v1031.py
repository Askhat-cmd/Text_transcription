from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from bot_agent.output_validator import OutputValidationResult
from tests.phase8_runtime_support import build_diagnostics, setup_phase8_runtime


def test_runtime_validation_receives_original_query(monkeypatch) -> None:
    observed_queries: list[str] = []

    def _diagnostics(*, query, state_analysis, informational_mode_hint=False):
        mode = "informational" if informational_mode_hint else "coaching"
        return build_diagnostics(interaction_mode=mode, request_function="understand")

    setup_phase8_runtime(
        monkeypatch,
        adaptive,
        turns_count=2,
        informational_branch_enabled=True,
        diagnostics_builder=_diagnostics,
    )
    monkeypatch.setattr(adaptive, "_output_validation_enabled", lambda: True)

    def _fake_validate(
        text: str,
        *,
        route: str,
        mode: str,
        safety_override: bool = False,
        query: str = "",
        preserve_structure: bool = False,
    ) -> OutputValidationResult:
        observed_queries.append(query)
        return OutputValidationResult(
            valid=True,
            text=text,
            errors=[],
            warnings=[],
            repair_applied=False,
            needs_regeneration=False,
        )

    monkeypatch.setattr(adaptive.output_validator, "validate", _fake_validate)

    query = "Объясни, что такое избегание, потому что кажется это про меня"
    result = adaptive.answer_question_adaptive(
        query=query,
        user_id="phase1031_validation_query",
        debug=True,
    )

    assert result["status"] == "success"
    assert observed_queries
    assert all(item == query for item in observed_queries)
