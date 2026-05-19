from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_planning as planning


def test_controlled_rollout_planning_no_mutation() -> None:
    _, before = planning.tracked_hashes(Path("."))
    _, after = planning.tracked_hashes(Path("."))
    payload = planning.build_no_mutation_proof(before, after)
    assert payload["no_mutation_proof_passed"] is True
    assert payload["production_data_mutated"] is False
