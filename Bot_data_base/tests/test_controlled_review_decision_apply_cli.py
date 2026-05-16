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


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _block(block_id: str, chunk_type: str = "theory") -> dict:
    return {
        "id": block_id,
        "source": "book:123__кузница_духа",
        "text": f"text-{block_id}",
        "metadata": {
            "source_id": "123__кузница_духа",
            "governance": {
                "chunk_type": chunk_type,
                "allowed_use": ["writer_context"],
                "safety_flags": ["not_for_direct_quote"],
            }
        },
    }


def _queue_item(rid: str, block_id: str, chunk_type: str = "theory") -> dict:
    return {
        "review_item_id": rid,
        "block_id": block_id,
        "source_id": "123__кузница_духа",
        "source_title": "Кузница Духа",
        "chunk_type": chunk_type,
        "review_priority": "P2",
        "review_reasons": ["needs_human_review"],
        "recommended_action": "defer",
        "safe_preview": f"preview-{block_id}",
        "advisory_summary_preview": f"summary-{block_id}",
    }


def _decision(rid: str, block_id: str, decision: str, approved: list[str] | None = None, edited: dict | None = None, reason: str = "") -> dict:
    return {
        "review_item_id": rid,
        "block_id": block_id,
        "decision": decision,
        "reviewer": "architect",
        "reason": reason,
        "approved_fields": approved or [],
        "rejected_fields": [],
        "edited_fields": edited or {},
        "created_at": "2026-05-16T00:00:00+00:00",
        "source_prd": "PRD-046.0.9.3",
    }


def _make_env(tmp_path: Path, with_run1: bool = True) -> dict[str, Path]:
    blocks_path = tmp_path / "all_blocks_merged.json"
    registry_path = tmp_path / "registry.json"
    queue_path = tmp_path / "review_queue_after_real_enrichment.json"
    decisions_primary = tmp_path / "architect_decisions_overlay.json"
    decisions_fallback = tmp_path / "architect_auto_decisions_overlay.json"
    logs_root = tmp_path / "logs"
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"

    _write_json(
        blocks_path,
        {
            "schema_version": "bot_data_base_v1.0",
            "blocks": [_block("b1", "theory"), _block("b2", "practice"), _block("b3", "quote"), _block("b4", "lens"), _block("b5", "style")],
        },
    )
    _write_json(
        registry_path,
        [{"source_id": "123__кузница_духа", "status": "done", "blocks_count": 5}],
    )
    _write_json(
        queue_path,
        {
            "schema_version": "post_reprocess_review_queue_after_real_enrichment_v1",
            "source_prd": "PRD-046.0.9-RUN1",
            "items": [
                _queue_item("rid-1", "b1"),
                _queue_item("rid-2", "b2", "practice"),
                _queue_item("rid-3", "b3", "quote"),
                _queue_item("rid-4", "b4"),
            ],
        },
    )
    overlay = {
        "schema_version": "kb_review_decisions_v1",
        "source_prd": "PRD-046.0.9.3",
        "source_review_queue_prd": "PRD-046.0.9-RUN1",
        "review_queue_hash": "hash",
        "blocks_hash_before": "hash",
        "decision_owner": "architect_auto_policy",
        "apply_ready": True,
        "decisions": [
            _decision("rid-1", "b1", "approved", approved=["summary", "tags"]),
            _decision(
                "rid-2",
                "b2",
                "needs_edit",
                edited={"summary": "edited-b2", "avoid_when": ["при дистрессе обратиться к специалисту"]},
                reason="edited",
            ),
            _decision("rid-3", "b3", "rejected", reason="not safe"),
            _decision("rid-4", "b4", "defer", reason="defer"),
        ],
    }
    _write_json(decisions_primary, overlay)
    _write_json(decisions_fallback, overlay)

    if with_run1:
        run1_dir = logs_root / "PRD-046.0.9-RUN1"
        _write_json(
            run1_dir / "real_enrichment_candidate_overlay.json",
            {
                "schema_version": "post_reprocess_llm_enrichment_overlay_v1",
                "source_prd": "PRD-046.0.9",
                "items": [
                    {"block_id": "b1", "advisory": {"summary": "run1-b1", "tags": ["a"]}, "quality": {"confidence": 0.8}},
                    {"block_id": "b2", "advisory": {"summary": "run1-b2", "tags": ["b"]}, "quality": {"confidence": 0.7}},
                    {"block_id": "b3", "advisory": {"summary": "run1-b3", "tags": ["c"]}, "quality": {"confidence": 0.6}},
                    {"block_id": "b4", "advisory": {"summary": "run1-b4", "tags": ["d"]}, "quality": {"confidence": 0.6}},
                    {"block_id": "b5", "advisory": {"summary": "run1-b5", "tags": ["e"]}, "quality": {"confidence": 0.9}},
                ],
            },
        )
        _write_json(
            run1_dir / "real_enrichment_validation.json",
            {
                "source_prd": "PRD-046.0.9-RUN1",
                "items_completed": 5,
                "validation_errors_count": 0,
            },
        )
    return {
        "blocks_path": blocks_path,
        "registry_path": registry_path,
        "queue_path": queue_path,
        "decisions_primary": decisions_primary,
        "decisions_fallback": decisions_fallback,
        "logs_root": logs_root,
        "out_dir": out_dir,
        "reports_dir": reports_dir,
    }


def test_preflight_fails_when_run1_source_missing(tmp_path: Path) -> None:
    env = _make_env(tmp_path, with_run1=False)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "preflight_review_decision_apply.py"),
        "--source-prd",
        "PRD-046.0.7.1",
        "--blocks",
        str(env["blocks_path"]),
        "--registry",
        str(env["registry_path"]),
        "--review-queue",
        str(env["queue_path"]),
        "--decisions-primary",
        str(env["decisions_primary"]),
        "--decisions-fallback",
        str(env["decisions_fallback"]),
        "--logs-root",
        str(env["logs_root"]),
        "--expected-blocks-total",
        "5",
        "--expected-review-items",
        "4",
        "--expected-decisions-count",
        "4",
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode == 3


def test_plan_cli_is_dry_run_and_does_not_mutate_blocks(tmp_path: Path) -> None:
    env = _make_env(tmp_path, with_run1=True)
    before_hash = _sha(env["blocks_path"])
    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "plan_review_decision_apply.py"),
        "--source-prd",
        "PRD-046.0.7.1",
        "--blocks",
        str(env["blocks_path"]),
        "--review-queue",
        str(env["queue_path"]),
        "--decisions-primary",
        str(env["decisions_primary"]),
        "--decisions-fallback",
        str(env["decisions_fallback"]),
        "--logs-root",
        str(env["logs_root"]),
        "--expected-blocks-total",
        "5",
        "--expected-review-items",
        "4",
        "--expected-decisions-count",
        "4",
        "--out",
        str(env["out_dir"] / "apply_plan.json"),
        "--out-md",
        str(env["reports_dir"] / "apply_plan.md"),
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert _sha(env["blocks_path"]) == before_hash


def test_apply_cli_creates_backups_and_result_counts(tmp_path: Path) -> None:
    env = _make_env(tmp_path, with_run1=True)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "Bot_data_base" / "tools" / "apply_review_decisions_controlled.py"),
        "--source-prd",
        "PRD-046.0.7.1",
        "--blocks",
        str(env["blocks_path"]),
        "--registry",
        str(env["registry_path"]),
        "--review-queue",
        str(env["queue_path"]),
        "--decisions-primary",
        str(env["decisions_primary"]),
        "--decisions-fallback",
        str(env["decisions_fallback"]),
        "--logs-root",
        str(env["logs_root"]),
        "--out-dir",
        str(env["out_dir"]),
        "--reports-dir",
        str(env["reports_dir"]),
        "--expected-blocks-total",
        "5",
        "--expected-review-items",
        "4",
        "--expected-decisions-count",
        "4",
        "--expected-review-approved-apply-candidates",
        "1",
        "--expected-review-needs-edit-apply-candidates",
        "1",
        "--expected-review-rejected-skip",
        "1",
        "--expected-review-defer-skip",
        "1",
    ]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr or completed.stdout

    assert (env["out_dir"] / "backups" / "all_blocks_merged.before_apply.json").exists()
    assert (env["out_dir"] / "backups" / "registry.before_apply.json").exists()

    apply_result = json.loads((env["out_dir"] / "apply_result.json").read_text(encoding="utf-8"))
    assert apply_result["status"] == "ok"
    assert apply_result["acceptance_snapshot"]["review_approved_apply_candidates"] == 1
    assert apply_result["acceptance_snapshot"]["review_needs_edit_apply_candidates"] == 1
    assert apply_result["acceptance_snapshot"]["review_rejected_skip"] == 1
    assert apply_result["acceptance_snapshot"]["review_defer_skip"] == 1
