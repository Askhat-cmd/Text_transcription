from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sample_queue_payload() -> dict:
    return {
        "schema_version": "post_reprocess_review_queue_after_real_enrichment_v1",
        "source_prd": "PRD-046.0.9-RUN1",
        "items": [
            {
                "review_item_id": "post_reprocess::b1",
                "block_id": "b1",
                "source_id": "123__кузница_духа",
                "source_title": "Кузница Духа",
                "chunk_type": "practice",
                "review_priority": "P2",
                "review_reasons": ["needs_human_review"],
                "recommended_action": "defer",
                "safe_preview": "preview practice",
                "advisory_summary_preview": "summary practice",
            },
            {
                "review_item_id": "post_reprocess::b2",
                "block_id": "b2",
                "source_id": "123__кузница_духа",
                "source_title": "Кузница Духа",
                "chunk_type": "quote",
                "review_priority": "P2",
                "review_reasons": ["needs_human_review"],
                "recommended_action": "defer",
                "safe_preview": "preview quote",
                "advisory_summary_preview": "summary quote",
            },
            {
                "review_item_id": "post_reprocess::b3",
                "block_id": "b3",
                "source_id": "123__кузница_духа",
                "source_title": "Кузница Духа",
                "chunk_type": "lens",
                "review_priority": "P2",
                "review_reasons": ["needs_human_review"],
                "recommended_action": "defer",
                "safe_preview": "preview lens",
                "advisory_summary_preview": "summary lens",
            },
            {
                "review_item_id": "post_reprocess::b4",
                "block_id": "b4",
                "source_id": "123__кузница_духа",
                "source_title": "Кузница Духа",
                "chunk_type": "theory",
                "review_priority": "P2",
                "review_reasons": ["needs_human_review"],
                "recommended_action": "defer",
                "safe_preview": "preview theory",
                "advisory_summary_preview": "summary theory",
            },
        ],
    }


def _sample_blocks_payload() -> dict:
    return {
        "schema_version": "bot_data_base_v1.0",
        "blocks": [
            {
                "id": "b1",
                "source": "book:123__кузница_духа",
                "metadata": {
                    "source_id": "123__кузница_духа",
                    "heading_path": ["H1"],
                    "governance": {
                        "chunk_type": "practice",
                        "allowed_use": ["writer_context", "practice_suggestion"],
                        "safety_flags": ["practice_requires_low_resource_check"],
                        "lens_family": ["somatic"],
                    },
                    "llm_enrichment": {"summary": "Сделай практику сразу и строго."},
                },
            },
            {
                "id": "b2",
                "source": "book:123__кузница_духа",
                "metadata": {
                    "source_id": "123__кузница_духа",
                    "heading_path": ["H2"],
                    "governance": {
                        "chunk_type": "quote",
                        "allowed_use": ["writer_context"],
                        "safety_flags": ["not_for_direct_quote"],
                        "lens_family": ["self_reflection"],
                    },
                    "llm_enrichment": {"summary": "Нейтральный пересказ без цитаты."},
                },
            },
            {
                "id": "b3",
                "source": "book:123__кузница_духа",
                "metadata": {
                    "source_id": "123__кузница_духа",
                    "heading_path": ["H3"],
                    "governance": {
                        "chunk_type": "lens",
                        "allowed_use": ["writer_context"],
                        "safety_flags": ["not_for_direct_quote"],
                        "lens_family": ["self_reflection"],
                    },
                    "llm_enrichment": {"summary": "Нейтральная внутренняя линза для бережной саморефлексии."},
                },
            },
            {
                "id": "b4",
                "source": "book:123__кузница_духа",
                "metadata": {
                    "source_id": "123__кузница_духа",
                    "heading_path": ["H4"],
                    "governance": {
                        "chunk_type": "theory",
                        "allowed_use": ["writer_context"],
                        "safety_flags": ["not_for_direct_quote"],
                        "lens_family": ["theory"],
                    },
                    "llm_enrichment": {"summary": "Может быть использовано для обогащения консультирования."},
                },
            },
        ],
    }


def test_generate_architect_auto_decisions_cli_full_coverage(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue_after_real_enrichment.json"
    blocks_path = tmp_path / "all_blocks_merged.json"
    batches_index_path = tmp_path / "architect_review_batches_index.json"
    base_overlay_path = tmp_path / "architect_decisions_overlay.json"
    official_overlay_path = tmp_path / "official_architect_decisions_overlay.json"
    registry_path = tmp_path / "registry.json"
    chroma_path = tmp_path / "chroma_admin_runtime_diagnostic.json"
    out_dir = tmp_path / "out"
    auto_md = tmp_path / "auto.md"
    validation_md = tmp_path / "validation.md"

    _write_json(queue_path, _sample_queue_payload())
    _write_json(blocks_path, _sample_blocks_payload())
    _write_json(
        batches_index_path,
        {
            "schema_version": "architect_review_batches_index_v1",
            "source_prd": "PRD-046.0.9.2",
            "queue_source_prd": "PRD-046.0.9-RUN1",
            "queue_items_count": 4,
            "batch_size_requested": 2,
            "batches_count": 2,
            "batches": [],
            "forbidden_batch_keys_detected": [],
            "sanitized": True,
        },
    )
    _write_json(
        base_overlay_path,
        {
            "schema_version": "kb_review_decisions_v1",
            "source_prd": "PRD-046.0.9.2",
            "source_review_queue_prd": "PRD-046.0.9-RUN1",
            "review_queue_hash": "hash",
            "blocks_hash_before": "hash",
            "decision_owner": "architect_chatgpt",
            "ready_for_architect_review": True,
            "apply_ready": False,
            "decisions": [],
        },
    )
    _write_json(registry_path, [{"source_id": "123__кузница_духа", "blocks_count": 4}])
    _write_json(chroma_path, {"dashboard_chroma_count": 4})

    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "generate_architect_auto_decisions.py"),
        "--review-queue",
        str(queue_path),
        "--blocks",
        str(blocks_path),
        "--batches-index",
        str(batches_index_path),
        "--base-overlay",
        str(base_overlay_path),
        "--expected-queue-count",
        "4",
        "--out-dir",
        str(out_dir),
        "--official-overlay",
        str(official_overlay_path),
        "--out-md-auto",
        str(auto_md),
        "--out-md-validation",
        str(validation_md),
        "--registry",
        str(registry_path),
        "--chroma-snapshot",
        str(chroma_path),
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr or completed.stdout

    overlay_payload = json.loads((out_dir / "architect_auto_decisions_overlay.json").read_text(encoding="utf-8"))
    validation_payload = json.loads((out_dir / "architect_auto_decisions_validation.json").read_text(encoding="utf-8"))
    policy_payload = json.loads((out_dir / "architect_auto_decisions_policy_report.json").read_text(encoding="utf-8"))
    no_mutation = json.loads((out_dir / "no_mutation_proof.json").read_text(encoding="utf-8"))

    assert len(overlay_payload["decisions"]) == 4
    assert validation_payload["valid"] is True
    assert validation_payload["apply_ready"] is True
    assert validation_payload["coverage"]["coverage_percent"] == 100.0
    assert validation_payload["coverage"]["remaining_items_count"] == 0

    assert policy_payload["items_total"] == 4
    assert policy_payload["official_overlay_updated"] is True

    assert official_overlay_path.exists()
    official_payload = json.loads(official_overlay_path.read_text(encoding="utf-8"))
    assert len(official_payload["decisions"]) == 4

    assert no_mutation["all_blocks_merged_mutated"] is False
    assert no_mutation["registry_mutated"] is False
    assert no_mutation["chroma_mutated"] is False
    assert auto_md.exists()
    assert validation_md.exists()
