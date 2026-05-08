from chunkers.book_chunker import BookChunker
from governance.governance_adapter import apply_governance_to_blocks_v1


def _chunk_types(blocks):
    return [b.governance.get("chunk_type") for b in blocks]


def test_structure_aware_manual_produces_lens_practice_safety() -> None:
    text = """
# Synthetic Practice Manual

## Паттерн избегания

Когда человек откладывает действие, иногда работает паттерн защиты от стыда.

## Практика 1: Стоп-кадр избегания

Цель: заметить момент откладывания.
Время: 3 минуты.

Шаг 1: остановись и назови действие, которое откладываешь.
Шаг 2: отметь чувство в теле.
Шаг 3: выбери один микрошаг на 2 минуты.

## Безопасность

Эта практика не заменяет специалиста. При кризисе или риске самоповреждения
нужно обратиться за живой помощью.
""".strip()

    chunker = BookChunker(config={"target_tokens": 220, "min_tokens": 60, "max_tokens": 320, "overlap_tokens": 0})
    blocks = chunker.chunk_file_from_text(text, "Автор", "Synthetic Manual", "ru")
    blocks = apply_governance_to_blocks_v1(
        blocks=blocks,
        source_id="src",
        source_title="Synthetic Practice Manual",
        source_type="book",
        source_kind="practice_manual",
        governance_profile="practice_manual",
    )

    types = _chunk_types(blocks)
    assert "lens" in types
    assert "practice" in types
    assert "safety" in types


def test_practice_section_preserved_within_budget() -> None:
    text = """
## Практика 1: Стоп-кадр

Цель: заметить избегание.
Время: 3 минуты.
Шаг 1: остановись.
Шаг 2: подыши.
Шаг 3: выбери микрошаг.
""".strip()

    chunker = BookChunker(config={"target_tokens": 400, "min_tokens": 50, "max_tokens": 600, "overlap_tokens": 0})
    blocks = chunker.chunk_file_from_text(text, "Автор", "Книга", "ru")
    practice_blocks = [b for b in blocks if b.section_role_hint == "practice"]

    assert len(practice_blocks) == 1
    assert practice_blocks[0].split_reason == "practice_preserved"
    assert "Шаг 1" in practice_blocks[0].text
    assert "Шаг 3" in practice_blocks[0].text


def test_long_practice_splits_by_step_boundaries() -> None:
    long_step = " ".join(["подробное описание" for _ in range(120)])
    text = f"""
## Практика 2: Длинная

Цель: тренировка внимания.
Время: 15 минут.

Шаг 1: {long_step}

Шаг 2: {long_step}

Шаг 3: {long_step}
""".strip()

    chunker = BookChunker(config={"target_tokens": 90, "min_tokens": 30, "max_tokens": 120, "overlap_tokens": 0})
    blocks = chunker.chunk_file_from_text(text, "Автор", "Книга", "ru")
    practice_blocks = [b for b in blocks if b.section_role_hint == "practice"]

    assert len(practice_blocks) >= 2
    assert all(b.split_reason == "practice_step_split" for b in practice_blocks)
    assert any("Шаг 2" in b.text for b in practice_blocks)


def test_architecture_notes_not_marked_as_practice_suggestion_without_explicit_practice() -> None:
    text = """
# Neo MindBot Architecture

## Writer Rules

Бот работает как зеркало и навигатор. Не становиться духовным авторитетом.
""".strip()

    chunker = BookChunker(config={})
    blocks = chunker.chunk_file_from_text(text, "Автор", "Neo MindBot Architecture", "ru")
    blocks = apply_governance_to_blocks_v1(
        blocks=blocks,
        source_id="src_arch",
        source_title="Neo MindBot Architecture",
        source_type="book",
        source_kind="architecture_notes",
        governance_profile="architecture_notes",
    )

    assert blocks
    for block in blocks:
        assert "practice_suggestion" not in block.governance.get("allowed_use", [])
        assert block.governance.get("chunk_type") in {"style", "principle", "lens", "theory"}


def test_plain_book_text_fallback_still_chunks() -> None:
    plain_text = "Это обычный текст без markdown структуры. " * 220
    chunker = BookChunker(config={"target_tokens": 120, "min_tokens": 60, "max_tokens": 180, "overlap_tokens": 20})
    blocks = chunker.chunk_file_from_text(plain_text, "Автор", "Книга", "ru")

    assert len(blocks) > 0
    assert all(block.text.strip() for block in blocks)
