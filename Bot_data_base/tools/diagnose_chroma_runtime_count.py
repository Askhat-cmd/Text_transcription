from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _resolve_botdb_path(botdb_dir: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        return raw
    return (botdb_dir / raw).resolve()


def _load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _diagnose_via_chromadb(
    *,
    botdb_dir: Path,
    config_path: Path,
    sample_ids_limit: int,
) -> dict[str, Any]:
    cfg = _load_config(config_path)
    storage_cfg = cfg.get("storage") if isinstance(cfg.get("storage"), dict) else {}
    db_path = _resolve_botdb_path(botdb_dir, str(storage_cfg.get("chroma_db_path") or "data/chroma_db"))
    collection_name = _normalize(storage_cfg.get("collection_name")) or "bot_knowledge_base"

    try:
        import chromadb  # type: ignore
        from chromadb.config import Settings  # type: ignore
    except Exception as exc:
        return {
            "status": "diagnostic_unavailable",
            "collection_name": collection_name,
            "persist_directory": str(db_path),
            "total_count": None,
            "source_ids": [],
            "count_by_source_id": {},
            "sample_ids_count": 0,
            "sample_ids": [],
            "raw_text_leak_detected": False,
            "errors": [f"chromadb_import_error:{exc}"],
            "warnings": [],
        }

    try:
        client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False, allow_reset=True))
        collection = client.get_or_create_collection(name=collection_name)
        total_count = int(collection.count())

        include_fields = ["metadatas"]
        rows = collection.get(limit=max(1, total_count), include=include_fields) if total_count > 0 else {"ids": [], "metadatas": []}
        ids = rows.get("ids") if isinstance(rows, dict) and isinstance(rows.get("ids"), list) else []
        metas = rows.get("metadatas") if isinstance(rows, dict) and isinstance(rows.get("metadatas"), list) else []

        source_counter: Counter[str] = Counter()
        for meta in metas:
            if not isinstance(meta, dict):
                continue
            sid = _normalize(meta.get("source_id"))
            if sid:
                source_counter[sid] += 1

        count_by_source_id = dict(sorted(source_counter.items(), key=lambda item: item[0]))
        source_ids = sorted(count_by_source_id.keys())
        sample_ids = [str(item) for item in ids[: max(0, int(sample_ids_limit))]]
        return {
            "status": "ok",
            "collection_name": collection_name,
            "persist_directory": str(db_path),
            "total_count": total_count,
            "source_ids": source_ids,
            "count_by_source_id": count_by_source_id,
            "sample_ids_count": len(sample_ids),
            "sample_ids": sample_ids,
            "raw_text_leak_detected": False,
            "errors": [],
            "warnings": [],
        }
    except Exception as exc:
        return {
            "status": "diagnostic_unavailable",
            "collection_name": collection_name,
            "persist_directory": str(db_path),
            "total_count": None,
            "source_ids": [],
            "count_by_source_id": {},
            "sample_ids_count": 0,
            "sample_ids": [],
            "raw_text_leak_detected": False,
            "errors": [f"chroma_runtime_error:{exc}"],
            "warnings": [],
        }


def run_diagnostic(
    *,
    source_prd: str,
    botdb_dir: Path,
    config_path: Path,
    sample_ids_limit: int = 10,
) -> dict[str, Any]:
    base = _diagnose_via_chromadb(
        botdb_dir=botdb_dir,
        config_path=config_path,
        sample_ids_limit=sample_ids_limit,
    )
    return {
        "schema_version": "direct_chroma_diagnostic_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now_iso(),
        **base,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only direct Chroma runtime diagnostic.")
    parser.add_argument("--source-prd", default="PRD-046.0.7.2-HF4")
    parser.add_argument("--botdb-dir", default="Bot_data_base")
    parser.add_argument("--config-path", default="Bot_data_base/config.yaml")
    parser.add_argument("--sample-ids-limit", type=int, default=10)
    parser.add_argument(
        "--out",
        default="TO_DO_LIST/logs/PRD-046.0.7.2-HF4/direct_chroma_diagnostic_before.json",
    )
    args = parser.parse_args()

    payload = run_diagnostic(
        source_prd=str(args.source_prd),
        botdb_dir=Path(args.botdb_dir),
        config_path=Path(args.config_path),
        sample_ids_limit=int(args.sample_ids_limit),
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
