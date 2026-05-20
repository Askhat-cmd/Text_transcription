from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_rollout_results_gate as gate  # noqa: E402


def test_controlled_rollout_results_gate_no_mutation() -> None:
    repo_root = Path(".").resolve()
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.31"), Path("TO_DO_LIST/reports"))
    source_no_mutation = preflight["parsed"]["no_mutation_proof"]

    tracked, before = gate.tracked_hashes(repo_root)
    after = {name: gate._sha256(path) for name, path in tracked.items()}  # noqa: SLF001
    payload = gate.build_no_mutation_proof(hash_before=before, hash_after=after, source_no_mutation=source_no_mutation)

    assert payload["production_data_mutated"] is False
    assert payload["runtime_defaults_changed"] is False
    assert payload["kb_registry_chroma_config_mutated"] is False
    assert payload["no_mutation_proof_passed"] is True
