from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_activation_readiness as gate  # noqa: E402


def test_limited_activation_readiness_runtime_defaults_gate() -> None:
    payload = gate.build_runtime_defaults_gate()
    assert payload["runtime_defaults_gate_passed"] is True
    assert payload["runtime_defaults_changed"] is False

