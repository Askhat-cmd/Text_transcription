from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_trace_sanitization_gate() -> None:
    payload = gate.build_trace_provider_sanitization_gate(list(Path("TO_DO_LIST/logs/PRD-046.1.33").glob("*")))
    assert payload["trace_provider_sanitization_gate_passed"] is True
