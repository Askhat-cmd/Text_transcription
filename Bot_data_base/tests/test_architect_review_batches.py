from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sample_blocks_payload() -> dict:
    return {
        "schema_version": "bot_data_base_v1.0",
        "blocks": [
            {
                "id": "b1",
                "source": "book:123__кузница_духа",
                "metadata": {
                    "source_id": "123__кузница_духа",
                    "heading_path": ["A", "B"],
                    "governance": {
                        "chunk_type": "lens",
                        "allowed_use": ["writer_context"],
                        "safety_flags": ["not_for_direct_quote"],
                        "lens_family": ["self_reflection"],
                    },
                    "llm_enrichment": {
                        "summary": "summary one",
                        "tags": ["tag1"],
                        "lens_family_candidates": ["self_reflection"],
                        "use_when": ["when overwhelmed"],
                        "avoid_when": ["when panic"],
                        "self_contained_score": 0.8,
                        "self_contained_reason": "reason one",
                        "confidence": 0.9,
                    },
                },
            },
            {
                "id": "b2",
                "source": "book:123__кузница_духа",
                "metadata": {
                    "source_id": "123__кузница_духа",
                    "heading_path": ["C"],
                    "governance": {
                        "chunk_type": "practice",
                        "allowed_use": ["writer_context"],
                        "safety_flags": [],
                        "lens_family": ["body_awareness"],
                    },
                    "llm_enrichment": {
                        "summary": "summary two",
                        "tags": ["tag2"],
                        "lens_family_candidates": ["body_awareness"],
                        "use_when": ["when stable"],
                        "avoid_when": ["when low resource"],
                        "self_contained_score": 0.7,
                        "self_contained_reason": "reason two",
                        "confidence": 0.88,
                    },
                },
            },
            {
                "id": "b3",
                "source": "book:123__кузница_духа",
                "metadata": {
                    "source_id": "123__кузница_духа",
                    "heading_path": ["D"],
                    "governance": {
                        "chunk_type": "safety",
                        "allowed_use": ["writer_context"],
                        "safety_flags": ["low_resource_first"],
                        "lens_family": ["safety"],
                    },
                    "llm_enrichment": {
                        "summary": "summary three",
                        "tags": ["tag3"],
                        "lens_family_candidates": ["safety"],
                        "use_when": ["when tired"],
                        "avoid_when": ["when dysregulated"],
                        "self_contained_score": 0.75,
                        "self_contained_reason": "reason three",
                        "confidence": 0.87,
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
        "items_count": 3,
        "priority_counts": {"P0": 0, "P1": 1, "P2": 2},
        "items": [
            {
                "review_item_id": "post_reprocess::b1",
                "block_id": "b1",
                "source_id": "123__кузница_духа",
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
                "chunk_type": "practice",
                "review_priority": "P2",
                "review_reasons": ["needs_human_review"],
                "recommended_action": "defer",
                "safe_preview": "preview two",
                "advisory_summary_preview": "summary two",
            },
            {
                "review_item_id": "post_reprocess::b3",
                "block_id": "b3",
                "source_id": "123__кузница_духа",
                "chunk_type": "safety",
                "review_priority": "P2",
                "review_reasons": ["needs_human_review"],
                "recommended_action": "approved",
                "safe_preview": "preview three",
                "advisory_summary_preview": "summary three",
            },
        ],
    }


def test_prepare_architect_batches_cli_creates_expected_artifacts(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue_after_real_enrichment.json"
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma_admin_runtime_diagnostic.json"
    out_dir = tmp_path / "out"
    out_md = tmp_path / "report.md"

    _write_json(queue_path, _sample_queue_payload())
    _write_json(blocks_path, _sample_blocks_payload())
    _write_json(registry_path, [{"source_id": "123__кузница_духа", "blocks_count": 3}])
    _write_json(chroma_path, {"dashboard_chroma_count": 3})

    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "prepare_architect_review_batches.py"),
        "--review-queue",
        str(queue_path),
        "--blocks",
        str(blocks_path),
        "--source-prd",
        "PRD-046.0.9.2",
        "--expected-source-prd",
        "PRD-046.0.9-RUN1",
        "--expected-queue-count",
        "3",
        "--batch-size",
        "2",
        "--out-dir",
        str(out_dir),
        "--out-md",
        str(out_md),
        "--registry",
        str(registry_path),
        "--chroma-snapshot",
        str(chroma_path),
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr or completed.stdout

    index_path = out_dir / "architect_review_batches_index.json"
    template_path = out_dir / "architect_decisions_template.json"
    overlay_path = out_dir / "architect_decisions_overlay.json"
    no_mutation_path = out_dir / "no_mutation_proof.json"
    logs_path = out_dir / "sanitized_runtime_logs.txt"
    batch_1 = out_dir / "batches" / "review_batch_01.md"
    batch_2 = out_dir / "batches" / "review_batch_02.md"

    assert index_path.exists()
    assert template_path.exists()
    assert overlay_path.exists()
    assert no_mutation_path.exists()
    assert logs_path.exists()
    assert batch_1.exists()
    assert batch_2.exists()
    assert out_md.exists()

    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert index_payload["queue_items_count"] == 3
    assert index_payload["batches_count"] == 2
    assert index_payload["sanitized"] is True

    template_payload = json.loads(template_path.read_text(encoding="utf-8"))
    assert template_payload["decision_owner"] == "architect_chatgpt"
    assert template_payload["ready_for_architect_review"] is True
    assert template_payload["apply_ready"] is False

    batch_text = batch_1.read_text(encoding="utf-8").lower()
    assert "full_text:" not in batch_text
    assert "raw_text:" not in batch_text
    assert "embedding:" not in batch_text
    assert "vector:" not in batch_text

    no_mutation = json.loads(no_mutation_path.read_text(encoding="utf-8"))
    assert no_mutation["all_blocks_merged_mutated"] is False
    assert no_mutation["production_apply_performed"] is False


def test_prepare_architect_batches_fails_on_queue_count_mismatch(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue_after_real_enrichment.json"
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma_admin_runtime_diagnostic.json"
    out_dir = tmp_path / "out"

    _write_json(queue_path, _sample_queue_payload())
    _write_json(blocks_path, _sample_blocks_payload())
    _write_json(registry_path, [{"source_id": "123__кузница_духа", "blocks_count": 3}])
    _write_json(chroma_path, {"dashboard_chroma_count": 3})

    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "prepare_architect_review_batches.py"),
        "--review-queue",
        str(queue_path),
        "--blocks",
        str(blocks_path),
        "--expected-queue-count",
        "99",
        "--out-dir",
        str(out_dir),
        "--registry",
        str(registry_path),
        "--chroma-snapshot",
        str(chroma_path),
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode != 0
