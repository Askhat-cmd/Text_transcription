from __future__ import annotations

from pathlib import Path

from bot_agent.experiments.thin_spine_cases import load_cases_jsonl


def test_prd_047_28_fixture_meets_required_groups_and_multi_turn_count() -> None:
    fixture = Path("TO_DO_LIST/fixtures/PRD-047.28/thin_spine_cases_ru.jsonl")
    cases = load_cases_jsonl(fixture)

    assert len(cases) >= 10
    assert sum(1 for case in cases if case.is_multi_turn) >= 5
    assert {case.group for case in cases} >= {
        "greeting_personal_question",
        "resistance",
        "anger_at_boss",
        "simplify_after_complexity",
        "practice_pushback",
        "long_term_perspective",
        "no_kb_request",
        "alternatives_to_breathing",
        "direct_kb_question",
        "safety_boundary",
    }


def test_prd_047_28_case_loader_requires_last_user_turn() -> None:
    fixture = Path("TO_DO_LIST/fixtures/PRD-047.28/thin_spine_cases_ru.jsonl")
    cases = load_cases_jsonl(fixture)

    assert all(case.current_user_message for case in cases)
    assert any(not case.expected_behavior.kb_allowed for case in cases)
    assert any(case.expected_behavior.kb_allowed for case in cases)
