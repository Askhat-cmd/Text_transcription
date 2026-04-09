"""Convert bot markdown text into Telegram-compatible HTML."""

from __future__ import annotations

import html
import re


def format_for_telegram(text: str) -> str:
    """
    Convert markdown-ish text from backend into Telegram HTML.

    The function escapes raw HTML first and then applies safe replacements.
    """
    escaped = html.escape(text or "")

    # Code blocks before inline formatting to keep multiline content intact.
    escaped = re.sub(r"```[\w-]*\n?(.*?)```", r"<pre>\1</pre>", escaped, flags=re.DOTALL)
    escaped = re.sub(r"`([^`]+?)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped, flags=re.DOTALL)
    escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", escaped)

    # Markdown headings and horizontal rules.
    escaped = re.sub(r"^#{1,3}\s+(.+)$", r"<b>\1</b>", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"^\s*-{3,}\s*$", "", escaped, flags=re.MULTILINE)
    escaped = re.sub(r"\n{3,}", "\n\n", escaped)

    return escaped.strip()


def split_long_message(text: str, max_length: int = 4096) -> list[str]:
    """
    Split text into Telegram-safe chunks with no data loss.

    Order of split attempts:
    1) by paragraphs;
    2) by sentences for oversized paragraph;
    3) hard cut for oversized sentence.
    """
    if max_length <= 0:
        raise ValueError("max_length must be positive")

    normalized = text or ""
    if len(normalized) <= max_length:
        return [normalized]

    parts: list[str] = []
    current = ""

    for paragraph in normalized.split("\n\n"):
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_length:
            current = candidate
            continue

        if current:
            parts.append(current)
            current = ""

        if len(paragraph) <= max_length:
            current = paragraph
            continue

        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if not current:
                if len(sentence) <= max_length:
                    current = sentence
                    continue
                for start in range(0, len(sentence), max_length):
                    parts.append(sentence[start : start + max_length])
                current = ""
                continue

            candidate_sentence = f"{current} {sentence}"
            if len(candidate_sentence) <= max_length:
                current = candidate_sentence
                continue

            parts.append(current)
            if len(sentence) <= max_length:
                current = sentence
            else:
                for start in range(0, len(sentence), max_length):
                    parts.append(sentence[start : start + max_length])
                current = ""

    if current:
        parts.append(current)

    assert all(len(part) <= max_length for part in parts), "split_long_message: limit exceeded"
    return parts

