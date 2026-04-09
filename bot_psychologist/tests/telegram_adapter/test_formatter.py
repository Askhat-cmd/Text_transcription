from __future__ import annotations

from telegram_adapter.formatters.telegram_formatter import (
    format_for_telegram,
    split_long_message,
)


def test_t5_1_bold() -> None:
    assert format_for_telegram("**текст**") == "<b>текст</b>"


def test_t5_2_italic() -> None:
    assert format_for_telegram("*текст*") == "<i>текст</i>"


def test_t5_3_inline_code() -> None:
    assert format_for_telegram("`код`") == "<code>код</code>"


def test_t5_4_headers_to_bold() -> None:
    assert format_for_telegram("## Заголовок") == "<b>Заголовок</b>"
    assert format_for_telegram("# H1") == "<b>H1</b>"
    assert format_for_telegram("### H3") == "<b>H3</b>"


def test_t5_5_dividers_removed() -> None:
    result = format_for_telegram("текст\n---\nтекст2")
    assert "---" not in result


def test_t5_6_no_triple_newlines() -> None:
    result = format_for_telegram("a\n\n\n\n\nb")
    assert "\n\n\n" not in result


def test_t5_7_html_escape_before_conversion() -> None:
    result = format_for_telegram("x > y & z < w")
    assert "&gt;" in result
    assert "&amp;" in result
    assert "&lt;" in result
    assert format_for_telegram("**жирный**") == "<b>жирный</b>"


def test_t5_8_complex_text_with_specials() -> None:
    text = "**Результат:** x > 5 & y < 10"
    result = format_for_telegram(text)
    assert "<b>Результат:</b>" in result
    assert "&gt;" in result
    assert "&amp;" in result


def test_t5_9_split_normal() -> None:
    assert split_long_message("короткий текст") == ["короткий текст"]


def test_t5_10_split_by_paragraphs() -> None:
    long_text = "\n\n".join([f"Абзац {i}." for i in range(200)])
    parts = split_long_message(long_text, max_length=400)
    assert len(parts) > 1
    assert all(len(part) <= 400 for part in parts)


def test_t5_11_split_no_text_loss() -> None:
    long_text = "\n\n".join([f"Абзац {i}" for i in range(100)])
    parts = split_long_message(long_text, max_length=120)
    reconstructed = "\n\n".join(parts)
    for i in range(100):
        assert f"Абзац {i}" in reconstructed


def test_t5_12_split_oversized_paragraph() -> None:
    huge_paragraph = "Это очень длинное предложение без переносов. " * 200
    parts = split_long_message(huge_paragraph, max_length=200)
    assert parts
    assert all(len(part) <= 200 for part in parts)

