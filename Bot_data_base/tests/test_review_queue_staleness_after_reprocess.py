from __future__ import annotations

from pathlib import Path

from tools.controlled_candidate_apply import build_review_queue_staleness_report


def test_review_queue_marked_stale_when_input_hash_changed(tmp_path: Path) -> None:
    old_payload = {
        "input_file_sha256_before": "old_hash",
        "review_items_count": 12,
    }
    report = build_review_queue_staleness_report(
        old_review_queue_payload=old_payload,
        old_review_queue_path=tmp_path / "review_queue.json",
        old_all_blocks_sha="old_hash",
        new_all_blocks_sha="new_hash",
        candidate_blocks_count=247,
    )
    assert report["stale"] is True
    assert report["action"] == "rebuild_new_review_queue_baseline"


def test_review_queue_not_stale_when_hash_matches(tmp_path: Path) -> None:
    old_payload = {
        "input_file_sha256_before": "same_hash",
        "review_items_count": 5,
    }
    report = build_review_queue_staleness_report(
        old_review_queue_payload=old_payload,
        old_review_queue_path=tmp_path / "review_queue.json",
        old_all_blocks_sha="same_hash",
        new_all_blocks_sha="same_hash",
        candidate_blocks_count=247,
    )
    assert report["stale"] is False
