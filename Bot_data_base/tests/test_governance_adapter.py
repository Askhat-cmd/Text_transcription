from models.universal_block import UniversalBlock
from governance.governance_adapter import apply_governance_to_blocks_v1


def test_apply_governance_adds_required_schema_fields() -> None:
    blocks = [
        UniversalBlock(
            text="Цель: снизить напряжение. Время: 3 минуты. Шаг 1: медленный выдох.",
            title="Практика дыхания",
            source_type="book",
            source_id="src1",
            author="Author",
            sd_level="GREEN",
        )
    ]

    governed = apply_governance_to_blocks_v1(
        blocks=blocks,
        source_id="src1",
        source_title="Тестовый источник",
        source_type="book",
        source_kind="practice_manual",
        governance_profile="practice_manual",
    )

    assert governed
    gov = governed[0].governance
    assert gov["schema_version"] == "governance_v1"
    assert gov["chunk_type"] == "practice"
    assert "practice_suggestion" in gov["allowed_use"]
    assert "source_trace" in gov


def test_architecture_profile_marks_internal_only() -> None:
    blocks = [
        UniversalBlock(
            text="Внутренняя архитектурная заметка, не использовать как прямую цитату.",
            title="Neo MindBot Notes",
            source_type="book",
            source_id="src2",
            author="Author",
            sd_level="GREEN",
        )
    ]

    governed = apply_governance_to_blocks_v1(
        blocks=blocks,
        source_id="src2",
        source_title="Neo MindBot Architecture",
        source_type="book",
        source_kind="architecture_notes",
        governance_profile="architecture_notes",
    )

    gov = governed[0].governance
    assert "internal_only" in gov["allowed_use"]
    assert "source_style_not_user_facing" in gov["safety_flags"]
