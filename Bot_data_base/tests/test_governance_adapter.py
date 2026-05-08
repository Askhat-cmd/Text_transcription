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
            section_role_hint="practice",
            heading_path=["Manual", "Практика дыхания"],
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


def test_section_role_hint_safety_forces_chunk_type_safety() -> None:
    block = UniversalBlock(
        text="Нейтральный текст без явных маркеров.",
        title="Раздел",
        section_role_hint="safety",
        heading_path=["Doc", "Безопасность"],
    )

    governed = apply_governance_to_blocks_v1(
        blocks=[block],
        source_id="src_safe",
        source_title="Manual",
        source_type="book",
        source_kind="practice_manual",
        governance_profile="practice_manual",
    )

    assert governed[0].governance["chunk_type"] == "safety"


def test_architecture_profile_marks_internal_only() -> None:
    blocks = [
        UniversalBlock(
            text="Внутренняя архитектурная заметка, не использовать как прямую цитату.",
            title="Neo MindBot Notes",
            source_type="book",
            source_id="src2",
            author="Author",
            sd_level="GREEN",
            section_role_hint="architecture",
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
    assert "practice_suggestion" not in gov["allowed_use"]


def test_practice_metadata_extracts_duration_steps_and_channel() -> None:
    block = UniversalBlock(
        text=(
            "Цель: снизить тревогу.\n"
            "Время: 5 минут.\n"
            "Шаг 1: сделай 5 медленных вдохов.\n"
            "Шаг 2: отметь ощущения в теле.\n"
            "Шаг 3: выбери один микрошаг."
        ),
        title="Практика",
        section_role_hint="practice",
    )

    governed = apply_governance_to_blocks_v1(
        blocks=[block],
        source_id="src_pm",
        source_title="Manual",
        source_type="book",
        source_kind="practice_manual",
        governance_profile="practice_manual",
    )

    metadata = governed[0].governance.get("practice_metadata", {})
    assert metadata.get("steps_count", 0) >= 3
    assert "5" in str(metadata.get("duration", ""))
    assert metadata.get("channel") in {"body", "action", "mixed"}
