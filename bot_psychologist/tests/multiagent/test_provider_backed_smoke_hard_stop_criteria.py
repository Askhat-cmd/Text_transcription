from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_readiness as readiness


def test_provider_backed_smoke_hard_stop_criteria_contains_botdb_and_boundary_guards() -> None:
    payload = readiness.build_hard_stop_criteria()
    checks = payload["hard_stop_if"]
    assert any("botdb_query_http_200=false" == item for item in checks)
    assert any("raw_kb_quote_exposure_count > 0" == item for item in checks)
    assert any("normal_user_apply_count > 0" == item for item in checks)
