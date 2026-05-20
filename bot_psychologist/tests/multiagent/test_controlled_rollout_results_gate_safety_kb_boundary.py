from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate  # noqa: E402


def test_controlled_rollout_results_gate_safety_kb_boundary() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.31"), Path("TO_DO_LIST/reports"))
    payload = gate.build_safety_kb_boundary_gate(preflight["parsed"])
    assert payload["raw_kb_text_exposure_count"] == 0
    assert payload["kb_authority_violation_count"] == 0
    assert payload["unsafe_practice_suggestion_count"] == 0
    assert payload["safety_kb_boundary_gate_passed"] is True
