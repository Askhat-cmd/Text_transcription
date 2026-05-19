from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_limited_smoke_consolidation as gate


def test_limited_smoke_consolidation_provider_evidence() -> None:
    preflight = gate.preflight_source_chain(
        [Path("TO_DO_LIST/logs/PRD-046.1.23"), Path("TO_DO_LIST/logs/PRD-046.1.24"), Path("TO_DO_LIST/logs/PRD-046.1.25")],
        Path("TO_DO_LIST/reports"),
    )
    payload = gate.build_cumulative_provider_evidence(preflight["parsed"])
    assert payload["provider_cycles_total"] == 2
    assert payload["provider_calls_total"] == 11
    assert payload["cumulative_provider_evidence_passed"] is True

