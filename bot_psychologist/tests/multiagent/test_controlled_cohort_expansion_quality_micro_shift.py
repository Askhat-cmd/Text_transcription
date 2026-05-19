from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_controlled_cohort_expansion as gate


def test_controlled_cohort_expansion_quality_micro_shift_gate() -> None:
    fixture = Path("bot_psychologist/tests/fixtures/diagnostic_center_controlled_cohort_expansion_cases.json")
    scenarios = gate.load_scenarios_from_fixture(fixture)
    execution, _ = gate.execute_controlled_cohort_expansion(
        scenarios=scenarios,
        provider_mode="mock",
        provider_preflight_passed=True,
    )
    quality = gate.build_quality_micro_shift_gate(execution)
    assert quality["quality_micro_shift_gate_passed"] is True
    assert quality["scenario_count"] >= 12
    assert quality["target_user_count"] == 3

