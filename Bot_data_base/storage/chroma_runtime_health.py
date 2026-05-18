from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb
import yaml
from chromadb.config import Settings


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _sanitize_error_message(exc: Exception) -> str:
    text = str(exc or "").replace("\n", " ").replace("\r", " ").strip()
    return text[:300] if text else "unknown"


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    value = Path(raw_path)
    if value.is_absolute():
        return value
    return (base_dir / value).resolve()


def _load_config(config_path: str) -> tuple[dict[str, Any], Path]:
    path = Path(config_path)
    if not path.is_absolute():
        cwd_candidate = (Path.cwd() / path).resolve()
        if cwd_candidate.exists():
            path = cwd_candidate
        else:
            botdb_candidate = (Path(__file__).resolve().parents[1] / path).resolve()
            path = botdb_candidate
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    return (cfg or {}), path.parent


def _collect_source_stats(collection: Any, total: int) -> tuple[list[str], dict[str, int]]:
    if total <= 0:
        return [], {}
    raw = collection.get(limit=max(1, total), include=["metadatas"])
    metas = raw.get("metadatas") if isinstance(raw, dict) and isinstance(raw.get("metadatas"), list) else []
    counts: dict[str, int] = {}
    for item in metas:
        if not isinstance(item, dict):
            continue
        source_id = _normalize(item.get("source_id"))
        if not source_id:
            continue
        counts[source_id] = counts.get(source_id, 0) + 1
    return sorted(counts.keys()), dict(sorted(counts.items(), key=lambda kv: kv[0]))


def _extract_source_id_from_block(block: dict[str, Any]) -> str:
    source_raw = _normalize(block.get("source"))
    if ":" in source_raw:
        return _normalize(source_raw.split(":", 1)[1])
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    source_trace = governance.get("source_trace") if isinstance(governance.get("source_trace"), dict) else {}
    return _normalize(source_trace.get("source_id") or metadata.get("source_id"))


def _fallback_runtime_from_blocks(base_dir: Path) -> tuple[int, list[str], dict[str, int]]:
    candidates = [
        base_dir / "data" / "processed" / "all_blocks_merged.json",
        Path.cwd() / "data" / "processed" / "all_blocks_merged.json",
        Path(__file__).resolve().parents[1] / "data" / "processed" / "all_blocks_merged.json",
    ]
    merged_path = None
    for candidate in candidates:
        if candidate.exists():
            merged_path = candidate
            break
    if merged_path is None:
        return 0, [], {}
    payload = json.loads(merged_path.read_text(encoding="utf-8"))
    blocks = payload.get("blocks") if isinstance(payload, dict) and isinstance(payload.get("blocks"), list) else []
    counts: dict[str, int] = {}
    for block in blocks:
        if not isinstance(block, dict):
            continue
        source_id = _extract_source_id_from_block(block)
        if not source_id:
            continue
        counts[source_id] = counts.get(source_id, 0) + 1
    source_ids = sorted(counts.keys())
    return int(len(blocks)), source_ids, dict(sorted(counts.items(), key=lambda kv: kv[0]))


def get_chroma_runtime_health(config_path: str) -> dict[str, Any]:
    cfg, base_dir = _load_config(config_path)
    storage_cfg = cfg.get("storage") if isinstance(cfg.get("storage"), dict) else {}
    persist_directory = _resolve_path(base_dir, str(storage_cfg.get("chroma_db_path") or "data/chroma_db"))
    collection_name = _normalize(storage_cfg.get("collection_name")) or "bot_knowledge_base"

    payload: dict[str, Any] = {
        "status": "unavailable",
        "count": 0,
        "source_ids": [],
        "count_by_source_id": {},
        "persist_directory": str(persist_directory),
        "collection_name": collection_name,
        "fresh_client_used": True,
        "error_code": None,
        "error_message_sanitized": None,
    }

    try:
        client = chromadb.PersistentClient(
            path=str(persist_directory),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        collection = client.get_or_create_collection(name=collection_name)
        total = _to_int(collection.count())
        source_ids: list[str] = []
        count_by_source_id: dict[str, int] = {}
        source_stats_error: str | None = None
        try:
            source_ids, count_by_source_id = _collect_source_stats(collection, total)
        except Exception as exc:
            source_stats_error = _sanitize_error_message(exc)
        payload.update(
            {
                "status": "ok",
                "count": total,
                "source_ids": source_ids,
                "count_by_source_id": count_by_source_id,
            }
        )
        if source_stats_error:
            payload["error_code"] = "chroma_source_stats_unavailable"
            payload["error_message_sanitized"] = source_stats_error
        return payload
    except Exception as exc:
        payload["status"] = "unavailable"
        payload["error_code"] = "chroma_runtime_unavailable"
        payload["error_message_sanitized"] = _sanitize_error_message(exc)
        try:
            fallback_total, fallback_source_ids, fallback_by_source = _fallback_runtime_from_blocks(base_dir)
            if fallback_total > 0:
                payload["status"] = "ok"
                payload["count"] = int(fallback_total)
                payload["source_ids"] = fallback_source_ids
                payload["count_by_source_id"] = fallback_by_source
                payload["fresh_client_used"] = False
                payload["error_code"] = "chroma_runtime_fallback_all_blocks"
        except Exception:
            pass
        return payload


def save_chroma_runtime_health(config_path: str, out_path: Path) -> dict[str, Any]:
    payload = get_chroma_runtime_health(config_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
