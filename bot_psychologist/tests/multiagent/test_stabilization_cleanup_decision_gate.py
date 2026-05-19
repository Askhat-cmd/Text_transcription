from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_stabilization_cleanup as cleanup


def test_stabilization_cleanup_decision_gate_passed() -> None:
    preflight = cleanup.preflight_source_reports(Path("TO_DO_LIST/reports"))
    source_gate = cleanup.build_source_gate(preflight)
    inventory = cleanup.collect_artifact_inventory(Path("."))
    classification, archive_manifest, cleanup_manifest = cleanup.classify_inventory(inventory)
    snapshot = cleanup.create_docs_snapshots(Path("."), write_snapshots=False)
    snapshot["created"] = True
    docs_compaction = {
        "docs_compaction_passed": True,
        "runtime_map_created": True,
        "eval_harness_map_created": True,
    }
    permanent = cleanup.revalidate_permanent_gates(Path("."))
    artifact_hygiene = {
        "artifact_hygiene_normalization_passed": True,
    }
    no_mutation = {
        "no_mutation_proof_passed": True,
        "production_data_mutated": False,
        "runtime_defaults_changed": False,
    }
    decision, scorecard = cleanup.build_decision(
        source_gate=source_gate,
        inventory=inventory,
        classification=classification,
        archive_manifest=archive_manifest,
        cleanup_manifest=cleanup_manifest,
        snapshot_proof=snapshot,
        docs_compaction=docs_compaction,
        permanent_gates=permanent,
        artifact_hygiene=artifact_hygiene,
        no_mutation=no_mutation,
    )
    assert decision["final_status"] == "passed"
    assert scorecard["decision"] == "diagnostic_center_stabilized_cleanup_manifested"
