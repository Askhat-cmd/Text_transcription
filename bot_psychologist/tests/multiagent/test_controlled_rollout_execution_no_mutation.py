from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_execution as execution  # noqa: E402


def test_controlled_rollout_execution_no_mutation() -> None:
    payload = execution.build_no_mutation_proof(
        hash_before={"all_blocks_merged": "a", "registry": "b", "config": "c"},
        hash_after={"all_blocks_merged": "a", "registry": "b", "config": "c"},
    )
    assert payload["no_mutation_proof_passed"] is True
    assert payload["production_data_mutated"] is False

