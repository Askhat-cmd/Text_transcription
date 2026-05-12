import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.schemas import RegistryListResponse, StatsResponse
from pipeline_runner import PipelineRunner
from storage.json_export import JSONExporter

router = APIRouter()

_runner: PipelineRunner | None = None


def _normalize(value: object) -> str:
    return str(value or "").strip()


def _is_focus_source(source_row: dict) -> bool:
    source_id = _normalize(source_row.get("source_id")).lower()
    title = _normalize(source_row.get("title")).lower()
    blocks_count = int(source_row.get("blocks_count") or 0)
    source_type = _normalize(source_row.get("source_type")).lower()
    if "кузниц" in source_id and "дух" in source_id:
        return True
    if "кузниц" in title and "дух" in title:
        return True
    return source_type == "book" and blocks_count >= 200


def _classify_hygiene(source_row: dict) -> tuple[str, list[str]]:
    source_id = _normalize(source_row.get("source_id"))
    title = _normalize(source_row.get("title"))
    author = _normalize(source_row.get("author"))
    status = _normalize(source_row.get("status")).lower()
    blocks_count = int(source_row.get("blocks_count") or 0)
    is_focus = _is_focus_source(source_row)

    if is_focus:
        return "keep", ["focus_source_protected"]
    if status == "archived":
        return "keep", ["already_archived"]

    hay = f"{source_id} {title} {author}".lower()
    is_test_like = ("test" in hay) or (title.lower() in {"книга", "book", ""} and blocks_count <= 1)
    is_processing_stale = status == "processing" and blocks_count == 0
    is_empty = blocks_count == 0

    reasons: list[str] = []
    if is_test_like:
        reasons.append("test_like")
    if is_processing_stale:
        reasons.append("processing_stale")
    if is_empty:
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


def _build_sources_payload(raw_sources: list[dict]) -> list[dict]:
    payload: list[dict] = []
    for row in raw_sources:
        item = dict(row)
        action, reasons = _classify_hygiene(item)
        item["is_focus_source"] = _is_focus_source(item)
        item["recommended_hygiene_action"] = action
        item["hygiene_reason"] = reasons
        payload.append(item)
    return payload


def _get_runner() -> PipelineRunner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner(config_path="config.yaml")
    return _runner


@router.get("/", response_model=RegistryListResponse)
async def list_sources():
    runner = _get_runner()
    payload_sources = _build_sources_payload([s.to_dict() for s in runner.registry.list_all()])
    return {"total": len(payload_sources), "sources": payload_sources}


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    runner = _get_runner()
    stats = runner.registry.get_statistics()
    chroma_stats = runner.chroma_manager.get_stats()
    sources = [s.to_dict() for s in runner.registry.list_all()]
    focus_sources = [row for row in sources if _is_focus_source(row)]
    classified = _build_sources_payload(sources)
    archive_candidates = sum(
        1 for row in classified if _normalize(row.get("recommended_hygiene_action")) == "archive"
    )
    processing_stale = sum(
        1
        for row in classified
        if _normalize(row.get("status")).lower() == "processing" and int(row.get("blocks_count") or 0) == 0
    )

    review_queue_items = 0
    review_queue_path = Path("TO_DO_LIST/logs/PRD-046.0.7/review_queue.json")
    if review_queue_path.exists():
        try:
            review_queue_items = int(
                (json.loads(review_queue_path.read_text(encoding="utf-8"))).get("review_items_count")
                or 0
            )
        except Exception:
            review_queue_items = 0

    return {
        "total_sources": stats.get("total_sources", 0),
        "total_blocks": stats.get("total_blocks", 0),
        "chroma_total": chroma_stats.get("total", 0),
        # Legacy compatibility field: SD is decommissioned from admin semantics.
        "sd_distribution": {},
        "sources_by_type": stats.get("sources_by_type", {}),
        "legacy_sd_active": False,
        "governance_readiness": {
            "focus_source_count": len(focus_sources),
            "focus_source_blocks": int(focus_sources[0].get("blocks_count") or 0) if focus_sources else 0,
            "archive_candidate_sources": archive_candidates,
            "processing_stale_sources": processing_stale,
            "review_queue_items": review_queue_items,
        },
    }


@router.delete("/{source_id}")
async def delete_source(source_id: str):
    runner = _get_runner()
    source = runner.registry.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    source_dict = source.to_dict()
    if _is_focus_source(source_dict):
        raise HTTPException(status_code=403, detail="Focus source deletion is forbidden")
    if int(source_dict.get("blocks_count") or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Hard delete for sources with blocks_count > 0 is forbidden in hygiene mode",
        )

    deleted = runner.chroma_manager.delete_source(source_id)
    removed = runner.registry.delete_source(source_id)
    files_deleted: list[str] = []

    file_paths = source.file_paths or {}
    upload_path = file_paths.get("upload")
    if upload_path:
        path = Path(str(upload_path))
        if path.exists():
            path.unlink()
            files_deleted.append(str(path))

    json_path = file_paths.get("json")
    if json_path:
        path = Path(str(json_path))
        if path.exists():
            path.unlink()
            files_deleted.append(str(path))

    base_dir = Path(runner.json_exporter.base_dir)
    for subdir in ("books", "youtube"):
        dir_path = base_dir / subdir
        if not dir_path.exists():
            continue
        for f in dir_path.glob(f"*{source_id}*"):
            if f.exists():
                f.unlink()
                files_deleted.append(str(f))

    return {"deleted": deleted, "removed": removed, "files_deleted": files_deleted}


@router.get("/export/merged")
async def export_merged():
    runner = _get_runner()
    exporter = JSONExporter(runner.json_exporter.base_dir)
    path = exporter.export_all_merged()
    return {"path": path}
