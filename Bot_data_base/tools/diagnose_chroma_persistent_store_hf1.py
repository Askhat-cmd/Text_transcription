from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from storage.chroma_manager import ChromaManager  # noqa: E402


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _resolve_botdb_path(botdb_dir: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        return raw
    return (botdb_dir / raw).resolve()


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _safe_error(exc: Exception) -> dict[str, str]:
    name = exc.__class__.__name__
    msg = str(exc or "").replace("\n", " ").replace("\r", " ").strip()
    return {"class": name, "message": msg[:500]}


def run_diagnostic(
    *,
    source_prd: str,
    botdb_dir: Path,
    config_path: Path,
    expected_source_id: str,
) -> dict[str, Any]:
    cfg = _load_config(config_path)
    storage_cfg = cfg.get("storage") if isinstance(cfg.get("storage"), dict) else {}
    embed_cfg = cfg.get("embedding") if isinstance(cfg.get("embedding"), dict) else {}

    db_path = _resolve_botdb_path(botdb_dir, str(storage_cfg.get("chroma_db_path") or "data/chroma_db"))
    collection_name = _normalize(storage_cfg.get("collection_name")) or "bot_knowledge_base"
    embedding_model_name = _normalize(embed_cfg.get("model")) or "sentence-transformers/all-MiniLM-L6-v2"

    result: dict[str, Any] = {
        "schema_version": "chroma_persistent_store_diagnostic_hf1_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now_iso(),
        "persist_directory": str(db_path),
        "collection_name": collection_name,
        "expected_source_id": expected_source_id,
        "storage_path_exists": db_path.exists(),
        "status": "ok",
        "errors": [],
        "warnings": [],
    }

    manager = ChromaManager(
        db_path=str(db_path),
        collection_name=collection_name,
        embedding_model_name=embedding_model_name,
    )

    probe = manager.probe_collection_health()
    result["health_probe"] = probe

    checks: dict[str, Any] = {}

    try:
        checks["collection_count"] = int(manager._collection.count())  # noqa: SLF001
    except Exception as exc:
        checks["collection_count_error"] = _safe_error(exc)

    try:
        sample = manager._collection.get(limit=1, include=["metadatas", "documents"])  # noqa: SLF001
        checks["collection_get_limit_1"] = {
            "ids_count": len(sample.get("ids") or []) if isinstance(sample, dict) else 0,
            "metadatas_count": len(sample.get("metadatas") or []) if isinstance(sample, dict) else 0,
        }
    except Exception as exc:
        checks["collection_get_limit_1_error"] = _safe_error(exc)

    try:
        query_vector = manager._embed_texts(["проверка chroma hf1"])
        queried = manager._collection.query(  # noqa: SLF001
            query_embeddings=query_vector,
            n_results=1,
            include=["metadatas", "distances"],
        )
        hits = queried.get("ids") if isinstance(queried, dict) else []
        first_hits = hits[0] if isinstance(hits, list) and hits else []
        checks["query_smoke"] = {"hits_count": len(first_hits) if isinstance(first_hits, list) else 0}
    except Exception as exc:
        checks["query_smoke_error"] = _safe_error(exc)

    try:
        checks["source_exists_expected"] = bool(manager.source_exists(expected_source_id))
    except Exception as exc:
        checks["source_exists_expected_error"] = _safe_error(exc)

    try:
        checks["get_stats"] = manager.get_stats()
    except Exception as exc:
        checks["get_stats_error"] = _safe_error(exc)

    result["checks"] = checks

    errors = [
        value
        for key, value in checks.items()
        if key.endswith("_error") and isinstance(value, dict)
    ]
    result["error_count"] = len(errors)
    result["errors"] = errors

    fingerprint_match = any(
        "object of type 'int' has no len()" in str(item.get("message") or "") for item in errors
    )
    result["matches_int_len_fingerprint"] = fingerprint_match

    if errors:
        result["status"] = "diagnostic_unavailable"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="HF1 persistent Chroma store diagnostic")
    parser.add_argument("--source-prd", default="PRD-046.1.21-HF1")
    parser.add_argument("--botdb-dir", default="Bot_data_base")
    parser.add_argument("--config-path", default="Bot_data_base/config.yaml")
    parser.add_argument("--expected-source-id", default="123__кузница_духа")
    parser.add_argument(
        "--out",
        default="TO_DO_LIST/logs/PRD-046.1.21-HF1/chroma_persistent_store_diagnostic_before.json",
    )
    args = parser.parse_args()

    payload = run_diagnostic(
        source_prd=str(args.source_prd),
        botdb_dir=Path(args.botdb_dir),
        config_path=Path(args.config_path),
        expected_source_id=str(args.expected_source_id),
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
