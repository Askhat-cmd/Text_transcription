from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_results_gate as gate  # noqa: E402


def test_creator_live_results_trace_sanitization_gate() -> None:
    root = Path(__file__).resolve().parents[3]
    preflight = gate.preflight_source_artifacts(
        root / "TO_DO_LIST/logs/PRD-046.1.34",
        root / "TO_DO_LIST/reports",
    )
    scan_paths = list((root / "TO_DO_LIST/logs/PRD-046.1.34").glob("*"))
    payload = gate.build_trace_sanitization_results_gate(preflight["parsed_json"], scan_paths)
    assert payload["trace_sanitization_gate_passed"] is True
    assert payload["trace_sanitization_gate"] == "passed"

