from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_stabilization_cleanup as cleanup


def test_stabilization_cleanup_no_mutation_proof_passed() -> None:
    _, hash_before = cleanup.tracked_hashes(Path("."))
    _, hash_after = cleanup.tracked_hashes(Path("."))
    payload = cleanup.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)
    assert payload["no_mutation_proof_passed"] is True
    assert payload["production_data_mutated"] is False
