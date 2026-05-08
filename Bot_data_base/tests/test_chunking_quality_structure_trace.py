from governance.chunking_quality import build_chunking_quality_v1
from models.universal_block import UniversalBlock


def test_chunking_quality_marks_heading_path_presence() -> None:
    block = UniversalBlock(
        text="Шаг 1: сделай вдох. Шаг 2: сделай выдох.",
        title="Практика",
        heading_path=["Manual", "Практика"],
        section_role_hint="practice",
        boundary_confidence=0.88,
        split_reason="practice_preserved",
        governance={"chunk_type": "practice"},
    )

    quality = build_chunking_quality_v1(block)
    assert quality["heading_path_present"] is True
    assert quality["section_role_hint"] == "practice"


def test_chunking_quality_detects_mixed_intent_risk() -> None:
    block = UniversalBlock(
        text=(
            "Практика: шаг 1 дыхание. Безопасность: при кризисе обращайся за экстренной помощью. "
            "Этот паттерн избегания повторяется."
        ),
        title="Смешанный блок",
        heading_path=["Manual", "Mixed"],
        section_role_hint="practice",
        boundary_confidence=0.7,
        split_reason="practice_step_split",
        governance={"chunk_type": "practice"},
    )

    quality = build_chunking_quality_v1(block)
    assert quality["mixed_intent_risk"] is True
    assert "mixed_intent_risk" in quality["quality_notes"]


def test_chunking_quality_preserves_split_reason() -> None:
    block = UniversalBlock(
        text="Короткий фрагмент",
        title="Фрагмент",
        split_reason="safety_boundary",
        governance={"chunk_type": "safety"},
    )

    quality = build_chunking_quality_v1(block)
    assert quality["split_reason"] == "safety_boundary"


def test_chunking_quality_marks_practice_steps_preserved() -> None:
    block = UniversalBlock(
        text="Шаг 1: ... Шаг 2: ...",
        title="Практика",
        heading_path=["Manual", "Practice"],
        section_role_hint="practice",
        split_reason="practice_preserved",
        governance={"chunk_type": "practice"},
    )

    quality = build_chunking_quality_v1(block)
    assert quality["practice_steps_preserved"] is True
