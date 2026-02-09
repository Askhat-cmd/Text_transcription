"""Mode handler utilities for rendering prompt directives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..response import build_mode_prompt


@dataclass
class ModeDirective:
    """Structured mode directive passed to answer generation."""

    mode: str
    confidence_level: str
    reason: str
    forbid: List[str]
    prompt: str


def build_mode_directive(
    mode: str,
    confidence_level: str,
    reason: str = "",
    forbid: List[str] | None = None,
) -> ModeDirective:
    """Build a mode directive object with prompt text."""
    forbid_items = list(forbid or [])
    prompt = build_mode_prompt(mode, confidence_level, forbid_items)
    return ModeDirective(
        mode=mode,
        confidence_level=confidence_level,
        reason=reason,
        forbid=forbid_items,
        prompt=prompt,
    )
