from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent import diagnostic_center_provider_backed_smoke_results_gate as gate


def test_provider_backed_smoke_results_normal_user_no_effect_passed() -> None:
    preflight = gate.preflight_source(Path("TO_DO_LIST/logs/PRD-046.1.23"), Path("TO_DO_LIST/reports"))
    review = gate.build_normal_user_no_effect_review(preflight["parsed"])
    assert review["normal_user_no_effect_status"] == "passed"
    assert review["normal_user_apply_count"] == 0
    assert review["normal_user_provider_apply_count"] == 0

