from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_results_gate as gate


def test_provider_backed_smoke_results_safety_kb_boundary_passed() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.23"), Path("TO_DO_LIST/reports"))
    review = gate.build_safety_kb_boundary_consolidation(preflight["parsed"])
    assert review["safety_kb_boundary_consolidation_status"] == "passed"
    assert review["raw_kb_quote_exposure_count"] == 0
    assert review["kuznitsa_authority_citation_count"] == 0

