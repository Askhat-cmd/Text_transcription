from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_readiness as readiness


def test_provider_backed_smoke_live_dependency_gate_build() -> None:
    gate = readiness.build_live_dependency_gate(
        {
            "admin_base_url": "http://127.0.0.1:8003",
            "botdb_live_reachable": True,
            "dashboard_chroma_status": "ok",
            "dashboard_chroma_count": 247,
            "registry_sources_count": 1,
            "registry_focus_source_id": "123__кузница_духа",
            "registry_focus_source_blocks": 247,
            "registry_stats_chroma_total": 247,
            "query_http_200": True,
            "query_rag_hits_count": 2,
            "semantic_fallback_used": False,
            "botdb_circuit_open": False,
            "checks": {},
        }
    )
    assert gate["live_dependency_readiness_passed"] is True
