from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.contracts.diagnostic_center_final_runtime_governance_acceptance_v1 import (
    DiagnosticCenterFinalRuntimeGovernanceAcceptanceV1,
)


def test_final_runtime_governance_acceptance_contract_serialization() -> None:
    payload = DiagnosticCenterFinalRuntimeGovernanceAcceptanceV1(
        final_status="passed",
        decision="accepted_ready_for_cleanup_stabilization",
        source_chain={"source_chain_complete": True},
        provider_evidence={"provider_backed_cycles_total": 3},
    ).to_dict()
    assert payload["schema_version"] == "diagnostic_center_final_runtime_governance_acceptance_v1"
    assert payload["final_status"] == "passed"
    assert payload["decision"] == "accepted_ready_for_cleanup_stabilization"
    assert payload["provider_evidence"]["provider_backed_cycles_total"] == 3

