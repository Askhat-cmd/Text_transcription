from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_activation_readiness as gate  # noqa: E402


def test_limited_activation_readiness_normal_user_boundary_gate() -> None:
    payload = gate.build_normal_user_boundary_gate()
    assert payload["normal_user_boundary_gate_passed"] is True
    assert payload["normal_user_apply_effect_count"] == 0
    assert payload["normal_user_provider_call_count"] == 0

