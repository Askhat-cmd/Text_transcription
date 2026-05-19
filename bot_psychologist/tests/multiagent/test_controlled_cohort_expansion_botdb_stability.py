from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate


def test_controlled_cohort_expansion_botdb_stability_gate() -> None:
    before = {
        "botdb_preflight_passed": True,
        "dashboard_chroma_count": 247,
        "dashboard_chroma_status": "ok",
        "registry_sources_count": 1,
        "query_status_code": 200,
        "semantic_fallback_used": False,
        "botdb_circuit_open": False,
    }
    after = dict(before)
    payload = gate.build_botdb_stability_gate(before=before, after=after)
    assert payload["botdb_stability_gate_passed"] is True

