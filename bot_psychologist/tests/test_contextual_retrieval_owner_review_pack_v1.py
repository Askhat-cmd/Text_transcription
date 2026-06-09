from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "TO_DO_LIST" / "logs" / "PRD-047.15-HF1"


def _read_json(name: str):
    return json.loads((LOG_DIR / name).read_text(encoding="utf-8-sig"))


def test_owner_review_sheet_is_generated_but_not_pre_filled() -> None:
    sheet = (LOG_DIR / "owner_trace_review_sheet.md").read_text(encoding="utf-8-sig")

    assert "Owner score options" in sheet
    assert "Owner score: `pending`" in sheet
    assert "Owner note: `pending`" in sheet
    assert "should_use_hybrid" in sheet


def test_decision_brief_compares_three_architectures() -> None:
    brief = _read_json("llm_hybrid_decision_brief.json")
    option_names = {option["name"] for option in brief["options"]}

    assert "Heuristic-only Composer" in option_names
    assert "Hybrid Heuristics + LLM-assisted Composer" in option_names
    assert "LLM-first Composer" in option_names
    assert brief["recommendation"] in {
        "keep_heuristic_v1_and_tune",
        "build_hybrid_llm_assist_for_low_confidence_cases",
        "design_llm_first_composer_experiment",
        "defer_llm_until_more_live_data",
    }
    assert "final answer" in brief["forbidden_llm_output"]


def test_acceptance_artifact_preserves_calibration_warning_boundary() -> None:
    acceptance = _read_json("calibration_acceptance.json")

    assert acceptance["cases_total"] >= 40
    assert acceptance["literal_short_reply_query_count"] == 0
    assert acceptance["summary_external_kb_leak_count"] == 0
    assert acceptance["no_stub_violations_count"] == 0
    assert acceptance["llm_calls_added"] is False
    assert acceptance["new_runtime_path_added"] is False
    assert acceptance["new_user_facing_stub_created"] is False
    assert acceptance["owner_review_status"] == "sheet_created"
