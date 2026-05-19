from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate


def test_second_provider_backed_smoke_trace_sanitization_gate() -> None:
    payload = gate.build_trace_sanitization_gate()
    assert payload["contains_raw_provider_payload"] is False
    assert payload["nul_byte_count"] == 0
    assert payload["trace_sanitization_gate_passed"] is True
