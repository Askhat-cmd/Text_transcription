from __future__ import annotations

import json
from pathlib import Path

from tools import real_provider_enrichment_run as run1


def _mk_block(idx: int) -> dict:
    return {
        "id": f"block-{idx}",
        "text": "text",
        "source": "book:123__кузница_духа",
        "metadata": {
            "source_title": "Кузница Духа",
            "governance": {"chunk_type": "theory", "allowed_use": ["writer_context"], "safety_flags": ["not_for_direct_quote"]},
            "chunking_quality": {"mixed_intent_severity": "none"},
        },
    }


def test_run1_validate_existing_keeps_sources_unchanged(tmp_path: Path, monkeypatch) -> None:
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    base_logs = tmp_path / "base"
    logs_dir = tmp_path / "run1"
    reports_dir = tmp_path / "reports"
    blocks_path.write_text(json.dumps({"blocks": [_mk_block(i) for i in range(247)]}, ensure_ascii=False), encoding="utf-8")
    registry_path.write_text(json.dumps([{"source_id": "123__кузница_духа", "blocks_count": 247}], ensure_ascii=False), encoding="utf-8")
    base_logs.mkdir(parents=True, exist_ok=True)
    for name in ("enrichment_candidate_overlay.json", "enrichment_inventory.json", "enrichment_scorecard.json"):
        (base_logs / name).write_text("{}", encoding="utf-8")

    before_blocks = blocks_path.read_text(encoding="utf-8")
    before_registry = registry_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        run1,
        "evaluate_preflight",
        lambda **_: {
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
        run1,
        "run_provider_preflight",
        lambda **_: {"passed": True, "model": "gpt-4o-mini", "configured_budget_usd": 1.0, "hard_stop_budget_usd": 2.0},
    )
    monkeypatch.setattr(
        run1,
        "generate_overlay",
        lambda **_: (
                {
                    "items": [
                        {
                            "block_id": "block-0",
                            "input_text_hash": "x",
                            "advisory": {"summary": "s", "tags": ["t"], "use_when": ["u"], "avoid_when": ["a"], "lens_family_candidates": ["l"]},
                            "quality": {"confidence": 0.9, "self_contained_score": 0.9, "needs_human_review": False, "review_reasons": []},
                        }
                    ]
                },
            {"provider_status": "ok"},
        ),
    )
    monkeypatch.setattr(
        run1,
        "validate_overlay",
        lambda **_: {
            "validation_errors_count": 0,
            "validation_warnings_count": 0,
            "raw_full_text_leak_detected": False,
            "governance_authority_mutated": False,
        },
    )
    monkeypatch.setattr(run1, "build_retrieval_preview", lambda **_: {"queries_total": 1, "top_k_before_summary_available": 0, "top_k_overlay_summary_available": 1, "overlay_candidate_useful_count": 1, "overlay_candidate_noise_count": 0})

    result = run1.run_real_provider_cycle(
        mode="validate-existing",
        model="gpt-4o-mini",
        blocks_path=blocks_path,
        registry_path=registry_path,
        base_rebaseline_logs_dir=base_logs,
        logs_dir=logs_dir,
        reports_dir=reports_dir,
        overlay_input_path=tmp_path / "overlay.json",
        batch_size=5,
        resume=False,
        limit=1,
        force=False,
        timeout_seconds=5.0,
        configured_budget_usd=1.0,
        hard_stop_budget_usd=2.0,
        input_price_per_1k=0.001,
        output_price_per_1k=0.001,
    )
    assert result["status"] in {"done", "partial"}
    assert blocks_path.read_text(encoding="utf-8") == before_blocks
    assert registry_path.read_text(encoding="utf-8") == before_registry
