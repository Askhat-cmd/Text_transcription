from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_activation_readiness as gate  # noqa: E402


def test_limited_activation_readiness_no_mutation_proof() -> None:
    tracked, before = gate.tracked_hashes(Path("."))
    after = {name: gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001
    payload = gate.build_no_mutation_proof(hash_before=before, hash_after=after, source_no_mutation={})
    assert payload["no_mutation_proof_passed"] is True
    assert payload["production_data_mutated"] is False

