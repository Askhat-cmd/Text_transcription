from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.diagnostic_center import build_diagnostic_card_v1  # noqa: E402
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot  # noqa: E402
from bot_agent.multiagent.contracts.thread_state import ThreadState  # noqa: E402


def test_hf4_writer_move_for_example_request_is_concrete_example() -> None:
    snapshot = StateSnapshot(
        nervous_state="hypo",
        intent="clarify",
        openness="mixed",
        ok_position="I+W+",
        safety_flag=False,
        confidence=0.85,
    )
    now = datetime.utcnow()
    thread_state = ThreadState(
        thread_id="hf4-thread-1",
        user_id="hf4-user",
        core_direction="example request",
        phase="clarify",
        response_mode="regulate",
        response_goal="softly stabilize state",
        created_at=now,
        updated_at=now,
    )
    card = build_diagnostic_card_v1(
        user_message="с родителем пример хочу",
        state_snapshot=snapshot,
        thread_state=thread_state,
        context_package=None,
        thread_diagnostics={},
    )
    assert card.suggested_writer_move == "give_concrete_example"
    assert "request_type=example_request" in card.trace.rules_applied

