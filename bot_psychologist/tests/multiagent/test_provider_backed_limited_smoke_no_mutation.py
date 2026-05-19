from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution


def test_provider_backed_limited_smoke_no_mutation() -> None:
    before = {"all_blocks": "a", "registry": "b", "config": "c"}
    after = {"all_blocks": "a", "registry": "b", "config": "c"}
    runtime_before = {"orchestrator": "x", "writer": "y"}
    runtime_after = {"orchestrator": "x", "writer": "y"}
    proof = execution.build_no_mutation_proof(
        hash_before=before,
        hash_after=after,
        runtime_hash_before=runtime_before,
        runtime_hash_after=runtime_after,
        provider_called_for_pilot_operator=True,
    )
    assert proof["all_blocks_merged_mutated"] is False
    assert proof["registry_mutated"] is False
    assert proof["config_mutated"] is False
