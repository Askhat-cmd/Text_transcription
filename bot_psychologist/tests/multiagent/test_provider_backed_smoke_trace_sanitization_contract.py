from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_readiness as readiness


def test_provider_backed_smoke_trace_sanitization_contract_is_strict() -> None:
    payload = readiness.build_trace_sanitization_contract()
    assert payload["contains_raw_provider_payload"] is False
    assert payload["contains_user_private_identifier"] is False
    assert payload["trace_sanitization_contract_ready"] is True
