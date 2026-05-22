from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_results_gate as gate  # noqa: E402


def test_creator_live_results_rollback_gate_passes_for_prd_046_1_34() -> None:
    root = Path(__file__).resolve().parents[3]
    preflight = gate.preflight_source_artifacts(
        root / "TO_DO_LIST/logs/PRD-046.1.34",
        root / "TO_DO_LIST/reports",
    )
    rollback = gate.build_rollback_quality_gate(preflight["parsed_json"])
    assert rollback["rollback_quality_gate_passed"] is True
    assert rollback["rollback_quality_gate"] == "passed"

