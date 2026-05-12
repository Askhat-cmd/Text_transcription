from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_PRD = "PRD-046.0.7-HF1"
DEFAULT_FOCUS_HINT = "кузниц"


@dataclass
class SourceAuditItem:
    source_id: str
    title: str
    author: str
    source_type: str
    status: str
    blocks_count: int
    chroma_indexed_blocks_count: int
    raw_file_exists: bool
    processed_export_exists: bool
    is_focus_source: bool
    is_test_like: bool
    is_empty: bool
    is_processing_stale: bool
    is_orphaned: bool
    recommended_hygiene_action: str
    reason: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "author": self.author,
            "source_type": self.source_type,
            "status": self.status,
            "blocks_count": self.blocks_count,
            "chroma_indexed_blocks_count": self.chroma_indexed_blocks_count,
            "raw_file_exists": self.raw_file_exists,
            "processed_export_exists": self.processed_export_exists,
            "is_focus_source": self.is_focus_source,
            "is_test_like": self.is_test_like,
            "is_empty": self.is_empty,
            "is_processing_stale": self.is_processing_stale,
            "is_orphaned": self.is_orphaned,
            "recommended_hygiene_action": self.recommended_hygiene_action,
            "reason": self.reason,
        }


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


def _resolve_file(path_value: str, botdb_dir: Path) -> Path:
    raw = Path(path_value)
    if raw.is_absolute():
        return raw
    # file_paths часто сохраняются как "data/..." относительно Bot_data_base
    return (botdb_dir / raw).resolve()


def _source_id_from_block(block: dict[str, Any]) -> str:
    source = _normalize(block.get("source"))
    if ":" in source:
        return source.split(":", 1)[1]
    meta = block.get("metadata") or {}
    return _normalize(meta.get("source_id")) or source


def _collect_processed_counts(blocks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for block in blocks:
        source_id = _source_id_from_block(block)
        if not source_id:
            continue
        counts[source_id] = counts.get(source_id, 0) + 1
    return counts


def _is_focus_source(title: str, source_id: str, source_type: str, blocks_count: int, raw_exists: bool, focus_hint: str) -> bool:
    hay = f"{title} {source_id}".lower()
    if focus_hint and focus_hint.lower() in hay and "дух" in hay:
        return True
    if "кузниц" in hay and "дух" in hay:
        return True
    if source_type == "book" and blocks_count >= 200 and raw_exists:
        return True
    return False


def _is_test_like(title: str, source_id: str, author: str, source_type: str, blocks_count: int) -> bool:
    hay = f"{title} {source_id} {author}".lower()
    if any(token in hay for token in ("test", "test123")):
        return True
    if title.strip().lower() in {"книга", "book", ""} and source_type in {"book", "youtube"} and blocks_count <= 1:
        return True
    if author.strip().lower() in {"автор", "author"} and blocks_count <= 1:
        return True
    return False


def _detect_action(
    *,
    status: str,
    is_focus: bool,
    blocks_count: int,
    chroma_count: int,
    is_empty: bool,
    is_processing_stale: bool,
    is_test_like: bool,
    is_orphaned: bool,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if status == "archived":
        return "keep", ["already_archived"]

    if is_focus:
        return "keep", ["focus_source_protected"]

    if blocks_count > 0 or chroma_count > 0:
        if chroma_count == 0 and blocks_count <= 1 and is_test_like:
            return "archive", ["registry_only_blocks_test_like"]
        reasons.append("has_blocks_or_index_data")
        return "manual_review", reasons

    if is_processing_stale:
        reasons.append("processing_stale_zero_blocks")
    if is_test_like:
        reasons.append("test_like_zero_blocks")
    if is_orphaned:
        reasons.append("orphaned_zero_blocks")
    if is_empty:
        reasons.append("empty_zero_blocks")

    if reasons:
        return "archive", reasons
    return "manual_review", ["unknown_needs_review"]


def build_source_hygiene_audit(
    *,
    registry_records: list[dict[str, Any]],
    processed_blocks: list[dict[str, Any]],
    botdb_dir: Path,
    focus_hint: str = DEFAULT_FOCUS_HINT,
) -> dict[str, Any]:
    processed_counts = _collect_processed_counts(processed_blocks)
    by_source_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_title: Counter[str] = Counter()

    for row in registry_records:
        sid = _normalize(row.get("source_id"))
        by_source_id[sid].append(row)
        by_title[_normalize(row.get("title")).lower()] += 1

    items: list[SourceAuditItem] = []
    focus_candidates: set[str] = set()
    test_candidates: set[str] = set()
    processing_stale_ids: set[str] = set()
    stale_ids: set[str] = set()
    orphaned_ids: set[str] = set()
    archived_ids: set[str] = set()
    active_ids: set[str] = set()

    for row in registry_records:
        source_id = _normalize(row.get("source_id"))
        title = _normalize(row.get("title"))
        author = _normalize(row.get("author"))
        source_type = _normalize(row.get("source_type")) or "unknown"
        status = _normalize(row.get("status")) or "unknown"
        blocks_count = _to_int(row.get("blocks_count"))
        chroma_count = processed_counts.get(source_id, 0)

        file_paths = row.get("file_paths") or {}
        file_paths = file_paths if isinstance(file_paths, dict) else {}
        upload_path = _normalize(file_paths.get("upload"))
        export_path = _normalize(file_paths.get("json"))
        raw_exists = _resolve_file(upload_path, botdb_dir).exists() if upload_path else False
        processed_export_exists = _resolve_file(export_path, botdb_dir).exists() if export_path else False
        if not processed_export_exists and source_id:
            processed_export_exists = any(
                source_id.lower() in p.name.lower()
                for p in (botdb_dir / "data" / "processed").rglob("*_blocks.json")
            )

        is_focus = _is_focus_source(title, source_id, source_type, blocks_count, raw_exists, focus_hint)
        is_test_like = _is_test_like(title, source_id, author, source_type, blocks_count)
        is_empty = blocks_count <= 0 and chroma_count <= 0
        is_processing_stale = status == "processing" and blocks_count <= 0 and chroma_count <= 0
        is_orphaned = (not raw_exists) and (not processed_export_exists) and blocks_count <= 0 and chroma_count <= 0

        action, reasons = _detect_action(
            status=status,
            is_focus=is_focus,
            blocks_count=blocks_count,
            chroma_count=chroma_count,
            is_empty=is_empty,
            is_processing_stale=is_processing_stale,
            is_test_like=is_test_like,
            is_orphaned=is_orphaned,
        )

        item = SourceAuditItem(
            source_id=source_id,
            title=title,
            author=author,
            source_type=source_type,
            status=status,
            blocks_count=blocks_count,
            chroma_indexed_blocks_count=chroma_count,
            raw_file_exists=raw_exists,
            processed_export_exists=processed_export_exists,
            is_focus_source=is_focus,
            is_test_like=is_test_like,
            is_empty=is_empty,
            is_processing_stale=is_processing_stale,
            is_orphaned=is_orphaned,
            recommended_hygiene_action=action,
            reason=reasons,
        )
        items.append(item)

        if source_id:
            if is_focus:
                focus_candidates.add(source_id)
            if is_test_like:
                test_candidates.add(source_id)
            if is_processing_stale:
                processing_stale_ids.add(source_id)
            if status == "failed" and is_empty:
                stale_ids.add(source_id)
            if is_orphaned:
                orphaned_ids.add(source_id)
            if status == "archived":
                archived_ids.add(source_id)
            if status in {"done", "processing"}:
                active_ids.add(source_id)

    duplicate_source_id_sources = sorted([sid for sid, rows in by_source_id.items() if sid and len(rows) > 1])
    duplicate_title_sources = sorted(
        [title for title, count in by_title.items() if title and count > 1]
    )

    summary = {
        "total_sources": len(registry_records),
        "unique_source_ids": len([sid for sid in by_source_id.keys() if sid]),
        "active_sources": len(active_ids),
        "sources_with_blocks": sum(
            1
            for row in registry_records
            if _to_int(row.get("blocks_count")) > 0 and _normalize(row.get("status")) != "archived"
        ),
        "sources_zero_blocks": sum(
            1
            for row in registry_records
            if _to_int(row.get("blocks_count")) <= 0 and _normalize(row.get("status")) != "archived"
        ),
        "processing_sources": sum(1 for row in registry_records if _normalize(row.get("status")) == "processing"),
        "processing_stale_sources": len(processing_stale_ids),
        "archived_sources": len(archived_ids),
        "orphaned_sources": len(orphaned_ids),
        "duplicate_title_sources": len(duplicate_title_sources),
        "duplicate_source_id_sources": len(duplicate_source_id_sources),
        "focus_source_candidates": len(focus_candidates),
        "test_source_candidates": len(test_candidates),
    }

    return {
        "schema_version": "source_hygiene_audit_v1",
        "generated_at": _utc_now(),
        "summary": summary,
        "focus_source_candidates": sorted(focus_candidates),
        "test_source_candidates": sorted(test_candidates),
        "processing_stale_source_ids": sorted(processing_stale_ids),
        "stale_source_ids": sorted(stale_ids),
        "orphaned_source_ids": sorted(orphaned_ids),
        "duplicate_title_values": duplicate_title_sources,
        "duplicate_source_id_values": duplicate_source_id_sources,
        "sources": [item.to_dict() for item in items],
    }


def _render_markdown(payload: dict[str, Any], source_prd: str) -> str:
    summary = payload.get("summary") or {}
    lines = [
        f"# {source_prd} SOURCE HYGIENE AUDIT REPORT",
        "",
        "## Summary",
        f"- total_sources: `{summary.get('total_sources', 0)}`",
        f"- unique_source_ids: `{summary.get('unique_source_ids', 0)}`",
        f"- sources_with_blocks: `{summary.get('sources_with_blocks', 0)}`",
        f"- sources_zero_blocks: `{summary.get('sources_zero_blocks', 0)}`",
        f"- processing_stale_sources: `{summary.get('processing_stale_sources', 0)}`",
        f"- orphaned_sources: `{summary.get('orphaned_sources', 0)}`",
        f"- duplicate_source_id_sources: `{summary.get('duplicate_source_id_sources', 0)}`",
        "",
        "## Focus Source Candidates",
    ]
    focus = payload.get("focus_source_candidates") or []
    if focus:
        lines.extend([f"- `{sid}`" for sid in focus])
    else:
        lines.append("- none")
    lines.extend(["", "## Test-Like Source Candidates"])
    tests = payload.get("test_source_candidates") or []
    if tests:
        lines.extend([f"- `{sid}`" for sid in tests])
    else:
        lines.append("- none")

    lines.extend(["", "## Recommended Actions", "| source_id | status | blocks | action | reason |", "| --- | --- | ---: | --- | --- |"])
    for row in payload.get("sources", []):
        reason = ", ".join(row.get("reason") or [])
        lines.append(
            f"| `{row.get('source_id','')}` | `{row.get('status','')}` | {int(row.get('blocks_count') or 0)} | `{row.get('recommended_hygiene_action','')}` | `{reason}` |"
        )
    lines.append("")
    return "\n".join(lines)


def run_audit_cli(
    *,
    output_json: Path,
    output_md: Path,
    registry_path: Path | None,
    all_blocks_path: Path | None,
    focus_hint: str,
    source_prd: str,
) -> dict[str, Any]:
    root = Path.cwd()
    botdb_dir = root / "Bot_data_base"
    reg_path = registry_path or (botdb_dir / "data" / "registry.json")
    blocks_path = all_blocks_path or (botdb_dir / "data" / "processed" / "all_blocks_merged.json")

    degraded: list[str] = []
    registry_records: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []

    if not reg_path.exists():
        degraded.append(f"registry_missing:{reg_path}")
    else:
        raw_registry = _load_json(reg_path)
        if isinstance(raw_registry, list):
            registry_records = [row for row in raw_registry if isinstance(row, dict)]
        else:
            degraded.append("registry_schema_not_list")

    if not blocks_path.exists():
        degraded.append(f"processed_blocks_missing:{blocks_path}")
    else:
        raw_blocks = _load_json(blocks_path)
        if isinstance(raw_blocks, dict):
            payload_blocks = raw_blocks.get("blocks")
            if isinstance(payload_blocks, list):
                blocks = [row for row in payload_blocks if isinstance(row, dict)]
            else:
                degraded.append("processed_blocks_missing_blocks_array")
        elif isinstance(raw_blocks, list):
            blocks = [row for row in raw_blocks if isinstance(row, dict)]
        else:
            degraded.append("processed_blocks_unknown_schema")

    result = build_source_hygiene_audit(
        registry_records=registry_records,
        processed_blocks=blocks,
        botdb_dir=botdb_dir,
        focus_hint=focus_hint,
    )
    result["source_prd"] = source_prd
    result["registry_path"] = str(reg_path)
    result["processed_blocks_path"] = str(blocks_path)
    result["degraded_reasons"] = degraded
    result["mode"] = "degraded" if degraded else "normal"

    _save_json(output_json, result)
    _save_markdown(output_md, _render_markdown(result, source_prd))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit BotDB source registry hygiene state.")
    parser.add_argument(
        "--output-json",
        default="TO_DO_LIST/logs/PRD-046.0.7-HF1/source_hygiene_audit.json",
    )
    parser.add_argument(
        "--output-md",
        default="TO_DO_LIST/reports/PRD-046.0.7-HF1_SOURCE_HYGIENE_AUDIT_REPORT.md",
    )
    parser.add_argument("--registry-path", default="")
    parser.add_argument("--all-blocks-path", default="")
    parser.add_argument("--focus-hint", default=DEFAULT_FOCUS_HINT)
    parser.add_argument("--source-prd", default=DEFAULT_SOURCE_PRD)
    args = parser.parse_args()

    payload = run_audit_cli(
        output_json=Path(args.output_json),
        output_md=Path(args.output_md),
        registry_path=Path(args.registry_path) if args.registry_path else None,
        all_blocks_path=Path(args.all_blocks_path) if args.all_blocks_path else None,
        focus_hint=args.focus_hint,
        source_prd=args.source_prd,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
