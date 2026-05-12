from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_PRD = "PRD-046.0.7-HF1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _save_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve_upload_path(raw_value: str, botdb_dir: Path) -> Path:
    path = Path(raw_value)
    if path.is_absolute():
        return path
    return (botdb_dir / path).resolve()


def _source_id_from_block(block: dict[str, Any]) -> str:
    source = _normalize(block.get("source"))
    if ":" in source:
        return source.split(":", 1)[1]
    meta = block.get("metadata") or {}
    return _normalize(meta.get("source_id")) or source


def build_reprocess_readiness_payload(
    *,
    source_prd: str,
    registry_records: list[dict[str, Any]],
    all_blocks: list[dict[str, Any]],
    hygiene_audit: dict[str, Any] | None,
    hygiene_plan: dict[str, Any] | None,
    legacy_sd_report: dict[str, Any] | None,
    review_queue: dict[str, Any] | None,
    botdb_dir: Path,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    focus_candidates = (hygiene_audit or {}).get("focus_source_candidates") or []
    focus_source_id = _normalize(focus_candidates[0]) if focus_candidates else ""

    if not focus_source_id:
        blockers.append("focus_source_not_found")
    elif len(focus_candidates) > 1:
        warnings.append("multiple_focus_candidates_detected")

    active_sources = [
        row
        for row in registry_records
        if _normalize(row.get("status")) in {"done", "processing"}
    ]
    unique_active_ids = sorted({_normalize(row.get("source_id")) for row in active_sources if _normalize(row.get("source_id"))})
    if len(unique_active_ids) > 1:
        blockers.append("multiple_active_sources_without_allowlist")

    focus_row = None
    if focus_source_id:
        for row in registry_records:
            if _normalize(row.get("source_id")) == focus_source_id:
                focus_row = row
                break
    if focus_row is None and focus_source_id:
        blockers.append("focus_source_missing_in_registry")

    raw_source_found = False
    if focus_row:
        upload_value = _normalize((focus_row.get("file_paths") or {}).get("upload"))
        if upload_value:
            raw_source_found = _resolve_upload_path(upload_value, botdb_dir).exists()
    if not raw_source_found:
        blockers.append("raw_markdown_missing")

    processed_blocks_count = 0
    if focus_source_id:
        processed_blocks_count = sum(
            1 for block in all_blocks if _source_id_from_block(block) == focus_source_id
        )
    if processed_blocks_count <= 0:
        blockers.append("processed_blocks_missing")

    chroma_count = processed_blocks_count
    if focus_row:
        chroma_count = max(processed_blocks_count, _to_int(focus_row.get("blocks_count")))
    if chroma_count != processed_blocks_count:
        blockers.append("chroma_count_mismatch")

    legacy_sd_active = bool((legacy_sd_report or {}).get("legacy_sd_filter_still_active"))
    if legacy_sd_active:
        blockers.append("legacy_sd_filter_still_active")

    zero_block_unclassified = False
    for row in (hygiene_audit or {}).get("sources") or []:
        if _to_int(row.get("blocks_count")) > 0:
            continue
        action = _normalize(row.get("recommended_hygiene_action"))
        if action not in {"archive", "safe_delete_zero_block", "keep", "manual_review"}:
            zero_block_unclassified = True
            break
    if zero_block_unclassified:
        blockers.append("registry_has_unclassified_zero_block_sources")

    if not hygiene_plan:
        blockers.append("source_hygiene_plan_missing")

    if review_queue is None:
        warnings.append("review_queue_missing")

    status = "ready"
    if blockers:
        status = "not_ready"
    elif warnings:
        status = "degraded"

    ready_for_clean_reprocess = status == "ready"
    recommendation = (
        "Можно переходить к PRD-046.0.8 clean reprocess."
        if ready_for_clean_reprocess
        else "Сначала закрыть blockers/warnings из readiness gate."
    )

    return {
        "schema_version": "reprocess_readiness_gate_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "ready_for_clean_reprocess": ready_for_clean_reprocess,
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "active_source_count": len(unique_active_ids),
        "active_source_id": focus_source_id,
        "active_source_title": _normalize((focus_row or {}).get("title")),
        "legacy_sd_active": legacy_sd_active,
        "registry_stale_sources_count": len((hygiene_audit or {}).get("stale_source_ids") or []),
        "empty_sources_count": int((hygiene_audit or {}).get("summary", {}).get("sources_zero_blocks") or 0),
        "processing_stale_count": len((hygiene_audit or {}).get("processing_stale_source_ids") or []),
        "raw_source_found": raw_source_found,
        "processed_blocks_count": processed_blocks_count,
        "chroma_count": chroma_count,
        "review_queue_items_count": int((review_queue or {}).get("review_items_count") or 0),
        "recommendation": recommendation,
    }


def _render_markdown(payload: dict[str, Any], source_prd: str) -> str:
    lines = [
        f"# {source_prd} REPROCESS READINESS GATE REPORT",
        "",
        "## Status",
        f"- ready_for_clean_reprocess: `{payload.get('ready_for_clean_reprocess')}`",
        f"- status: `{payload.get('status')}`",
        f"- active_source_count: `{payload.get('active_source_count')}`",
        f"- active_source_id: `{payload.get('active_source_id')}`",
        f"- active_source_title: `{payload.get('active_source_title')}`",
        f"- legacy_sd_active: `{payload.get('legacy_sd_active')}`",
        f"- processed_blocks_count: `{payload.get('processed_blocks_count')}`",
        f"- chroma_count: `{payload.get('chroma_count')}`",
        "",
        "## Blockers",
    ]
    blockers = payload.get("blockers") or []
    lines.extend([f"- `{item}`" for item in blockers] or ["- none"])
    lines.extend(["", "## Warnings"])
    warnings = payload.get("warnings") or []
    lines.extend([f"- `{item}`" for item in warnings] or ["- none"])
    lines.extend(["", "## Recommendation", f"- {payload.get('recommendation', '')}", ""])
    return "\n".join(lines)


def run_gate_cli(
    *,
    output_json: Path,
    output_md: Path,
    source_prd: str,
    registry_path: Path | None,
    all_blocks_path: Path | None,
    hygiene_audit_json: Path | None,
    hygiene_plan_json: Path | None,
    legacy_sd_report_json: Path | None,
    review_queue_json: Path | None,
) -> dict[str, Any]:
    root = Path.cwd()
    botdb_dir = root / "Bot_data_base"
    reg_path = registry_path or (botdb_dir / "data" / "registry.json")
    blocks_path = all_blocks_path or (botdb_dir / "data" / "processed" / "all_blocks_merged.json")

    registry_records: list[dict[str, Any]] = []
    all_blocks: list[dict[str, Any]] = []
    hygiene_audit = None
    hygiene_plan = None
    legacy_sd_report = None
    review_queue = None

    if reg_path.exists():
        raw = _load_json(reg_path)
        if isinstance(raw, list):
            registry_records = [row for row in raw if isinstance(row, dict)]
    if blocks_path.exists():
        raw = _load_json(blocks_path)
        if isinstance(raw, dict) and isinstance(raw.get("blocks"), list):
            all_blocks = [row for row in raw.get("blocks") if isinstance(row, dict)]
        elif isinstance(raw, list):
            all_blocks = [row for row in raw if isinstance(row, dict)]

    if hygiene_audit_json and hygiene_audit_json.exists():
        hygiene_audit = _load_json(hygiene_audit_json)
    if hygiene_plan_json and hygiene_plan_json.exists():
        hygiene_plan = _load_json(hygiene_plan_json)
    if legacy_sd_report_json and legacy_sd_report_json.exists():
        legacy_sd_report = _load_json(legacy_sd_report_json)
    if review_queue_json and review_queue_json.exists():
        review_queue = _load_json(review_queue_json)

    payload = build_reprocess_readiness_payload(
        source_prd=source_prd,
        registry_records=registry_records,
        all_blocks=all_blocks,
        hygiene_audit=hygiene_audit,
        hygiene_plan=hygiene_plan,
        legacy_sd_report=legacy_sd_report,
        review_queue=review_queue,
        botdb_dir=botdb_dir,
    )
    _save_json(output_json, payload)
    _save_markdown(output_md, _render_markdown(payload, source_prd))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build reprocess readiness gate report.")
    parser.add_argument(
        "--output-json",
        default="TO_DO_LIST/logs/PRD-046.0.7-HF1/reprocess_readiness_gate.json",
    )
    parser.add_argument(
        "--output-md",
        default="TO_DO_LIST/reports/PRD-046.0.7-HF1_REPROCESS_READINESS_GATE_REPORT.md",
    )
    parser.add_argument("--source-prd", default=DEFAULT_SOURCE_PRD)
    parser.add_argument("--registry-path", default="")
    parser.add_argument("--all-blocks-path", default="")
    parser.add_argument(
        "--hygiene-audit-json",
        default="TO_DO_LIST/logs/PRD-046.0.7-HF1/source_hygiene_audit.json",
    )
    parser.add_argument(
        "--hygiene-plan-json",
        default="TO_DO_LIST/logs/PRD-046.0.7-HF1/source_hygiene_plan.json",
    )
    parser.add_argument(
        "--legacy-sd-report-json",
        default="TO_DO_LIST/logs/PRD-046.0.7-HF1/legacy_sd_usage_report.json",
    )
    parser.add_argument(
        "--review-queue-json",
        default="TO_DO_LIST/logs/PRD-046.0.7/review_queue.json",
    )
    args = parser.parse_args()

    payload = run_gate_cli(
        output_json=Path(args.output_json),
        output_md=Path(args.output_md),
        source_prd=args.source_prd,
        registry_path=Path(args.registry_path) if args.registry_path else None,
        all_blocks_path=Path(args.all_blocks_path) if args.all_blocks_path else None,
        hygiene_audit_json=Path(args.hygiene_audit_json) if args.hygiene_audit_json else None,
        hygiene_plan_json=Path(args.hygiene_plan_json) if args.hygiene_plan_json else None,
        legacy_sd_report_json=Path(args.legacy_sd_report_json) if args.legacy_sd_report_json else None,
        review_queue_json=Path(args.review_queue_json) if args.review_queue_json else None,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
