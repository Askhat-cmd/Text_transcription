from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_web_chat_creator_live_smoke_gate() -> None:
    probe = {"runtime_reachable": True}
    creator = {"creator_identity_gate_passed": True}
    payload = gate.build_web_chat_creator_live_smoke(runtime_probe=probe, creator_identity_gate=creator)
    assert payload["smoke_passed"] is True
    assert payload["diagnostic_center_mode"] == "creator_only"
