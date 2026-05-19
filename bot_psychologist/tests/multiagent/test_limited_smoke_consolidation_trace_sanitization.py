from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_smoke_consolidation as gate


def test_limited_smoke_consolidation_trace_sanitization() -> None:
    preflight = gate.preflight_source_chain(
        [Path("TO_DO_LIST/logs/PRD-046.1.23"), Path("TO_DO_LIST/logs/PRD-046.1.24"), Path("TO_DO_LIST/logs/PRD-046.1.25")],
        Path("TO_DO_LIST/reports"),
    )
    payload = gate.build_trace_provider_sanitization_cumulative(preflight["parsed"], artifact_hygiene={"nul_byte_file_count": 0, "utf8_decode_error_count": 0, "json_parse_error_count": 0})
    assert payload["raw_provider_payload_in_artifacts"] is False
    assert payload["trace_provider_sanitization_cumulative_passed"] is True

