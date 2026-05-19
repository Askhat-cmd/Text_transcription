from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_results_gate as gate


def test_provider_backed_smoke_results_no_mutation_passed() -> None:
    repo_root = Path(".").resolve()
    tracked, hash_before = gate.tracked_hashes(repo_root)
    hash_after = {name: gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001
    generated = gate.build_no_mutation_proof(hash_before=hash_before, hash_after=hash_after)
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.23"), Path("TO_DO_LIST/reports"))
    review = gate.build_no_mutation_review(preflight["parsed"], generated)
    assert review["no_mutation_status"] == "passed"
    assert review["provider_called_by_prd_046_1_24"] is False

