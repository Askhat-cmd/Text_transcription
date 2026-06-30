from __future__ import annotations

import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
BOT_PSYCHOLOGIST_ROOT = CURRENT_FILE.parents[1]
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from tools import prd_047_36_owner_pilot_readiness_gate_lib as gate


def test_scenario_runner_emits_all_required_ids() -> None:
    scenarios = gate.build_scenarios()
    assert [scenario.scenario_id for scenario in scenarios] == [
        "S1",
        "S2",
        "S3",
        "S4",
        "S5",
        "S6",
        "S7",
        "S8",
        "S9",
        "S10",
        "S11",
        "S12",
        "S13",
        "S14",
    ]


def test_public_internal_language_leak_is_blocker() -> None:
    scenario = next(item for item in gate.build_scenarios() if item.scenario_id == "S2")
    result = gate.evaluate_scenario(
        scenario=scenario,
        answer="Я вижу это по trace и semantic cards из внутренней базы.",
        runtime_truth_trace={},
        writer_grounding_visibility={},
        source_trace={},
    )
    assert result["status"] == "BLOCKER"
    assert "internal_language_leak" in result["tags"]


def test_no_internal_db_scenario_blocks_writer_visible_payload() -> None:
    scenario = next(item for item in gate.build_scenarios() if item.scenario_id == "S9")
    result = gate.evaluate_scenario(
        scenario=scenario,
        answer="Я рядом. Скажу по-человечески и без лишней теории.",
        runtime_truth_trace={"writer_visible_payload_count": 1},
        writer_grounding_visibility={"kb_visible_to_writer": True},
        source_trace={},
    )
    assert result["status"] == "BLOCKER"
    assert "no_internal_db_violation" in result["tags"]

