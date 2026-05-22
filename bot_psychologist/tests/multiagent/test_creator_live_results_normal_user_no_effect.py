from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_results_gate as gate  # noqa: E402


def test_creator_live_results_normal_user_boundary_proof() -> None:
    root = Path(__file__).resolve().parents[3]
    preflight = gate.preflight_source_artifacts(
        root / "TO_DO_LIST/logs/PRD-046.1.34",
        root / "TO_DO_LIST/reports",
    )
    proof = gate.build_normal_user_boundary_proof(preflight["parsed_json"])
    assert proof["normal_user_boundary_gate_passed"] is True
    assert proof["normal_user_apply_effect_count"] == 0

