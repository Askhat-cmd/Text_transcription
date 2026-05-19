from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_limited_smoke_execution as execution


def test_provider_backed_limited_smoke_operator_only() -> None:
    scenarios = execution.load_scenarios({})
    pilot, _, _ = execution.execute_pilot_operator(
        scenarios=scenarios,
        provider_mode="mock",
        provider_model_name="gpt-5-mini",
        provider_client={"mock": True},
        retrieval_source="api",
        semantic_fallback_used=False,
    )
    assert pilot["pilot_scenarios_executed"] == 5
    assert pilot["pilot_apply_only_for_allowed_user"] is True
    assert pilot["provider_calls_performed"] <= 5
