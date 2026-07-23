from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from TO_DO_LIST.tools import run_prd_047_42_apply_30_mvp_slice2 as runner
from bot_agent.multiagent.agents.writer_agent_mvp_slice2 import (
    MvpPart2Result,
    _classify_mvp_part2,
)

_STALE_STUB_TEXT = "Сейчас полезнее прямое объяснение механизма, а не общие слова."
_FOLLOWUP_TEXT = "Вот финальный ответ на твой вопрос. Хочешь продолжим дальше?"


def _classify(**overrides):
    kwargs = dict(
        text="ok text",
        user_message="ok",
        lowered_user="ok",
        concept="",
        practice_overview_requested=False,
        planner_answer_shape="compact_direct",
        planner_question_policy="required",
        has_question=False,
        expansion_requested=False,
        repair_and_expand_requested=False,
        user_repair_signal=False,
        should_answer_directly=False,
        asks_define_known_term=False,
        has_external_surveillance_frame=False,
        application_request=False,
        active_line_intent="other",
        answer_obligation="none",
        answer_fit={},
    )
    kwargs.update(overrides)
    return _classify_mvp_part2(**kwargs)


def test_mvp_slice2_dataclass_field_order_matches_runner_expectation() -> None:
    assert [field.name for field in dataclasses.fields(MvpPart2Result)] == runner.EXPECTED_FIELD_ORDER


def test_all_nine_tags_are_declared() -> None:
    assert set(runner.EXPECTED_OUTCOMES) == {
        "not_matched",
        "practice_catalog_repair",
        "direct_no_forced_question",
        "repair_and_expand",
        "concept_explanation_repair",
        "preserved_application_answer",
        "concept_expansion_repair",
        "expanded_explanation_repair",
        "stale_stub_retry_deferred_to_gate",
    }
    assert len(runner.EXPECTED_OUTCOMES) == 9


def test_practice_catalog_repair_outcome() -> None:
    result = _classify(practice_overview_requested=True, text="short")
    assert result.outcome == "practice_catalog_repair"


def test_direct_no_forced_question_outcome_computes_return_text() -> None:
    result = _classify(planner_question_policy="none", has_question=True, text="Q1? Q2?")
    assert result.outcome == "direct_no_forced_question"
    assert result.return_text == "Q1. Q2."


def test_repair_and_expand_outcome() -> None:
    result = _classify(repair_and_expand_requested=True)
    assert result.outcome == "repair_and_expand"


def test_concept_explanation_repair_outcome() -> None:
    result = _classify(should_answer_directly=True, asks_define_known_term=True)
    assert result.outcome == "concept_explanation_repair"


def test_preserved_application_answer_outcome() -> None:
    result = _classify(
        expansion_requested=True,
        text="x" * 150,
        answer_obligation="answer_direct_question",
    )
    assert result.outcome == "preserved_application_answer"


def test_concept_expansion_repair_outcome() -> None:
    result = _classify(expansion_requested=True, text="short", concept="нейросталкинг")
    assert result.outcome == "concept_expansion_repair"


def test_expanded_explanation_repair_outcome() -> None:
    result = _classify(expansion_requested=True, text="short", concept="other")
    assert result.outcome == "expanded_explanation_repair"


def test_stale_stub_retry_deferred_to_gate_outcome() -> None:
    result = _classify(text=_STALE_STUB_TEXT)
    assert result.outcome == "stale_stub_retry_deferred_to_gate"
    assert result.return_text == _STALE_STUB_TEXT


def test_answer_fit_repair_applied_is_computed_true_not_hardcoded() -> None:
    """Особенность 1: answer_fit_repair_applied must carry the computed
    bool(answer_fit.get("concrete_need", False)) value, never a literal
    True regardless of input.
    """
    result = _classify(text=_STALE_STUB_TEXT, answer_fit={"concrete_need": True})
    assert result.outcome == "stale_stub_retry_deferred_to_gate"
    assert result.last_debug_patch["answer_fit_repair_applied"] is True
    assert result.last_debug_patch["template_leakage_repair_deferred_to_gate"] is True


def test_answer_fit_repair_applied_is_computed_false_not_hardcoded() -> None:
    result = _classify(text=_STALE_STUB_TEXT, answer_fit={"concrete_need": False})
    assert result.outcome == "stale_stub_retry_deferred_to_gate"
    assert result.last_debug_patch["answer_fit_repair_applied"] is False
    assert result.last_debug_patch["template_leakage_repair_deferred_to_gate"] is True


def test_answer_fit_repair_applied_defaults_to_false_when_key_missing() -> None:
    result = _classify(text=_STALE_STUB_TEXT, answer_fit={})
    assert result.last_debug_patch["answer_fit_repair_applied"] is False


def test_not_matched_terminal_default_when_answer_obligation_in_preserve_set() -> None:
    result = _classify(answer_obligation="answer_direct_question", text=_FOLLOWUP_TEXT)
    assert result.outcome == "not_matched"
    assert result.return_text != _FOLLOWUP_TEXT
    assert "Хочешь" not in result.return_text


def test_not_matched_terminal_default_when_answer_obligation_not_in_preserve_set() -> None:
    result = _classify(answer_obligation="some_other_obligation", text=_FOLLOWUP_TEXT)
    assert result.outcome == "not_matched"
    assert result.return_text == _FOLLOWUP_TEXT


def test_classifier_is_pure_and_idempotent() -> None:
    kwargs = dict(practice_overview_requested=True, text="short")
    first = _classify(**kwargs)
    second = _classify(**kwargs)
    assert first == second


def test_classifier_helper_module_has_no_self_access() -> None:
    import inspect

    from bot_agent.multiagent.agents import writer_agent_mvp_slice2 as module

    source = inspect.getsource(module)
    assert "self." not in source
