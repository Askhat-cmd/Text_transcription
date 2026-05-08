from models.universal_block import UniversalBlock
from governance.governance_adapter import apply_governance_to_blocks_v1


def _govern(text: str, title: str, role_hint: str):
    blocks = [
        UniversalBlock(
            text=text,
            title=title,
            section_role_hint=role_hint,
            heading_path=["Synthetic", title],
            source_type="book",
            source_id="src",
        )
    ]
    return apply_governance_to_blocks_v1(
        blocks=blocks,
        source_id="src",
        source_title="Synthetic Practice Manual",
        source_type="book",
        source_kind="practice_manual",
        governance_profile="practice_manual",
    )[0]


def test_practice_manual_lens_block_has_no_practice_suggestion() -> None:
    block = _govern(
        text="Паттерн избегания и триггер стыда в сценарии откладывания.",
        title="Паттерн избегания",
        role_hint="lens",
    )
    assert block.governance.get("chunk_type") == "lens"
    assert "diagnostic_lens" in block.governance.get("allowed_use", [])
    assert "practice_suggestion" not in block.governance.get("allowed_use", [])


def test_practice_manual_safety_block_has_safety_protocol_without_practice_suggestion() -> None:
    block = _govern(
        text="Эта практика не заменяет специалиста. При кризисе нужна экстренная помощь.",
        title="Безопасность",
        role_hint="safety",
    )
    allowed = block.governance.get("allowed_use", [])
    assert block.governance.get("chunk_type") == "safety"
    assert "safety_protocol" in allowed
    assert "practice_suggestion" not in allowed


def test_practice_manual_practice_block_gets_practice_suggestion() -> None:
    block = _govern(
        text="Цель: стабилизировать внимание. Время: 3 минуты. Шаг 1: вдох. Шаг 2: выдох.",
        title="Практика 1",
        role_hint="practice",
    )
    allowed = block.governance.get("allowed_use", [])
    assert block.governance.get("chunk_type") == "practice"
    assert "practice_suggestion" in allowed


def test_architecture_non_practice_block_has_internal_only_style_guidance() -> None:
    blocks = [
        UniversalBlock(
            text="Внутренние правила Writer и Diagnostic Center, не для прямой цитаты пользователю.",
            title="Writer Rules",
            section_role_hint="architecture",
            heading_path=["Neo MindBot", "Writer Rules"],
            source_type="book",
            source_id="arch_src",
        )
    ]
    block = apply_governance_to_blocks_v1(
        blocks=blocks,
        source_id="arch_src",
        source_title="Neo MindBot Architecture",
        source_type="book",
        source_kind="architecture_notes",
        governance_profile="architecture_notes",
    )[0]

    allowed = block.governance.get("allowed_use", [])
    flags = block.governance.get("safety_flags", [])
    assert "internal_only" in allowed
    assert "style_guidance" in allowed
    assert "practice_suggestion" not in allowed
    assert "source_style_not_user_facing" in flags
    assert "not_for_direct_quote" in flags
