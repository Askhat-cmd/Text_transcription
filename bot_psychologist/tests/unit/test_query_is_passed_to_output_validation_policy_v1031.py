from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bot_agent.answer_adaptive as adaptive
from bot_agent.output_validator import OutputValidationResult


def test_query_is_passed_to_output_validation_policy(monkeypatch) -> None:
    observed_queries: list[str] = []
    observed_preserve: list[bool] = []

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
        observed_preserve.append(bool(preserve_structure))
        if len(observed_queries) == 1:
            return OutputValidationResult(
                valid=False,
                text=text,
                errors=["underfilled_inform_answer"],
                warnings=[],
                repair_applied=False,
                needs_regeneration=True,
            )
        return OutputValidationResult(
            valid=True,
            text=text,
            errors=[],
            warnings=[],
            repair_applied=False,
            needs_regeneration=False,
        )

    monkeypatch.setattr(adaptive.output_validator, "validate", _fake_validate)
    monkeypatch.setattr(
        adaptive.output_validator,
        "build_regeneration_hint",
        lambda errors, *, route, mode, query="": f"HINT::{query}",
    )

    def _retry_generate(hint: str) -> dict:
        assert "мой вопрос про сравнение" in hint
        return {"answer": "перегенерированный ответ"}

    answer, meta, _retry = adaptive._apply_output_validation_policy(
        answer="черновой ответ",
        query="мой вопрос про сравнение",
        route="inform",
        mode="CLARIFICATION",
        generate_retry_fn=_retry_generate,
    )

    assert observed_queries == ["мой вопрос про сравнение", "мой вопрос про сравнение"]
    assert observed_preserve == [True, True]
    assert meta["enabled"] is True
    assert meta["final_valid"] is True
    assert answer == "перегенерированный ответ"
