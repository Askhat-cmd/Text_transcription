from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_trace_sanitization() -> None:
    payload = execution.build_trace_provider_sanitization_gate()
    assert payload["gate_passed"] is True
    assert payload["contains_raw_private_logs"] is False
    assert payload["contains_raw_provider_payload"] is False

