from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate


def test_controlled_cohort_expansion_trace_sanitization_gate() -> None:
    trace = {
        "raw_provider_payload_detected": False,
        "raw_private_logs_committed": False,
        "secret_like_values_count": 0,
        "env_key_exposure_count": 0,
    }
    payload = gate.build_trace_provider_sanitization_gate(trace, artifact_hygiene={"nul_byte_file_count": 0})
    assert payload["trace_provider_sanitization_gate_passed"] is True

