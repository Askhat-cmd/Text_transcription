from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _utc_now_iso() -> str:
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


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _resolve_botdb_path(botdb_dir: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        return raw
    return (botdb_dir / raw).resolve()


def _extract_blocks(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = payload.get("blocks")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _source_id_from_block(block: dict[str, Any]) -> str:
    source = _normalize(block.get("source"))
    if ":" in source:
        return source.split(":", 1)[1]
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    return _normalize(metadata.get("source_id"))


def _to_universal_block(raw: dict[str, Any]) -> Any:
    from models.universal_block import UniversalBlock

    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    source = str(raw.get("source") or "")
    source_type = ""
    source_id = ""
    if ":" in source:
        source_type, source_id = source.split(":", 1)
    return UniversalBlock(
        block_id=str(raw.get("id") or raw.get("chunk_id") or ""),
        source_type=source_type or str(metadata.get("source_type") or ""),
        source_id=source_id or str(metadata.get("source_id") or ""),
        text=str(raw.get("text") or ""),
        title=str(raw.get("title") or ""),
        summary=str(raw.get("summary") or ""),
        sd_level=str(raw.get("sd_level") or "GREEN"),
        sd_confidence=float(raw.get("sd_confidence") or 0.0),
        complexity=float(raw.get("complexity") or 0.0),
        author=str(metadata.get("author") or ""),
        author_id=str(metadata.get("author_id") or ""),
        source_title=str(metadata.get("source_title") or ""),
        language=str(metadata.get("language") or "ru"),
        published_date=str(metadata.get("published_date") or ""),
        chapter_title=str(metadata.get("chapter_title") or ""),
        chunk_index=int(metadata.get("chunk_index") or 0),
        heading_path=(metadata.get("heading_path") or []),
        section_role_hint=str(metadata.get("section_role_hint") or ""),
        boundary_confidence=float(metadata.get("boundary_confidence") or 0.0),
        split_reason=str(metadata.get("split_reason") or ""),
        parent_section_id=str(metadata.get("parent_section_id") or ""),
        governance=(metadata.get("governance") or {}),
        chunking_quality=(metadata.get("chunking_quality") or {}),
        llm_enrichment=(metadata.get("llm_enrichment") if isinstance(metadata.get("llm_enrichment"), dict) else {}),
    )


def _probe_collection(
    *,
    db_path: Path,
    collection_name: str,
    embedding_model_name: str | None,
) -> dict[str, Any]:
    from storage.chroma_manager import ChromaManager

    manager = ChromaManager(
        db_path=str(db_path),
        collection_name=collection_name,
        embedding_model_name=embedding_model_name,
    )
    health = manager.probe_collection_health()
    collection_count = _to_int(health.get("collection_count"))
    source_ids: list[str] = []
    try:
        sample = manager._collection.get(limit=max(1, collection_count), include=["metadatas"]) if collection_count > 0 else {"metadatas": []}  # noqa: SLF001
        metas = sample.get("metadatas") if isinstance(sample, dict) and isinstance(sample.get("metadatas"), list) else []
        for meta in metas:
            if not isinstance(meta, dict):
                continue
            sid = _normalize(meta.get("source_id"))
            if sid and sid not in source_ids:
                source_ids.append(sid)
    except Exception:
        pass
    return {
        "health": health,
        "collection_count": collection_count,
        "source_ids": sorted(source_ids),
        "manager": manager,
    }


def run_controlled_reindex(
    *,
    source_prd: str,
    botdb_dir: Path,
    config_path: Path,
    blocks_path: Path,
    expected_source_id: str,
    expected_blocks: int,
    backup_root: Path,
    confirm: bool,
) -> dict[str, Any]:
    cfg = _load_config(config_path)
    storage_cfg = cfg.get("storage") if isinstance(cfg.get("storage"), dict) else {}
    embed_cfg = cfg.get("embedding") if isinstance(cfg.get("embedding"), dict) else {}
    db_path = _resolve_botdb_path(botdb_dir, str(storage_cfg.get("chroma_db_path") or "data/chroma_db"))
    collection_name = _normalize(storage_cfg.get("collection_name")) or "bot_knowledge_base"
    embedding_model_name = _normalize(embed_cfg.get("model")) or None

    blocks_payload = _load_json(blocks_path)
    blocks = _extract_blocks(blocks_payload)
    focus_blocks = [row for row in blocks if _source_id_from_block(row) == expected_source_id]
    source_ids = sorted({_source_id_from_block(row) for row in blocks if _source_id_from_block(row)})
    non_focus_with_blocks = len([row for row in blocks if _source_id_from_block(row) != expected_source_id])

    preflight_issues: list[str] = []
    if len(blocks) != expected_blocks:
        preflight_issues.append("all_blocks_total_mismatch")
    if len(focus_blocks) != expected_blocks:
        preflight_issues.append("focus_source_blocks_mismatch")
    if source_ids != [expected_source_id]:
        preflight_issues.append("source_ids_not_focus_only")
    if non_focus_with_blocks > 0:
        preflight_issues.append("non_focus_blocks_present")

    probe_before = _probe_collection(
        db_path=db_path,
        collection_name=collection_name,
        embedding_model_name=embedding_model_name,
    )
    backup_path = backup_root / f"chroma_before_reindex_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    backup_manifest = {
        "schema_version": "chroma_backup_manifest_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now_iso(),
        "persist_directory": str(db_path),
        "backup_path": str(backup_path),
        "copied": False,
        "errors": [],
    }

    reindex_performed = False
    indexed_blocks = 0
    status = "blocked_preflight"
    errors: list[str] = []
    if not confirm:
        status = "blocked_confirmation_required"
    elif preflight_issues:
        status = "blocked_preflight"
    else:
        try:
            if db_path.exists():
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(db_path, backup_path)
                backup_manifest["copied"] = True
            manager = probe_before["manager"]
            manager.reset_collection()
            indexed_blocks = int(manager.add_blocks([_to_universal_block(row) for row in focus_blocks]))
            reindex_performed = True
            status = "reindex_performed"
        except Exception as exc:
            status = "reindex_failed"
            errors.append(f"reindex_error:{exc}")
            backup_manifest["errors"].append(str(exc))

    probe_after = _probe_collection(
        db_path=db_path,
        collection_name=collection_name,
        embedding_model_name=embedding_model_name,
    )
    after_count = _to_int(probe_after.get("collection_count"))
    after_source_ids = list(probe_after.get("source_ids") or [])
    passed = reindex_performed and status == "reindex_performed" and after_count == expected_blocks and after_source_ids == [expected_source_id]
    final_status = "passed" if passed else "failed"

    result = {
        "schema_version": "chroma_reindex_result_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now_iso(),
        "status": final_status,
        "preflight_issues": preflight_issues,
        "confirm": bool(confirm),
        "persist_directory": str(db_path),
        "collection_name": collection_name,
        "all_blocks_total": len(blocks),
        "focus_source_id": expected_source_id,
        "focus_source_blocks": len(focus_blocks),
        "source_ids_from_blocks": source_ids,
        "chroma_count_before": _to_int(probe_before.get("collection_count")),
        "chroma_source_ids_before": list(probe_before.get("source_ids") or []),
        "reindex_performed": reindex_performed,
        "indexed_blocks_count": indexed_blocks,
        "chroma_count_after": after_count,
        "chroma_source_ids_after": after_source_ids,
        "errors": errors,
    }
    return {"result": result, "backup_manifest": backup_manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled reindex for focus source only.")
    parser.add_argument("--source-prd", default="PRD-046.0.7.2-HF4")
    parser.add_argument("--botdb-dir", default="Bot_data_base")
    parser.add_argument("--config-path", default="Bot_data_base/config.yaml")
    parser.add_argument("--blocks-path", default="Bot_data_base/data/processed/all_blocks_merged.json")
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument("--expected-blocks", type=int, default=247)
    parser.add_argument("--backup-root", default="TO_DO_LIST/backups/PRD-046.0.7.2-HF4/chroma_before_reindex")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--result-out", default="TO_DO_LIST/logs/PRD-046.0.7.2-HF4/chroma_reindex_result.json")
    parser.add_argument("--backup-manifest-out", default="TO_DO_LIST/logs/PRD-046.0.7.2-HF4/chroma_backup_manifest.json")
    args = parser.parse_args()

    payload = run_controlled_reindex(
        source_prd=str(args.source_prd),
        botdb_dir=Path(args.botdb_dir),
        config_path=Path(args.config_path),
        blocks_path=Path(args.blocks_path),
        expected_source_id=str(args.expected_source_id),
        expected_blocks=int(args.expected_blocks),
        backup_root=Path(args.backup_root),
        confirm=bool(args.confirm),
    )

    result_out = Path(args.result_out)
    backup_out = Path(args.backup_manifest_out)
    result_out.parent.mkdir(parents=True, exist_ok=True)
    backup_out.parent.mkdir(parents=True, exist_ok=True)
    result_out.write_text(json.dumps(payload["result"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    backup_out.write_text(json.dumps(payload["backup_manifest"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
