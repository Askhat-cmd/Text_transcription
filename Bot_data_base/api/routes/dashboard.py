from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from pipeline_runner import PipelineRunner
from storage.chroma_runtime_health import get_chroma_runtime_health

router = APIRouter()

_runner: PipelineRunner | None = None


def _normalize(value: object) -> str:
    return str(value or "").strip()


def _to_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


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


def _extract_source_id(block: dict[str, Any]) -> str:
    source_value = _normalize(block.get("source"))
    if ":" in source_value:
        return _normalize(source_value.split(":", 1)[1])
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
    trace = governance.get("source_trace") if isinstance(governance.get("source_trace"), dict) else {}
    return _normalize(trace.get("source_id") or metadata.get("source_id"))


def _load_blocks_payload(runner: PipelineRunner) -> dict[str, Any] | None:
    merged_path = Path(runner.json_exporter.base_dir) / "all_blocks_merged.json"
    payload = _read_json(merged_path)
    if payload is not None:
        return payload
    fallback = _resolve_existing_path("Bot_data_base/data/processed/all_blocks_merged.json")
    return _read_json(fallback)


def _governance_summary(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(blocks)
    if total <= 0:
        return {
            "readiness": "unknown",
            "governance_present_rate": 0.0,
            "allowed_use_present_rate": 0.0,
            "safety_flags_present_rate": 0.0,
            "legacy_sd_active": False,
        }

    governance_present = 0
    allowed_use_present = 0
    safety_flags_present = 0
    legacy_sd_active = False

    for block in blocks:
        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        governance = metadata.get("governance") if isinstance(metadata.get("governance"), dict) else {}
        if governance:
            governance_present += 1
            allowed_use = governance.get("allowed_use") if isinstance(governance.get("allowed_use"), list) else []
            safety_flags = governance.get("safety_flags") if isinstance(governance.get("safety_flags"), list) else []
            if allowed_use:
                allowed_use_present += 1
            if safety_flags:
                safety_flags_present += 1
            if "sd_level" in governance or "sd_distribution" in governance:
                legacy_sd_active = True

    governance_rate = governance_present / total
    allowed_rate = allowed_use_present / total
    safety_rate = safety_flags_present / total
    # Legacy SD metadata may still be present in historical blocks, but it is not
    # an active readiness authority signal.
    readiness = "ready" if governance_rate >= 1.0 and allowed_rate >= 1.0 and safety_rate >= 1.0 else "warning"

    return {
        "readiness": readiness,
        "governance_present_rate": round(governance_rate, 4),
        "allowed_use_present_rate": round(allowed_rate, 4),
        "safety_flags_present_rate": round(safety_rate, 4),
        "legacy_sd_active": legacy_sd_active,
    }


def _load_enrichment_summary() -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []

    scorecard_path = _resolve_existing_path("TO_DO_LIST/logs/PRD-046.0.9-RUN1/real_enrichment_scorecard.json")
    queue_path = _resolve_existing_path("TO_DO_LIST/logs/PRD-046.0.9-RUN1/review_queue_after_real_enrichment.json")

    scorecard = _read_json(scorecard_path)
    queue = _read_json(queue_path)

    if scorecard is None:
        warnings.append("enrichment_scorecard_missing")
    if queue is None:
        warnings.append("review_queue_artifact_missing")

    priority_counts = queue.get("priority_counts") if isinstance((queue or {}).get("priority_counts"), dict) else {}

    provider_status = _normalize((scorecard or {}).get("provider_status")) or "unknown"
    items_completed = _to_int((scorecard or {}).get("items_completed"))
    validation_errors_count = _to_int((scorecard or {}).get("validation_errors_count"))
    validation_warnings_count = _to_int((scorecard or {}).get("validation_warnings_count"))
    review_queue_items_count = _to_int((queue or {}).get("items_count")) or _to_int(
        (scorecard or {}).get("review_queue_items_count")
    )

    return (
        {
            "provider_status": provider_status,
            "items_completed": items_completed,
            "validation_errors_count": validation_errors_count,
            "validation_warnings_count": validation_warnings_count,
            "review_queue_items_count": review_queue_items_count,
            "p0": _to_int(priority_counts.get("P0")),
            "p1": _to_int(priority_counts.get("P1")),
            "p2": _to_int(priority_counts.get("P2")),
            "production_apply_performed": bool((scorecard or {}).get("production_apply_performed", False)),
        },
        warnings,
    )


def _build_recent_sources(raw_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_sources = sorted(
        raw_sources,
        key=lambda row: _normalize(row.get("processed_at") or row.get("added_at")),
        reverse=True,
    )
    recent: list[dict[str, Any]] = []
    for row in sorted_sources[:5]:
        focus = _is_focus_source(row)
        recent.append(
            {
                "source_id": _normalize(row.get("source_id")),
                "title": _normalize(row.get("title")) or _normalize(row.get("source_id")),
                "status": _normalize(row.get("status")) or "unknown",
                "blocks": _to_int(row.get("blocks_count")),
                "hygiene_action": "keep" if focus else "manual_review",
                "protected": focus,
            }
        )
    return recent


def _is_payload_valid(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not isinstance(payload.get("sources"), dict):
        missing.append("sources")
    if not isinstance(payload.get("blocks"), dict):
        missing.append("blocks")
    if not isinstance(payload.get("chroma"), dict):
        missing.append("chroma")
    if not isinstance(payload.get("governance"), dict):
        missing.append("governance")
    if not isinstance(payload.get("enrichment"), dict):
        missing.append("enrichment")
    if not isinstance(payload.get("recent_sources"), list):
        missing.append("recent_sources")
    return len(missing) == 0, missing


def _build_dashboard_summary() -> dict[str, Any]:
    runner = _get_runner()
    warnings: list[str] = []

    raw_sources = [s.to_dict() for s in runner.registry.list_all()]
    stats = runner.registry.get_statistics()

    archived_sources = sum(1 for row in raw_sources if _normalize(row.get("status")).lower() == "archived")
    failed_sources = sum(1 for row in raw_sources if _normalize(row.get("status")).lower() == "failed")
    zero_block_sources = sum(1 for row in raw_sources if _to_int(row.get("blocks_count")) <= 0)
    protected_sources = sum(1 for row in raw_sources if _is_focus_source(row))
    active_sources = sum(
        1
        for row in raw_sources
        if _normalize(row.get("status")).lower() in {"done", "processing"} and _to_int(row.get("blocks_count")) > 0
    )

    focus_source_blocks = sum(
        _to_int(row.get("blocks_count"))
        for row in raw_sources
        if _normalize(row.get("status")).lower() in {"done", "processing"} and _is_focus_source(row)
    )
    active_source_blocks = sum(
        _to_int(row.get("blocks_count"))
        for row in raw_sources
        if _normalize(row.get("status")).lower() in {"done", "processing"}
    )
    production_blocks = focus_source_blocks if focus_source_blocks > 0 else active_source_blocks

    chroma_health = get_chroma_runtime_health("config.yaml")
    chroma_status = _normalize(chroma_health.get("status")).lower() or "unavailable"
    chroma_count = _to_int(chroma_health.get("count"))
    if chroma_status != "ok":
        warnings.append("Chroma unavailable")

    blocks_payload = _load_blocks_payload(runner)
    blocks = blocks_payload.get("blocks") if isinstance((blocks_payload or {}).get("blocks"), list) else []
    indexed_source_ids = [
        _normalize(item)
        for item in (chroma_health.get("source_ids") if isinstance(chroma_health.get("source_ids"), list) else [])
        if _normalize(item)
    ]
    if not indexed_source_ids:
        indexed_source_ids = sorted({sid for sid in (_extract_source_id(block) for block in blocks) if sid})
    if not indexed_source_ids:
        indexed_source_ids = sorted(
            {
                _normalize(row.get("source_id"))
                for row in raw_sources
                if _normalize(row.get("status")).lower() in {"done", "processing"} and _to_int(row.get("blocks_count")) > 0
            }
        )

    governance = _governance_summary(blocks)
    if governance["readiness"] != "ready":
        warnings.append("governance_readiness_not_ready")

    enrichment, enrichment_warnings = _load_enrichment_summary()
    warnings.extend(enrichment_warnings)

    if enrichment["provider_status"] == "unknown":
        warnings.append("enrichment_state_unknown")

    payload = {
        "schema_version": "botdb_dashboard_summary_v1",
        "status": "ok",
        "generated_at": _utc_now(),
        "sources": {
            "total": _to_int(stats.get("total_sources")),
            "active": active_sources,
            "protected": protected_sources,
            "archived": archived_sources,
            "failed": failed_sources,
            "zero_block": zero_block_sources,
        },
        "blocks": {
            "production_total": production_blocks,
            "active_source_blocks": active_source_blocks,
            "registry_total": _to_int(stats.get("total_blocks")),
        },
        "chroma": {
            "status": chroma_status,
            "count": chroma_count,
            "indexed_source_ids": indexed_source_ids,
        },
        "governance": governance,
        "enrichment": enrichment,
        "recent_sources": _build_recent_sources(raw_sources),
        "warnings": sorted(set(warnings)),
    }
    valid, missing = _is_payload_valid(payload)
    if not valid:
        payload["status"] = "warning"
        payload["warnings"] = sorted(set(list(payload.get("warnings", [])) + [f"missing_fields:{','.join(missing)}"]))
    return payload


def _get_runner() -> PipelineRunner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner(config_path="config.yaml")
    return _runner


@router.get("")
@router.get("/")
async def get_dashboard_summary() -> dict[str, Any]:
    return _build_dashboard_summary()
