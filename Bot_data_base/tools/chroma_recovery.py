from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_DIR = CURRENT_DIR.parent
if str(BOTDB_DIR) not in sys.path:
    sys.path.insert(0, str(BOTDB_DIR))

from models.universal_block import UniversalBlock
from storage.chroma_manager import ChromaManager
from tools.kb_quality_audit import (
    DEFAULT_PROBE_QUERIES,
    evaluate_governed_index_gate,
    load_processed_blocks,
    probe_chroma_readiness,
    run_retrieval_probe_snapshot,
)

DEFAULT_REPORT_PREFIX = "PRD-046.0.4.1"
DEFAULT_OUTPUT_DIR = f"TO_DO_LIST/logs/{DEFAULT_REPORT_PREFIX}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def _resolve_from_botdb(base_dir: Path, value: str) -> str:
    if not value:
        return ""
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((base_dir / value).resolve())


def _to_universal_block(raw: dict[str, Any]) -> UniversalBlock:
    metadata = raw.get("metadata") or {}
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
        llm_enrichment=(
            metadata.get("llm_enrichment")
            if isinstance(metadata.get("llm_enrichment"), dict)
            else {}
        ),
    )


def run_recovery(
    *,
    config_path: Path,
    output_dir: Path,
    report_prefix: str,
    api_base_url: str,
    blocks_path: Path | None,
    probe_only: bool,
    dry_run: bool,
    do_reset: bool,
    do_reindex: bool,
    confirm: bool,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    config = _load_config(config_path)
    storage_cfg = (config.get("storage") or {}) if isinstance(config, dict) else {}
    embedding_cfg = (config.get("embedding") or {}) if isinstance(config, dict) else {}

    chroma_db_path = _resolve_from_botdb(BOTDB_DIR, str(storage_cfg.get("chroma_db_path") or "data/chroma_db"))
    collection_name = str(storage_cfg.get("collection_name") or "bot_knowledge_base")
    embedding_model_name = str(embedding_cfg.get("model") or "").strip() or None
    registry_path = BOTDB_DIR / "data" / "registry.json"
    default_blocks_path = BOTDB_DIR / "data" / "processed" / "all_blocks_merged.json"
    effective_blocks_path = blocks_path or default_blocks_path

    manager = ChromaManager(
        db_path=chroma_db_path,
        collection_name=collection_name,
        embedding_model_name=embedding_model_name,
    )

    before_health = manager.probe_collection_health()
    raw_blocks = load_processed_blocks(effective_blocks_path)
    gate_before = evaluate_governed_index_gate(blocks=raw_blocks, source_label="КУЗНИЦА ДУХА")
    gate_status_before = str(gate_before.get("status") or "")
    gate_blockers = list(gate_before.get("blocker_reasons") or [])
    gate_allow_status = gate_status_before in {"ready", "degraded"}
    reindex_allowed = bool(gate_allow_status and not gate_blockers and len(raw_blocks) > 0)
    preflight_gate = {
        "generated_at": _utc_now(),
        "report_prefix": report_prefix,
        "blocks_path": str(effective_blocks_path),
        "local_blocks_count": len(raw_blocks),
        "gate_status": gate_status_before,
        "blocker_reasons": gate_blockers,
        "warnings": list(gate_before.get("warnings") or []),
        "metrics": gate_before.get("metrics") or {},
        "thresholds": gate_before.get("thresholds") or {},
        "reindex_allowed": reindex_allowed,
        "reason": (
            "gate_passed"
            if reindex_allowed
            else "gate_blocked_or_empty_blocks"
        ),
    }
    registry_records = []
    if registry_path.exists():
        registry_records = json.loads(registry_path.read_text(encoding="utf-8"))

    audit_probe = probe_chroma_readiness(
        api_base_url=api_base_url,
        config=config,
        all_blocks_path=effective_blocks_path,
        registry_records=registry_records,
    )

    actions: list[str] = []
    mutation_blocked = False
    mutation_reason = ""
    indexed_blocks_count = 0
    if do_reset or do_reindex:
        if not reindex_allowed:
            mutation_blocked = True
            mutation_reason = (
                f"Governed gate blocked mutation: status={gate_status_before},"
                f" blockers={gate_blockers}, local_blocks_count={len(raw_blocks)}"
            )
            actions.append("blocked_by_gate")
        elif not confirm:
            mutation_blocked = True
            mutation_reason = "Destructive operations require --confirm."
        elif dry_run:
            actions.append("dry_run_no_mutation")
        else:
            if do_reset:
                manager.reset_collection()
                actions.append("collection_reset")
            if do_reindex:
                to_index = [_to_universal_block(block) for block in raw_blocks]
                indexed_blocks_count = manager.add_blocks(to_index)
                actions.append("reindex_from_json")
    else:
        actions.append("probe_only")

    after_health = manager.probe_collection_health()
    gate_after = evaluate_governed_index_gate(blocks=raw_blocks, source_label="КУЗНИЦА ДУХА")

    query_smoke = run_retrieval_probe_snapshot(
        queries=DEFAULT_PROBE_QUERIES[:4],
        api_base_url=api_base_url,
        focus_blocks=raw_blocks,
    )

    recovery_probe = {
        "generated_at": _utc_now(),
        "report_prefix": report_prefix,
        "config_path": str(config_path),
        "api_base_url": api_base_url,
        "chroma_db_path": chroma_db_path,
        "collection_name": collection_name,
        "embedding_model_configured": embedding_model_name
        or os.getenv("SENTENCE_TRANSFORMERS_MODEL")
        or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "blocks_path": str(effective_blocks_path),
        "local_blocks_count": len(raw_blocks),
        "mode": {
            "probe_only": probe_only,
            "dry_run": dry_run,
            "reset": do_reset,
            "reindex_from_json": do_reindex,
            "confirm": confirm,
        },
        "actions": actions,
        "mutation_blocked": mutation_blocked,
        "mutation_reason": mutation_reason,
        "indexed_blocks_count": indexed_blocks_count,
        "before_health": before_health,
        "after_health": after_health,
        "audit_probe": audit_probe,
        "governed_gate_status_before": gate_before.get("status"),
        "governed_gate_status_after": gate_after.get("status"),
        "reindex_allowed": reindex_allowed,
        "preflight_reason": preflight_gate.get("reason"),
    }

    (output_dir / "preflight_gate.json").write_text(
        json.dumps(preflight_gate, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "chroma_recovery_probe.json").write_text(
        json.dumps(recovery_probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "governed_index_gate.json").write_text(
        json.dumps({"before": gate_before, "after": gate_after}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "query_smoke_snapshot.json").write_text(
        json.dumps(query_smoke, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "chroma_reindex_snapshot.json").write_text(
        json.dumps(recovery_probe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "sanitized_runtime_logs.txt").write_text(
        "\n".join(
            [
                f"[{_utc_now()}] {report_prefix} chroma recovery run",
                f"actions={actions}",
                f"mutation_blocked={mutation_blocked}",
                f"reindex_allowed={reindex_allowed}",
                f"gate_before={gate_before.get('status')}",
                f"gate_after={gate_after.get('status')}",
                f"api_query_status={(audit_probe.get('api_query') or {}).get('status_code')}",
                f"collection_count_before={before_health.get('collection_count')}",
                f"collection_count_after={after_health.get('collection_count')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "preflight_gate_path": str(output_dir / "preflight_gate.json"),
        "recovery_probe_path": str(output_dir / "chroma_recovery_probe.json"),
        "reindex_snapshot_path": str(output_dir / "chroma_reindex_snapshot.json"),
        "governed_gate_path": str(output_dir / "governed_index_gate.json"),
        "query_smoke_path": str(output_dir / "query_smoke_snapshot.json"),
        "gate_status_after": gate_after.get("status"),
        "recommended_next_prd": gate_after.get("recommended_next_prd"),
        "mutation_blocked": mutation_blocked,
        "reindex_allowed": reindex_allowed,
        "local_blocks_count": len(raw_blocks),
        "indexed_blocks_count": indexed_blocks_count,
        "collection_count_before": before_health.get("collection_count"),
        "collection_count_after": after_health.get("collection_count"),
    }


def write_reports(
    *,
    reports_dir: Path,
    report_prefix: str,
    result: dict[str, Any],
    recovery_probe: dict[str, Any],
    gate_data: dict[str, Any],
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    recovery_report = reports_dir / f"{report_prefix}_CHROMA_REINDEX_REPORT.md"
    gate_report = reports_dir / f"{report_prefix}_GOVERNED_INDEX_GATE_REPORT.md"
    impl_report = reports_dir / f"{report_prefix}_IMPLEMENTATION_REPORT.md"

    recovery_lines = [
        f"# {report_prefix} Chroma Reindex Report",
        "",
        "## Mode",
        f"- probe_only: `{(recovery_probe.get('mode') or {}).get('probe_only')}`",
        f"- dry_run: `{(recovery_probe.get('mode') or {}).get('dry_run')}`",
        f"- reset: `{(recovery_probe.get('mode') or {}).get('reset')}`",
        f"- reindex_from_json: `{(recovery_probe.get('mode') or {}).get('reindex_from_json')}`",
        f"- confirm: `{(recovery_probe.get('mode') or {}).get('confirm')}`",
        "",
        "## Safety",
        f"- mutation_blocked: `{recovery_probe.get('mutation_blocked')}`",
        f"- mutation_reason: `{recovery_probe.get('mutation_reason')}`",
        f"- reindex_allowed: `{recovery_probe.get('reindex_allowed')}`",
        f"- preflight_reason: `{recovery_probe.get('preflight_reason')}`",
        "",
        "## Health Before/After",
        f"- collection_count_before: `{(recovery_probe.get('before_health') or {}).get('collection_count')}`",
        f"- collection_count_after: `{(recovery_probe.get('after_health') or {}).get('collection_count')}`",
        f"- dimension_mismatch_before: `{(recovery_probe.get('before_health') or {}).get('dimension_mismatch')}`",
        f"- dimension_mismatch_after: `{(recovery_probe.get('after_health') or {}).get('dimension_mismatch')}`",
        "",
        "## API Probe",
        f"- /api/status code: `{((recovery_probe.get('audit_probe') or {}).get('api_status') or {}).get('status_code')}`",
        f"- /api/query code: `{((recovery_probe.get('audit_probe') or {}).get('api_query') or {}).get('status_code')}`",
        "",
        "## Indexed Blocks",
        f"- local_blocks_count: `{recovery_probe.get('local_blocks_count')}`",
        f"- indexed_blocks_count: `{recovery_probe.get('indexed_blocks_count')}`",
        "",
        "## Recommendation",
        f"- `{result.get('recommended_next_prd')}`",
    ]
    recovery_report.write_text("\n".join(recovery_lines) + "\n", encoding="utf-8")

    gate_after = gate_data.get("after") or {}
    gate_metrics = gate_after.get("metrics") or {}
    gate_lines = [
        f"# {report_prefix} Governed Index Gate Report",
        "",
        "## Gate Status",
        f"- status: `{gate_after.get('status')}`",
        f"- blockers: `{gate_after.get('blocker_reasons')}`",
        f"- warnings: `{gate_after.get('warnings')}`",
        "",
        "## Metrics",
        f"- total_blocks: `{gate_metrics.get('total_blocks')}`",
        f"- governance_present_ratio: `{gate_metrics.get('governance_present_ratio')}`",
        f"- allowed_use_present_ratio: `{gate_metrics.get('allowed_use_present_ratio')}`",
        f"- safety_flags_present_ratio: `{gate_metrics.get('safety_flags_present_ratio')}`",
        f"- not_for_direct_quote_ratio: `{gate_metrics.get('not_for_direct_quote_ratio')}`",
        f"- summary_present_ratio: `{gate_metrics.get('summary_present_ratio')}`",
        f"- boundary_confidence_present_ratio: `{gate_metrics.get('boundary_confidence_present_ratio')}`",
        f"- lens_family_present_ratio: `{gate_metrics.get('lens_family_present_ratio')}`",
        "",
        "## Runtime Readiness",
        "- If status != ready, Chroma may be technically restored but knowledge index is not production-ready.",
        f"- recommended_next_prd: `{gate_after.get('recommended_next_prd')}`",
    ]
    gate_report.write_text("\n".join(gate_lines) + "\n", encoding="utf-8")

    impl_lines = [
        f"# {report_prefix} IMPLEMENTATION REPORT",
        "",
        "## Status",
        "- Implementation: done (Chroma reindex + governed gate preflight)",
        "- Branch: `main`",
        "",
        "## Artifacts",
        f"- `TO_DO_LIST/logs/{report_prefix}/preflight_gate.json`",
        f"- `TO_DO_LIST/logs/{report_prefix}/chroma_recovery_probe.json`",
        f"- `TO_DO_LIST/logs/{report_prefix}/chroma_reindex_snapshot.json`",
        f"- `TO_DO_LIST/logs/{report_prefix}/governed_index_gate.json`",
        f"- `TO_DO_LIST/logs/{report_prefix}/query_smoke_snapshot.json`",
        f"- `TO_DO_LIST/logs/{report_prefix}/sanitized_runtime_logs.txt`",
        "",
        "## Outcome",
        f"- reindex_allowed: `{result.get('reindex_allowed')}`",
        f"- local_blocks_count: `{result.get('local_blocks_count')}`",
        f"- indexed_blocks_count: `{result.get('indexed_blocks_count')}`",
        f"- collection_count_before: `{result.get('collection_count_before')}`",
        f"- collection_count_after: `{result.get('collection_count_after')}`",
        f"- gate_status_after: `{result.get('gate_status_after')}`",
        f"- recommended_next_prd: `{result.get('recommended_next_prd')}`",
        "",
        "## Commit / Push",
        "- Commit hash: `pending`",
        "- Push status: `pending`",
    ]
    impl_report.write_text("\n".join(impl_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chroma recovery and governed index gate CLI with report prefix isolation."
    )
    parser.add_argument("--config-path", default="Bot_data_base/config.yaml")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--reports-dir", default="TO_DO_LIST/reports")
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX)
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8003")
    parser.add_argument("--blocks-path", default="")
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--reindex-from-json", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config_path)
    output_dir_arg = str(args.output_dir).strip()
    if output_dir_arg == DEFAULT_OUTPUT_DIR and str(args.report_prefix).strip() != DEFAULT_REPORT_PREFIX:
        output_dir = Path("TO_DO_LIST") / "logs" / str(args.report_prefix).strip()
    else:
        output_dir = Path(output_dir_arg)
    reports_dir = Path(args.reports_dir)
    blocks_path = Path(args.blocks_path) if str(args.blocks_path).strip() else None

    if not args.probe_only and not args.reset and not args.reindex_from_json:
        args.probe_only = True

    result = run_recovery(
        config_path=config_path,
        output_dir=output_dir,
        report_prefix=str(args.report_prefix).strip() or DEFAULT_REPORT_PREFIX,
        api_base_url=args.api_base_url.rstrip("/"),
        blocks_path=blocks_path,
        probe_only=bool(args.probe_only),
        dry_run=bool(args.dry_run),
        do_reset=bool(args.reset),
        do_reindex=bool(args.reindex_from_json),
        confirm=bool(args.confirm),
    )

    recovery_probe = json.loads((output_dir / "chroma_recovery_probe.json").read_text(encoding="utf-8"))
    gate_data = json.loads((output_dir / "governed_index_gate.json").read_text(encoding="utf-8"))
    write_reports(
        reports_dir=reports_dir,
        report_prefix=str(args.report_prefix).strip() or DEFAULT_REPORT_PREFIX,
        result=result,
        recovery_probe=recovery_probe,
        gate_data=gate_data,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
