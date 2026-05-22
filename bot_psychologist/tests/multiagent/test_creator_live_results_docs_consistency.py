from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_results_gate as gate  # noqa: E402


def test_creator_live_results_docs_consistency_gate() -> None:
    docs = gate.build_docs_consistency_gate(
        project_state_text="PRD-046.1.35\n",
        roadmap_text=f"## Next\n1. {gate.NEXT_PRD_HF1}.\n",
        prd_index_text="| PRD-046.1.35 |\n",
        decisions_text="ADR-054\n",
        expected_next=gate.NEXT_PRD_HF1,
    )
    assert docs["docs_consistency_gate_passed"] is True

