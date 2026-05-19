from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate


def test_controlled_cohort_expansion_no_mutation_proof() -> None:
    proof = gate.build_no_mutation_proof(
        hash_before={"all_blocks": "a", "registry": "b", "config": "c"},
        hash_after={"all_blocks": "a", "registry": "b", "config": "c"},
        runtime_hash_before={"runtime": "d"},
        runtime_hash_after={"runtime": "d"},
    )
    assert proof["no_mutation_passed"] is True
    assert proof["production_mutation_detected"] is False

