from __future__ import annotations

from bot_agent.experiments.thin_context_collector import collect_thin_context
from bot_agent.experiments.thin_safety_check import run_thin_safety_check
from bot_agent.experiments.thin_spine_cases import ExpectedBehavior, ExperimentCase


def _case(*, kb_allowed: bool) -> ExperimentCase:
    return ExperimentCase(
        case_id="TS-X",
        group="no_kb_request",
        title="test",
        messages=(
            {"role": "user", "content": "Ответь своими словами и не опирайся на внутреннюю БД."},
        ),
        expected_behavior=ExpectedBehavior(
            must_answer_directly=True,
            kb_allowed=kb_allowed,
            practice_allowed="forbidden",
            must_not=("use_internal_db", "forced_practice"),
            preferred_mode="direct_human_answer",
        ),
        explicit_constraints=("Не использовать внутреннюю БД.",),
        knowledge_package=(),
    )


def test_context_collector_excludes_kb_when_forbidden() -> None:
    payload = collect_thin_context(case=_case(kb_allowed=False), recent_turn_count=4, include_kb=True)

    assert payload["knowledge_package_present"] is False
    assert any("internal DB" in item or "internal knowledge" in item for item in payload["explicit_constraints"])


def test_thin_safety_check_detects_leaks_and_forced_practice() -> None:
    result = run_thin_safety_check(
        answer="Knowledge package: source: internal db. Сделай упражнение и подыши.",
        allow_practice=False,
    )

    assert result["passed"] is False
    assert result["internal_leak_count"] > 0
    assert result["raw_kb_dump_count"] > 0
    assert result["practice_forced"] is True
