from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[2]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.creator_live_behavior_guard import (  # noqa: E402
    REQUEST_TYPE_EXAMPLE,
    REQUEST_TYPE_EXPLAIN,
    REQUEST_TYPE_SAFETY,
    detect_request_type_v1,
)


def test_hf4_detects_example_request() -> None:
    assert detect_request_type_v1("с родителем пример хочу") == REQUEST_TYPE_EXAMPLE


def test_hf4_detects_explain_request() -> None:
    assert detect_request_type_v1("что такое нейросталкинг") == REQUEST_TYPE_EXPLAIN


def test_hf4_detects_safety_request() -> None:
    message = "мне очень тревожно, не могу успокоиться, помоги прямо сейчас"
    assert detect_request_type_v1(message) == REQUEST_TYPE_SAFETY

