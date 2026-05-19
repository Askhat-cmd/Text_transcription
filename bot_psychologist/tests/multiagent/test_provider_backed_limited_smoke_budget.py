from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution


def test_provider_backed_limited_smoke_budget() -> None:
    ok = execution.build_provider_call_budget(
        provider_calls_performed=5,
        provider_calls_for_normal_users=0,
        provider_error_leak_to_user_output=False,
    )
    assert ok["budget_passed"] is True
    bad = execution.build_provider_call_budget(
        provider_calls_performed=6,
        provider_calls_for_normal_users=0,
        provider_error_leak_to_user_output=False,
    )
    assert bad["budget_passed"] is False
