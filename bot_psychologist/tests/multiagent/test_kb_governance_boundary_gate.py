from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_acceptance as module


def test_kb_governance_boundary_gate_passes_with_clean_source() -> None:
    payload = module.build_kb_governance_boundary_gate(
        {
            "all_blocks_merged_mutated": False,
            "registry_mutated": False,
            "config_mutated": False,
        }
    )
    assert payload["governance_authority_mutated"] is False
    assert payload["raw_kb_text_exposed_via_prompt_constraint"] is False
    assert payload["final_status"] == "passed"
