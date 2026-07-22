from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .writer_agent_constants import _contains_any


BoundedPracticeOutcome = Literal[
    "not_matched", "be_strong", "defer_repair", "strip_followup"
]


@dataclass(frozen=True)
class EnforceSlice3BoundedPracticeResult:
    outcome: BoundedPracticeOutcome


def _classify_enforce_slice3_bounded_practice(
    *,
    text: str,
    lowered_user: str,
    lowered_text: str,
    answer_obligation: str,
) -> EnforceSlice3BoundedPracticeResult:
    if answer_obligation != "provide_one_bounded_practice":
        return EnforceSlice3BoundedPracticeResult(outcome="not_matched")
    practice_anchor_present = _contains_any(
        lowered_text,
        ("будь сильным", "драйвер", "сильн", "напряж", "сдерж"),
    )
    practice_step_present = _contains_any(
        lowered_text,
        ("сделай", "заметь", "отметь", "поймай", "назови", "остановись", "выдох"),
    )
    practice_multistep = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", text)) > 1
    if (
        "?" in text
        or len(text.strip()) > 900
        or practice_multistep
        or not practice_step_present
        or not practice_anchor_present
    ):
        if "будь сильным" in lowered_user:
            return EnforceSlice3BoundedPracticeResult(outcome="be_strong")
        return EnforceSlice3BoundedPracticeResult(outcome="defer_repair")
    return EnforceSlice3BoundedPracticeResult(outcome="strip_followup")
