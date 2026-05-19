from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution


def test_provider_backed_limited_smoke_live_preflight() -> None:
    payload = execution.build_live_dependency_preflight("http://127.0.0.1:8003")
    assert "live_dependency_preflight_passed" in payload
    assert "dashboard_chroma_status" in payload
    assert "query_http_200" in payload
