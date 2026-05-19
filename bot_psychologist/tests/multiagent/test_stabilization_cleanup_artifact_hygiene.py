from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_stabilization_cleanup as cleanup


def test_stabilization_cleanup_artifact_hygiene_normalization_passed() -> None:
    encoding_report = {
        "utf8_decode_error_count": 0,
        "nul_byte_file_count": 0,
        "json_parse_error_count": 0,
        "replacement_char_warning_count": 0,
    }
    payload = cleanup.build_artifact_hygiene_normalization(
        encoding_report=encoding_report,
        source_warning_text="Warnings: replacement characters in command log (historical)",
    )
    assert payload["historical_warning_documented"] is True
    assert payload["artifact_hygiene_normalization_passed"] is True
