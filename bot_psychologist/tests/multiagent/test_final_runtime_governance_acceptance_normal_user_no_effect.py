from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_runtime_governance_acceptance as gate


def test_final_runtime_governance_acceptance_normal_user_no_effect() -> None:
    preflight = gate.preflight_source_chain(
        [
            Path("TO_DO_LIST/logs/PRD-046.1.23"),
            Path("TO_DO_LIST/logs/PRD-046.1.24"),
            Path("TO_DO_LIST/logs/PRD-046.1.25"),
            Path("TO_DO_LIST/logs/PRD-046.1.26"),
            Path("TO_DO_LIST/logs/PRD-046.1.27"),
        ],
        Path("TO_DO_LIST/reports"),
        Path("."),
    )
    payload = gate.build_normal_user_no_effect_gate(preflight["parsed"])
    assert payload["normal_user_controls_total"] >= 7
    assert payload["normal_user_apply_count_total"] == 0
    assert payload["normal_user_provider_calls_total"] == 0
    assert payload["normal_user_no_effect_gate_passed"] is True

