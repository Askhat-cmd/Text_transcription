from __future__ import annotations

import json
from pathlib import Path

from tools.llm_enrichment_post_reprocess import evaluate_preflight


def _mk_block(idx: int) -> dict:
    return {
        "id": f"block-{idx}",
        "text": f"Текст блока {idx}",
        "source": "book:123__кузница_духа",
        "metadata": {
            "source_title": "Кузница Духа",
            "governance": {"chunk_type": "theory", "allowed_use": ["writer_context"], "safety_flags": ["not_for_direct_quote"]},
            "chunking_quality": {"mixed_intent_severity": "none"},
        },
    }


def test_preflight_passes_when_all_inputs_match(tmp_path: Path) -> None:
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma_reindex_result.json"
    stale_path = tmp_path / "review_queue_staleness_report.json"
    new_queue_path = tmp_path / "review_queue_new_baseline.json"
    retrieval_path = tmp_path / "retrieval_eval_after_reprocess.json"
    legacy_path = tmp_path / "post_apply_legacy_sd_usage_report.json"

    blocks = {"blocks": [_mk_block(i) for i in range(247)]}
    blocks_path.write_text(json.dumps(blocks, ensure_ascii=False), encoding="utf-8")
    registry_path.write_text(json.dumps([{"source_id": "123__кузница_духа", "blocks_count": 247}], ensure_ascii=False), encoding="utf-8")
    chroma_path.write_text(json.dumps({"chroma_count_after": 247}, ensure_ascii=False), encoding="utf-8")
    stale_path.write_text(json.dumps({"stale": True}, ensure_ascii=False), encoding="utf-8")
    new_queue_path.write_text(json.dumps({"items": []}, ensure_ascii=False), encoding="utf-8")
    retrieval_path.write_text(json.dumps({"status": "ok"}, ensure_ascii=False), encoding="utf-8")
    legacy_path.write_text(json.dumps({"legacy_sd_filter_still_active": False}, ensure_ascii=False), encoding="utf-8")

    payload = evaluate_preflight(
        blocks_path=blocks_path,
        registry_path=registry_path,
        chroma_reindex_result_path=chroma_path,
        review_queue_staleness_path=stale_path,
        review_queue_new_baseline_path=new_queue_path,
        retrieval_eval_path=retrieval_path,
        legacy_sd_usage_report_path=legacy_path,
    )
    assert payload["passed"] is True
    assert payload["blockers"] == []


def test_preflight_detects_mismatch(tmp_path: Path) -> None:
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma_reindex_result.json"
    stale_path = tmp_path / "review_queue_staleness_report.json"
    retrieval_path = tmp_path / "retrieval_eval_after_reprocess.json"
    legacy_path = tmp_path / "post_apply_legacy_sd_usage_report.json"

    blocks = {"blocks": [_mk_block(i) for i in range(2)]}
    blocks_path.write_text(json.dumps(blocks, ensure_ascii=False), encoding="utf-8")
    registry_path.write_text(json.dumps([{"source_id": "123__кузница_духа", "blocks_count": 2}], ensure_ascii=False), encoding="utf-8")
    chroma_path.write_text(json.dumps({"chroma_count_after": 2}, ensure_ascii=False), encoding="utf-8")
    stale_path.write_text(json.dumps({"stale": False}, ensure_ascii=False), encoding="utf-8")
    retrieval_path.write_text(json.dumps({"status": "failed"}, ensure_ascii=False), encoding="utf-8")
    legacy_path.write_text(json.dumps({"legacy_sd_filter_still_active": True}, ensure_ascii=False), encoding="utf-8")

    payload = evaluate_preflight(
        blocks_path=blocks_path,
        registry_path=registry_path,
        chroma_reindex_result_path=chroma_path,
        review_queue_staleness_path=stale_path,
        review_queue_new_baseline_path=tmp_path / "missing.json",
        retrieval_eval_path=retrieval_path,
        legacy_sd_usage_report_path=legacy_path,
    )
    assert payload["passed"] is False
    assert "production_blocks_count_mismatch" in payload["blockers"]
    assert "retrieval_eval_not_ok" in payload["blockers"]
