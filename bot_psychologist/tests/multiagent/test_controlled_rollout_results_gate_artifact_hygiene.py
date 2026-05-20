from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate  # noqa: E402


def test_controlled_rollout_results_gate_artifact_hygiene() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.31"), Path("TO_DO_LIST/reports"))
    payload = gate.build_artifact_hygiene_gate(
        preflight["parsed"],
        {
            "final_status": "passed",
            "utf8_decode_error_count": 0,
            "nul_byte_file_count": 0,
            "json_parse_error_count": 0,
            "replacement_char_warning_count": 0,
        },
    )
    assert payload["artifact_encoding_hygiene_passed"] is True
    assert payload["utf8_decode_error_count"] == 0
    assert payload["nul_byte_file_count"] == 0
    assert payload["json_parse_error_count"] == 0
