from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_creator_live_pilot_acceptance as gate  # noqa: E402


def test_prd_046_1_36_pilot_cases_gate_passes() -> None:
    fixture = Path("bot_psychologist/tests/fixtures/prd_046_1_36_creator_live_pilot_cases.json")
    creator_payload, trace_payload, normal_payload = gate.run_creator_live_pilot_cases(
        repo_root=Path(".").resolve(),
        fixture_path=fixture.resolve(),
    )
    assert creator_payload["creator_cases_total"] == 7
    assert creator_payload["creator_cases_passed"] == 7
    assert creator_payload["creator_live_pilot_acceptance_gate"] == "passed"
    assert trace_payload["trace_acceptance_gate"] == "passed"
    assert normal_payload["normal_user_no_effect_gate"] == "passed"

