from __future__ import annotations

from pathlib import Path

from tools.controlled_candidate_apply import build_apply_plan


def test_apply_plan_contains_required_sections(tmp_path: Path) -> None:
    plan = build_apply_plan(
        source_prd="PRD-046.0.8.1",
        preflight={"passed": True},
        candidate_blocks_count=247,
        production_blocks_before=229,
        source_id="123__кузница_духа",
        all_blocks_path=tmp_path / "all_blocks_merged.json",
        registry_path=tmp_path / "registry.json",
        source_export_path=tmp_path / "source_blocks.json",
        backups_dir=tmp_path / "backups",
    )
    assert plan["preflight_passed"] is True
    assert plan["block_count_delta"] == 18
    assert "files_to_mutate" in plan
    assert len(plan["files_to_mutate"]) == 3
    assert "backup_paths" in plan
    assert "forbidden_mutation_checks" in plan
