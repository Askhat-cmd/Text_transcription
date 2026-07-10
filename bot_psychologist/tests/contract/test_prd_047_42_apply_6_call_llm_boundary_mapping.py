from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from TO_DO_LIST.tools import run_prd_047_42_apply_6_call_llm_boundary_mapping as runner


def test_boundary_sections_cover_call_llm_without_gaps() -> None:
    sections = runner.BOUNDARY_SECTIONS

    assert sections[0].start == 141
    assert sections[-1].end == 938

    for previous, current in zip(sections, sections[1:]):
        assert current.start == previous.end + 1

    assert any(section.start <= 902 <= section.end and section.name == "provider_dispatch" for section in sections)


def test_variable_inventory_contains_expected_spine_variables() -> None:
    inventory = runner.build_variable_inventory()
    names = {item["name"]: item for item in inventory}

    assert names["ctx"]["cluster"] == "client_and_ctx_default_seeding"
    assert names["context_meta"]["scope"] == "writer_prompt_input"
    assert names["writer_kb_payload_text"]["scope"] == "writer_prompt_input"
    assert names["runtime_settings"]["scope"] == "provider_dispatch_input"
    assert names["user_prompt"]["scope"] == "provider_dispatch_input"


def test_snapshot_baseline_has_three_cases_and_stable_debug_surface() -> None:
    payload = runner.asyncio.run(runner.build_snapshot_baseline())

    assert payload["schema_version"] == "prd_047_42_apply_6_call_llm_snapshot_v1"
    assert [case["case"] for case in payload["cases"]] == [
        "safe_guided_direct",
        "mvp_free_overview",
        "mvp_free_rich_request",
    ]
    for case in payload["cases"]:
        debug = case["last_debug"]
        assert case["llm_response"].startswith("FAKE::snapshot-model::")
        assert debug["api_mode"] == "snapshot_fake"
        assert debug["tokens_total"] == 148
        assert debug["duration_ms"] == 123
        assert isinstance(debug["user_prompt"], str) and debug["user_prompt"]
        assert isinstance(case["user_prompt_sha1"], str) and len(case["user_prompt_sha1"]) == 40


def test_runner_writes_expected_reports(tmp_path: Path) -> None:
    reports = runner.write_reports(tmp_path)

    expected_names = {
        "call_llm_boundary_map.md",
        "call_llm_variable_dependency_graph.md",
        "call_llm_snapshot_baseline.json",
        "no_mutation_proof.md",
        "implementation_report.md",
        "next_recommendation.md",
    }
    assert {path.name for path in reports.values()} == expected_names
    assert all(path.exists() for path in reports.values())

    snapshot = json.loads((tmp_path / "call_llm_snapshot_baseline.json").read_text(encoding="utf-8"))
    assert len(snapshot["cases"]) == 3

    no_mutation = (tmp_path / "no_mutation_proof.md").read_text(encoding="utf-8")
    assert "Protected diff result: `0 changed paths`" in no_mutation
