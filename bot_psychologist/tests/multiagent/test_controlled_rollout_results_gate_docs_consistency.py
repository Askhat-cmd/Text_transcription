from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate  # noqa: E402


def test_controlled_rollout_results_gate_docs_consistency() -> None:
    project_state = """# Project State
## Current Stage
post-PRD-046.1.32
## Next Planned PRD
PRD-046.1.33
"""
    roadmap = """# Roadmap
## Next
1. PRD-046.1.33 - next step
"""
    prd_index = "| PRD-046.1.32 | some row |\n"
    decisions = "ADR-051 - Controlled Rollout Results Gate Boundary for PRD-046.1.32\n"

    payload = gate.build_docs_consistency_gate(
        project_state_text=project_state,
        roadmap_text=roadmap,
        prd_index_text=prd_index,
        decisions_text=decisions,
    )
    assert payload["stale_next_prd_reference_count"] == 0
    assert payload["duplicate_roadmap_next_item_count"] == 0
    assert payload["docs_consistency_passed"] is True
