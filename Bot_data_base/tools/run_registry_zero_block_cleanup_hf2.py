from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from storage.chroma_runtime_health import get_chroma_runtime_health


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _extract_rows(registry_payload: Any) -> tuple[list[dict[str, Any]], str]:
    if isinstance(registry_payload, list):
        return [row for row in registry_payload if isinstance(row, dict)], "list"
    if isinstance(registry_payload, dict):
        sources = registry_payload.get("sources")
        if isinstance(sources, list):
            return [row for row in sources if isinstance(row, dict)], "dict_sources"
    return [], "unknown"


def _extract_source_id_from_block(block: dict[str, Any]) -> str:
    source_raw = _normalize(block.get("source"))
    if ":" in source_raw:
        return _normalize(source_raw.split(":", 1)[1])
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    source_trace = governance.get("source_trace") if isinstance(governance.get("source_trace"), dict) else {}
    return _normalize(source_trace.get("source_id") or metadata.get("source_id"))


def _extract_all_blocks_source_ids(blocks_payload: Any) -> set[str]:
    blocks = blocks_payload.get("blocks") if isinstance(blocks_payload, dict) and isinstance(blocks_payload.get("blocks"), list) else []
    source_ids: set[str] = set()
    for block in blocks:
        if not isinstance(block, dict):
            continue
        source_id = _extract_source_id_from_block(block)
        if source_id:
            source_ids.add(source_id)
    return source_ids


def _is_test_or_archive_row(source_id: str, status: str) -> bool:
    sid = source_id.lower()
    return (
        status in {"failed", "archived"}
        or sid.startswith("test")
        or "archive" in sid
        or sid.startswith("tmp")
    )


@dataclass
class GateStatus:
    live_preflight_passed: bool
    query_recovery_passed: bool
    bot_runtime_retrieval_passed: bool
    chroma_consistency_passed: bool

    @property
    def cleanup_allowed(self) -> bool:
        return all(
            [
                self.live_preflight_passed,
                self.query_recovery_passed,
                self.bot_runtime_retrieval_passed,
                self.chroma_consistency_passed,
            ]
        )


def build_hygiene_audit_and_plan(
    *,
    registry_rows: list[dict[str, Any]],
    expected_source_id: str,
    all_blocks_source_ids: set[str],
    chroma_count_by_source: dict[str, int],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    focus_source_protected: list[dict[str, Any]] = []
    safe_delete_candidates: list[dict[str, Any]] = []
    blocked_delete_candidates: list[dict[str, Any]] = []
    safe_delete_source_ids: set[str] = set()

    for row in registry_rows:
        source_id = _normalize(row.get("source_id"))
        status = _normalize(row.get("status")).lower()
        blocks = _to_int(row.get("blocks_count"))
        chroma_records = _to_int(chroma_count_by_source.get(source_id))
        all_blocks_records = source_id in all_blocks_source_ids

        base = {
            "source_id": source_id,
            "status": status,
            "blocks_count": blocks,
            "chroma_records": chroma_records,
            "all_blocks_records": all_blocks_records,
        }

        if source_id == expected_source_id:
            focus_source_protected.append({**base, "action": "keep"})
            continue

        if blocks > 0:
            blocked_delete_candidates.append({**base, "reason": "non_zero_blocks"})
            continue

        test_archive = _is_test_or_archive_row(source_id, status)
        if test_archive and chroma_records == 0 and not all_blocks_records:
            safe_delete_candidates.append({**base, "reason": "zero_block_test_or_archive"})
            if source_id:
                safe_delete_source_ids.add(source_id)
        else:
            reasons = []
            if not test_archive:
                reasons.append("not_test_archive_marker")
            if chroma_records > 0:
                reasons.append("has_chroma_records")
            if all_blocks_records:
                reasons.append("has_all_blocks_records")
            blocked_delete_candidates.append({**base, "reason": ",".join(reasons) or "unsafe"})

    audit = {
        "schema_version": "zero_block_registry_hygiene_audit_hf2_v1",
        "generated_at": _utc_now_iso(),
        "focus_source_protected": focus_source_protected,
        "safe_delete_candidates": safe_delete_candidates,
        "blocked_delete_candidates": blocked_delete_candidates,
        "summary": {
            "focus_source_protected_count": len(focus_source_protected),
            "safe_delete_candidates_count": len(safe_delete_candidates),
            "blocked_delete_candidates_count": len(blocked_delete_candidates),
        },
    }

    plan = {
        "schema_version": "zero_block_cleanup_plan_hf2_v1",
        "generated_at": _utc_now_iso(),
        "zero_block_cleanup_plan_ready": True,
        "safe_delete_candidates_count": len(safe_delete_candidates),
        "safe_delete_source_ids": sorted(safe_delete_source_ids),
        "blocked_delete_source_ids": sorted({_normalize(item.get("source_id")) for item in blocked_delete_candidates if _normalize(item.get("source_id"))}),
        "focus_source_id": expected_source_id,
        "rules": {
            "focus_source_protected": True,
            "delete_only_zero_block_test_archive_rows": True,
            "require_no_chroma_records": True,
            "require_no_all_blocks_records": True,
        },
    }
    return audit, plan, sorted(safe_delete_source_ids)


def apply_zero_block_cleanup(
    *,
    registry_path: Path,
    registry_payload: Any,
    registry_format: str,
    safe_delete_source_ids: list[str],
    expected_source_id: str,
    backup_root: Path,
    chroma_manifest: dict[str, Any],
    gates: GateStatus,
    perform_cleanup: bool,
) -> dict[str, Any]:
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = _timestamp()
    registry_backup = backup_root / f"registry_before_zero_block_cleanup_{stamp}.json"
    chroma_backup = backup_root / f"chroma_manifest_before_cleanup_{stamp}.json"
    registry_backup.write_text(json.dumps(registry_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    chroma_backup.write_text(json.dumps(chroma_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result: dict[str, Any] = {
        "schema_version": "zero_block_cleanup_apply_result_hf2_v1",
        "generated_at": _utc_now_iso(),
        "backup_created": True,
        "registry_backup_path": str(registry_backup),
        "chroma_manifest_backup_path": str(chroma_backup),
        "cleanup_performed": False,
        "cleanup_reason": "operator_not_required",
        "removed_zero_block_sources_count": 0,
        "removed_source_ids": [],
        "registry_zero_block_test_archive_rows_removed": False,
        "focus_source_deleted": False,
        "focus_source_mutated": False,
        "all_blocks_merged_mutated": False,
        "kb_text_mutated": False,
        "kb_governance_mutated": False,
        "safety_gates": {
            "live_preflight_passed": gates.live_preflight_passed,
            "query_recovery_passed": gates.query_recovery_passed,
            "bot_runtime_retrieval_passed": gates.bot_runtime_retrieval_passed,
            "chroma_consistency_passed": gates.chroma_consistency_passed,
            "cleanup_allowed": gates.cleanup_allowed,
        },
    }

    if not safe_delete_source_ids:
        result["cleanup_reason"] = "no_safe_candidates"
        return result
    if not perform_cleanup:
        result["cleanup_reason"] = "operator_not_required"
        return result
    if not gates.cleanup_allowed:
        result["cleanup_reason"] = "blocked_by_safety_gates"
        return result

    if registry_format == "list":
        rows = [row for row in registry_payload if isinstance(row, dict)]
        mutable_payload: Any = rows
    elif registry_format == "dict_sources":
        rows = [row for row in (registry_payload.get("sources") or []) if isinstance(row, dict)]
        mutable_payload = dict(registry_payload)
    else:
        result["cleanup_reason"] = "unknown_registry_format"
        return result

    removed_ids: list[str] = []
    keep_rows: list[dict[str, Any]] = []
    safe_set = set(safe_delete_source_ids)
    for row in rows:
        source_id = _normalize(row.get("source_id"))
        blocks = _to_int(row.get("blocks_count"))
        status = _normalize(row.get("status")).lower()
        is_safe_row = source_id in safe_set and blocks <= 0 and _is_test_or_archive_row(source_id, status)
        if is_safe_row and source_id != expected_source_id:
            removed_ids.append(source_id)
            continue
        keep_rows.append(row)

    if registry_format == "list":
        mutable_payload = keep_rows
    else:
        mutable_payload["sources"] = keep_rows
    registry_path.write_text(json.dumps(mutable_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result["cleanup_performed"] = True
    result["cleanup_reason"] = "cleanup_applied"
    result["removed_source_ids"] = sorted(set(removed_ids))
    result["removed_zero_block_sources_count"] = len(removed_ids)
    result["registry_zero_block_test_archive_rows_removed"] = len(removed_ids) > 0
    return result


def run_cleanup(
    *,
    repo_root: Path,
    output_dir: Path,
    expected_source_id: str,
    perform_cleanup: bool,
    gates: GateStatus,
) -> dict[str, Any]:
    botdb_dir = repo_root / "Bot_data_base"
    config_path = botdb_dir / "config.yaml"
    registry_path = botdb_dir / "data" / "registry.json"
    blocks_path = botdb_dir / "data" / "processed" / "all_blocks_merged.json"
    backup_root = repo_root / "TO_DO_LIST" / "backups" / "PRD-046.1.21-HF2"

    registry_payload = _read_json(registry_path)
    blocks_payload = _read_json(blocks_path)
    registry_rows, registry_format = _extract_rows(registry_payload)
    all_blocks_source_ids = _extract_all_blocks_source_ids(blocks_payload)

    chroma_manifest = get_chroma_runtime_health(str(config_path))
    chroma_by_source = chroma_manifest.get("count_by_source_id") if isinstance(chroma_manifest.get("count_by_source_id"), dict) else {}
    audit, plan, safe_delete_source_ids = build_hygiene_audit_and_plan(
        registry_rows=registry_rows,
        expected_source_id=expected_source_id,
        all_blocks_source_ids=all_blocks_source_ids,
        chroma_count_by_source={_normalize(k): _to_int(v) for k, v in chroma_by_source.items()},
    )
    _write_json(output_dir / "zero_block_registry_hygiene_audit.json", audit)
    _write_json(output_dir / "zero_block_cleanup_plan.json", plan)

    apply_result = apply_zero_block_cleanup(
        registry_path=registry_path,
        registry_payload=registry_payload,
        registry_format=registry_format,
        safe_delete_source_ids=safe_delete_source_ids,
        expected_source_id=expected_source_id,
        backup_root=backup_root,
        chroma_manifest=chroma_manifest,
        gates=gates,
        perform_cleanup=perform_cleanup,
    )
    _write_json(output_dir / "zero_block_cleanup_apply_result.json", apply_result)
    return {
        "audit": audit,
        "plan": plan,
        "apply_result": apply_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="HF2 registry zero-block cleanup gate.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--perform-cleanup", action="store_true")
    parser.add_argument("--live-preflight-passed", action="store_true")
    parser.add_argument("--query-recovery-passed", action="store_true")
    parser.add_argument("--bot-runtime-retrieval-passed", action="store_true")
    parser.add_argument("--chroma-consistency-passed", action="store_true")
    args = parser.parse_args()

    gates = GateStatus(
        live_preflight_passed=bool(args.live_preflight_passed),
        query_recovery_passed=bool(args.query_recovery_passed),
        bot_runtime_retrieval_passed=bool(args.bot_runtime_retrieval_passed),
        chroma_consistency_passed=bool(args.chroma_consistency_passed),
    )
    payload = run_cleanup(
        repo_root=Path(args.repo_root).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        expected_source_id=str(args.expected_source_id),
        perform_cleanup=bool(args.perform_cleanup),
        gates=gates,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
