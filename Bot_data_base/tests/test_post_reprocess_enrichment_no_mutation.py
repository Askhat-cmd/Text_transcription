from __future__ import annotations

import json
from pathlib import Path

from tools import llm_enrichment_post_reprocess as prd


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


def test_run_dry_no_mutation(tmp_path: Path, monkeypatch) -> None:
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    blocks_path.write_text(json.dumps({"blocks": [_mk_block(i) for i in range(247)]}, ensure_ascii=False), encoding="utf-8")
    registry_path.write_text(json.dumps([{"source_id": "123__кузница_духа", "blocks_count": 247}], ensure_ascii=False), encoding="utf-8")
    before_blocks = blocks_path.read_text(encoding="utf-8")
    before_registry = registry_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        prd,
        "evaluate_preflight",
        lambda **_: {
            "schema_version": "post_reprocess_enrichment_preflight_v1",
            "source_prd": "PRD-046.0.9",
            "passed": True,
            "blockers": [],
            "production_blocks_count": 247,
            "registry_blocks_count": 247,
            "chroma_count": 247,
            "active_source_ids": ["123__кузница_духа"],
            "legacy_sd_active": False,
            "old_review_queue_stale": True,
            "new_review_queue_baseline_exists": True,
            "retrieval_eval_status": "ok",
        },
    )
    monkeypatch.setattr(
        prd,
        "build_retrieval_preview",
        lambda **_: {
            "queries_total": 1,
            "queries_ok": 1,
            "top_k_before_summary_available": 0,
            "top_k_overlay_summary_available": 0,
            "overlay_candidate_useful_count": 0,
            "overlay_candidate_noise_count": 0,
            "examples": [],
        },
    )

    result = prd.run_post_reprocess_enrichment(
        mode="dry-run",
        blocks_path=blocks_path,
        registry_path=registry_path,
        logs_dir=tmp_path / "logs",
        reports_dir=tmp_path / "reports",
        overlay_input_path=None,
        batch_size=10,
        resume=False,
        model="gpt-4o-mini",
        timeout_seconds=5.0,
    )
    assert result["status"] == "done"
    assert blocks_path.read_text(encoding="utf-8") == before_blocks
    assert registry_path.read_text(encoding="utf-8") == before_registry
