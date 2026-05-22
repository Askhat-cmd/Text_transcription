from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_results_gate as gate  # noqa: E402


def test_creator_live_results_decision_evidence_incomplete() -> None:
    scorecard = gate.build_results_scorecard(
        source_manifest={"source_artifacts_gate": "passed"},
        evidence_audit={
            "evidence_strength_gate": "warning",
            "actual_live_turn_evidence_count": 0,
            "runtime_probe_evidence_count": 1,
            "simulated_gate_evidence_count": 1,
            "missing_evidence_count": 0,
        },
        quality_gate={"live_results_quality_gate": "blocked"},
        rollback_gate={"rollback_quality_gate": "passed"},
        normal_user_gate={"normal_user_boundary_gate": "passed"},
        trace_gate={"trace_sanitization_gate": "passed"},
        provider_gate={"provider_budget_gate": "passed"},
        no_mutation_proof={"no_mutation_proof_passed": True},
        docs_consistency_gate={"docs_consistency_gate_passed": True},
        artifact_encoding_hygiene_passed=True,
    )
    assert scorecard["decision"] == gate.DECISION_EVIDENCE_HOTFIX
    assert scorecard["final_status"] == "evidence_incomplete"

