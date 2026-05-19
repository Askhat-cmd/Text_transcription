from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_final_runtime_governance_acceptance as gate


def test_final_runtime_governance_acceptance_botdb_stability() -> None:
    preflight = gate.preflight_source_chain(
        [
            Path("TO_DO_LIST/logs/PRD-046.1.23"),
            Path("TO_DO_LIST/logs/PRD-046.1.24"),
            Path("TO_DO_LIST/logs/PRD-046.1.25"),
            Path("TO_DO_LIST/logs/PRD-046.1.26"),
            Path("TO_DO_LIST/logs/PRD-046.1.27"),
        ],
        Path("TO_DO_LIST/reports"),
        Path("."),
    )
    payload = gate.build_botdb_stability_gate(preflight["parsed"], "http://127.0.0.1:8003")
    assert payload["dashboard_chroma_count"] == 247
    assert payload["dashboard_chroma_status"] == "ok"
    assert payload["registry_source_count"] == 1
    assert payload["botdb_stability_gate_passed"] is True

