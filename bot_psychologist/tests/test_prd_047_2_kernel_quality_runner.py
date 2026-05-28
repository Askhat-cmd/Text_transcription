from __future__ import annotations

from scripts.run_prd_047_2_kernel_quality_cases import _evaluate_case


def _case(expected: dict) -> dict:
    return {
        "id": "case",
        "group": "T",
        "query": "test",
        "expected": expected,
    }


def _compact(within_budget: bool = True) -> dict:
    return {
        "philosophy_kernel_prompt_block_chars": 800,
        "writer_freedom_contract_chars": 400,
        "combined_chars": 1200,
        "selected_lenses_count": 1,
        "within_budget": within_budget,
    }


def test_short_support_with_long_analysis_fails() -> None:
    case = _case({"short_answer": True, "no_analysis_lecture": True})
    answer = "Это теория и концепция, длинная лекция про модель внутренней психики. " * 8
    result = _evaluate_case(
        case=case,
        answer=answer,
        kernel_trace={"selected_lenses": ["resource_first_contact"]},
        compactness=_compact(),
    )
    assert result["passed"] is False
    assert result["checks"]["short_answer_when_requested"] is False


def test_short_support_with_short_contact_passes() -> None:
    case = _case({"short_answer": True, "no_analysis_lecture": True, "must_not_ask_question": True})
    answer = "Я рядом. Сейчас можно выдохнуть и немного отпустить напряжение."
    result = _evaluate_case(
        case=case,
        answer=answer,
        kernel_trace={"selected_lenses": ["resource_first_contact"]},
        compactness=_compact(),
    )
    assert result["checks"]["short_answer_when_requested"] is True
    assert result["checks"]["no_analysis_when_requested"] is True


def test_answer_containing_quote_source_fails() -> None:
    case = _case({"must_not_quote_source": True})
    answer = "Согласно книге, тебе нужно делать так."
    result = _evaluate_case(
        case=case,
        answer=answer,
        kernel_trace={"selected_lenses": ["neurostalking"]},
        compactness=_compact(),
    )
    assert result["checks"]["no_quote_source"] is False


def test_answer_diagnosing_user_fails() -> None:
    case = _case({"must_not_diagnose": True})
    answer = "У тебя диагноз, это патология."
    result = _evaluate_case(
        case=case,
        answer=answer,
        kernel_trace={"selected_lenses": ["imperfect_self_program"]},
        compactness=_compact(),
    )
    assert result["checks"]["no_diagnosis"] is False


def test_driver_hard_label_fails() -> None:
    case = _case({"must_not_hard_label": True})
    answer = "У вас драйвер будь сильным, поэтому так."
    result = _evaluate_case(
        case=case,
        answer=answer,
        kernel_trace={"selected_lenses": ["drivers"]},
        compactness=_compact(),
    )
    assert result["checks"]["no_hard_label"] is False


def test_imperfect_self_without_mechanism_frame_fails() -> None:
    case = _case({"must_frame_as_mechanism_not_defect": True})
    answer = "Ты просто слабый и не справляешься."
    result = _evaluate_case(
        case=case,
        answer=answer,
        kernel_trace={"selected_lenses": ["imperfect_self_program"]},
        compactness=_compact(),
    )
    assert result["checks"]["mechanism_not_defect_frame"] is False


def test_external_surveillance_fails_neuro_case() -> None:
    case = _case({"must_not_external_surveillance": True})
    answer = "Это внешнее слежение и биофидбек через ЭЭГ."
    result = _evaluate_case(
        case=case,
        answer=answer,
        kernel_trace={"selected_lenses": ["neurostalking"]},
        compactness=_compact(),
    )
    assert result["checks"]["no_external_surveillance"] is False


def test_prompt_compactness_over_budget_fails() -> None:
    case = _case({})
    answer = "Короткий ответ."
    result = _evaluate_case(
        case=case,
        answer=answer,
        kernel_trace={"selected_lenses": []},
        compactness=_compact(within_budget=False),
    )
    assert result["checks"]["prompt_compactness_within_budget"] is False
