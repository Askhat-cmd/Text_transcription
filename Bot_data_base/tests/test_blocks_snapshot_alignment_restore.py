from __future__ import annotations

import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

from review.blocks_snapshot_alignment import build_alignment_audit, write_json


REPO_ROOT = Path(__file__).resolve().parents[2]


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


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


def test_restore_dry_run_does_not_mutate_files(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue.json"
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma.json"
    out_dir = tmp_path / "out"

    write_json(queue_path, _queue_payload())
    write_json(blocks_path, {"schema_version": "bot_data_base_v1.0", "blocks": [_block("x1"), _block("x2")]})
    write_json(registry_path, [{"source_id": "123__focus_source", "blocks_count": 2, "status": "done"}])
    write_json(chroma_path, {"dashboard_chroma_count": 3})

    audit_payload = build_alignment_audit(
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
    audit_path = tmp_path / "audit.json"
    write_json(audit_path, audit_payload)

    before_blocks = _sha(blocks_path)
    before_registry = _sha(registry_path)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "restore_blocks_snapshot_alignment.py"),
        "--dry-run",
        "--audit-json",
        str(audit_path),
        "--review-queue",
        str(queue_path),
        "--blocks",
        str(blocks_path),
        "--registry",
        str(registry_path),
        "--chroma-snapshot",
        str(chroma_path),
        "--expected-blocks-total",
        "3",
        "--expected-source-id",
        "123__focus_source",
        "--out-dir",
        str(out_dir),
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert _sha(blocks_path) == before_blocks
    assert _sha(registry_path) == before_registry


def test_restore_apply_requires_authoritative_candidate(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue.json"
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma.json"
    out_dir = tmp_path / "out"

    write_json(queue_path, _queue_payload())
    write_json(blocks_path, {"schema_version": "bot_data_base_v1.0", "blocks": [_block("x1"), _block("x2")]})
    write_json(registry_path, [{"source_id": "123__focus_source", "blocks_count": 2, "status": "done"}])
    write_json(chroma_path, {"dashboard_chroma_count": 3})

    audit_payload = {
        "schema_version": "blocks_snapshot_alignment_audit_v1",
        "source_prd": "PRD-046.0.9.1-HF1",
        "status": "not_aligned",
        "candidate_snapshots": [],
    }
    audit_path = tmp_path / "audit.json"
    write_json(audit_path, audit_payload)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "restore_blocks_snapshot_alignment.py"),
        "--apply",
        "--audit-json",
        str(audit_path),
        "--review-queue",
        str(queue_path),
        "--blocks",
        str(blocks_path),
        "--registry",
        str(registry_path),
        "--chroma-snapshot",
        str(chroma_path),
        "--expected-blocks-total",
        "3",
        "--expected-source-id",
        "123__focus_source",
        "--out-dir",
        str(out_dir),
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode != 0


def test_restore_apply_creates_backups_and_restores_alignment(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue.json"
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma.json"
    out_dir = tmp_path / "out"
    candidates_root = tmp_path / "candidates"
    candidate_path = candidates_root / "candidate_to_apply.snapshot.json"

    write_json(queue_path, _queue_payload())
    write_json(blocks_path, {"schema_version": "bot_data_base_v1.0", "blocks": [_block("x1"), _block("x2")]})
    write_json(registry_path, [{"source_id": "123__focus_source", "blocks_count": 2, "status": "done"}])
    write_json(chroma_path, {"dashboard_chroma_count": 3})
    write_json(
        candidate_path,
        {
            "schema_version": "candidate_snapshot_v1",
            "candidate": {"blocks_count": 3, "blocks": [_block("b1"), _block("b2"), _block("b3")]},
        },
    )

    audit_payload = build_alignment_audit(
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
    audit_path = tmp_path / "audit.json"
    write_json(audit_path, audit_payload)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "restore_blocks_snapshot_alignment.py"),
        "--apply",
        "--audit-json",
        str(audit_path),
        "--review-queue",
        str(queue_path),
        "--blocks",
        str(blocks_path),
        "--registry",
        str(registry_path),
        "--chroma-snapshot",
        str(chroma_path),
        "--expected-blocks-total",
        "3",
        "--expected-source-id",
        "123__focus_source",
        "--out-dir",
        str(out_dir),
        "--scan-root",
        str(candidates_root),
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr or completed.stdout

    assert (out_dir / "backups" / "all_blocks_merged.before_restore.json").exists()
    assert (out_dir / "backups" / "registry.before_restore.json").exists()

    restored = json.loads(blocks_path.read_text(encoding="utf-8"))
    assert len(restored["blocks"]) == 3
    restored_ids = {row.get("id") for row in restored["blocks"]}
    assert {"b1", "b2"}.issubset(restored_ids)

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert int(registry[0]["blocks_count"]) == 3
