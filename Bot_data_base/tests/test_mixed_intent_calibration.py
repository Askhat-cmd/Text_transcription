from governance.chunking_quality import build_chunking_quality_v1
from models.universal_block import UniversalBlock


def _quality(text: str, role_hint: str, chunk_type: str):
    block = UniversalBlock(
        text=text,
        title="Synthetic",
        heading_path=["Doc", "Synthetic"],
        section_role_hint=role_hint,
        boundary_confidence=0.8,
        split_reason="practice_preserved" if chunk_type == "practice" else "theory_budget_split",
        governance={"chunk_type": chunk_type},
    )
    return build_chunking_quality_v1(block)


def test_practice_with_light_lens_reference_is_low_not_high_risk() -> None:
    q = _quality(
        text="Практика: шаг 1 сделай вдох. шаг 2 сделай выдох. Это помогает при избегании.",
        role_hint="practice",
        chunk_type="practice",
    )
    assert q["mixed_intent_severity"] in {"none", "low"}
    assert q["mixed_intent_risk"] is False


def test_safety_context_phrase_not_treated_as_high_mixed() -> None:
    q = _quality(
        text="Эта практика не заменяет специалиста. При кризисе и риске самоповреждения нужна экстренная помощь.",
        role_hint="safety",
        chunk_type="safety",
    )
    assert q["mixed_intent_severity"] in {"none", "low"}
    assert q["mixed_intent_risk"] is False


def test_true_mixed_chunk_keeps_warning() -> None:
    q = _quality(
        text=(
            "Практика: Шаг 1 сделай вдох. Шаг 2 запиши реакцию. "
            "Безопасность: при кризисе нужна экстренная помощь. "
            "Паттерн избегания и триггер стыда повторяются."
        ),
        role_hint="safety",
        chunk_type="safety",
    )
    assert q["mixed_intent_risk"] is True
    assert q["mixed_intent_severity"] in {"medium", "high"}
    assert "mixed_intent_risk" in q["quality_notes"]
