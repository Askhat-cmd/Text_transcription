from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.creator_live_behavior_guard import evaluate_anti_regulate_loop_v1  # noqa: E402


def test_hf4_true_regulate_still_allowed_for_urgent_case() -> None:
    payload = evaluate_anti_regulate_loop_v1(
        user_message="мне очень тревожно, не могу успокоиться, помоги прямо сейчас",
        recent_turn_texts=[],
        safety_active=False,
        response_mode="regulate",
        suggested_writer_move="regulate_first",
    )
    assert payload["request_type"] == "safety_regulation_request"
    assert payload["explicit_regulation_request"] is True
    assert payload["practice_or_regulate_should_be_suppressed"] is False

