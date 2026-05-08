from chunkers.structure_parser import parse_markdown_like_sections_v1


def test_parser_preserves_heading_hierarchy() -> None:
    text = """
# Root

## Child

Text body.

### Leaf

Leaf text.
""".strip()

    sections = parse_markdown_like_sections_v1(text)
    assert len(sections) >= 3
    assert sections[1].heading_path == ["Root", "Child"]
    assert sections[2].heading_path == ["Root", "Child", "Leaf"]


def test_parser_detects_practice_role_from_heading() -> None:
    text = """
# Практика 1: Стоп-кадр

Цель: заметить автоматизм.
Время: 3 минуты.
Шаг 1: остановись.
Шаг 2: подыши.
""".strip()

    sections = parse_markdown_like_sections_v1(text)
    assert sections[0].section_role_hint == "practice"


def test_parser_detects_safety_role_from_text() -> None:
    text = """
## Важно

Эта практика не заменяет специалиста.
При кризисе и риске самоповреждения нужна экстренная помощь.
""".strip()

    sections = parse_markdown_like_sections_v1(text)
    assert sections[0].section_role_hint == "safety"


def test_parser_detects_lens_role_from_markers() -> None:
    text = """
## Паттерн избегания

Этот паттерн связан с триггерами стыда и слепой зоной самоценности.
""".strip()

    sections = parse_markdown_like_sections_v1(text)
    assert sections[0].section_role_hint == "lens"


def test_parser_fallback_returns_single_section_without_headings() -> None:
    text = "Просто текст без явной структуры и без markdown-заголовков."
    sections = parse_markdown_like_sections_v1(text)
    assert len(sections) == 1
    assert sections[0].heading_path == ["Document"]
