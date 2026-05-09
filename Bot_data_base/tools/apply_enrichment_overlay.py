from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from tools.kb_quality_audit import evaluate_governed_index_gate, load_processed_blocks

RUN_TAG = "PRD-046.0.5-APPLY1"
SOURCE_OVERLAY_TAG = "PRD-046.0.5-RUN1-HF3"
DEFAULT_BLOCKS_PATH = Path("Bot_data_base/data/processed/all_blocks_merged.json")
DEFAULT_OVERLAY_PATH = Path("TO_DO_LIST/logs/PRD-046.0.5-RUN1-HF3/real_enrichment_candidates.jsonl")
DEFAULT_READINESS_PATH = Path("TO_DO_LIST/logs/PRD-046.0.5-RUN1-HF3/real_overlay_readiness_report.json")
DEFAULT_OUTPUT_DIR = Path(f"TO_DO_LIST/logs/{RUN_TAG}")
DEFAULT_BACKUP_DIR = DEFAULT_OUTPUT_DIR / "backups"
FORBIDDEN_LEAK_KEYS = {"content_full", "raw_full_text", "raw_text", "raw_llm_prompt_with_text"}
IMMUTABLE_GOVERNANCE_FIELDS = {
    "text",
    "governance.chunk_type",
    "governance.allowed_use",
    "governance.safety_flags",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _safe_preview(text: str, limit: int = 160) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_overlay_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        payload = json.loads(raw)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _parse_blocks_container(path: Path) -> tuple[list[dict[str, Any]], Any, bool]:
    raw = _load_json(path)
    if isinstance(raw, dict):
        blocks = raw.get("blocks")
        return (blocks if isinstance(blocks, list) else [], raw, True)
    if isinstance(raw, list):
        return raw, raw, False
    return [], raw, False


def _serialize_blocks_container(original_container: Any, blocks: list[dict[str, Any]], wrapped: bool) -> str:
    if wrapped and isinstance(original_container, dict):
        out = dict(original_container)
        out["blocks"] = blocks
        out["blocks_count"] = len(blocks)
        return json.dumps(out, ensure_ascii=False, indent=2)
    return json.dumps(blocks, ensure_ascii=False, indent=2)


def _validate_readiness(path: Path) -> tuple[bool, list[str], dict[str, Any]]:
    reasons: list[str] = []
    if not path.exists():
        return False, ["readiness_report_missing"], {}
    report = _load_json(path)
    expected_pairs = {
        "run_kind": "real",
        "validation_failed": 0,
        "hard_validation_failed": 0,
        "unknown_lens_candidates": 0,
        "summary_direct_quote_risk_count": 0,
        "safety_governance_invariant_violations": 0,
        "raw_text_leak_check": "pass",
        "production_candidate_ready": True,
        "promotion_allowed": False,
    }
    for key, expected in expected_pairs.items():
        if report.get(key) != expected:
            reasons.append(f"readiness_{key}_unexpected")
    promotion_reasons = report.get("promotion_reasons") or []
    if "requires_separate_apply_prd" not in promotion_reasons:
        reasons.append("readiness_requires_separate_apply_prd_missing")
    return (len(reasons) == 0), reasons, report


def build_preflight_gate(
    *,
    readiness_path: Path,
    overlay_path: Path,
    blocks_path: Path,
) -> dict[str, Any]:
    reasons: list[str] = []
    readiness_ok, readiness_reasons, readiness_report = _validate_readiness(readiness_path)
    if not readiness_ok:
        reasons.extend(readiness_reasons)
    if not overlay_path.exists():
        reasons.append("overlay_candidates_missing")
    if not blocks_path.exists():
        reasons.append("blocks_path_missing")

    blocks = load_processed_blocks(blocks_path) if blocks_path.exists() else []
    gate = evaluate_governed_index_gate(blocks=blocks, source_label="КУЗНИЦА ДУХА")
    gate_ready = str(gate.get("status") or "") == "ready"
    if not gate_ready:
        reasons.append(f"governed_gate_status_{gate.get('status')}")

    preflight_passed = len(reasons) == 0
    return {
        "generated_at": _utc_now(),
        "run_tag": RUN_TAG,
        "preflight_passed": preflight_passed,
        "reasons": reasons,
        "paths": {
            "readiness_path": str(readiness_path),
            "overlay_path": str(overlay_path),
            "blocks_path": str(blocks_path),
        },
        "readiness_report": readiness_report,
        "governed_gate": {
            "status": gate.get("status"),
            "blocker_reasons": gate.get("blocker_reasons") or [],
            "warnings": gate.get("warnings") or [],
            "metrics": gate.get("metrics") or {},
        },
    }


def _build_llm_enrichment_payload(row: dict[str, Any], *, applied_at: str) -> dict[str, Any]:
    llm_metadata_raw = row.get("llm_metadata")
    llm_metadata = llm_metadata_raw if isinstance(llm_metadata_raw, dict) else {}
    review_status = (
        "machine_candidate_needs_human_review"
        if _as_bool(row.get("needs_human_review"))
        else "machine_candidate"
    )
    split_raw = row.get("split_merge_suggestion")
    split_payload = split_raw if isinstance(split_raw, dict) else {}
    return {
        "schema_version": str(row.get("schema_version") or "kb_llm_enrichment_v1"),
        "applied_from_prd": RUN_TAG,
        "source_overlay": SOURCE_OVERLAY_TAG,
        "status": "applied_candidate",
        "review_status": review_status,
        "summary": str(row.get("summary_candidate") or "").strip(),
        "lens_family_candidates": _normalize_list(row.get("lens_family_candidates")),
        "tags": _normalize_list(row.get("tags")),
        "use_when": _normalize_list(row.get("use_when")),
        "avoid_when": _normalize_list(row.get("avoid_when")),
        "self_contained_score": _as_float(row.get("self_contained_score")),
        "self_contained_reason": str(row.get("self_contained_reason") or "").strip(),
        "split_merge_suggestion": {
            "action": str(split_payload.get("action") or "keep").strip() or "keep",
            "reason": str(split_payload.get("reason") or "").strip(),
        },
        "confidence": _as_float(row.get("confidence")),
        "needs_human_review": _as_bool(row.get("needs_human_review")),
        "review_reasons": _normalize_list(row.get("review_reasons")),
        "llm_metadata": {
            "provider": str(llm_metadata.get("provider") or "").strip(),
            "model": str(llm_metadata.get("model") or "").strip(),
            "prompt_version": str(llm_metadata.get("prompt_version") or "").strip(),
            "mock": _as_bool(llm_metadata.get("mock")),
            "generated_at": str(llm_metadata.get("generated_at") or "").strip(),
        },
        "applied_at": applied_at,
    }


def _stable_payload_for_compare(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(payload)
    if isinstance(normalized, dict):
        normalized.pop("applied_at", None)
    return normalized


def _extract_invariants(block: dict[str, Any]) -> dict[str, Any]:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    return {
        "text": str(block.get("text") or ""),
        "governance.chunk_type": str(governance.get("chunk_type") or ""),
        "governance.allowed_use": list(governance.get("allowed_use") or []),
        "governance.safety_flags": list(governance.get("safety_flags") or []),
    }


def _detect_forbidden_key(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key).strip().lower() in FORBIDDEN_LEAK_KEYS:
                return True
            if _detect_forbidden_key(value):
                return True
    elif isinstance(payload, list):
        return any(_detect_forbidden_key(item) for item in payload)
    return False


def apply_overlay_to_blocks(
    *,
    blocks: list[dict[str, Any]],
    overlay_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    now = _utc_now()
    blocks_out = copy.deepcopy(blocks)
    by_id = {
        str(item.get("id") or item.get("chunk_id") or ""): idx
        for idx, item in enumerate(blocks_out)
    }
    invariant_before = {block_id: _extract_invariants(blocks_out[idx]) for block_id, idx in by_id.items()}
    changed_ids: set[str] = set()
    unmatched_rows: list[str] = []
    forbidden_overlay_rows = 0
    needs_human_review_count = 0

    for row in overlay_rows:
        if _detect_forbidden_key(row):
            forbidden_overlay_rows += 1
            continue
        block_id = str(row.get("block_id") or "").strip()
        if not block_id:
            continue
        idx = by_id.get(block_id)
        if idx is None:
            unmatched_rows.append(block_id)
            continue
        block = blocks_out[idx]
        metadata = block.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            block["metadata"] = metadata
        previous = metadata.get("llm_enrichment")
        previous_payload = previous if isinstance(previous, dict) else {}

        llm_payload = _build_llm_enrichment_payload(row, applied_at=now)
        if str(block.get("summary") or "").strip():
            llm_payload["previous_summary"] = str(block.get("summary") or "").strip()

        is_same_payload = _stable_payload_for_compare(previous_payload) == _stable_payload_for_compare(
            llm_payload
        )
        if is_same_payload and previous_payload:
            metadata["llm_enrichment"] = previous_payload
        else:
            metadata["llm_enrichment"] = llm_payload

        effective_payload = (
            metadata.get("llm_enrichment")
            if isinstance(metadata.get("llm_enrichment"), dict)
            else {}
        )
        if effective_payload.get("needs_human_review"):
            needs_human_review_count += 1

        if not is_same_payload:
            changed_ids.add(block_id)

    invariant_after = {
        block_id: _extract_invariants(blocks_out[idx])
        for block_id, idx in by_id.items()
    }
    text_changed_count = 0
    chunk_type_changed_count = 0
    allowed_use_changed_count = 0
    safety_flags_changed_count = 0
    governance_invariant_violations = 0
    for block_id, before in invariant_before.items():
        after = invariant_after.get(block_id) or {}
        if before.get("text") != after.get("text"):
            text_changed_count += 1
            governance_invariant_violations += 1
        if before.get("governance.chunk_type") != after.get("governance.chunk_type"):
            chunk_type_changed_count += 1
            governance_invariant_violations += 1
        if before.get("governance.allowed_use") != after.get("governance.allowed_use"):
            allowed_use_changed_count += 1
            governance_invariant_violations += 1
        if before.get("governance.safety_flags") != after.get("governance.safety_flags"):
            safety_flags_changed_count += 1
            governance_invariant_violations += 1

    present_count = 0
    for block in blocks_out:
        meta = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        if isinstance(meta.get("llm_enrichment"), dict):
            present_count += 1

    overlay_rows_total = len(overlay_rows)
    matched_blocks = overlay_rows_total - len(unmatched_rows) - forbidden_overlay_rows
    matched_blocks = max(0, matched_blocks)
    updated_blocks = len(changed_ids)
    unchanged_blocks = max(0, len(blocks_out) - updated_blocks)
    diff_summary = {
        "generated_at": now,
        "run_tag": RUN_TAG,
        "blocks_total": len(blocks_out),
        "overlay_rows_total": overlay_rows_total,
        "matched_blocks": matched_blocks,
        "updated_blocks": updated_blocks,
        "unmatched_overlay_rows": len(unmatched_rows),
        "forbidden_overlay_rows": forbidden_overlay_rows,
        "unchanged_blocks": unchanged_blocks,
        "text_changed_count": text_changed_count,
        "chunk_type_changed_count": chunk_type_changed_count,
        "allowed_use_changed_count": allowed_use_changed_count,
        "safety_flags_changed_count": safety_flags_changed_count,
        "governance_invariant_violations": governance_invariant_violations,
        "top_level_summary_changed_count": 0,
        "metadata_llm_enrichment_present_count": present_count,
        "needs_human_review_count": needs_human_review_count,
        "review_status": "machine_candidate_needs_human_review",
        "immutable_fields_checked": sorted(IMMUTABLE_GOVERNANCE_FIELDS),
        "unmatched_overlay_block_ids_sample": unmatched_rows[:20],
    }

    validation_payload = dict(diff_summary)
    validation_payload["raw_text_leak_check"] = "pass"
    validation_payload["forbidden_leak_keys_present"] = False
    validation_payload["overlay_candidate_preview"] = [
        {
            "block_id": str(row.get("block_id") or ""),
            "summary_preview": _safe_preview(str(row.get("summary_candidate") or ""), limit=120),
            "needs_human_review": _as_bool(row.get("needs_human_review")),
            "review_reasons": _normalize_list(row.get("review_reasons"))[:4],
        }
        for row in overlay_rows[:8]
    ]
    return blocks_out, diff_summary, validation_payload


def run_apply(
    *,
    blocks_path: Path,
    overlay_path: Path,
    output_path: Path,
    output_dir: Path,
    backup_dir: Path,
    readiness_path: Path,
    apply_changes: bool,
    confirm: bool,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)

    preflight = build_preflight_gate(
        readiness_path=readiness_path,
        overlay_path=overlay_path,
        blocks_path=blocks_path,
    )
    (output_dir / "preflight_apply_gate.json").write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if not preflight.get("preflight_passed"):
        return {"status": "blocked", "reason": "preflight_failed", "preflight": preflight}

    if apply_changes and not confirm:
        raise RuntimeError("--apply requires --confirm")

    blocks, container_raw, wrapped = _parse_blocks_container(blocks_path)
    overlay_rows = _load_overlay_rows(overlay_path)
    mutated_blocks, diff_summary, validation_payload = apply_overlay_to_blocks(
        blocks=blocks,
        overlay_rows=overlay_rows,
    )

    before_text = _serialize_blocks_container(container_raw, blocks, wrapped)
    after_text = _serialize_blocks_container(container_raw, mutated_blocks, wrapped)
    changed = before_text != after_text

    diff_summary["apply_mode"] = "apply" if apply_changes else "dry_run"
    diff_summary["would_change_output"] = changed
    validation_payload["apply_mode"] = diff_summary["apply_mode"]
    validation_payload["would_change_output"] = changed
    validation_payload["output_sha256_before"] = _sha256_of_text(before_text)
    validation_payload["output_sha256_after"] = _sha256_of_text(after_text)

    if _detect_forbidden_key(validation_payload):
        validation_payload["raw_text_leak_check"] = "fail"
        validation_payload["forbidden_leak_keys_present"] = True

    backup_path = None
    if apply_changes:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"all_blocks_merged.before_apply.{ts}.json"
        backup_path.write_text(before_text, encoding="utf-8")
        output_path.write_text(after_text, encoding="utf-8")

    (output_dir / "apply_diff_summary.json").write_text(
        json.dumps(diff_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "applied_overlay_validation.json").write_text(
        json.dumps(validation_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "sanitized_runtime_logs.txt").write_text(
        "\n".join(
            [
                f"[{_utc_now()}] {RUN_TAG} apply run",
                f"apply_mode={diff_summary['apply_mode']}",
                f"overlay_rows_total={diff_summary.get('overlay_rows_total')}",
                f"matched_blocks={diff_summary.get('matched_blocks')}",
                f"updated_blocks={diff_summary.get('updated_blocks')}",
                f"governance_invariant_violations={diff_summary.get('governance_invariant_violations')}",
                f"raw_text_leak_check={validation_payload.get('raw_text_leak_check')}",
                f"backup_path={str(backup_path) if backup_path else 'not_created'}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "status": "done",
        "apply_mode": diff_summary["apply_mode"],
        "backup_path": str(backup_path) if backup_path else "",
        "output_path": str(output_path),
        "preflight_path": str(output_dir / "preflight_apply_gate.json"),
        "diff_summary_path": str(output_dir / "apply_diff_summary.json"),
        "validation_path": str(output_dir / "applied_overlay_validation.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply LLM enrichment overlay to processed blocks (safe mode).")
    parser.add_argument("--blocks-path", default=str(DEFAULT_BLOCKS_PATH))
    parser.add_argument("--overlay-path", default=str(DEFAULT_OVERLAY_PATH))
    parser.add_argument("--readiness-path", default=str(DEFAULT_READINESS_PATH))
    parser.add_argument("--output-path", default=str(DEFAULT_BLOCKS_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    apply_changes = bool(args.apply)
    if not args.apply:
        apply_changes = False
    if args.dry_run:
        apply_changes = False

    result = run_apply(
        blocks_path=Path(args.blocks_path),
        overlay_path=Path(args.overlay_path),
        output_path=Path(args.output_path),
        output_dir=Path(args.output_dir),
        backup_dir=Path(args.backup_dir),
        readiness_path=Path(args.readiness_path),
        apply_changes=apply_changes,
        confirm=bool(args.confirm),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "done" else 2


if __name__ == "__main__":
    raise SystemExit(main())
