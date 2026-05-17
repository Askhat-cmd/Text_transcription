from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.prompt_constraint_section import format_prompt_constraint_section_v1


def test_prompt_section_empty_when_not_applied() -> None:
    section = format_prompt_constraint_section_v1(
        {"activation_mode": "shadow_only", "apply_to_writer_prompt": False}
    )
    assert section == ""


def test_prompt_section_contains_sanitized_constraints() -> None:
    section = format_prompt_constraint_section_v1(
        {
            "activation_mode": "test_apply",
            "apply_to_writer_prompt": True,
            "candidate_constraints": {
                "depth_limit": "low",
                "max_questions": 0,
                "max_concepts": 1,
                "must_do": ["keep_language_short", "validate_current_state"],
                "must_not_do": ["do_not_analyze_deeply"],
                "kb_usage_mode": "internal_lens_only",
                "must_not_quote_source": True,
            },
        }
    )
    assert section.startswith("PILOT PROMPT CONSTRAINTS:")
    assert "raw_text" not in section
    assert "kb_usage_mode: internal_lens_only" in section

