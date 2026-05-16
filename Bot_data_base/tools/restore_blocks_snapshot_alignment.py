from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from review.blocks_snapshot_alignment import (
    build_alignment_audit,
    choose_authoritative_candidate,
    load_blocks_payload_from_candidate,
    read_json,
    sanitize_runtime_log_lines,
    sha256_file,
    update_registry_focus_blocks,
    write_json,
    write_text,
)


def _build_restore_plan(
    *,
    audit_payload: dict,
    source_prd: str,
    blocks_path: Path,
    registry_path: Path,
    out_dir: Path,
) -> dict:
    candidate = choose_authoritative_candidate(audit_payload)
    backups_dir = out_dir / "backups"
    return {
        "schema_version": "blocks_snapshot_alignment_restore_plan_v1",
        "source_prd": source_prd,
        "generated_at": audit_payload.get("generated_at"),
        "audit_status": audit_payload.get("status"),
        "authoritative_candidate": candidate,
        "apply_allowed": candidate is not None,
        "blocks_path": blocks_path.as_posix(),
        "registry_path": registry_path.as_posix(),
        "backup_paths": {
            "all_blocks_before_restore": (backups_dir / "all_blocks_merged.before_restore.json").as_posix(),
            "registry_before_restore": (backups_dir / "registry.before_restore.json").as_posix(),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore blocks snapshot alignment from authoritative candidate.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")

    parser.add_argument(
        "--audit-json",
        default="TO_DO_LIST/logs/PRD-046.0.9.1-HF1/blocks_alignment_audit.json",
    )
    parser.add_argument(
        "--review-queue",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json",
    )
    parser.add_argument("--blocks", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--registry", default="Bot_data_base/data/registry.json")
    parser.add_argument(
        "--chroma-snapshot",
        default="TO_DO_LIST/logs/PRD-046.0.9-RUN1-HF3/chroma_admin_runtime_diagnostic.json",
    )
    parser.add_argument("--expected-blocks-total", type=int, default=247)
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--source-prd", default="PRD-046.0.9.1-HF1")
    parser.add_argument("--out-dir", default="TO_DO_LIST/logs/PRD-046.0.9.1-HF1")
    parser.add_argument(
        "--scan-root",
        action="append",
        default=[
            "TO_DO_LIST/logs/PRD-046.0.8.1",
            "TO_DO_LIST/logs/PRD-046.0.9",
            "TO_DO_LIST/logs/PRD-046.0.9-RUN1",
            "Bot_data_base/data/backups",
            "Bot_data_base/data/processed/backups",
        ],
    )
    args = parser.parse_args()

    if not args.apply:
        args.dry_run = True

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    audit_json_path = Path(args.audit_json)
    blocks_path = Path(args.blocks)
    registry_path = Path(args.registry)
    queue_path = Path(args.review_queue)
    chroma_snapshot_path = Path(args.chroma_snapshot)

    if audit_json_path.exists():
        audit_payload = read_json(audit_json_path)
    else:
        if not queue_path.exists() or not blocks_path.exists() or not registry_path.exists():
            raise FileNotFoundError("missing_inputs_for_restore")
        audit_payload = build_alignment_audit(
            queue_payload=read_json(queue_path),
            blocks_payload=read_json(blocks_path),
            registry_payload=read_json(registry_path),
            queue_path=queue_path,
            blocks_path=blocks_path,
            registry_path=registry_path,
            expected_blocks_total=max(1, int(args.expected_blocks_total)),
            expected_source_id=str(args.expected_source_id),
            scan_roots=[Path(item) for item in (args.scan_root or [])],
            chroma_snapshot_path=chroma_snapshot_path,
            source_prd=str(args.source_prd),
        )
        write_json(audit_json_path, audit_payload)

    plan = _build_restore_plan(
        audit_payload=audit_payload,
        source_prd=str(args.source_prd),
        blocks_path=blocks_path,
        registry_path=registry_path,
        out_dir=out_dir,
    )
    write_json(out_dir / "restore_plan.json", plan)

    candidate = plan.get("authoritative_candidate") if isinstance(plan.get("authoritative_candidate"), dict) else None

    blocks_hash_before = sha256_file(blocks_path) if blocks_path.exists() else ""
    registry_hash_before = sha256_file(registry_path) if registry_path.exists() else ""

    result = {
        "schema_version": "blocks_snapshot_alignment_restore_result_v1",
        "source_prd": args.source_prd,
        "mode": "apply" if args.apply else "dry_run",
        "status": "dry_run_no_mutation",
        "apply_performed": False,
        "candidate_selected": candidate,
        "blocks_hash_before": blocks_hash_before,
        "registry_hash_before": registry_hash_before,
        "blocks_hash_after": blocks_hash_before,
        "registry_hash_after": registry_hash_before,
        "blocks_mutated": False,
        "registry_mutated": False,
        "production_apply_performed": False,
        "chroma_reindex_performed": False,
    }

    if args.apply and candidate is None:
        result["status"] = "blocked_no_authoritative_snapshot_found"
        write_json(out_dir / "restore_result.json", result)
        write_json(out_dir / "no_mutation_or_restore_proof.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    if args.apply and candidate is not None:
        candidate_path = Path(str(candidate.get("path") or ""))
        if not candidate_path.exists():
            result["status"] = "blocked_candidate_path_missing"
            write_json(out_dir / "restore_result.json", result)
            write_json(out_dir / "no_mutation_or_restore_proof.json", result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2

        backups_dir = out_dir / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        backup_blocks = backups_dir / "all_blocks_merged.before_restore.json"
        backup_registry = backups_dir / "registry.before_restore.json"

        shutil.copy2(blocks_path, backup_blocks)
        shutil.copy2(registry_path, backup_registry)

        restored_payload = load_blocks_payload_from_candidate(candidate_path)
        write_json(blocks_path, restored_payload)

        registry_payload = read_json(registry_path)
        registry_updated, registry_changed = update_registry_focus_blocks(
            registry_payload=registry_payload,
            expected_source_id=str(args.expected_source_id),
            blocks_count=int(restored_payload.get("blocks_count") or 0),
        )
        write_json(registry_path, registry_updated)

        blocks_hash_after = sha256_file(blocks_path)
        registry_hash_after = sha256_file(registry_path)

        post_audit = build_alignment_audit(
            queue_payload=read_json(queue_path),
            blocks_payload=read_json(blocks_path),
            registry_payload=read_json(registry_path),
            queue_path=queue_path,
            blocks_path=blocks_path,
            registry_path=registry_path,
            expected_blocks_total=max(1, int(args.expected_blocks_total)),
            expected_source_id=str(args.expected_source_id),
            scan_roots=[Path(item) for item in (args.scan_root or [])],
            chroma_snapshot_path=chroma_snapshot_path,
            source_prd=str(args.source_prd),
        )

        result.update(
            {
                "status": "restored",
                "apply_performed": True,
                "blocks_hash_after": blocks_hash_after,
                "registry_hash_after": registry_hash_after,
                "blocks_mutated": blocks_hash_before != blocks_hash_after,
                "registry_mutated": registry_hash_before != registry_hash_after,
                "registry_focus_row_updated": bool(registry_changed),
                "post_restore_audit": {
                    "status": post_audit.get("status"),
                    "blocks_total": post_audit.get("blocks_total"),
                    "queue_items_count": post_audit.get("queue_items_count"),
                    "queue_block_ids_present_count": post_audit.get("queue_block_ids_present_count"),
                    "queue_block_ids_missing_count": post_audit.get("queue_block_ids_missing_count"),
                    "registry_focus_blocks": post_audit.get("registry_focus_blocks"),
                    "chroma_count": post_audit.get("chroma_count"),
                },
            }
        )

    write_json(out_dir / "restore_result.json", result)
    write_json(out_dir / "no_mutation_or_restore_proof.json", result)

    runtime_lines = sanitize_runtime_log_lines(
        [
            f"source_prd={args.source_prd}",
            f"mode={'apply' if args.apply else 'dry_run'}",
            f"status={result.get('status')}",
            f"apply_performed={result.get('apply_performed')}",
            f"blocks_mutated={result.get('blocks_mutated')}",
            f"registry_mutated={result.get('registry_mutated')}",
            f"chroma_reindex_performed={result.get('chroma_reindex_performed')}",
        ]
    )
    write_text(out_dir / "sanitized_runtime_logs.txt", "\n".join(runtime_lines) + "\n")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"dry_run_no_mutation", "restored"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
