from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent import answer_adaptive
from bot_agent.user_level_adapter import UserLevel


def test_user_level_adapter_not_used_in_adaptive_runtime() -> None:
    assert not hasattr(answer_adaptive, "UserLevelAdapter")


def test_path_user_level_is_neutral_for_any_input() -> None:
    assert answer_adaptive._resolve_path_user_level("beginner") == UserLevel.INTERMEDIATE
    assert answer_adaptive._resolve_path_user_level("advanced") == UserLevel.INTERMEDIATE
    assert answer_adaptive._resolve_path_user_level("custom") == UserLevel.INTERMEDIATE
