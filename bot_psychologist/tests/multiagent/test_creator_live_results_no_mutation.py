from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_results_gate as gate  # noqa: E402


def test_creator_live_results_no_mutation_proof_passes() -> None:
    root = Path(__file__).resolve().parents[3]
    preflight = gate.preflight_source_artifacts(
        root / "TO_DO_LIST/logs/PRD-046.1.34",
        root / "TO_DO_LIST/reports",
    )
    tracked, before = gate.tracked_hashes(root)
    after = {name: gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001
    payload = gate.build_no_mutation_proof(hash_before=before, hash_after=after, source_parsed=preflight["parsed_json"])
    assert payload["no_mutation_proof_passed"] is True

