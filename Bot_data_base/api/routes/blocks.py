from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from pipeline_runner import PipelineRunner

router = APIRouter()

_runner: PipelineRunner | None = None


def _get_runner() -> PipelineRunner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner(config_path="config.yaml")
    return _runner


def _resolve_blocks_path(source_id: str, source_type: str, file_paths: dict | None) -> Path | None:
    # Primary: json path from registry entry.
    if file_paths:
        json_path = file_paths.get("json")
        if json_path:
            path = Path(str(json_path))
            if path.exists():
                return path

    # Fallback: exported folder naming convention.
    runner = _get_runner()
    base_dir = Path(runner.json_exporter.base_dir)
    subdir = "youtube" if source_type == "youtube" else "books"
    fallback = base_dir / subdir / f"{source_id}_blocks.json"
    if fallback.exists():
        return fallback
    return None


@router.get("/{source_id}")
async def get_source_blocks(source_id: str):
    """
    Совместимый endpoint для bot_psychologist:
    GET /api/blocks/{source_id} -> {"blocks": [...]}.
    """
    runner = _get_runner()
    source = runner.registry.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"source '{source_id}' not found")

    path = _resolve_blocks_path(source_id, source.source_type, source.file_paths)
    if path is None:
        raise HTTPException(status_code=404, detail=f"blocks for '{source_id}' not found")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to read blocks json: {exc}")

    blocks = payload.get("blocks", []) if isinstance(payload, dict) else []
    return {
        "source_id": source.source_id,
        "source_type": source.source_type,
        "blocks_count": len(blocks),
        "blocks": blocks,
    }

