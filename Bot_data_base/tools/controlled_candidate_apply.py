from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
REPO_ROOT = BOTDB_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from models.universal_block import UniversalBlock
from review.review_queue_builder import build_review_queue
from storage.chroma_manager import ChromaManager
from tools.clean_source_reprocess import (
    build_mixed_intent_audit_report,
    build_practice_taxonomy_report,
)
from tools.legacy_sd_usage_audit import ACTIVE_SD_PATTERNS, TARGET_FILES, run_legacy_sd_usage_audit
from tools.run_retrieval_eval import load_dataset, run_retrieval_eval, validate_dataset_payload
from tools.source_hygiene_audit import run_audit_cli


DEFAULT_SOURCE_PRD = "PRD-046.0.8.1"
DEFAULT_HF2_GATE_PATH = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-046.0.8-HF2" / "governance_gate.json"
DEFAULT_CANDIDATE_PATH = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-046.0.8-HF2" / "clean_reprocess_candidate.json"
DEFAULT_ALL_BLOCKS_PATH = BOTDB_DIR / "data" / "processed" / "all_blocks_merged.json"
DEFAULT_REGISTRY_PATH = BOTDB_DIR / "data" / "registry.json"
DEFAULT_CONFIG_PATH = BOTDB_DIR / "config.yaml"
DEFAULT_OLD_REVIEW_QUEUE_PATH = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-046.0.7" / "review_queue.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-046.0.8.1"
DEFAULT_REPORTS_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
DEFAULT_DATASET_PATH = BOTDB_DIR / "eval" / "retrieval_eval_v1.json"
EXPECTED_SOURCE_ID = "123__кузница_духа"
EXPECTED_CANDIDATE_BLOCKS = 247


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _extract_blocks(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        blocks = payload.get("blocks")
        if isinstance(blocks, list):
            return [row for row in blocks if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _save_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
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


def _split_csv(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _contains_active_legacy_sd() -> bool:
    for rel_path in TARGET_FILES:
        full = REPO_ROOT / rel_path
        if not full.exists():
            continue
        for line in full.read_text(encoding="utf-8", errors="replace").splitlines():
            if any(pattern in line for pattern in ACTIVE_SD_PATTERNS):
                return True
    return False


def _collect_completeness(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    total = max(1, len(blocks))
    source_id_consistent = 0
    governance_present = 0
    chunking_present = 0
    allowed_use_present = 0
    safety_flags_present = 0

    for block in blocks:
        if _source_id_from_block(block):
            source_id_consistent += 1
        meta = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        governance = meta.get("governance") if isinstance(meta.get("governance"), dict) else {}
        chunking = meta.get("chunking_quality") if isinstance(meta.get("chunking_quality"), dict) else {}
        if governance:
            governance_present += 1
        if chunking:
            chunking_present += 1
        if isinstance(governance.get("allowed_use"), list) and governance.get("allowed_use"):
            allowed_use_present += 1
        if isinstance(governance.get("safety_flags"), list) and governance.get("safety_flags"):
            safety_flags_present += 1

    return {
        "candidate_blocks_count": len(blocks),
        "source_id_consistency_rate": round(source_id_consistent / total, 6),
        "governance_present_rate": round(governance_present / total, 6),
        "chunking_quality_present_rate": round(chunking_present / total, 6),
        "allowed_use_present_rate": round(allowed_use_present / total, 6),
        "safety_flags_present_rate": round(safety_flags_present / total, 6),
    }


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _resolve_botdb_path(path_value: str) -> str:
    raw = Path(path_value)
    if raw.is_absolute():
        return str(raw)
    return str((BOTDB_DIR / raw).resolve())


def _probe_chroma(config_path: Path) -> dict[str, Any]:
    cfg = _load_config(config_path)
    storage_cfg = cfg.get("storage") or {}
    embed_cfg = cfg.get("embedding") or {}
    db_path = _resolve_botdb_path(str(storage_cfg.get("chroma_db_path") or "data/chroma_db"))
    collection_name = str(storage_cfg.get("collection_name") or "bot_knowledge_base")
    model_name = str(embed_cfg.get("model") or "").strip() or None
    manager = ChromaManager(db_path=db_path, collection_name=collection_name, embedding_model_name=model_name)
    health = manager.probe_collection_health()

    source_ids: list[str] = []
    ids_sample: list[str] = []
    try:
        sample = manager._collection.get(limit=min(500, max(1, _to_int(health.get("collection_count")))), include=["metadatas"])  # noqa: SLF001
        ids = sample.get("ids") if isinstance(sample, dict) else []
        if isinstance(ids, list):
            ids_sample = [str(item) for item in ids[:20]]
        metas = sample.get("metadatas") if isinstance(sample, dict) else []
        if isinstance(metas, list):
            for meta in metas:
                if not isinstance(meta, dict):
                    continue
                sid = _normalize(meta.get("source_id"))
                if sid and sid not in source_ids:
                    source_ids.append(sid)
    except Exception:
        pass

    return {
        "generated_at": _utc_now(),
        "db_path": db_path,
        "collection_name": collection_name,
        "embedding_model_name": health.get("embedding_model_name"),
        "collection_count": _to_int(health.get("collection_count")),
        "ids_sample": ids_sample,
        "source_ids_sample": sorted(source_ids),
    }


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 20.0) -> dict[str, Any]:
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(
        url=url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else None
            return {"ok": True, "status_code": int(resp.status), "body": parsed, "error": None}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_error = json.loads(raw) if raw else None
        except Exception:
            parsed_error = {"raw": raw[:500]}
        return {"ok": False, "status_code": int(exc.code), "body": parsed_error, "error": str(exc)}
    except URLError as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status_code": None, "body": None, "error": str(exc)}


def build_apply_preflight(
    *,
    source_prd: str,
    hf2_gate: dict[str, Any],
    candidate_blocks: list[dict[str, Any]],
    production_blocks: list[dict[str, Any]],
    registry_records: list[dict[str, Any]],
    chroma_probe: dict[str, Any],
    expected_source_id: str = EXPECTED_SOURCE_ID,
    expected_candidate_blocks: int = EXPECTED_CANDIDATE_BLOCKS,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    gate_status = _normalize(hf2_gate.get("status"))
    ready_for_apply = bool(hf2_gate.get("candidate_ready_for_apply"))
    if gate_status != "passed":
        blockers.append("hf2_gate_not_passed")
    if not ready_for_apply:
        blockers.append("hf2_candidate_ready_false")

    candidate_source_ids = sorted({_source_id_from_block(block) for block in candidate_blocks if _source_id_from_block(block)})
    candidate_source_id = candidate_source_ids[0] if len(candidate_source_ids) == 1 else ""
    if not candidate_source_id:
        blockers.append("candidate_source_id_missing_or_mixed")
    if candidate_source_id and candidate_source_id != expected_source_id:
        blockers.append("candidate_source_id_unexpected")

    if len(candidate_blocks) <= 0:
        blockers.append("candidate_blocks_empty")
    if len(candidate_blocks) != expected_candidate_blocks:
        warnings.append("candidate_blocks_count_differs_from_expected_247")

    completeness = _collect_completeness(candidate_blocks)
    if completeness["source_id_consistency_rate"] < 1.0:
        blockers.append("candidate_source_id_consistency_not_full")
    if completeness["governance_present_rate"] < 1.0:
        blockers.append("candidate_governance_incomplete")
    if completeness["chunking_quality_present_rate"] < 1.0:
        blockers.append("candidate_chunking_quality_incomplete")
    if completeness["allowed_use_present_rate"] < 1.0:
        blockers.append("candidate_allowed_use_incomplete")
    if completeness["safety_flags_present_rate"] < 1.0:
        blockers.append("candidate_safety_flags_incomplete")

    focus_done_rows = [
        row
        for row in registry_records
        if _normalize(row.get("source_id")) == expected_source_id and _normalize(row.get("status")) == "done"
    ]
    if len(focus_done_rows) != 1:
        blockers.append("registry_focus_source_done_row_not_single")

    active_non_archived_with_blocks = [
        row
        for row in registry_records
        if _normalize(row.get("status")) in {"done", "processing"} and _to_int(row.get("blocks_count")) > 0
    ]
    if len(active_non_archived_with_blocks) != 1:
        blockers.append("registry_active_source_count_not_one")

    if _contains_active_legacy_sd():
        blockers.append("legacy_sd_active_detected")

    if _to_int(hf2_gate.get("mixed_intent_unresolved_count")) > 0:
        blockers.append("mixed_intent_unresolved_present")
    if _to_int(hf2_gate.get("mixed_intent_split_required_count")) > 0:
        blockers.append("mixed_intent_split_required_present")
    if _to_int(hf2_gate.get("direct_practice_misclassified_count")) > 0:
        blockers.append("direct_practice_misclassified_present")
    if _to_int(hf2_gate.get("unsafe_practice_suggestion_count")) > 0:
        blockers.append("unsafe_practice_suggestion_present")

    return {
        "schema_version": "controlled_candidate_apply_preflight_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "passed": len(blockers) == 0,
        "blockers": blockers,
        "warnings": warnings,
        "hf2_gate_status": gate_status,
        "candidate_ready_for_apply": ready_for_apply,
        "active_source_id": expected_source_id,
        "candidate_source_ids": candidate_source_ids,
        "candidate_blocks_count": len(candidate_blocks),
        "production_blocks_before": len(production_blocks),
        "chroma_count_before": _to_int(chroma_probe.get("collection_count")),
        "legacy_sd_active": _contains_active_legacy_sd(),
        "mixed_intent_unresolved_count": _to_int(hf2_gate.get("mixed_intent_unresolved_count")),
        "direct_practice_misclassified_count": _to_int(hf2_gate.get("direct_practice_misclassified_count")),
        "unsafe_practice_suggestion_count": _to_int(hf2_gate.get("unsafe_practice_suggestion_count")),
        "completeness": completeness,
    }


def build_apply_plan(
    *,
    source_prd: str,
    preflight: dict[str, Any],
    candidate_blocks_count: int,
    production_blocks_before: int,
    source_id: str,
    all_blocks_path: Path,
    registry_path: Path,
    source_export_path: Path,
    backups_dir: Path,
) -> dict[str, Any]:
    files_to_mutate = [
        str(all_blocks_path),
        str(registry_path),
        str(source_export_path),
    ]
    backups = {
        "all_blocks_merged_before": str(backups_dir / "all_blocks_merged.before.json"),
        "registry_before": str(backups_dir / "registry.before.json"),
        "review_queue_before": str(backups_dir / "review_queue.before.json"),
        "chroma_manifest_before": str(backups_dir / "chroma_manifest.before.json"),
        "candidate_snapshot": str(backups_dir / "candidate_to_apply.snapshot.json"),
        "apply_plan_snapshot": str(backups_dir / "apply_plan.snapshot.json"),
    }
    return {
        "schema_version": "controlled_candidate_apply_plan_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "preflight_passed": bool(preflight.get("passed")),
        "production_blocks_before": production_blocks_before,
        "candidate_blocks_after": candidate_blocks_count,
        "block_count_delta": candidate_blocks_count - production_blocks_before,
        "affected_source_id": source_id,
        "files_to_mutate": files_to_mutate,
        "registry_fields_to_update": [
            "blocks_count",
            "status",
            "processed_at",
            "pipeline_version",
            "file_paths.json",
            "sd_distribution",
        ],
        "chroma_operation_plan": {
            "action": "reset_and_reindex",
            "expected_chroma_count_after": candidate_blocks_count,
        },
        "review_queue_stale_handling": {
            "old_queue_mutated": False,
            "new_artifact": "review_queue_staleness_report.json",
            "new_baseline": "review_queue_new_baseline.json",
        },
        "backup_paths": backups,
        "expected_post_apply_counts": {
            "production_blocks_after": candidate_blocks_count,
            "registry_focus_blocks_after": candidate_blocks_count,
            "chroma_count_after": candidate_blocks_count,
        },
        "forbidden_mutation_checks": [
            "raw_markdown_unchanged",
            "runtime_logic_unchanged",
            "writer_unchanged",
            "diagnostic_center_unchanged",
        ],
    }


def build_registry_update(
    *,
    registry_records: list[dict[str, Any]],
    source_id: str,
    source_export_path: Path,
    candidate_blocks_count: int,
    source_prd: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = copy.deepcopy(registry_records)
    updated_index = -1
    for idx, row in enumerate(records):
        if _normalize(row.get("source_id")) == source_id and _normalize(row.get("status")) == "done":
            updated_index = idx
            break
    if updated_index < 0:
        for idx, row in enumerate(records):
            if _normalize(row.get("source_id")) == source_id:
                updated_index = idx
                break
    if updated_index < 0:
        raise RuntimeError(f"Focus source row not found in registry: {source_id}")

    row = records[updated_index]
    row["status"] = "done"
    row["blocks_count"] = int(candidate_blocks_count)
    row["processed_at"] = _utc_now()
    row["sd_distribution"] = {}
    old_pipeline = _normalize(row.get("pipeline_version")) or "bot_data_base_v1.0"
    marker = f"candidate_apply_{source_prd}"
    if marker not in old_pipeline:
        row["pipeline_version"] = f"{old_pipeline}+{marker}"
    file_paths = row.get("file_paths") if isinstance(row.get("file_paths"), dict) else {}
    file_paths["json"] = str(source_export_path)
    row["file_paths"] = file_paths
    records[updated_index] = row
    return records, {"updated_index": updated_index, "updated_source_id": source_id}


def verify_no_unplanned_mutation(
    *,
    before_hashes: dict[str, str],
    after_hashes: dict[str, str],
    allowed_mutated_paths: set[str],
) -> dict[str, Any]:
    mutated: list[str] = []
    unexpected: list[str] = []
    for path, before_hash in before_hashes.items():
        after_hash = after_hashes.get(path, "")
        if before_hash != after_hash:
            mutated.append(path)
            if path not in allowed_mutated_paths:
                unexpected.append(path)
    return {
        "mutated_paths": sorted(mutated),
        "unexpected_mutations": sorted(unexpected),
        "passed": len(unexpected) == 0,
    }


def build_review_queue_staleness_report(
    *,
    old_review_queue_payload: dict[str, Any] | None,
    old_review_queue_path: Path,
    old_all_blocks_sha: str,
    new_all_blocks_sha: str,
    candidate_blocks_count: int,
) -> dict[str, Any]:
    old_input_sha = ""
    old_items_count = 0
    if isinstance(old_review_queue_payload, dict):
        old_input_sha = _normalize(old_review_queue_payload.get("input_file_sha256_before"))
        old_items_count = _to_int(old_review_queue_payload.get("review_items_count"))
    stale = bool(old_input_sha and old_input_sha != new_all_blocks_sha)
    return {
        "schema_version": "review_queue_staleness_report_v1",
        "generated_at": _utc_now(),
        "old_review_queue_path": str(old_review_queue_path),
        "old_review_queue_exists": old_review_queue_path.exists(),
        "old_review_items_count": old_items_count,
        "old_input_sha256_before": old_input_sha,
        "all_blocks_sha_before_apply": old_all_blocks_sha,
        "all_blocks_sha_after_apply": new_all_blocks_sha,
        "candidate_blocks_count": candidate_blocks_count,
        "stale": stale,
        "reason": "block_boundaries_changed_after_reprocess" if stale else "queue_can_be_reused",
        "action": "rebuild_new_review_queue_baseline",
    }


def _build_source_export_payload(
    *,
    source_id: str,
    source_type: str,
    candidate_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "bot_data_base_v1.0",
        "source_id": source_id,
        "source_type": source_type,
        "generated_at": _utc_now(),
        "blocks_count": len(candidate_blocks),
        "blocks": candidate_blocks,
    }


def _build_all_blocks_payload(candidate_blocks: list[dict[str, Any]], old_payload: Any) -> dict[str, Any]:
    schema_version = "bot_data_base_v1.0"
    if isinstance(old_payload, dict):
        schema_version = _normalize(old_payload.get("schema_version")) or schema_version
    return {
        "schema_version": schema_version,
        "generated_at": _utc_now(),
        "blocks_count": len(candidate_blocks),
        "blocks": candidate_blocks,
    }


def _capture_hashes(paths: list[Path]) -> dict[str, str]:
    payload: dict[str, str] = {}
    for path in paths:
        payload[str(path)] = _sha256_file(path) if path.exists() else ""
    return payload


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _to_universal_block(raw: dict[str, Any]) -> UniversalBlock:
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


def run_chroma_reindex(
    *,
    config_path: Path,
    blocks: list[dict[str, Any]],
    source_id: str,
) -> dict[str, Any]:
    cfg = _load_config(config_path)
    storage_cfg = cfg.get("storage") or {}
    embed_cfg = cfg.get("embedding") or {}
    db_path = _resolve_botdb_path(str(storage_cfg.get("chroma_db_path") or "data/chroma_db"))
    collection_name = str(storage_cfg.get("collection_name") or "bot_knowledge_base")
    model_name = str(embed_cfg.get("model") or "").strip() or None
    manager = ChromaManager(db_path=db_path, collection_name=collection_name, embedding_model_name=model_name)
    before = manager.probe_collection_health()
    before_count = _to_int(before.get("collection_count"))
    manager.reset_collection()
    indexed = manager.add_blocks([_to_universal_block(block) for block in blocks])
    after = manager.probe_collection_health()
    after_count = _to_int(after.get("collection_count"))
    indexed_source_ids = sorted({_source_id_from_block(block) for block in blocks if _source_id_from_block(block)})
    return {
        "schema_version": "candidate_apply_chroma_reindex_result_v1",
        "generated_at": _utc_now(),
        "db_path": db_path,
        "collection_name": collection_name,
        "embedding_model_name": model_name,
        "source_id_expected": source_id,
        "indexed_source_ids": indexed_source_ids,
        "chroma_count_before": before_count,
        "chroma_count_after": after_count,
        "indexed_blocks_count": indexed,
        "status": "passed" if after_count == len(blocks) else "failed",
    }


def run_api_smoke(*, api_base_url: str) -> dict[str, Any]:
    base = api_base_url.rstrip("/")
    status_resp = _http_json("GET", f"{base}/api/status/")
    test_queries = [
        {"label": "semantic_basic", "payload": {"query": "я чувствую вину когда выбираю себя", "top_k": 5, "pre_filter_k": 20, "use_rerank": False}},
        {"label": "sd_level_compat", "payload": {"query": "мне нужна безопасная практика за 5 минут", "top_k": 5, "pre_filter_k": 20, "use_rerank": False, "sd_level": 6}},
        {"label": "practice_like", "payload": {"query": "дай мягкую практику когда мало сил", "top_k": 5, "pre_filter_k": 20, "use_rerank": False}},
        {"label": "theory_lens", "payload": {"query": "почему включается самокритика и стыд", "top_k": 5, "pre_filter_k": 20, "use_rerank": False}},
        {"label": "non_safety", "payload": {"query": "я прокрастинирую и боюсь оценки", "top_k": 5, "pre_filter_k": 20, "use_rerank": False}},
    ]
    rows: list[dict[str, Any]] = []
    internal_only_unsafe = 0
    governance_missing = 0
    sd_filter_applied_true = 0

    for row in test_queries:
        response = _http_json("POST", f"{base}/api/query/", payload=row["payload"])
        body = response.get("body") if isinstance(response.get("body"), dict) else {}
        chunks = body.get("chunks") if isinstance(body, dict) and isinstance(body.get("chunks"), list) else []
        sd_filter_applied = bool(body.get("sd_filter_applied")) if isinstance(body, dict) else False
        if sd_filter_applied:
            sd_filter_applied_true += 1
        safe_hits: list[dict[str, Any]] = []
        for chunk in chunks[:5]:
            governance = chunk.get("governance") if isinstance(chunk.get("governance"), dict) else {}
            allowed_use = _split_csv(governance.get("allowed_use"))
            if not governance:
                governance_missing += 1
            if row["label"] == "non_safety" and any(item.lower() == "internal_only" for item in allowed_use):
                internal_only_unsafe += 1
            safe_hits.append(
                {
                    "id": chunk.get("chunk_id"),
                    "score": chunk.get("score"),
                    "chunk_type": governance.get("chunk_type"),
                    "allowed_use": allowed_use,
                    "safety_flags": _split_csv(governance.get("safety_flags")),
                }
            )
        rows.append(
            {
                "label": row["label"],
                "status": "ok" if response.get("ok") else "error",
                "http_status": response.get("status_code"),
                "hits_count": len(chunks),
                "sd_filter_applied": sd_filter_applied,
                "error": response.get("error"),
                "top_hits": safe_hits,
            }
        )

    return {
        "schema_version": "api_retrieval_smoke_v1",
        "generated_at": _utc_now(),
        "api_base_url": base,
        "status_ok": bool(status_resp.get("ok")),
        "status_http": status_resp.get("status_code"),
        "query_rows": rows,
        "query_hits_positive": sum(1 for row in rows if _to_int(row.get("hits_count")) > 0),
        "sd_filter_applied_true_count": sd_filter_applied_true,
        "internal_only_unsafe_exposure_count": internal_only_unsafe,
        "governance_missing_count": governance_missing,
    }


def _build_consistency_report(
    *,
    source_prd: str,
    candidate_blocks: list[dict[str, Any]],
    production_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_ids = {_normalize(block.get("id")) for block in candidate_blocks if _normalize(block.get("id"))}
    production_ids = {_normalize(block.get("id")) for block in production_blocks if _normalize(block.get("id"))}
    candidate_sources = sorted({_source_id_from_block(block) for block in candidate_blocks if _source_id_from_block(block)})
    production_sources = sorted({_source_id_from_block(block) for block in production_blocks if _source_id_from_block(block)})
    completeness = _collect_completeness(production_blocks)
    return {
        "schema_version": "post_apply_consistency_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "candidate_blocks_count": len(candidate_blocks),
        "production_blocks_count": len(production_blocks),
        "candidate_source_ids": candidate_sources,
        "production_source_ids": production_sources,
        "id_overlap_count": len(candidate_ids.intersection(production_ids)),
        "id_only_in_candidate": len(candidate_ids - production_ids),
        "id_only_in_production": len(production_ids - candidate_ids),
        "completeness": completeness,
        "passed": (
            len(candidate_blocks) == len(production_blocks)
            and candidate_sources == production_sources
            and len(candidate_ids - production_ids) == 0
            and len(production_ids - candidate_ids) == 0
        ),
    }


def _render_report_md(title: str, lines: list[str]) -> str:
    body = [f"# {title}", ""]
    body.extend(lines)
    return "\n".join(body).rstrip() + "\n"


def run_controlled_candidate_apply(
    *,
    source_prd: str,
    mode: str,
    confirm: bool,
    hf2_gate_path: Path,
    candidate_path: Path,
    all_blocks_path: Path,
    registry_path: Path,
    old_review_queue_path: Path,
    output_dir: Path,
    reports_dir: Path,
    config_path: Path,
    api_base_url: str,
    dataset_path: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    backups_dir = output_dir / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    hf2_gate = _load_json(hf2_gate_path)
    candidate_payload = _load_json(candidate_path)
    candidate_blocks = _extract_blocks((candidate_payload.get("candidate") or {}).get("blocks"))
    all_blocks_payload_before = _load_json(all_blocks_path)
    production_blocks_before = _extract_blocks(all_blocks_payload_before)
    registry_records_before = _load_json(registry_path)
    if not isinstance(registry_records_before, list):
        raise RuntimeError("registry.json must be a list")

    source_ids = sorted({_source_id_from_block(block) for block in candidate_blocks if _source_id_from_block(block)})
    source_id = source_ids[0] if len(source_ids) == 1 else EXPECTED_SOURCE_ID
    source_type = "book"
    if candidate_blocks:
        meta = candidate_blocks[0].get("metadata") if isinstance(candidate_blocks[0].get("metadata"), dict) else {}
        source_type = _normalize(meta.get("source_type")) or source_type

    focus_row = next((row for row in registry_records_before if _normalize(row.get("source_id")) == source_id and _normalize(row.get("status")) == "done"), None)
    if focus_row is None:
        focus_row = next((row for row in registry_records_before if _normalize(row.get("source_id")) == source_id), None)
    if focus_row is None:
        raise RuntimeError(f"Focus source row not found for source_id={source_id}")
    source_export_path = Path(_normalize(((focus_row.get("file_paths") or {}).get("json"))))
    if not source_export_path.is_absolute():
        source_export_path = (BOTDB_DIR / source_export_path).resolve()

    chroma_probe_before = _probe_chroma(config_path)
    preflight = build_apply_preflight(
        source_prd=source_prd,
        hf2_gate=hf2_gate,
        candidate_blocks=candidate_blocks,
        production_blocks=production_blocks_before,
        registry_records=registry_records_before,
        chroma_probe=chroma_probe_before,
    )
    _save_json(output_dir / "apply_preflight.json", preflight)

    plan = build_apply_plan(
        source_prd=source_prd,
        preflight=preflight,
        candidate_blocks_count=len(candidate_blocks),
        production_blocks_before=len(production_blocks_before),
        source_id=source_id,
        all_blocks_path=all_blocks_path,
        registry_path=registry_path,
        source_export_path=source_export_path,
        backups_dir=backups_dir,
    )
    _save_json(output_dir / "apply_plan.json", plan)

    if not preflight.get("passed"):
        return {"status": "blocked", "reason": "preflight_failed", "preflight": preflight, "plan": plan}

    if mode == "apply" and not confirm:
        return {"status": "blocked", "reason": "confirm_required_for_apply_mode", "preflight": preflight, "plan": plan}

    _copy_if_exists(all_blocks_path, backups_dir / "all_blocks_merged.before.json")
    _copy_if_exists(registry_path, backups_dir / "registry.before.json")
    _copy_if_exists(old_review_queue_path, backups_dir / "review_queue.before.json")
    _save_json(backups_dir / "candidate_to_apply.snapshot.json", candidate_payload)
    _save_json(backups_dir / "apply_plan.snapshot.json", plan)
    _save_json(backups_dir / "chroma_manifest.before.json", chroma_probe_before)

    target_paths = [
        all_blocks_path,
        registry_path,
        source_export_path,
        BOTDB_DIR / "api" / "routes" / "query.py",
        BOTDB_DIR / "api" / "schemas.py",
    ]
    before_hashes = _capture_hashes(target_paths)
    old_all_blocks_sha = before_hashes.get(str(all_blocks_path), "")

    apply_result: dict[str, Any] = {
        "schema_version": "controlled_candidate_apply_result_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "mode": mode,
        "mutated": False,
    }

    if mode == "apply":
        new_all_blocks_payload = _build_all_blocks_payload(candidate_blocks, all_blocks_payload_before)
        _save_json(all_blocks_path, new_all_blocks_payload)
        source_export_payload = _build_source_export_payload(
            source_id=source_id,
            source_type=source_type,
            candidate_blocks=candidate_blocks,
        )
        _save_json(source_export_path, source_export_payload)
        registry_records_after, registry_update_info = build_registry_update(
            registry_records=registry_records_before,
            source_id=source_id,
            source_export_path=source_export_path,
            candidate_blocks_count=len(candidate_blocks),
            source_prd=source_prd,
        )
        _save_json(registry_path, registry_records_after)
        apply_result["mutated"] = True
        apply_result["registry_update"] = registry_update_info

    after_hashes = _capture_hashes(target_paths)
    mutation_check = verify_no_unplanned_mutation(
        before_hashes=before_hashes,
        after_hashes=after_hashes,
        allowed_mutated_paths={str(all_blocks_path), str(registry_path), str(source_export_path)} if mode == "apply" else set(),
    )
    apply_result["mutation_check"] = mutation_check
    apply_result["all_blocks_hash_before"] = old_all_blocks_sha
    apply_result["all_blocks_hash_after"] = after_hashes.get(str(all_blocks_path), "")
    apply_result["registry_hash_before"] = before_hashes.get(str(registry_path), "")
    apply_result["registry_hash_after"] = after_hashes.get(str(registry_path), "")
    _save_json(output_dir / "apply_result.json", apply_result)

    old_review_queue_payload = _load_json(old_review_queue_path) if old_review_queue_path.exists() else None
    staleness_report = build_review_queue_staleness_report(
        old_review_queue_payload=old_review_queue_payload if isinstance(old_review_queue_payload, dict) else None,
        old_review_queue_path=old_review_queue_path,
        old_all_blocks_sha=old_all_blocks_sha,
        new_all_blocks_sha=after_hashes.get(str(all_blocks_path), ""),
        candidate_blocks_count=len(candidate_blocks),
    )
    _save_json(output_dir / "review_queue_staleness_report.json", staleness_report)

    production_payload_after = _load_json(all_blocks_path)
    production_blocks_after = _extract_blocks(production_payload_after)
    consistency = _build_consistency_report(
        source_prd=source_prd,
        candidate_blocks=candidate_blocks,
        production_blocks=production_blocks_after,
    )
    _save_json(output_dir / "post_apply_consistency.json", consistency)

    quality_summary = {
        "schema_version": "post_apply_kb_quality_audit_v1",
        "source_prd": source_prd,
        "generated_at": _utc_now(),
        "completeness": _collect_completeness(production_blocks_after),
    }
    _save_json(output_dir / "post_apply_kb_quality_audit.json", quality_summary)

    taxonomy_report = build_practice_taxonomy_report(
        source_prd=source_prd,
        candidate_blocks=copy.deepcopy(production_blocks_after),
    )
    _save_json(output_dir / "post_apply_practice_taxonomy_report.json", taxonomy_report)
    mixed_report = build_mixed_intent_audit_report(
        source_prd=source_prd,
        candidate_blocks=copy.deepcopy(production_blocks_after),
    )
    _save_json(output_dir / "post_apply_mixed_intent_audit.json", mixed_report)

    source_hygiene_json = output_dir / "post_apply_source_hygiene_audit.json"
    source_hygiene_md = reports_dir / "PRD-046.0.8.1_SOURCE_HYGIENE_AUDIT_REPORT.md"
    source_hygiene = run_audit_cli(
        output_json=source_hygiene_json,
        output_md=source_hygiene_md,
        registry_path=registry_path,
        all_blocks_path=all_blocks_path,
        focus_hint="кузниц",
        source_prd=source_prd,
    )

    legacy_sd_json = output_dir / "post_apply_legacy_sd_usage_report.json"
    legacy_sd_md = reports_dir / "PRD-046.0.8.1_LEGACY_SD_USAGE_REPORT.md"
    legacy_sd = run_legacy_sd_usage_audit(
        source_prd=source_prd,
        output_json=legacy_sd_json,
        output_md=legacy_sd_md,
    )

    review_queue_new = build_review_queue(
        input_path=all_blocks_path,
        max_items=300,
        source_prd=source_prd,
    )
    _save_json(output_dir / "review_queue_new_baseline.json", review_queue_new)

    chroma_reindex = {
        "schema_version": "candidate_apply_chroma_reindex_result_v1",
        "status": "skipped_dry_run",
    }
    if mode == "apply":
        chroma_reindex = run_chroma_reindex(
            config_path=config_path,
            blocks=production_blocks_after,
            source_id=source_id,
        )
    _save_json(output_dir / "chroma_reindex_result.json", chroma_reindex)

    api_smoke = run_api_smoke(api_base_url=api_base_url)
    _save_json(output_dir / "api_retrieval_smoke.json", api_smoke)

    retrieval_eval_payload: dict[str, Any] = {
        "schema_version": "post_apply_retrieval_eval_v1",
        "status": "skipped",
    }
    if dataset_path.exists():
        dataset = load_dataset(dataset_path)
        dataset["dataset_path"] = str(dataset_path)
        validation_errors = validate_dataset_payload(dataset)
        if validation_errors:
            retrieval_eval_payload = {
                "schema_version": "post_apply_retrieval_eval_v1",
                "status": "dataset_validation_failed",
                "errors": validation_errors,
            }
        else:
            eval_result = run_retrieval_eval(
                dataset=dataset,
                api_base_url=api_base_url,
                top_k=5,
                timeout_seconds=20.0,
                include_sanitized_previews=True,
                fail_on_api_error=False,
            )
            retrieval_eval_payload = {
                "schema_version": "post_apply_retrieval_eval_v1",
                "status": "ok",
                "scorecard": eval_result.get("scorecard"),
                "weak_cases_count": len(eval_result.get("weak_cases") or []),
                "results": eval_result.get("results"),
            }
    _save_json(output_dir / "retrieval_eval_after_reprocess.json", retrieval_eval_payload)

    _save_markdown(
        reports_dir / "PRD-046.0.8.1_PREFLIGHT_REPORT.md",
        _render_report_md(
            "PRD-046.0.8.1 PREFLIGHT REPORT",
            [
                "## Status",
                f"- passed: `{preflight.get('passed')}`",
                f"- blockers: `{len(preflight.get('blockers') or [])}`",
                f"- candidate_blocks_count: `{preflight.get('candidate_blocks_count')}`",
                f"- production_blocks_before: `{preflight.get('production_blocks_before')}`",
                f"- chroma_count_before: `{preflight.get('chroma_count_before')}`",
            ],
        ),
    )
    _save_markdown(
        reports_dir / "PRD-046.0.8.1_APPLY_PLAN_REPORT.md",
        _render_report_md(
            "PRD-046.0.8.1 APPLY PLAN REPORT",
            [
                "## Plan",
                f"- preflight_passed: `{plan.get('preflight_passed')}`",
                f"- block_count_delta: `{plan.get('block_count_delta')}`",
                f"- affected_source_id: `{plan.get('affected_source_id')}`",
                f"- files_to_mutate: `{len(plan.get('files_to_mutate') or [])}`",
            ],
        ),
    )
    _save_markdown(
        reports_dir / "PRD-046.0.8.1_APPLY_RESULT_REPORT.md",
        _render_report_md(
            "PRD-046.0.8.1 APPLY RESULT REPORT",
            [
                "## Result",
                f"- mode: `{mode}`",
                f"- mutated: `{apply_result.get('mutated')}`",
                f"- mutation_check_passed: `{(apply_result.get('mutation_check') or {}).get('passed')}`",
                f"- all_blocks_hash_before: `{apply_result.get('all_blocks_hash_before')}`",
                f"- all_blocks_hash_after: `{apply_result.get('all_blocks_hash_after')}`",
            ],
        ),
    )
    _save_markdown(
        reports_dir / "PRD-046.0.8.1_CHROMA_REINDEX_REPORT.md",
        _render_report_md(
            "PRD-046.0.8.1 CHROMA REINDEX REPORT",
            [
                "## Chroma",
                f"- status: `{chroma_reindex.get('status')}`",
                f"- chroma_count_before: `{chroma_reindex.get('chroma_count_before')}`",
                f"- chroma_count_after: `{chroma_reindex.get('chroma_count_after')}`",
                f"- indexed_source_ids: `{chroma_reindex.get('indexed_source_ids')}`",
            ],
        ),
    )
    _save_markdown(
        reports_dir / "PRD-046.0.8.1_KB_QUALITY_REAUDIT_REPORT.md",
        _render_report_md(
            "PRD-046.0.8.1 KB QUALITY RE-AUDIT REPORT",
            [
                "## Quality",
                f"- consistency_passed: `{consistency.get('passed')}`",
                f"- governance_present_rate: `{(quality_summary.get('completeness') or {}).get('governance_present_rate')}`",
                f"- chunking_quality_present_rate: `{(quality_summary.get('completeness') or {}).get('chunking_quality_present_rate')}`",
                f"- allowed_use_present_rate: `{(quality_summary.get('completeness') or {}).get('allowed_use_present_rate')}`",
                f"- safety_flags_present_rate: `{(quality_summary.get('completeness') or {}).get('safety_flags_present_rate')}`",
                f"- mixed_intent_unresolved_count: `{mixed_report.get('mixed_intent_unresolved_count')}`",
                f"- source_hygiene_mode: `{source_hygiene.get('mode')}`",
                f"- legacy_sd_filter_still_active: `{legacy_sd.get('legacy_sd_filter_still_active')}`",
            ],
        ),
    )
    _save_markdown(
        reports_dir / "PRD-046.0.8.1_RETRIEVAL_EVAL_REPORT.md",
        _render_report_md(
            "PRD-046.0.8.1 RETRIEVAL EVAL REPORT",
            [
                "## Retrieval",
                f"- retrieval_eval_status: `{retrieval_eval_payload.get('status')}`",
                f"- api_smoke_hits_positive: `{api_smoke.get('query_hits_positive')}`",
                f"- sd_filter_applied_true_count: `{api_smoke.get('sd_filter_applied_true_count')}`",
                f"- internal_only_unsafe_exposure_count: `{api_smoke.get('internal_only_unsafe_exposure_count')}`",
            ],
        ),
    )
    _save_markdown(
        reports_dir / "PRD-046.0.8.1_REVIEW_QUEUE_BASELINE_REPORT.md",
        _render_report_md(
            "PRD-046.0.8.1 REVIEW QUEUE BASELINE REPORT",
            [
                "## Review Queue",
                f"- old_queue_stale: `{staleness_report.get('stale')}`",
                f"- old_review_items_count: `{staleness_report.get('old_review_items_count')}`",
                f"- new_review_items_count: `{review_queue_new.get('review_items_count')}`",
                f"- new_queue_path: `{output_dir / 'review_queue_new_baseline.json'}`",
            ],
        ),
    )
    _save_markdown(
        reports_dir / "PRD-046.0.8.1_NEXT_PRD_RECOMMENDATION.md",
        _render_report_md(
            "PRD-046.0.8.1 NEXT PRD RECOMMENDATION",
            [
                "## Recommendation",
                "- Default: `PRD-046.0.9 — Post-Reprocess LLM Enrichment + Review Queue Rebaseline v1`.",
                "- If retrieval eval regressed: `PRD-046.0.8.1-HF1`.",
                "- If governance quality regressed: `PRD-046.0.8.1-HF2`.",
                "- Continue to `PRD-046.0.7.1` only with decisions mapped to new block ids.",
            ],
        ),
    )
    _save_markdown(
        reports_dir / "PRD-046.0.8.1_ROLLBACK_INSTRUCTIONS.md",
        _render_report_md(
            "PRD-046.0.8.1 ROLLBACK INSTRUCTIONS",
            [
                "## Steps",
                f"1. Restore `{all_blocks_path}` from `{backups_dir / 'all_blocks_merged.before.json'}`.",
                f"2. Restore `{registry_path}` from `{backups_dir / 'registry.before.json'}`.",
                "3. Rebuild Chroma from restored `all_blocks_merged.before.json` (229 blocks).",
                "4. Verify counts: production blocks=229, chroma count=229, source_id unchanged.",
                "5. Run API smoke to confirm `/api/query` works.",
            ],
        ),
    )

    implementation_report = _render_report_md(
        "PRD-046.0.8.1 IMPLEMENTATION REPORT",
        [
            "## Status",
            "- Implementation: done",
            "- Branch: main",
            "- Runtime behavior changed: false",
            "- Writer changed: false",
            "- DiagnosticCard changed: false",
            "- Thread Manager changed: false",
            "- State Analyzer changed: false",
            "- Context Assembly changed: false",
            f"- Production knowledge blocks mutated: `{mode == 'apply'}`",
            f"- Registry mutated: `{mode == 'apply'}`",
            f"- Chroma reindex performed: `{mode == 'apply'}`",
            f"- Production apply performed: `{mode == 'apply'}`",
            "",
            "## Preflight",
            f"- passed: `{preflight.get('passed')}`",
            f"- candidate_ready_for_apply: `{preflight.get('candidate_ready_for_apply')}`",
            f"- active_source_id: `{preflight.get('active_source_id')}`",
            f"- candidate_blocks_count: `{preflight.get('candidate_blocks_count')}`",
            f"- production_blocks_before: `{preflight.get('production_blocks_before')}`",
            f"- chroma_count_before: `{preflight.get('chroma_count_before')}`",
            "",
            "## Apply",
            f"- production_blocks_after: `{len(production_blocks_after)}`",
            f"- registry_blocks_after: `{next((row.get('blocks_count') for row in _load_json(registry_path) if _normalize(row.get('source_id')) == source_id and _normalize(row.get('status')) == 'done'), 0)}`",
            f"- all_blocks_hash_before: `{apply_result.get('all_blocks_hash_before')}`",
            f"- all_blocks_hash_after: `{apply_result.get('all_blocks_hash_after')}`",
            f"- registry_hash_before: `{apply_result.get('registry_hash_before')}`",
            f"- registry_hash_after: `{apply_result.get('registry_hash_after')}`",
            "- backup_created: true",
            "",
            "## Chroma",
            f"- chroma_count_before: `{chroma_reindex.get('chroma_count_before')}`",
            f"- chroma_count_after: `{chroma_reindex.get('chroma_count_after')}`",
            f"- indexed_source_ids: `{chroma_reindex.get('indexed_source_ids')}`",
            f"- reindex_status: `{chroma_reindex.get('status')}`",
            "",
            "## Quality",
            f"- governance_present_rate: `{(quality_summary.get('completeness') or {}).get('governance_present_rate')}`",
            f"- chunking_quality_present_rate: `{(quality_summary.get('completeness') or {}).get('chunking_quality_present_rate')}`",
            f"- allowed_use_present_rate: `{(quality_summary.get('completeness') or {}).get('allowed_use_present_rate')}`",
            f"- safety_flags_present_rate: `{(quality_summary.get('completeness') or {}).get('safety_flags_present_rate')}`",
            f"- direct_practice_misclassified_count: `{taxonomy_report.get('direct_practice_misclassified_count')}`",
            f"- unsafe_practice_suggestion_count: `{taxonomy_report.get('unsafe_practice_suggestion_count')}`",
            f"- mixed_intent_unresolved_count: `{mixed_report.get('mixed_intent_unresolved_count')}`",
            f"- internal_only_unsafe_exposure_count: `{api_smoke.get('internal_only_unsafe_exposure_count')}`",
            "",
            "## Review Queue",
            f"- old_review_queue_marked_stale: `{staleness_report.get('stale')}`",
            f"- new_review_queue_items_count: `{review_queue_new.get('review_items_count')}`",
            f"- new_review_queue_path: `{output_dir / 'review_queue_new_baseline.json'}`",
            "",
            "## Tests",
            "- test summary: see `TO_DO_LIST/logs/PRD-046.0.8.1/test_command_output.txt`",
            "",
            "## Commit / Push",
            "- Commit hash: pending",
            "- Push status: pending",
            "- Report sync: pending",
        ],
    )
    _save_markdown(reports_dir / "PRD-046.0.8.1_IMPLEMENTATION_REPORT.md", implementation_report)

    return {
        "status": "ok",
        "mode": mode,
        "preflight": preflight,
        "plan": plan,
        "apply_result": apply_result,
        "chroma_reindex_result": chroma_reindex,
        "api_smoke": api_smoke,
        "retrieval_eval": retrieval_eval_payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PRD-046.0.8.1 controlled candidate apply + chroma reindex + post-apply re-audit."
    )
    parser.add_argument("--source-prd", default=DEFAULT_SOURCE_PRD)
    parser.add_argument("--mode", choices=["dry_run", "apply"], default="apply")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--hf2-gate-path", default=str(DEFAULT_HF2_GATE_PATH))
    parser.add_argument("--candidate-path", default=str(DEFAULT_CANDIDATE_PATH))
    parser.add_argument("--all-blocks-path", default=str(DEFAULT_ALL_BLOCKS_PATH))
    parser.add_argument("--registry-path", default=str(DEFAULT_REGISTRY_PATH))
    parser.add_argument("--old-review-queue-path", default=str(DEFAULT_OLD_REVIEW_QUEUE_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--config-path", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--dataset-path", default=str(DEFAULT_DATASET_PATH))
    args = parser.parse_args()

    try:
        result = run_controlled_candidate_apply(
            source_prd=args.source_prd,
            mode=args.mode,
            confirm=bool(args.confirm),
            hf2_gate_path=Path(args.hf2_gate_path),
            candidate_path=Path(args.candidate_path),
            all_blocks_path=Path(args.all_blocks_path),
            registry_path=Path(args.registry_path),
            old_review_queue_path=Path(args.old_review_queue_path),
            output_dir=Path(args.output_dir),
            reports_dir=Path(args.reports_dir),
            config_path=Path(args.config_path),
            api_base_url=args.api_base_url,
            dataset_path=Path(args.dataset_path),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") == "ok" else 2
    except Exception as exc:
        print(f"[controlled_candidate_apply] failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
