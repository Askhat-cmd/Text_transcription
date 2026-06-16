from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from knowledge_governance.manual_review import build_candidate_index
from knowledge_governance.manual_review_preflight import (
    FIELD_APPLY_MAP,
    build_apply_preflight_report,
    build_dry_run_apply_plan,
    build_overlay_intake_report,
    build_processed_block_index,
)
from knowledge_governance.offline_enrichment import load_processed_blocks, read_json
from tools.run_mechanism_metadata_apply_preflight import build_negative_fixtures


REPO_ROOT = Path(__file__).resolve().parents[2]
PRD17_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.17"
PRD18_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.18"
PROCESSED_PATH = REPO_ROOT / "Bot_data_base" / "data" / "processed" / "books" / "123__кузница_духа_blocks.json"


def _overlay() -> dict:
    return read_json(PRD18_LOG_DIR / "curated_overlay_preview.json")


def _candidate_index() -> dict:
    candidate_run = read_json(PRD17_LOG_DIR / "enrichment_candidates_deterministic.json")
    return build_candidate_index(candidate_run["candidates"])


def _processed_index() -> dict:
    return build_processed_block_index(load_processed_blocks(processed_path=PROCESSED_PATH))


def _workspace_tmp(name: str) -> Path:
    base = REPO_ROOT / ".tmp_pytest_prd_047_19"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{name}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_intake_accepts_fixture_overlay_and_marks_expected_blockers() -> None:
    report = build_overlay_intake_report(
        overlay_document=_overlay(),
        candidate_index=_candidate_index(),
        processed_block_index=_processed_index(),
        overlay_file="TO_DO_LIST/logs/PRD-047.18/curated_overlay_preview.json",
    )
    assert report["intake_status"] == "passed_fixture_only"
    assert report["fixture_only"] is True
    assert "overlay_fixture_only" in report["real_apply_blockers"]
    assert "no_real_human_reviewed_decisions" in report["real_apply_blockers"]


def test_dry_run_plan_is_read_only_and_covers_fixture_overlay() -> None:
    plan = build_dry_run_apply_plan(
        overlay_document=_overlay(),
        candidate_index=_candidate_index(),
        processed_block_index=_processed_index(),
        overlay_file="overlay.json",
    )
    assert plan["live_metadata_mutation_allowed"] is False
    assert plan["chroma_reindex_allowed"] is False
    assert plan["summary"]["item_count"] == 2
    assert plan["summary"]["field_count"] == 5


def test_field_mapping_covers_all_review_fields() -> None:
    assert set(FIELD_APPLY_MAP.keys()) == {
        "summary_candidate",
        "core_thesis_candidate",
        "mechanism_hints_candidates",
        "use_when_candidates",
        "avoid_when_candidates",
        "contraindications_candidates",
        "safe_user_translation_candidate",
        "risk_if_exposed_candidate",
        "allowed_writer_use_candidate",
        "recommended_moves_candidates",
        "forbidden_moves_candidates",
        "depth_level_suggestion",
        "quote_policy_suggestion",
        "chunk_type_review_suggestion",
    }


def test_preflight_fixture_overlay_passes_with_expected_blockers() -> None:
    intake = build_overlay_intake_report(
        overlay_document=_overlay(),
        candidate_index=_candidate_index(),
        processed_block_index=_processed_index(),
        overlay_file="overlay.json",
    )
    plan = build_dry_run_apply_plan(
        overlay_document=_overlay(),
        candidate_index=_candidate_index(),
        processed_block_index=_processed_index(),
        overlay_file="overlay.json",
    )
    report = build_apply_preflight_report(intake_report=intake, dry_run_plan=plan)
    assert report["status"] == "passed_with_expected_blockers"
    assert report["ready_for_live_apply"] is False
    assert report["ready_for_eval_over_real_overlay"] is False


def test_unknown_accepted_field_produces_blocker() -> None:
    tmp_path = _workspace_tmp("missing_mapping")
    paths = build_negative_fixtures(out_dir=tmp_path, overlay_document=_overlay())
    negative = read_json(paths["missing_mapping"])
    plan = build_dry_run_apply_plan(
        overlay_document=negative,
        candidate_index=_candidate_index(),
        processed_block_index=_processed_index(),
        overlay_file="negative.json",
    )
    assert any("missing_field_mapping:not_mapped_field_candidate" in blocker for item in plan["items"] for blocker in item["item_blockers"])


def test_practice_without_contraindications_produces_blocker() -> None:
    tmp_path = _workspace_tmp("practice_without_contra")
    paths = build_negative_fixtures(out_dir=tmp_path, overlay_document=_overlay())
    negative = read_json(paths["practice_without_contra"])
    plan = build_dry_run_apply_plan(
        overlay_document=negative,
        candidate_index=_candidate_index(),
        processed_block_index=_processed_index(),
        overlay_file="negative.json",
    )
    first = plan["items"][0]
    assert "practice_missing_accepted_contraindications" in first["item_blockers"]
    assert "practice_missing_accepted_avoid_when" in first["item_blockers"]


def test_separator_only_preview_is_warning_for_fixture_and_blocker_for_real_overlay() -> None:
    base = _overlay()
    fixture_plan = build_dry_run_apply_plan(
        overlay_document=base,
        candidate_index=_candidate_index(),
        processed_block_index=_processed_index(),
        overlay_file="fixture.json",
    )
    concept_item = next(item for item in fixture_plan["items"] if item["chunk_type"] == "concept")
    assert "separator_only_source_preview_fixture_warning" in concept_item["item_warnings"]

    tmp_path = _workspace_tmp("real_empty_preview")
    paths = build_negative_fixtures(out_dir=tmp_path, overlay_document=base)
    real_negative = read_json(paths["real_empty_preview"])
    real_plan = build_dry_run_apply_plan(
        overlay_document=real_negative,
        candidate_index=_candidate_index(),
        processed_block_index=_processed_index(),
        overlay_file="real.json",
    )
    concept_real_item = next(item for item in real_plan["items"] if item["chunk_type"] == "concept")
    assert "separator_only_source_preview_real_overlay_blocker" in concept_real_item["item_blockers"]
