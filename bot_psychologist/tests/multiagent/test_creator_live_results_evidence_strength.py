from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_results_gate as gate  # noqa: E402


def test_creator_live_results_evidence_strength_is_not_actual_live() -> None:
    root = Path(__file__).resolve().parents[3]
    preflight = gate.preflight_source_artifacts(
        root / "TO_DO_LIST/logs/PRD-046.1.34",
        root / "TO_DO_LIST/reports",
    )
    audit = gate.build_evidence_strength_audit(preflight)
    assert audit["actual_live_turn_evidence_count"] == 0
    assert audit["simulated_gate_evidence_count"] >= 1
    assert audit["evidence_strength_gate"] in {"warning", "blocked"}

