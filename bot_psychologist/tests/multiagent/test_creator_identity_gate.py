from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_creator_identity_gate_passes_with_value() -> None:
    payload = gate.build_creator_identity_gate(creator_user_id="creator_001")
    assert payload["creator_identity_gate_passed"] is True
    assert payload["creator_identity_value"] == "creator_001"
