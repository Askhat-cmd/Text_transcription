from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_response_quality_eval as module


def test_response_quality_rubric_schema_valid() -> None:
    rubric = module.load_rubric(Path("bot_psychologist/tests/fixtures/diagnostic_center_response_quality_rubric.json"))
    validation = module.validate_rubric(rubric)
    assert validation["rubric_dimension_count"] >= 10
    assert validation["all_required_dimensions_present"] is True
    assert validation["final_status"] == "passed"
