from __future__ import annotations

import re
from typing import List
import tiktoken


def count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text or ""))


def clean_text(text: str) -> str:
    if text is None:
        return ""
    # Normalize newlines
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple spaces/tabs to single space
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    # Collapse 3+ newlines to 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # Trim spaces around newlines
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    return cleaned.strip()


def split_into_paragraphs(text: str) -> List[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    return [p for p in cleaned.split("\n\n") if p.strip()]


def detect_language(text: str) -> str:
    if not text:
        return "unknown"
    cyrillic = re.findall(r"[А-Яа-яЁё]", text)
    latin = re.findall(r"[A-Za-z]", text)
    total = len(cyrillic) + len(latin)
    if total == 0:
        return "unknown"
    cyr_ratio = len(cyrillic) / total
    lat_ratio = len(latin) / total
    if cyr_ratio >= 0.6:
        return "ru"
    if lat_ratio >= 0.6:
        return "en"
    return "unknown"
