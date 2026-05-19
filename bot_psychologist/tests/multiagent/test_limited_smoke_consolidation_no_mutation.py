from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_smoke_consolidation as gate


def test_limited_smoke_consolidation_no_mutation() -> None:
    payload = gate.build_no_mutation_proof(
        hash_before={"all_blocks": "1", "registry": "2", "config": "3"},
        hash_after={"all_blocks": "1", "registry": "2", "config": "3"},
        runtime_hash_before={"r": "a"},
        runtime_hash_after={"r": "a"},
    )
    assert payload["production_data_mutated"] is False
    assert payload["no_mutation_gate"] == "passed"

