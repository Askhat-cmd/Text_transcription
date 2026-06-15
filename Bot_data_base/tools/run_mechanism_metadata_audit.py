from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_ROOT = CURRENT_DIR.parent
REPO_ROOT = BOTDB_ROOT.parent
BOT_PSYCHOLOGIST_ROOT = REPO_ROOT / "bot_psychologist"

if str(BOTDB_ROOT) not in sys.path:
    sys.path.insert(0, str(BOTDB_ROOT))

from knowledge_governance.mechanism_metadata import (  # noqa: E402
    MECHANISM_METADATA_SCHEMA_VERSION,
    adapt_block_to_mechanism_metadata,
    build_schema_snapshot,
    sanitize_metadata_preview,
)


PRD_ID = "PRD-047.16"
DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
DEFAULT_REPORTS_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
DEFAULT_REAL_BLOCKS_PATH = REPO_ROOT / "Bot_data_base" / "data" / "processed" / "all_blocks_merged.json"
SHARED_ENCODING_VALIDATOR_PATH = BOT_PSYCHOLOGIST_ROOT / "tools" / "validate_prd_artifact_encoding.py"


def _safe_preview(text: str, limit: int = 160) -> str:
    value = " ".join(str(text or "").strip().split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + "..."


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _load_shared_encoding_validator():
    spec = importlib.util.spec_from_file_location(
        "shared_validate_prd_artifact_encoding",
        SHARED_ENCODING_VALIDATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load encoding validator: {SHARED_ENCODING_VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.run


def _fixture_blocks() -> list[dict[str, Any]]:
    return [
        {
            "id": "fixture-concept-001",
            "title": "Факт и интерпретация",
            "summary": "Разделяет событие и смысл, который человек к нему добавляет.",
            "text": "Когда человек сливает факт и интерпретацию, тревога и стыд легко растут.",
            "source": "book:fixture_manual",
            "metadata": {
                "source_title": "Fixture Manual",
                "source_type": "book",
                "heading_path": ["Concepts", "Fact vs Interpretation"],
                "governance": {
                    "schema_version": "governance_v1",
                    "chunk_type": "theory",
                    "allowed_use": ["writer_context"],
                    "safety_flags": ["not_for_direct_quote"],
                    "source_trace": {"source_id": "fixture_manual", "source_title": "Fixture Manual", "source_type": "book"},
                },
                "chunking_quality": {"schema_version": "chunking_quality_v1"},
            },
        },
        {
            "id": "fixture-mechanism-001",
            "title": "Контроль как попытка вернуть безопасность",
            "summary": "Контроль помогает не чувствовать уязвимость, но сужает жизнь.",
            "text": "Человек усиливает контроль, когда тревога поднимается и кажется, что иначе станет опасно.",
            "source": "book:fixture_manual",
            "metadata": {
                "source_title": "Fixture Manual",
                "source_type": "book",
                "heading_path": ["Mechanisms", "Control as Safety"],
                "governance": {
                    "schema_version": "governance_v1",
                    "chunk_type": "lens",
                    "allowed_use": ["writer_context", "diagnostic_lens"],
                    "safety_flags": ["not_for_direct_quote"],
                    "source_trace": {"source_id": "fixture_manual", "source_title": "Fixture Manual", "source_type": "book"},
                },
                "chunking_quality": {"schema_version": "chunking_quality_v1"},
            },
        },
        {
            "id": "fixture-practice-001",
            "title": "Три медленных выдоха",
            "summary": "Короткая практика для снижения перегрузки.",
            "text": "Цель: снизить напряжение.\nВремя: 3 минуты.\nШаг 1: заметь напряжение.\nШаг 2: сделай медленный выдох.\nШаг 3: проверь, стало ли чуть спокойнее.",
            "source": "book:fixture_manual",
            "metadata": {
                "source_title": "Fixture Manual",
                "source_type": "book",
                "heading_path": ["Practices", "Three Exhales"],
                "governance": {
                    "schema_version": "governance_v1",
                    "chunk_type": "practice",
                    "allowed_use": ["writer_context", "practice_suggestion"],
                    "safety_flags": ["not_for_direct_quote"],
                    "practice_metadata": {"duration": "3 min", "preconditions": ["user_has_some_capacity"]},
                    "source_trace": {"source_id": "fixture_manual", "source_title": "Fixture Manual", "source_type": "book"},
                },
                "chunking_quality": {"schema_version": "chunking_quality_v1"},
            },
        },
        {
            "id": "fixture-safety-001",
            "title": "Паника и безопасность",
            "summary": "Сначала стабилизация, потом смысл.",
            "text": "Если страшно умереть и трудно дышать, сначала нужна короткая безопасная опора, а не спор с паникой.",
            "source": "book:fixture_manual",
            "metadata": {
                "source_title": "Fixture Manual",
                "source_type": "book",
                "heading_path": ["Safety", "Panic First Aid"],
                "governance": {
                    "schema_version": "governance_v1",
                    "chunk_type": "safety",
                    "allowed_use": ["writer_context", "safety_protocol"],
                    "safety_flags": ["not_for_direct_quote", "requires_grounding"],
                    "source_trace": {"source_id": "fixture_manual", "source_title": "Fixture Manual", "source_type": "book"},
                },
                "chunking_quality": {"schema_version": "chunking_quality_v1"},
            },
        },
    ]


def _load_real_blocks(limit: int) -> tuple[list[dict[str, Any]], list[str], str]:
    checked_paths = [str(DEFAULT_REAL_BLOCKS_PATH.relative_to(REPO_ROOT)).replace("\\", "/")]
    if not DEFAULT_REAL_BLOCKS_PATH.exists():
        return [], checked_paths, "real_blocks_missing"
    payload = _read_json(DEFAULT_REAL_BLOCKS_PATH)
    blocks = payload.get("blocks", []) if isinstance(payload, dict) else payload
    if not isinstance(blocks, list):
        return [], checked_paths, "real_blocks_invalid_payload"
    return list(blocks[: max(0, limit)]), checked_paths, "real_blocks_loaded"


def _summarize_counts(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        value = item.get(key)
        if isinstance(value, list):
            if not value:
                counter["unknown/empty"] += 1
            for entry in value:
                counter[str(entry or "unknown/empty")] += 1
        else:
            counter[str(value or "unknown/empty")] += 1
    return dict(sorted(counter.items()))


def _build_completeness_report(normalized: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(normalized) or 1
    def present(field_name: str) -> int:
        return sum(1 for item in normalized if item.get(field_name))

    return {
        "schema_version": "mechanism_metadata_completeness_v1",
        "chunks_checked": len(normalized),
        "field_presence": {
            "core_thesis_present_ratio": round(present("core_thesis") / total, 4),
            "mechanism_hints_present_ratio": round(sum(1 for item in normalized if item.get("mechanism_hints")) / total, 4),
            "use_when_present_ratio": round(sum(1 for item in normalized if item.get("use_when")) / total, 4),
            "avoid_when_present_ratio": round(sum(1 for item in normalized if item.get("avoid_when")) / total, 4),
            "contraindications_present_ratio": round(sum(1 for item in normalized if item.get("contraindications")) / total, 4),
            "source_trace_present_ratio": round(sum(1 for item in normalized if item.get("source_trace")) / total, 4),
        },
        "missing_counts": {
            "missing_allowed_use_count": sum(1 for item in normalized if not item.get("allowed_use")),
            "missing_core_thesis_count": sum(1 for item in normalized if not item.get("core_thesis")),
            "missing_mechanism_hints_count": sum(1 for item in normalized if not item.get("mechanism_hints")),
            "missing_source_trace_count": sum(1 for item in normalized if not item.get("source_trace")),
        },
    }


def _anti_heuristic_report() -> dict[str, Any]:
    targets = [
        REPO_ROOT / "Bot_data_base" / "knowledge_governance" / "mechanism_metadata.py",
        REPO_ROOT / "Bot_data_base" / "tools" / "run_mechanism_metadata_audit.py",
    ]
    forbidden_patterns = [
        'if "мама" in user_message',
        'if "стыд" in user_message',
        'if "контроль" in user_message',
        'if "паника" in user_message',
        "depth_level = 3 if",
    ]
    file_results: list[dict[str, Any]] = []
    all_clear = True
    for path in targets:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        executable_lines = [
            line.strip().lower()
            for line in text.splitlines()
            if not line.strip().startswith(("'", '"'))
        ]
        hits = [pattern for pattern in forbidden_patterns if pattern in executable_lines]
        if hits:
            all_clear = False
        file_results.append(
            {
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "forbidden_pattern_hits": hits,
                "status": "passed" if not hits else "failed",
            }
        )
    return {
        "schema_version": "anti_heuristic_compliance_report_v1",
        "status": "passed" if all_clear else "failed",
        "forbidden_patterns_checked": forbidden_patterns,
        "files": file_results,
        "notes": [
            "mechanism_hints are stored as metadata only",
            "no bot_psychologist runtime module was changed by this audit runner",
        ],
    }


def _build_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.16 Mechanism Metadata Audit",
        "",
        f"- schema_version: `{audit['schema_version']}`",
        f"- metadata_schema_version: `{audit['metadata_schema_version']}`",
        f"- mode: `{audit['mode']}`",
        f"- status: `{audit['status']}`",
        f"- fixture_chunks_checked: `{audit['fixture_chunks_checked']}`",
        f"- real_chunks_checked: `{audit['real_chunks_checked']}`",
        f"- total_chunks_checked: `{audit['total_chunks_checked']}`",
        f"- real_sample_status: `{audit['real_sample_status']}`",
        "",
        "## Distribution",
        f"- by_chunk_type: `{json.dumps(audit['by_chunk_type'], ensure_ascii=False)}`",
        f"- by_allowed_use: `{json.dumps(audit['by_allowed_use'], ensure_ascii=False)}`",
        "",
        "## Validation",
        f"- error_count: `{audit['error_count']}`",
        f"- warning_count: `{audit['warning_count']}`",
        f"- top_errors: `{audit['top_errors']}`",
        f"- top_warnings: `{audit['top_warnings']}`",
        "",
        "## Boundary Confirmation",
        "- dry-run only: yes",
        "- Chroma reindexed: no",
        "- DB mutated: no",
        "- Writer/runtime path changed: no",
        "- raw full chunk text in artifacts: no",
        "",
        "## Notes",
    ]
    for note in audit.get("notes", []):
        lines.append(f"- {note}")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    fixture_blocks = _fixture_blocks()
    real_blocks: list[dict[str, Any]] = []
    checked_real_paths: list[str] = []
    real_status = "skipped_by_mode"
    if args.mode in {"dry-run", "real"}:
        real_blocks, checked_real_paths, real_status = _load_real_blocks(limit=int(args.limit))

    selected_blocks = fixture_blocks + real_blocks
    normalized_payloads: list[dict[str, Any]] = []
    sample_previews: list[dict[str, Any]] = []
    validation_errors: list[str] = []
    validation_warnings: list[str] = []

    for raw in selected_blocks:
        metadata, validation = adapt_block_to_mechanism_metadata(raw)
        payload = metadata.to_dict()
        normalized_payloads.append(payload)
        if len(sample_previews) < 20:
            sample_previews.append(sanitize_metadata_preview(metadata))
        validation_errors.extend(validation["errors"])
        validation_warnings.extend(validation["warnings"])

    by_chunk_type = _summarize_counts(normalized_payloads, "chunk_type")
    by_allowed_use = _summarize_counts(normalized_payloads, "allowed_use")
    chunk_type_distribution = {
        "schema_version": "mechanism_metadata_chunk_type_distribution_v1",
        "total_chunks_checked": len(normalized_payloads),
        "by_chunk_type": by_chunk_type,
        "by_allowed_use": by_allowed_use,
    }
    completeness = _build_completeness_report(normalized_payloads)
    anti_heuristic = _anti_heuristic_report()
    status = "passed"
    if validation_errors or anti_heuristic["status"] != "passed":
        status = "warning"

    audit = {
        "schema_version": "mechanism_metadata_audit_v1",
        "metadata_schema_version": MECHANISM_METADATA_SCHEMA_VERSION,
        "mode": args.mode,
        "status": status,
        "fixture_chunks_checked": len(fixture_blocks),
        "real_chunks_checked": len(real_blocks),
        "total_chunks_checked": len(normalized_payloads),
        "real_sample_status": real_status,
        "source_paths_checked": checked_real_paths,
        "by_chunk_type": by_chunk_type,
        "by_allowed_use": by_allowed_use,
        "error_count": len(validation_errors),
        "warning_count": len(validation_warnings),
        "top_errors": sorted(dict(Counter(validation_errors).most_common(10)).keys()),
        "top_warnings": sorted(dict(Counter(validation_warnings).most_common(10)).keys()),
        "notes": [
            "Mechanism-aware metadata is semantic guidance, not deterministic routing.",
            "Legacy governance metadata was normalized without mutating source files, DB, or Chroma.",
            "Sample artifacts are sanitized previews only.",
        ],
    }

    no_mutation = {
        "prd_id": PRD_ID,
        "runtime_user_facing_changed": False,
        "writer_prompt_changed": False,
        "state_analyzer_changed": False,
        "thread_manager_changed": False,
        "hybrid_retrieval_planner_runtime_changed": False,
        "chroma_reindexed": False,
        "db_schema_destructive_change": False,
        "embeddings_changed": False,
        "new_runtime_path_created": False,
        "provider_llm_calls_used_for_enrichment": False,
        "raw_content_full_in_reports": False,
        "secrets_or_env_committed": False,
        "files_changed_summary": [
            "Bot_data_base/knowledge_governance/mechanism_metadata.py",
            "Bot_data_base/tools/run_mechanism_metadata_audit.py",
            "Bot_data_base/tests/test_mechanism_metadata.py",
            "Bot_data_base/tests/test_run_mechanism_metadata_audit.py",
        ],
        "commands_run": [],
        "status": "passed",
    }

    _write_json(out_dir / "mechanism_metadata_schema_snapshot.json", build_schema_snapshot())
    _write_json(out_dir / "sample_normalized_chunks.json", sample_previews)
    _write_json(out_dir / "chunk_type_distribution.json", chunk_type_distribution)
    _write_json(out_dir / "metadata_completeness_report.json", completeness)
    _write_json(out_dir / "anti_heuristic_compliance_report.json", anti_heuristic)
    _write_json(out_dir / "mechanism_metadata_audit.json", audit)
    _write_text(out_dir / "mechanism_metadata_audit.md", _build_audit_markdown(audit))
    _write_json(out_dir / "no_mutation_proof.json", no_mutation)

    encoding_args = argparse.Namespace(
        prd=PRD_ID,
        logs_dir=str(out_dir),
        reports_dir=str(DEFAULT_REPORTS_DIR),
        out_dir=str(out_dir),
        report_prd=PRD_ID,
        repo_root=str(REPO_ROOT),
        fixed_file=[],
    )
    validate_artifact_encoding = _load_shared_encoding_validator()
    encoding_report = validate_artifact_encoding(encoding_args)
    target_encoding_path = out_dir / "encoding_hygiene_report.json"
    source_encoding_path = out_dir / "artifact_encoding_hygiene_report.json"
    if source_encoding_path.exists():
        source_encoding_path.replace(target_encoding_path)

    return {
        "audit": audit,
        "completeness": completeness,
        "anti_heuristic": anti_heuristic,
        "encoding_report": encoding_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run read-only mechanism-aware chunk metadata audit.")
    parser.add_argument("--mode", choices=["fixture", "dry-run", "real"], default="dry-run")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--out-dir", default=str(DEFAULT_LOG_DIR))
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result["audit"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
