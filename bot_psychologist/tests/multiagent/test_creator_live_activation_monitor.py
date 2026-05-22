from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_monitor_gate() -> None:
    payload = gate.build_monitor_gate(web_chat_smoke={"monitor_visible": True})
    assert payload["monitor_gate_passed"] is True
