from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_safety_kb_boundary() -> None:
    payload = execution.build_safety_kb_boundary_gate()
    assert payload["gate_passed"] is True
    assert payload["raw_kb_text_exposure_count"] == 0
    assert payload["raw_provider_payload_exposure_count"] == 0

