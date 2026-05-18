from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_response_quality_eval as module


def test_response_quality_scenario_group_coverage() -> None:
    scenarios = module.load_scenarios(Path("bot_psychologist/tests/fixtures/diagnostic_center_response_quality_scenarios.json"))
    catalog = module.validate_scenarios(scenarios)
    assert catalog["required_scenario_groups_present"] is True
    groups = catalog["scenario_groups"]
    assert groups["A"] >= 8
    assert groups["B"] >= 5
    assert groups["C"] >= 4
    assert groups["D"] >= 4
    assert groups["E"] >= 3
