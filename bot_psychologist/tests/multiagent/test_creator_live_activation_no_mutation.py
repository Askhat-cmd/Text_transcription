from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_activation as gate  # noqa: E402


def test_no_mutation_proof() -> None:
    _, before = gate.tracked_hashes(Path("."))
    payload = gate.build_no_mutation_proof(hash_before=before, hash_after=dict(before))
    assert payload["no_mutation_proof_passed"] is True
