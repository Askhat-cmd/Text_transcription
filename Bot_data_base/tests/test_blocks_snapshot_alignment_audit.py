from __future__ import annotations

import json
from pathlib import Path

from review.blocks_snapshot_alignment import build_alignment_audit, write_json


def _queue_payload() -> dict:
    return {
        "schema_version": "post_reprocess_review_queue_after_real_enrichment_v1",
        "source_prd": "PRD-046.0.9-RUN1",
        "items": [
            {"review_item_id": "post_reprocess::b1", "block_id": "b1"},
            {"review_item_id": "post_reprocess::b2", "block_id": "b2"},
        ],
    }


def _block(block_id: str) -> dict:
    return {
        "id": block_id,
        "source": "book:123__focus_source",
        "metadata": {
            "governance": {
                "chunk_type": "lens",
                "allowed_use": ["writer_context"],
                "safety_flags": ["not_for_direct_quote"],
                "source_trace": {"source_id": "123__focus_source"},
            }
        },
    }


def test_audit_detects_blocks_mismatch_and_queue_missing(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue.json"
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma.json"

    write_json(queue_path, _queue_payload())
    write_json(blocks_path, {"schema_version": "bot_data_base_v1.0", "blocks": [_block("x1"), _block("x2")]})
    write_json(registry_path, [{"source_id": "123__focus_source", "blocks_count": 3, "status": "done"}])
    write_json(chroma_path, {"dashboard_chroma_count": 3})

    audit = build_alignment_audit(
        queue_payload=_queue_payload(),
        blocks_payload=json.loads(blocks_path.read_text(encoding="utf-8")),
        registry_payload=json.loads(registry_path.read_text(encoding="utf-8")),
        queue_path=queue_path,
        blocks_path=blocks_path,
        registry_path=registry_path,
        expected_blocks_total=3,
        expected_source_id="123__focus_source",
        scan_roots=[tmp_path / "candidates"],
        chroma_snapshot_path=chroma_path,
        source_prd="PRD-046.0.9.1-HF1",
    )

    assert audit["status"] == "not_aligned"
    assert audit["blocks_total"] == 2
    assert audit["queue_items_count"] == 2
    assert audit["queue_block_ids_present_count"] == 0
    assert audit["queue_block_ids_missing_count"] == 2


def test_audit_finds_authoritative_candidate_when_present(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue.json"
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma.json"
    candidates_root = tmp_path / "candidates"
    candidate_path = candidates_root / "candidate_to_apply.snapshot.json"

    write_json(queue_path, _queue_payload())
    write_json(blocks_path, {"schema_version": "bot_data_base_v1.0", "blocks": [_block("x1"), _block("x2")]})
    write_json(registry_path, [{"source_id": "123__focus_source", "blocks_count": 3, "status": "done"}])
    write_json(chroma_path, {"dashboard_chroma_count": 3})

    candidate_payload = {
        "schema_version": "candidate_snapshot_v1",
        "candidate": {
            "blocks_count": 3,
            "blocks": [_block("b1"), _block("b2"), _block("b3")],
        },
    }
    write_json(candidate_path, candidate_payload)

    audit = build_alignment_audit(
        queue_payload=_queue_payload(),
        blocks_payload=json.loads(blocks_path.read_text(encoding="utf-8")),
        registry_payload=json.loads(registry_path.read_text(encoding="utf-8")),
        queue_path=queue_path,
        blocks_path=blocks_path,
        registry_path=registry_path,
        expected_blocks_total=3,
        expected_source_id="123__focus_source",
        scan_roots=[candidates_root],
        chroma_snapshot_path=chroma_path,
        source_prd="PRD-046.0.9.1-HF1",
    )

    assert audit["authoritative_candidates_found"] >= 1
    first = audit["authoritative_candidates"][0]
    assert first["blocks_total"] == 3
    assert first["queue_block_ids_present_count"] == 2
    assert first["queue_block_ids_missing_count"] == 0
    assert first["candidate_is_authoritative"] is True
