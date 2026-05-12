from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _source_id_from_block(block: dict[str, Any]) -> str:
    source = _normalize(block.get("source"))
    if ":" in source:
        return source.split(":", 1)[1]
    meta = block.get("metadata") or {}
    return _normalize(meta.get("source_id")) or source


def _read_blocks(all_blocks_path: Path) -> list[dict[str, Any]]:
    if not all_blocks_path.exists():
        return []
    raw = _load_json(all_blocks_path)
    if isinstance(raw, dict):
        blocks = raw.get("blocks")
        return [row for row in (blocks or []) if isinstance(row, dict)]
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    return []


def _focus_source_id(registry: list[dict[str, Any]]) -> str:
    for row in registry:
        sid = _normalize(row.get("source_id")).lower()
        title = _normalize(row.get("title")).lower()
        if "кузниц" in sid and "дух" in sid:
            return _normalize(row.get("source_id"))
        if "кузниц" in title and "дух" in title:
            return _normalize(row.get("source_id"))
    return ""


def build_snapshot(*, root: Path) -> dict[str, Any]:
    botdb = root / "Bot_data_base"
    registry_path = botdb / "data" / "registry.json"
    all_blocks_path = botdb / "data" / "processed" / "all_blocks_merged.json"
    review_queue_path = root / "TO_DO_LIST" / "logs" / "PRD-046.0.7" / "review_queue.json"

    registry = _load_json(registry_path) if registry_path.exists() else []
    if not isinstance(registry, list):
        registry = []
    blocks = _read_blocks(all_blocks_path)

    focus_source_id = _focus_source_id(registry)
    focus_blocks_registry = 0
    for row in registry:
        if _normalize(row.get("source_id")) == focus_source_id and _normalize(row.get("status")) == "done":
            focus_blocks_registry = max(focus_blocks_registry, int(row.get("blocks_count") or 0))
    focus_blocks_processed = sum(1 for block in blocks if _source_id_from_block(block) == focus_source_id)

    return {
        "captured_at": _utc_now(),
        "focus_source_id": focus_source_id,
        "all_blocks_merged_exists": all_blocks_path.exists(),
        "all_blocks_merged_sha256": _sha256(all_blocks_path) if all_blocks_path.exists() else "",
        "processed_blocks_total": len(blocks),
        "focus_blocks_processed": focus_blocks_processed,
        "chroma_count_proxy": focus_blocks_processed,
        "focus_blocks_registry": focus_blocks_registry,
        "review_queue_exists": review_queue_path.exists(),
        "review_queue_sha256": _sha256(review_queue_path) if review_queue_path.exists() else "",
    }


def build_invariant_payload(*, before: dict[str, Any], after: dict[str, Any], source_prd: str) -> dict[str, Any]:
    return {
        "schema_version": "invariant_check_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "all_blocks_merged_sha_before": before.get("all_blocks_merged_sha256", ""),
        "all_blocks_merged_sha_after": after.get("all_blocks_merged_sha256", ""),
        "all_blocks_merged_mutated": before.get("all_blocks_merged_sha256", "") != after.get("all_blocks_merged_sha256", ""),
        "chroma_count_before": int(before.get("chroma_count_proxy") or 0),
        "chroma_count_after": int(after.get("chroma_count_proxy") or 0),
        "processed_blocks_before": int(before.get("focus_blocks_processed") or 0),
        "processed_blocks_after": int(after.get("focus_blocks_processed") or 0),
        "review_queue_sha_before": before.get("review_queue_sha256", ""),
        "review_queue_sha_after": after.get("review_queue_sha256", ""),
        "review_queue_mutated": before.get("review_queue_sha256", "") != after.get("review_queue_sha256", ""),
        "focus_source_id_before": before.get("focus_source_id", ""),
        "focus_source_id_after": after.get("focus_source_id", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build invariant before/after check for hygiene cycles.")
    parser.add_argument("--source-prd", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--before-snapshot-json", default="")
    parser.add_argument("--write-snapshot-json", default="")
    args = parser.parse_args()

    root = Path.cwd()
    after_snapshot = build_snapshot(root=root)

    before_snapshot = after_snapshot
    if args.before_snapshot_json:
        before_path = Path(args.before_snapshot_json)
        if before_path.exists():
            raw = _load_json(before_path)
            if isinstance(raw, dict):
                before_snapshot = raw

    if args.write_snapshot_json:
        _save_json(Path(args.write_snapshot_json), after_snapshot)

    payload = build_invariant_payload(before=before_snapshot, after=after_snapshot, source_prd=args.source_prd)
    _save_json(Path(args.output_json), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
