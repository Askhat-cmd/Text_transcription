from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_activation_readiness as gate  # noqa: E402


def test_limited_activation_readiness_trace_provider_sanitization_gate() -> None:
    payload = gate.build_trace_provider_sanitization_gate([])
    assert payload["trace_provider_sanitization_gate_passed"] is True
    assert payload["raw_provider_payload_committed"] is False
    assert payload["secrets_committed"] is False

