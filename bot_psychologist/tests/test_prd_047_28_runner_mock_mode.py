from __future__ import annotations

import json
from pathlib import Path

from bot_agent.experiments.thin_spine_runner import run_prd_047_28_experiment
from bot_agent.multiagent.runtime_adapter import normalize_multiagent_result


def test_runner_mock_mode_creates_reports_and_variant_boundaries(tmp_path: Path) -> None:
    fixture = Path("TO_DO_LIST/fixtures/PRD-047.28/thin_spine_cases_ru.jsonl")

    summary = run_prd_047_28_experiment(
        cases_path=str(fixture),
        variant="all",
        include_kb=True,
        include_live_turn_note=True,
        output_dir=str(tmp_path),
        force_mock=True,
    )

    assert summary["final_status"] == "ACCEPTED WITH WARNING"
    rows = [
        json.loads(line)
        for line in (tmp_path / "variant_outputs.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows
    assert (tmp_path / "thin_spine_comparative_report.md").exists()
    assert (tmp_path / "trace_noise_comparison.json").exists()
    assert (tmp_path / "owner_review_sheet.md").exists()

    b_rows = [row for row in rows if row["variant"] == "B_thin"]
    c_rows = [row for row in rows if row["variant"] == "C_thin_note"]
    a_rows = [row for row in rows if row["variant"] == "A_current"]

    assert a_rows and all(row["status"] == "skipped" for row in a_rows)
    assert b_rows and c_rows
    assert all(not row["trace"]["live_turn_note"]["present"] for row in b_rows)
    assert all(row["trace"]["live_turn_note"]["present"] for row in c_rows)
    assert all(row["trace"]["disabled_heavy_layers"] for row in b_rows + c_rows)
    assert all(not row["metrics"]["kb_used_when_forbidden"] for row in b_rows + c_rows)


def test_production_runtime_entrypoint_contract_remains_multiagent() -> None:
    payload = normalize_multiagent_result(
        result={"status": "ok", "answer": "x", "debug": {}, "thread_id": "t", "phase": "clarify", "response_mode": "reflect", "relation_to_thread": "continue", "continuity_score": 1.0},
        query="hello",
        user_id="u",
        debug=False,
        started_at=0.0,
    )

    assert payload["metadata"]["runtime_entrypoint"] == "multiagent_adapter"
