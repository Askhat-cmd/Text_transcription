from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from TO_DO_LIST.tools import run_prd_047_42_apply_23_enforce_slice3 as runner
from bot_agent.multiagent.agents.writer_agent_enforce_slice3 import (
    EnforceSlice3BoundedPracticeResult,
    _classify_enforce_slice3_bounded_practice,
)


def test_enforce_slice3_dataclass_field_order_matches_runner_expectation() -> None:
    assert [field.name for field in dataclasses.fields(EnforceSlice3BoundedPracticeResult)] == runner.EXPECTED_FIELD_ORDER


def test_not_matched_outcome_when_answer_obligation_differs() -> None:
    result = _classify_enforce_slice3_bounded_practice(
        text="что угодно",
        lowered_user="что угодно",
        lowered_text="что угодно",
        answer_obligation="other_obligation",
    )
    assert result.outcome == "not_matched"


def test_be_strong_outcome_when_repair_needed_and_be_strong_phrase_present() -> None:
    result = _classify_enforce_slice3_bounded_practice(
        text="Как это работает?",
        lowered_user="объясни про будь сильным",
        lowered_text="как это работает?",
        answer_obligation="provide_one_bounded_practice",
    )
    assert result.outcome == "be_strong"


def test_defer_repair_outcome_when_repair_needed_without_be_strong_phrase() -> None:
    result = _classify_enforce_slice3_bounded_practice(
        text="Как это работает?",
        lowered_user="объясни механизм",
        lowered_text="как это работает?",
        answer_obligation="provide_one_bounded_practice",
    )
    assert result.outcome == "defer_repair"


def test_strip_followup_outcome_when_no_repair_needed() -> None:
    text = "Сделай вдох и почувствуй напряж в теле."
    result = _classify_enforce_slice3_bounded_practice(
        text=text,
        lowered_user="ок",
        lowered_text=text.lower(),
        answer_obligation="provide_one_bounded_practice",
    )
    assert result.outcome == "strip_followup"


def test_all_four_outcomes_are_covered_and_exhaustive() -> None:
    assert set(runner.EXPECTED_OUTCOMES) == {"not_matched", "be_strong", "defer_repair", "strip_followup"}


def test_classifier_is_pure_and_idempotent() -> None:
    kwargs = dict(
        text="Сделай вдох и почувствуй напряж в теле.",
        lowered_user="ок",
        lowered_text="сделай вдох и почувствуй напряж в теле.",
        answer_obligation="provide_one_bounded_practice",
    )
    first = _classify_enforce_slice3_bounded_practice(**kwargs)
    second = _classify_enforce_slice3_bounded_practice(**kwargs)
    assert first == second
    assert first.outcome == second.outcome


def test_classifier_helper_module_has_no_self_or_last_debug_access() -> None:
    import inspect

    from bot_agent.multiagent.agents import writer_agent_enforce_slice3 as module

    source = inspect.getsource(module)
    assert "self." not in source
    assert "last_debug" not in source
