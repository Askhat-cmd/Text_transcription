from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_active_influence_gate() -> None:
    smoke = {"creator_path_active": True}
    normal = {"normal_user_no_effect_gate_passed": True}
    payload = gate.build_active_influence_gate(web_chat_smoke=smoke, normal_user_gate=normal)
    assert payload["active_influence_gate_passed"] is True
