from __future__ import annotations

import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _sample_blocks_payload() -> dict:
    return {
        "schema_version": "bot_data_base_v1.0",
        "blocks": [
            {
                "id": "b1",
                "source": "book:123__кузница_духа",
                "metadata": {
                    "source_id": "123__кузница_духа",
                    "governance": {
                        "chunk_type": "lens",
                        "allowed_use": ["writer_context"],
                        "safety_flags": ["not_for_direct_quote"],
                        "lens_family": ["self_reflection"],
                    },
                },
            },
            {
                "id": "b2",
                "source": "book:123__кузница_духа",
                "metadata": {
                    "source_id": "123__кузница_духа",
                    "governance": {
                        "chunk_type": "practice",
                        "allowed_use": ["writer_context"],
                        "safety_flags": [],
                        "lens_family": ["body_awareness"],
                    },
                },
            },
        ],
    }


def _sample_queue_payload() -> dict:
    return {
        "schema_version": "post_reprocess_review_queue_after_real_enrichment_v1",
        "source_prd": "PRD-046.0.9-RUN1",
        "generated_at": "2026-05-16T00:00:00+00:00",
        "items_count": 2,
        "priority_counts": {"P0": 0, "P1": 1, "P2": 1},
        "items": [
            {
                "review_item_id": "post_reprocess::b1",
                "block_id": "b1",
                "source_id": "123__кузница_духа",
                "source_title": "Кузница Духа",
                "chunk_type": "lens",
                "review_priority": "P1",
                "review_reasons": ["low_confidence"],
                "recommended_action": "needs_edit",
                "safe_preview": "preview one",
                "advisory_summary_preview": "summary one",
            },
            {
                "review_item_id": "post_reprocess::b2",
                "block_id": "b2",
                "source_id": "123__кузница_духа",
                "source_title": "Кузница Духа",
                "chunk_type": "practice",
                "review_priority": "P2",
                "review_reasons": ["needs_human_review"],
                "recommended_action": "defer",
                "safe_preview": "preview two",
                "advisory_summary_preview": "summary two",
            },
        ],
    }


def test_prepare_cli_creates_manifest_workbench_and_no_mutation_proof(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue_after_real_enrichment.json"
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma_admin_runtime_diagnostic.json"
    out_dir = tmp_path / "out"

    _write_json(queue_path, _sample_queue_payload())
    _write_json(blocks_path, _sample_blocks_payload())
    _write_json(registry_path, [{"source_id": "123__кузница_духа", "blocks_count": 2}])
    _write_json(chroma_path, {"dashboard_chroma_count": 2})

    blocks_before = _sha256(blocks_path)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "prepare_human_review_decisions.py"),
        "--review-queue",
        str(queue_path),
        "--blocks",
        str(blocks_path),
        "--source-prd",
        "PRD-046.0.9.1",
        "--expected-source-prd",
        "PRD-046.0.9-RUN1",
        "--out-dir",
        str(out_dir),
        "--registry",
        str(registry_path),
        "--chroma-snapshot",
        str(chroma_path),
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr or completed.stdout

    manifest_path = out_dir / "review_source_manifest.json"
    workbench_path = out_dir / "review_workbench.md"
    template_path = out_dir / "review_decisions_template.json"
    summary_path = out_dir / "review_decisions_summary.json"
    no_mutation_path = out_dir / "no_mutation_proof.json"

    assert manifest_path.exists()
    assert workbench_path.exists()
    assert template_path.exists()
    assert summary_path.exists()
    assert no_mutation_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["queue_items_count"] == 2
    assert manifest["source_review_queue_prd_match"] is True

    workbench_text = workbench_path.read_text(encoding="utf-8").lower()
    for forbidden in ("content_full", "raw_text", "full_text", "source_raw", "embedding", "vector"):
        assert forbidden not in workbench_text

    no_mutation = json.loads(no_mutation_path.read_text(encoding="utf-8"))
    assert no_mutation["all_blocks_merged_mutated"] is False
    assert no_mutation["all_blocks_merged_hash_before"] == blocks_before
    assert no_mutation["all_blocks_merged_hash_after"] == blocks_before


def test_prepare_require_aligned_fails_when_queue_ids_missing(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue_after_real_enrichment.json"
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma_admin_runtime_diagnostic.json"
    out_dir = tmp_path / "out"

    queue_payload = _sample_queue_payload()
    queue_payload["items"].append(
        {
            "review_item_id": "post_reprocess::b3",
            "block_id": "b3",
            "source_id": "123__кузница_духа",
            "source_title": "Кузница Духа",
            "chunk_type": "lens",
            "review_priority": "P2",
            "review_reasons": ["needs_human_review"],
            "recommended_action": "defer",
            "safe_preview": "preview three",
            "advisory_summary_preview": "summary three",
        }
    )
    _write_json(queue_path, queue_payload)
    _write_json(blocks_path, _sample_blocks_payload())
    _write_json(registry_path, [{"source_id": "123__кузница_духа", "blocks_count": 2}])
    _write_json(chroma_path, {"dashboard_chroma_count": 2})

    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "prepare_human_review_decisions.py"),
        "--review-queue",
        str(queue_path),
        "--blocks",
        str(blocks_path),
        "--out-dir",
        str(out_dir),
        "--registry",
        str(registry_path),
        "--chroma-snapshot",
        str(chroma_path),
        "--require-aligned",
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode != 0
    manifest = json.loads((out_dir / "review_source_manifest.json").read_text(encoding="utf-8"))
    assert manifest["queue_block_ids_missing_in_blocks_count"] == 1


def test_prepare_require_aligned_passes_when_queue_ids_present(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue_after_real_enrichment.json"
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma_admin_runtime_diagnostic.json"
    out_dir = tmp_path / "out"

    _write_json(queue_path, _sample_queue_payload())
    _write_json(blocks_path, _sample_blocks_payload())
    _write_json(registry_path, [{"source_id": "123__кузница_духа", "blocks_count": 2}])
    _write_json(chroma_path, {"dashboard_chroma_count": 2})

    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "prepare_human_review_decisions.py"),
        "--review-queue",
        str(queue_path),
        "--blocks",
        str(blocks_path),
        "--out-dir",
        str(out_dir),
        "--registry",
        str(registry_path),
        "--chroma-snapshot",
        str(chroma_path),
        "--require-aligned",
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr or completed.stdout
