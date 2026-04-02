from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import inspect

from bot_agent import answer_adaptive


def test_no_level_based_prompting_in_active_adaptive_pipeline() -> None:
    source = inspect.getsource(answer_adaptive.answer_question_adaptive)
    assert "UserLevelAdapter(" not in source
    assert "level_adapter = None" in source
