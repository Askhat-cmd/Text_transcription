from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from api.schemas import RegistryListResponse, StatsResponse
from pipeline_runner import PipelineRunner
from storage.chroma_runtime_health import get_chroma_runtime_health
from storage.json_export import JSONExporter

router = APIRouter()

_runner: PipelineRunner | None = None


def _normalize(value: object) -> str:
    return str(value or "").strip()


def _to_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_error_detail(exc: Exception) -> str:
    text = str(exc or "").strip().replace("\n", " ").replace("\r", " ")
    if not text:
        return "unknown"
    return text[:200]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_existing_path(relative_path: str) -> Path:
    rel = Path(relative_path)
    candidates = [
        Path.cwd() / rel,
        _repo_root() / rel,
        _repo_root() / "Bot_data_base" / rel,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[1]


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _is_focus_source(source_row: dict[str, Any]) -> bool:
    source_id = _normalize(source_row.get("source_id")).lower()
    title = _normalize(source_row.get("title")).lower()
    blocks_count = _to_int(source_row.get("blocks_count"))
    source_type = _normalize(source_row.get("source_type")).lower()
    if "кузниц" in source_id and "дух" in source_id:
        return True
    if "кузниц" in title and "дух" in title:
        return True
    return source_type == "book" and blocks_count >= 200


def _is_test_like_source(source_row: dict[str, Any]) -> bool:
    source_id = _normalize(source_row.get("source_id")).lower()
    title = _normalize(source_row.get("title")).lower()
    author = _normalize(source_row.get("author")).lower()
    blocks_count = _to_int(source_row.get("blocks_count"))
    hay = f"{source_id} {title} {author}"
    if "test" in hay or "tmp" in hay or "demo" in hay:
        return True
    if title in {"книга", "book", "", "test"} and blocks_count <= 1:
        return True
    if source_id.startswith("test"):
        return True
    return False


def _extract_source_id(block: dict[str, Any]) -> str:
    source_value = _normalize(block.get("source"))
    if ":" in source_value:
        return _normalize(source_value.split(":", 1)[1])
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    trace = governance.get("source_trace") if isinstance(governance.get("source_trace"), dict) else {}
    return _normalize(trace.get("source_id") or metadata.get("source_id"))


def _load_production_source_ids(runner: PipelineRunner) -> set[str]:
    merged_path = Path(runner.json_exporter.base_dir) / "all_blocks_merged.json"
    payload = _read_json(merged_path)
    if payload is None:
        payload = _read_json(_resolve_existing_path("Bot_data_base/data/processed/all_blocks_merged.json"))
    blocks = payload.get("blocks") if isinstance((payload or {}).get("blocks"), list) else []
    return {sid for sid in (_extract_source_id(block) for block in blocks) if sid}


def _safe_chroma_source_exists(runner: PipelineRunner, source_id: str) -> tuple[bool | None, str | None]:
    normalized = _normalize(source_id)
    if not normalized:
        return False, None

    chroma = getattr(runner, "chroma_manager", None)
    if chroma is None:
        return None, "chroma_manager_unavailable"

    source_exists = getattr(chroma, "source_exists", None)
    if callable(source_exists):
        try:
            return bool(source_exists(normalized)), None
        except Exception as exc:
            return None, f"source_exists_error:{exc}"

    collection = getattr(chroma, "_collection", None)
    if collection is not None:
        try:
            queried = collection.get(where={"source_id": normalized})
            ids = queried.get("ids", []) if isinstance(queried, dict) else []
            return bool(ids), "fallback_collection_where_scan"
        except Exception as exc:
            return None, f"fallback_collection_scan_error:{exc}"

    return None, "chroma_source_exists_unavailable"


def _classify_hygiene(source_row: dict[str, Any]) -> tuple[str, list[str]]:
    status = _normalize(source_row.get("status")).lower()
    blocks_count = _to_int(source_row.get("blocks_count"))
    is_focus = _is_focus_source(source_row)
    is_test_like = _is_test_like_source(source_row)

    if is_focus:
        return "keep", ["focus_source_protected"]
    if status == "archived":
        if is_test_like and blocks_count <= 1:
            return "archive", ["registry_only_blocks_test_like"]
        return "keep", ["already_archived"]

    reasons: list[str] = []
    if is_test_like:
        reasons.append("test_like")
    if status == "processing" and blocks_count == 0:
        reasons.append("processing_stale")
    if blocks_count == 0:
        reasons.append("zero_blocks")
    if status == "failed":
        reasons.append("failed_status")

    if blocks_count > 0:
        if is_test_like and blocks_count <= 1:
            return "archive", ["registry_only_blocks_test_like"]
        return "manual_review", ["has_blocks_or_index_data"]
    if reasons:
        return "archive", reasons
    return "manual_review", ["unknown_needs_review"]


def _build_sources_payload(
    raw_sources: list[dict[str, Any]],
    *,
    runner: PipelineRunner,
    warnings: list[str] | None = None,
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    production_ids = _load_production_source_ids(runner)

    for index, row in enumerate(raw_sources):
        item = dict(row)
        source_id = _normalize(item.get("source_id")) or f"row_{index}"

        try:
            action, reasons = _classify_hygiene(item)
            item["is_focus_source"] = _is_focus_source(item)
            item["is_test_like"] = _is_test_like_source(item)
            item["recommended_hygiene_action"] = action
            item["hygiene_reason"] = reasons
        except Exception as exc:
            item["is_focus_source"] = False
            item["is_test_like"] = False
            item["recommended_hygiene_action"] = "manual_review"
            item["hygiene_reason"] = ["classification_error"]
            if warnings is not None:
                warnings.append(f"row_classification_error:{source_id}:{exc}")

        try:
            policy = _resolve_delete_policy(item, production_source_ids=production_ids, runner=runner)
        except Exception as exc:
            policy = {
                "allowed": False,
                "state": "unavailable",
                "reason": f"Ошибка политики: {exc}",
                "code": "row_policy_error",
            }
            if warnings is not None:
                warnings.append(f"row_policy_error:{source_id}:{exc}")

        item["delete_policy"] = policy
        item["delete_allowed"] = bool(policy.get("allowed"))
        payload.append(item)
    return payload


def _resolve_delete_policy(
    source_row: dict[str, Any],
    *,
    production_source_ids: set[str],
    runner: PipelineRunner,
) -> dict[str, Any]:
    source_id = _normalize(source_row.get("source_id"))
    status = _normalize(source_row.get("status")).lower()
    blocks_count = _to_int(source_row.get("blocks_count"))
    is_focus = _is_focus_source(source_row)
    is_test_like = _is_test_like_source(source_row)

    if is_focus:
        return {
            "allowed": False,
            "state": "protected",
            "reason": "Основной источник базы",
            "code": "focus_source_protected",
        }

    if blocks_count == 0 and status in {"archived", "failed", "processing", "done"}:
        return {
            "allowed": True,
            "state": "delete",
            "reason": "Архивный/пустой источник можно удалить",
            "code": "zero_block_safe_delete",
        }

    if blocks_count <= 1 and is_test_like:
        if source_id in production_source_ids:
            return {
                "allowed": False,
                "state": "unavailable",
                "reason": "Источник присутствует в production блоках",
                "code": "present_in_production",
            }
        chroma_exists, chroma_reason = _safe_chroma_source_exists(runner, source_id)
        if chroma_exists is True:
            return {
                "allowed": False,
                "state": "unavailable",
                "reason": "Источник имеет записи в Chroma, требуется ручная проверка",
                "code": "chroma_has_source",
            }
        if chroma_exists is None:
            return {
                "allowed": False,
                "state": "unavailable",
                "reason": f"Проверка Chroma недоступна: {chroma_reason or 'unknown'}",
                "code": "chroma_source_exists_unavailable",
            }
        return {
            "allowed": True,
            "state": "cleanup_test",
            "reason": "Тестовый источник можно очистить",
            "code": "registry_only_blocks_test_like",
        }

    if status == "archived":
        return {
            "allowed": False,
            "state": "archive",
            "reason": "Архивный источник сохранен для аудита",
            "code": "archived_retained",
        }

    return {
        "allowed": False,
        "state": "unavailable",
        "reason": "Удаление недоступно по политике",
        "code": "blocked_by_policy",
    }


def _get_runner() -> PipelineRunner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner(config_path="config.yaml")
    return _runner


def _create_registry_snapshot(runner: PipelineRunner, reason: str) -> str:
    registry_path = Path(runner.registry.registry_path)
    if not registry_path.exists():
        return ""
    out_dir = _resolve_existing_path("TO_DO_LIST/logs/PRD-046.0.9-RUN1-HF3")
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_reason = "".join(ch for ch in reason if ch.isalnum() or ch in {"_", "-"}) or "delete"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = out_dir / f"registry_snapshot_before_{safe_reason}_{stamp}.json"
    target.write_text(registry_path.read_text(encoding="utf-8"), encoding="utf-8")
    return str(target.as_posix())


@router.get("/", response_model=RegistryListResponse)
async def list_sources():
    runner = _get_runner()
    warnings: list[str] = []
    payload_sources = _build_sources_payload([s.to_dict() for s in runner.registry.list_all()], runner=runner, warnings=warnings)
    return {"total": len(payload_sources), "sources": payload_sources, "warnings": warnings}


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    runner = _get_runner()
    stats = runner.registry.get_statistics()
    warnings: list[str] = []
    chroma_health = get_chroma_runtime_health("config.yaml")
    chroma_status = _normalize(chroma_health.get("status")).lower() or "unavailable"
    chroma_error_code: str | None = None
    chroma_total = _to_int(chroma_health.get("count"))
    if chroma_status != "ok":
        chroma_error_code = "chroma_stats_unavailable"
        warnings.append("Chroma stats unavailable; registry stats returned in degraded mode")
        health_error = _normalize(chroma_health.get("error_message_sanitized"))
        if health_error:
            warnings.append(f"chroma_error:{health_error}")

    sources = [s.to_dict() for s in runner.registry.list_all()]
    focus_sources = [row for row in sources if _is_focus_source(row)]

    classification_warnings: list[str] = []
    classified = _build_sources_payload(sources, runner=runner, warnings=classification_warnings)
    archive_candidates = sum(
        1 for row in classified if _normalize(row.get("recommended_hygiene_action")) == "archive"
    )
    processing_stale = sum(
        1
        for row in classified
        if _normalize(row.get("status")).lower() == "processing" and _to_int(row.get("blocks_count")) == 0
    )

    review_queue_items = 0
    review_queue_path = _resolve_existing_path("TO_DO_LIST/logs/PRD-046.0.7/review_queue.json")
    if review_queue_path.exists():
        try:
            review_queue_items = _to_int((json.loads(review_queue_path.read_text(encoding="utf-8"))).get("review_items_count"))
        except Exception:
            review_queue_items = 0

    return {
        "total_sources": stats.get("total_sources", 0),
        "total_blocks": stats.get("total_blocks", 0),
        "chroma_total": chroma_total,
        "chroma_status": chroma_status,
        "chroma_error_code": chroma_error_code,
        "sd_distribution": {},
        "sources_by_type": stats.get("sources_by_type", {}),
        "legacy_sd_active": False,
        "governance_readiness": {
            "focus_source_count": len(focus_sources),
            "focus_source_blocks": _to_int(focus_sources[0].get("blocks_count")) if focus_sources else 0,
            "archive_candidate_sources": archive_candidates,
            "processing_stale_sources": processing_stale,
            "review_queue_items": review_queue_items,
            "row_policy_errors_count": sum(1 for w in classification_warnings if "row_policy_error:" in w),
        },
        "warnings": warnings,
    }


@router.delete("/{source_id}")
async def delete_source(source_id: str):
    runner = _get_runner()
    source = runner.registry.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Источник не найден")

    source_row = source.to_dict()
    production_ids = _load_production_source_ids(runner)
    policy = _resolve_delete_policy(source_row, production_source_ids=production_ids, runner=runner)
    if not bool(policy.get("allowed")):
        raise HTTPException(status_code=409, detail=str(policy.get("reason") or "Удаление запрещено"))

    snapshot_path = _create_registry_snapshot(runner, str(policy.get("code") or "delete"))
    chroma_deleted = runner.chroma_manager.delete_source(source_id)
    removed = runner.registry.delete_source(source_id)
    files_deleted: list[str] = []

    file_paths = source.file_paths or {}
    upload_path = file_paths.get("upload")
    if upload_path:
        path = Path(str(upload_path))
        if path.exists():
            path.unlink()
            files_deleted.append(str(path.as_posix()))

    json_path = file_paths.get("json")
    if json_path:
        path = Path(str(json_path))
        if path.exists():
            path.unlink()
            files_deleted.append(str(path.as_posix()))

    base_dir = Path(runner.json_exporter.base_dir)
    for subdir in ("books", "youtube"):
        dir_path = base_dir / subdir
        if not dir_path.exists():
            continue
        for file_path in dir_path.glob(f"*{source_id}*"):
            if file_path.exists():
                file_path.unlink()
                files_deleted.append(str(file_path.as_posix()))

    return {
        "deleted": int(chroma_deleted),
        "removed": bool(removed),
        "files_deleted": files_deleted,
        "snapshot_path": snapshot_path,
        "message": "Источник удален по политике гигиены",
        "policy_code": policy.get("code"),
        "timestamp": _utc_now(),
    }


@router.get("/export/merged")
async def export_merged():
    runner = _get_runner()
    exporter = JSONExporter(runner.json_exporter.base_dir)
    path = exporter.export_all_merged()
    return {"path": path}
