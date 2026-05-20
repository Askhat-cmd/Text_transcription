from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate  # noqa: E402


def test_controlled_rollout_results_gate_trace_sanitization() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.31"), Path("TO_DO_LIST/reports"))
    payload = gate.build_trace_provider_sanitization_gate(preflight["parsed"])
    assert payload["raw_provider_payload_committed_count"] == 0
    assert payload["secret_like_value_count"] == 0
    assert payload["private_log_leak_count"] == 0
    assert payload["trace_provider_sanitization_gate_passed"] is True
