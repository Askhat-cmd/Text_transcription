from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_results_gate as gate  # noqa: E402


def test_creator_live_results_quality_gate_strict_blocks_without_actual() -> None:
    audit = {
        "actual_live_turn_evidence_count": 0,
        "runtime_probe_evidence_count": 2,
        "simulated_gate_evidence_count": 1,
        "missing_evidence_count": 0,
    }
    quality = gate.build_live_results_quality_gate(evidence_audit=audit, strict=True)
    assert quality["quality_gate_passed"] is False
    assert quality["live_results_quality_gate"] == "blocked"

