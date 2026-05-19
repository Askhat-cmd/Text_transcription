from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_second_provider_backed_smoke as gate


def test_second_provider_backed_smoke_quality_micro_shift_gate() -> None:
    scenarios = gate.load_scenarios_from_fixture(
        Path("bot_psychologist/tests/fixtures/diagnostic_center_second_provider_backed_smoke_cases.json")
    )
    execution_result, _ = gate.execute_second_provider_backed_smoke(
        scenarios=scenarios,
        provider_mode="mock",
        provider_preflight_passed=True,
    )
    payload = gate.build_quality_micro_shift_gate(execution_result["aggregate"])
    assert payload["scenario_count"] == 6
    assert payload["quality_micro_shift_gate_passed"] is True
