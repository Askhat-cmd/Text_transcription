from __future__ import annotations

from pathlib import Path

from knowledge_governance.curated_batch_eval import (
    build_batch_1_decisions_pack,
    build_batch_1_overlay_preview,
    build_batch_1_preflight_bundle,
    build_batch_1_selection,
    build_candidate_index_from_run,
    build_retrieval_eval_dataset,
    build_retrieval_eval_results,
)
from knowledge_governance.manual_review_preflight import build_processed_block_index
from knowledge_governance.offline_enrichment import load_processed_blocks, load_registry_entry, read_json, resolve_registry_paths, source_filter_match


REPO_ROOT = Path(__file__).resolve().parents[2]
PRD17_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.17"
REGISTRY_PATH = REPO_ROOT / "Bot_data_base" / "data" / "registry.json"


def _context() -> dict:
    candidate_run = read_json(PRD17_LOG_DIR / "enrichment_candidates_deterministic.json")
    candidate_index = build_candidate_index_from_run(candidate_run)
    entry = load_registry_entry(registry_path=REGISTRY_PATH, source_hint="kuznica")
    paths = resolve_registry_paths(repo_root=REPO_ROOT, entry=entry)
    processed_blocks = load_processed_blocks(processed_path=paths["processed_json"])
    filtered_blocks = [
        block
        for block in processed_blocks
        if source_filter_match(
            block=block,
            source_hint="kuznica",
            source_id=str(entry.get("source_id") or ""),
            source_title=str(entry.get("title") or ""),
        )
    ]
    return {
        "candidate_index": candidate_index,
        "processed_block_index": build_processed_block_index(filtered_blocks),
    }


def test_batch_selection_uses_expected_mix() -> None:
    selection = build_batch_1_selection(candidate_index=_context()["candidate_index"])
    assert selection["status"] == "passed"
    assert selection["selection_count"] == 16
    assert selection["counts_by_group"] == {
        "diagnostic_lens": 4,
        "mechanism_or_concept": 4,
        "practice": 4,
        "source_fragment": 4,
    }
    assert selection["missing_candidates"] == []


def test_batch_decisions_pack_is_eval_only_and_has_no_high_risk_practice_accepts() -> None:
    context = _context()
    selection = build_batch_1_selection(candidate_index=context["candidate_index"])
    decisions = build_batch_1_decisions_pack(
        selection_document=selection,
        candidate_index=context["candidate_index"],
    )
    assert decisions["validation_status"] == "passed"
    assert decisions["human_final_approval"] is False
    assert decisions["evaluation_only"] is True
    assert decisions["live_apply_allowed"] is False
    assert decisions["accepted_item_count"] == 12
    assert decisions["high_risk_practice_accepted_fields"] == 0


def test_overlay_and_preflight_keep_eval_only_blockers_but_allow_offline_eval() -> None:
    context = _context()
    selection = build_batch_1_selection(candidate_index=context["candidate_index"])
    decisions = build_batch_1_decisions_pack(
        selection_document=selection,
        candidate_index=context["candidate_index"],
    )
    overlay = build_batch_1_overlay_preview(
        candidate_index=context["candidate_index"],
        decision_document=decisions,
        decisions_file="TO_DO_LIST/logs/PRD-047.20/batch_1_decisions_pack.json",
    )
    bundle = build_batch_1_preflight_bundle(
        overlay_document=overlay,
        candidate_index=context["candidate_index"],
        processed_block_index=context["processed_block_index"],
        overlay_file="TO_DO_LIST/logs/PRD-047.20/batch_1_accepted_overlay_preview.json",
    )
    assert overlay["evaluation_only"] is True
    assert overlay["human_final_approval"] is False
    assert overlay["summary"]["accepted_item_count"] == 12
    assert all(item["chunk_type"] != "source_fragment" for item in overlay["items"])
    preflight = bundle["apply_preflight_report"]
    assert preflight["status"] == "passed_with_expected_blockers"
    assert preflight["ready_for_live_apply"] is False
    assert preflight["ready_for_eval_over_real_overlay"] is True
    assert "human_final_approval_missing" in preflight["expected_blockers"]
    assert "evaluation_only_overlay" in preflight["expected_blockers"]


def test_retrieval_eval_shadow_results_pass_with_safe_overlay() -> None:
    context = _context()
    selection = build_batch_1_selection(candidate_index=context["candidate_index"])
    decisions = build_batch_1_decisions_pack(
        selection_document=selection,
        candidate_index=context["candidate_index"],
    )
    overlay = build_batch_1_overlay_preview(
        candidate_index=context["candidate_index"],
        decision_document=decisions,
        decisions_file="TO_DO_LIST/logs/PRD-047.20/batch_1_decisions_pack.json",
    )
    dataset = build_retrieval_eval_dataset(selection_document=selection)
    baseline_results = {
        case["id"]: [{"id": case["expected_candidate_ids"][0], "chunk_type": case["expected_chunk_types"][0], "score": 0.9}]
        for case in dataset["cases"]
    }
    results = build_retrieval_eval_results(
        dataset_document=dataset,
        overlay_document=overlay,
        selection_document=selection,
        baseline_results=baseline_results,
        baseline_available=True,
        baseline_warning="",
    )
    assert results["schema_version"] == "mechanism_metadata_curated_batch_retrieval_eval_results_v1"
    assert results["status"] == "passed"
    assert results["overlay_shadow_hit_rate"] >= 0.75
    assert results["baseline_hit_rate"] == 1.0
    assert results["unsafe_overlay_hit_count"] == 0
    assert results["separator_preview_accepted_count"] == 0
    assert results["practice_without_safety_count"] == 0
