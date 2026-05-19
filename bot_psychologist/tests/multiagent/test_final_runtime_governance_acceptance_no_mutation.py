from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_runtime_governance_acceptance as gate


def test_final_runtime_governance_acceptance_no_mutation() -> None:
    payload = gate.build_no_mutation_proof(
        hash_before={"all_blocks": "a", "registry": "b", "config": "c"},
        hash_after={"all_blocks": "a", "registry": "b", "config": "c"},
        runtime_hash_before={"orchestrator": "x"},
        runtime_hash_after={"orchestrator": "x"},
    )
    assert payload["all_blocks_merged_mutated"] is False
    assert payload["registry_mutated"] is False
    assert payload["config_mutated"] is False
    assert payload["no_mutation_proof_passed"] is True

