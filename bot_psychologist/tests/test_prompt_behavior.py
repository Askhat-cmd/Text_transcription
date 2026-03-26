#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prompt behavior guards: avoid mirroring user input."""

from pathlib import Path


def _load_prompt_texts() -> list[str]:
    root = Path(__file__).resolve().parents[1] / "bot_agent"
    return [p.read_text(encoding="utf-8") for p in root.glob("prompt_*.md")]


def test_prompts_do_not_force_mirroring() -> None:
    texts = _load_prompt_texts()
    combined = "\n".join(texts).lower()

    banned_phrases = [
        "я слышу",
        "слышу тебя",
        "перефраз",
        "перескаж",
        "paraphrase",
        "mirror",
    ]

    for phrase in banned_phrases:
        assert phrase not in combined, f"Found banned phrase in prompts: {phrase}"

