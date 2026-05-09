from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.apply_enrichment_overlay import run_apply


def _mk_blocks_payload() -> dict:
    return {
        "schema_version": "bot_data_base_v1.0",
        "generated_at": "2026-05-09T00:00:00+00:00",
        "blocks_count": 1,
        "blocks": [
            {
                "id": "block-1",
                "source": "book:test",
                "title": "Заголовок",
                "summary": "Краткое summary",
                "text": "Безопасный текст блока",
                "sd_level": "GREEN",
                "sd_confidence": 0.9,
                "complexity": 0.4,
                "metadata": {
                    "source_title": "КУЗНИЦА ДУХА",
                    "author": "A",
                    "author_id": "a",
                    "language": "ru",
                    "boundary_confidence": 0.95,
                    "governance": {
                        "schema_version": "governance_v1",
                        "chunk_type": "practice",
                        "allowed_use": ["writer_context", "practice_suggestion"],
                        "safety_flags": ["not_for_direct_quote"],
                        "lens_family": ["self_criticism"],
                    },
                    "chunking_quality": {"mixed_intent_severity": "low"},
                },
            }
        ],
    }


def _mk_overlay_row() -> dict:
    return {
        "schema_version": "kb_llm_enrichment_v1",
        "block_id": "block-1",
        "summary_candidate": "Sanitized enrichment summary",
        "lens_family_candidates": ["self_criticism"],
        "tags": ["practice", "self_criticism"],
        "use_when": ["when user asks for practical stabilizing step"],
        "avoid_when": ["when state is acutely unstable"],
        "self_contained_score": 0.73,
        "self_contained_reason": "safe",
        "split_merge_suggestion": {"action": "keep", "reason": "ok"},
        "confidence": 0.66,
        "needs_human_review": True,
        "review_reasons": ["summary_quality_uncertain"],
        "llm_metadata": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "prompt_version": "kb_enrichment_v1_3",
            "mock": False,
        },
    }


def _mk_readiness() -> dict:
    return {
        "run_kind": "real",
        "validation_failed": 0,
        "hard_validation_failed": 0,
        "unknown_lens_candidates": 0,
        "summary_direct_quote_risk_count": 0,
        "safety_governance_invariant_violations": 0,
        "raw_text_leak_check": "pass",
        "production_candidate_ready": True,
        "promotion_allowed": False,
        "promotion_reasons": ["requires_separate_apply_prd"],
    }


def test_apply_overlay_dry_run_and_idempotent_apply(tmp_path: Path) -> None:
    blocks_path = tmp_path / "all_blocks_merged.json"
    overlay_path = tmp_path / "overlay.jsonl"
    readiness_path = tmp_path / "readiness.json"
    output_dir = tmp_path / "logs"
    backup_dir = output_dir / "backups"

    blocks_path.write_text(json.dumps(_mk_blocks_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
    overlay_path.write_text(json.dumps(_mk_overlay_row(), ensure_ascii=False) + "\n", encoding="utf-8")
    readiness_path.write_text(json.dumps(_mk_readiness(), ensure_ascii=False, indent=2), encoding="utf-8")
    before = blocks_path.read_text(encoding="utf-8")

    dry_run = run_apply(
        blocks_path=blocks_path,
        overlay_path=overlay_path,
        output_path=blocks_path,
        output_dir=output_dir,
        backup_dir=backup_dir,
        readiness_path=readiness_path,
        apply_changes=False,
        confirm=False,
    )
    assert dry_run["status"] == "done"
    assert blocks_path.read_text(encoding="utf-8") == before
    dry_diff = json.loads((output_dir / "apply_diff_summary.json").read_text(encoding="utf-8"))
    assert dry_diff["apply_mode"] == "dry_run"
    assert dry_diff["updated_blocks"] == 1
    assert dry_diff["text_changed_count"] == 0
    assert dry_diff["chunk_type_changed_count"] == 0
    assert dry_diff["allowed_use_changed_count"] == 0
    assert dry_diff["safety_flags_changed_count"] == 0

    first_apply = run_apply(
        blocks_path=blocks_path,
        overlay_path=overlay_path,
        output_path=blocks_path,
        output_dir=output_dir,
        backup_dir=backup_dir,
        readiness_path=readiness_path,
        apply_changes=True,
        confirm=True,
    )
    assert first_apply["status"] == "done"
    assert first_apply["backup_path"]
    payload = json.loads(blocks_path.read_text(encoding="utf-8"))
    meta = payload["blocks"][0]["metadata"]
    assert isinstance(meta.get("llm_enrichment"), dict)
    assert meta["llm_enrichment"]["summary"] == "Sanitized enrichment summary"

    second_apply = run_apply(
        blocks_path=blocks_path,
        overlay_path=overlay_path,
        output_path=blocks_path,
        output_dir=output_dir,
        backup_dir=backup_dir,
        readiness_path=readiness_path,
        apply_changes=True,
        confirm=True,
    )
    assert second_apply["status"] == "done"
    second_diff = json.loads((output_dir / "apply_diff_summary.json").read_text(encoding="utf-8"))
    assert second_diff["updated_blocks"] == 0
    assert second_diff["governance_invariant_violations"] == 0


def test_apply_overlay_requires_confirm(tmp_path: Path) -> None:
    blocks_path = tmp_path / "all_blocks_merged.json"
    overlay_path = tmp_path / "overlay.jsonl"
    readiness_path = tmp_path / "readiness.json"
    output_dir = tmp_path / "logs"

    blocks_path.write_text(json.dumps(_mk_blocks_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
    overlay_path.write_text(json.dumps(_mk_overlay_row(), ensure_ascii=False) + "\n", encoding="utf-8")
    readiness_path.write_text(json.dumps(_mk_readiness(), ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(RuntimeError, match="requires --confirm"):
        run_apply(
            blocks_path=blocks_path,
            overlay_path=overlay_path,
            output_path=blocks_path,
            output_dir=output_dir,
            backup_dir=output_dir / "backups",
            readiness_path=readiness_path,
            apply_changes=True,
            confirm=False,
        )
