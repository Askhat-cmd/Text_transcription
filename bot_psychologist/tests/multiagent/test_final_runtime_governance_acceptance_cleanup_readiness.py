from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_runtime_governance_acceptance as gate


def test_final_runtime_governance_acceptance_cleanup_readiness() -> None:
    payload = gate.build_cleanup_stabilization_readiness()
    assert payload["cleanup_stabilization_readiness_ready"] is True
    assert len(payload["zones"]) == 4
    assert "next_prd_structure" in payload["summary"]

