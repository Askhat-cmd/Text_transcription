from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_artifact_hygiene() -> None:
    report = {
        "final_status": "passed",
        "utf8_decode_error_count": 0,
        "nul_byte_file_count": 0,
        "json_parse_error_count": 0,
        "warnings": [],
        "blockers": [],
    }
    payload = execution.build_artifact_hygiene_gate(report)
    assert payload["gate_passed"] is True
    assert payload["utf8_decode_error_count"] == 0

