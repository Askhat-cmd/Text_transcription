from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution


def test_provider_backed_limited_smoke_provider_preflight() -> None:
    mock_payload, _ = execution.build_provider_availability_preflight("mock")
    assert mock_payload["provider_availability_preflight_passed"] is True
    disabled_payload, _ = execution.build_provider_availability_preflight("disabled")
    assert disabled_payload["provider_availability_preflight_passed"] is False
    assert disabled_payload["decision"] == "provider_unavailable"
