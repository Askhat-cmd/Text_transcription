#!/usr/bin/env python3
"""Prepare governed knowledge chunks (dry-run only)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent

import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.knowledge_governance.chunker import chunk_markdown_document_v1
from bot_agent.knowledge_governance.contracts import (
    GovernedKnowledgeChunk,
    KnowledgeSourceManifest,
)
from bot_agent.knowledge_governance.export import export_governed_chunks_to_db_json_v1
from bot_agent.knowledge_governance.validators import validate_governed_chunks_v1


@dataclass
class SourceRunResult:
    manifest: KnowledgeSourceManifest
    raw_source_available: bool
    text_origin: str
    chunks: list[GovernedKnowledgeChunk]
    validation: dict[str, Any]
    export_payload: dict[str, Any]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve(path_raw: str) -> Path:
    path = Path(path_raw)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("PyYAML is required for registry parsing") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    raise ValueError(f"Registry payload must be mapping: {path}")


def _default_manifests() -> list[KnowledgeSourceManifest]:
    return [
        KnowledgeSourceManifest(
            source_id="forge_spirit_v2",
            title="КУЗНИЦА ДУХА v.2",
            source_kind="practice_manual",
            author="Salamat Sarsekenov",
            language="ru",
            version="v2",
            allowed_global_use=["diagnostic_lens", "practice_suggestion", "writer_context"],
            default_safety_flags=["requires_grounding", "not_for_direct_quote"],
            raw_path="bot_psychologist/knowledge_sources/raw/КУЗНИЦА ДУХА v.2.md",
        ),
        KnowledgeSourceManifest(
            source_id="neo_mindbot_notes",
            title="Neo MindBot КОНСПЕКТ",
            source_kind="architecture_notes",
            author=None,
            language="ru",
            version="notes",
            allowed_global_use=["internal_only", "style_guidance", "safety_protocol", "diagnostic_lens"],
            default_safety_flags=["source_style_not_user_facing", "not_for_direct_quote"],
            raw_path="bot_psychologist/knowledge_sources/raw/Neo MindBot КОНСПЕКТ.md",
        ),
    ]


def _load_manifests(registry_path: Path) -> list[KnowledgeSourceManifest]:
    if not registry_path.exists():
        return _default_manifests()
    payload = _load_yaml(registry_path)
    sources = payload.get("sources", [])
    if not isinstance(sources, list) or not sources:
        return _default_manifests()
    manifests: list[KnowledgeSourceManifest] = []
    for item in sources:
        if not isinstance(item, dict):
            continue
        manifests.append(KnowledgeSourceManifest.from_dict(item))
    return manifests or _default_manifests()


def _synthetic_fixture_text(manifest: KnowledgeSourceManifest) -> str:
    title = manifest.title
    if "конспект" in title.lower() or manifest.source_kind == "architecture_notes":
        return (
            "# Архитектурные принципы\n\n"
            "Внутренний материал. Не использовать как прямую цитату для пользователя.\n\n"
            "## Safety protocol\n\n"
            "Если есть кризисные признаки, приоритет — безопасность и короткая поддержка.\n\n"
            "## Style guidance\n\n"
            "Ответы должны быть конкретными, без авторитарных формулировок.\n"
        )
    return (
        "# Принципы\n\n"
        "Материал про практики саморегуляции и осторожные интервенции.\n\n"
        "## Практика 1: Дыхание 3 минуты\n\n"
        "Цель: снизить перегрузку.\n\n"
        "Время: 3 минуты.\n\n"
        "Шаг 1. Заметь напряжение в теле.\n"
        "Шаг 2. Сделай медленный вдох и длинный выдох.\n"
        "Шаг 3. Проверь, стало ли чуть спокойнее.\n\n"
        "## Линза избегания\n\n"
        "Если человек откладывает важный шаг снова и снова, важно назвать паттерн мягко.\n"
    )


def _source_text(manifest: KnowledgeSourceManifest) -> tuple[str, bool, str]:
    raw_path = manifest.raw_path or ""
    if raw_path:
        candidate = _resolve(raw_path)
        if candidate.exists() and candidate.is_file():
            return candidate.read_text(encoding="utf-8"), True, str(candidate)
    return _synthetic_fixture_text(manifest), False, "synthetic_fixture"


def _redacted_export_preview(export_payload: dict[str, Any], max_blocks: int = 5) -> dict[str, Any]:
    result = {
        "schema_version": export_payload.get("schema_version"),
        "source_id": export_payload.get("source_id"),
        "source_type": export_payload.get("source_type"),
        "title": export_payload.get("title"),
        "version": export_payload.get("version"),
        "blocks": [],
    }
    blocks = export_payload.get("blocks", [])
    if not isinstance(blocks, list):
        return result
    for block in blocks[:max_blocks]:
        if not isinstance(block, dict):
            continue
        meta = block.get("metadata", {})
        governance = meta.get("governance", {}) if isinstance(meta, dict) else {}
        result["blocks"].append(
            {
                "id": block.get("id"),
                "title": block.get("title"),
                "summary": block.get("summary"),
                "text_preview": str(block.get("text", "") or "")[:240],
                "complexity": block.get("complexity"),
                "metadata": {
                    "source_title": meta.get("source_title") if isinstance(meta, dict) else None,
                    "source_type": meta.get("source_type") if isinstance(meta, dict) else None,
                    "chunk_index": meta.get("chunk_index") if isinstance(meta, dict) else None,
                    "governance": governance,
                },
            }
        )
    return result


def _aggregate_counts(chunks: list[GovernedKnowledgeChunk]) -> dict[str, dict[str, int]]:
    by_type: Counter[str] = Counter()
    by_use: Counter[str] = Counter()
    by_flag: Counter[str] = Counter()
    by_lens: Counter[str] = Counter()
    for chunk in chunks:
        by_type[chunk.chunk_type] += 1
        for item in chunk.allowed_use:
            by_use[item] += 1
        for item in chunk.safety_flags:
            by_flag[item] += 1
        for item in chunk.lens_family:
            by_lens[item] += 1
    return {
        "by_chunk_type": dict(sorted(by_type.items())),
        "by_allowed_use": dict(sorted(by_use.items())),
        "by_safety_flag": dict(sorted(by_flag.items())),
        "by_lens_family": dict(sorted(by_lens.items())),
    }


def _render_markdown_report(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# PRD-046.0 Knowledge Base Governance Dry Run Report")
    lines.append("")
    lines.append("## Sources")
    for source in payload.get("sources", []):
        lines.append(
            f"- {source.get('source_id')} | {source.get('title')} | "
            f"raw source available: {source.get('raw_source_available')} | "
            f"chunks generated: {source.get('chunks_generated')}"
        )
    lines.append("")
    lines.append("## Counts")
    counts = payload.get("global_counts", {})
    lines.append(f"- by chunk_type: {json.dumps(counts.get('by_chunk_type', {}), ensure_ascii=False)}")
    lines.append(f"- by allowed_use: {json.dumps(counts.get('by_allowed_use', {}), ensure_ascii=False)}")
    lines.append(f"- by safety_flag: {json.dumps(counts.get('by_safety_flag', {}), ensure_ascii=False)}")
    lines.append(f"- by lens_family: {json.dumps(counts.get('by_lens_family', {}), ensure_ascii=False)}")
    lines.append("")
    findings = payload.get("governance_findings", {})
    lines.append("## Governance findings")
    lines.append(f"- high-risk chunks count: {findings.get('high_risk_chunks_count')}")
    lines.append(f"- practice chunks count: {findings.get('practice_chunks_count')}")
    lines.append(f"- practice chunks requiring low-resource check: {findings.get('practice_requires_low_resource_check')}")
    lines.append(f"- chunks marked not_for_direct_quote: {findings.get('not_for_direct_quote_count')}")
    lines.append(f"- chunks marked internal_only: {findings.get('internal_only_count')}")
    lines.append("")
    lines.append("## Export")
    lines.append(f"- generated preview path: {payload.get('preview_output_path')}")
    lines.append("- DB_JSON compatibility notes: Existing DataLoader can load content/title/summary; nested governance metadata may require follow-up runtime filtering PRD.")
    lines.append("")
    lines.append("## Runtime impact")
    lines.append("- live retrieval changed: no")
    lines.append("- Writer prompt changed: no")
    lines.append("- DiagnosticCard changed: no")
    lines.append("")
    lines.append("## Notes")
    lines.append(f"- raw_sources_missing={payload.get('raw_sources_missing')}")
    lines.append("- raw source docs not committed by this PRD.")
    lines.append("")
    return "\n".join(lines)


def _build_payload(
    *,
    registry_path: Path,
    results: list[SourceRunResult],
    output_path: Path,
) -> dict[str, Any]:
    all_chunks: list[GovernedKnowledgeChunk] = []
    all_sources: list[dict[str, Any]] = []
    raw_sources_missing = False

    for result in results:
        manifest = result.manifest
        all_chunks.extend(result.chunks)
        raw_sources_missing = raw_sources_missing or (not result.raw_source_available)
        all_sources.append(
            {
                "source_id": manifest.source_id,
                "title": manifest.title,
                "source_kind": manifest.source_kind,
                "raw_source_available": result.raw_source_available,
                "text_origin": result.text_origin,
                "chunks_generated": len(result.chunks),
                "validation_errors": len(result.validation.get("errors", [])),
                "validation_warnings": len(result.validation.get("warnings", [])),
                "counts_by_type": result.validation.get("counts_by_type", {}),
                "counts_by_allowed_use": result.validation.get("counts_by_allowed_use", {}),
                "counts_by_safety_flag": result.validation.get("counts_by_safety_flag", {}),
                "db_json_export_preview": _redacted_export_preview(result.export_payload),
            }
        )

    counts = _aggregate_counts(all_chunks)
    safety_counter = Counter()
    use_counter = Counter()
    type_counter = Counter()
    for chunk in all_chunks:
        type_counter[chunk.chunk_type] += 1
        for flag in chunk.safety_flags:
            safety_counter[flag] += 1
        for use in chunk.allowed_use:
            use_counter[use] += 1

    return {
        "schema_version": "governed_kb_dry_run_v1",
        "generated_at": _utc_now_iso(),
        "registry_path": str(registry_path),
        "dry_run": True,
        "raw_sources_missing": raw_sources_missing,
        "preview_output_path": str(output_path),
        "sources": all_sources,
        "global_counts": counts,
        "governance_findings": {
            "high_risk_chunks_count": int(safety_counter["clinical_risk"] + safety_counter["spiritual_authority_risk"]),
            "practice_chunks_count": int(type_counter["practice"]),
            "practice_requires_low_resource_check": int(safety_counter["practice_requires_low_resource_check"]),
            "not_for_direct_quote_count": int(safety_counter["not_for_direct_quote"]),
            "internal_only_count": int(use_counter["internal_only"]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare governed knowledge chunks (dry-run).")
    parser.add_argument("--registry", required=True, help="Path to source registry YAML.")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run only (default flow).")
    parser.add_argument("--output", required=True, help="JSON output path for governed preview.")
    parser.add_argument("--markdown-report", required=True, help="Markdown report output path.")
    args = parser.parse_args()

    registry_path = _resolve(args.registry)
    output_path = _resolve(args.output)
    markdown_path = _resolve(args.markdown_report)

    manifests = _load_manifests(registry_path)
    results: list[SourceRunResult] = []
    for manifest in manifests:
        text, raw_available, origin = _source_text(manifest)
        chunks = chunk_markdown_document_v1(text=text, manifest=manifest)
        validation = validate_governed_chunks_v1(chunks)
        export_payload = export_governed_chunks_to_db_json_v1(chunks=chunks, manifest=manifest)
        results.append(
            SourceRunResult(
                manifest=manifest,
                raw_source_available=raw_available,
                text_origin=origin,
                chunks=chunks,
                validation=validation,
                export_payload=export_payload,
            )
        )

    payload = _build_payload(registry_path=registry_path, results=results, output_path=output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_render_markdown_report(payload), encoding="utf-8")
    print(f"[OK] governed preview JSON: {output_path}")
    print(f"[OK] dry-run markdown report: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
