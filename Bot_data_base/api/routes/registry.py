from fastapi import APIRouter

from api.schemas import RegistryListResponse, StatsResponse
from pipeline_runner import PipelineRunner
from storage.json_export import JSONExporter

router = APIRouter()

_runner: PipelineRunner | None = None


def _get_runner() -> PipelineRunner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner(config_path="config.yaml")
    return _runner


@router.get("/", response_model=RegistryListResponse)
async def list_sources():
    runner = _get_runner()
    sources = runner.registry.list_all()
    return {"total": len(sources), "sources": [s.to_dict() for s in sources]}


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    runner = _get_runner()
    stats = runner.registry.get_statistics()
    chroma_stats = runner.chroma_manager.get_stats()
    return {
        "total_sources": stats.get("total_sources", 0),
        "total_blocks": stats.get("total_blocks", 0),
        "chroma_total": chroma_stats.get("total", 0),
        "sd_distribution": stats.get("sd_distribution", {}),
        "sources_by_type": stats.get("sources_by_type", {}),
    }


@router.delete("/{source_id}")
async def delete_source(source_id: str):
    runner = _get_runner()
    deleted = runner.chroma_manager.delete_source(source_id)
    removed = runner.registry.delete_source(source_id)
    return {"deleted": deleted, "removed": removed}


@router.get("/export/merged")
async def export_merged():
    runner = _get_runner()
    exporter = JSONExporter(runner.json_exporter.base_dir)
    path = exporter.export_all_merged()
    return {"path": path}

