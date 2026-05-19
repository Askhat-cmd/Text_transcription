from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate


def test_second_provider_backed_smoke_botdb_preflight_contains_required_fields() -> None:
    payload = gate.build_botdb_live_preflight("http://127.0.0.1:8003")
    assert "botdb_live_preflight_passed" in payload
    assert "dashboard_chroma_count" in payload
    assert "registry_sources_count" in payload
    assert "query_status_code" in payload
