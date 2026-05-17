from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools import run_planner_bridge_compliance_shadow_eval as runner


def test_runtime_smoke_has_shadow_compare_only_and_no_user_path_effect() -> None:
    cases = runner._run_runtime_smoke()
    assert len(cases) >= 3
    for item in cases:
        assert item["status"] == "ok"
        assert item["answer_exists"] is True
        assert item["diagnostic_center_shadow_exists"] is True
        assert item["planner_bridge_candidate_exists"] is True
        assert item["planner_bridge_compliance_shadow_exists"] is True
        assert item["runtime_mode"] == "shadow_compare_only"
        assert item["apply_to_writer"] is False
        assert item["apply_to_writer_contract"] is False
        assert item["writer_prompt_changed"] is False
        assert item["final_answer_changed"] is False
        assert item["writer_prompt_contains_shadow_output"] is False

