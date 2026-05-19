from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate


def test_second_provider_backed_smoke_no_mutation_proof() -> None:
    payload = gate.build_no_mutation_proof(
        hash_before={"all_blocks": "a", "registry": "b", "config": "c"},
        hash_after={"all_blocks": "a", "registry": "b", "config": "c"},
        runtime_hash_before={"x": "1"},
        runtime_hash_after={"x": "1"},
    )
    assert payload["production_mutation_detected"] is False
    assert payload["no_mutation_passed"] is True
