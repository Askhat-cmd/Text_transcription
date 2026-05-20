from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_activation_readiness as gate  # noqa: E402


def test_limited_activation_readiness_allowlist_policy_gate() -> None:
    payload = gate.build_allowlist_policy_gate()
    assert payload["allowlist_policy_gate_passed"] is True
    assert payload["allowlist_required"] is True
    assert payload["max_live_users_recommended"] <= 3

