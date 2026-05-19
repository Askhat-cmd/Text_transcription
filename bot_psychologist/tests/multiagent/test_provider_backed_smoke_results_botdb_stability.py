from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_results_gate as gate


def test_provider_backed_smoke_results_botdb_stability_passed() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.23"), Path("TO_DO_LIST/reports"))
    review = gate.build_botdb_stability_review(preflight["parsed"])
    assert review["botdb_stability_status"] == "passed"
    assert review["botdb_health_after_execution"]["dashboard_chroma_count"] == 247
    assert review["botdb_health_after_execution"]["registry_sources_count"] == 1

