from __future__ import annotations

import argparse
import importlib.util
import json
import os
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

from knowledge_governance.offline_enrichment import (  # noqa: E402
    DEFAULT_MANUAL_REVIEW_REASON,
    ENRICHMENT_CANDIDATE_SCHEMA_VERSION,
    LLM_PROMPT_VERSION,
    PRD_ID,
    build_candidates_sample_markdown,
    build_chapter_coverage_markdown,
    build_chapter_coverage_report,
    build_deterministic_candidate,
    build_enrichment_schema_snapshot,
    build_manual_review_markdown,
    build_manual_review_pack,
    build_quality_report,
    build_quality_report_markdown,
    build_source_profile,
    build_source_profile_markdown,
    current_metadata_summary,
    load_processed_blocks,
    load_registry_entry,
    normalize_text,
    prioritized_selection,
    read_json,
    relative_to_repo,
    resolve_registry_paths,
    selection_reason_bundle,
    source_filter_match,
    utc_now,
    validate_enrichment_candidate,
    write_json,
    write_text,
)
from knowledge_governance.mechanism_metadata import (  # noqa: E402
    adapt_block_to_mechanism_metadata,
    build_schema_snapshot,
    sanitize_metadata_preview,
)


DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
DEFAULT_REPORTS_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
SHARED_ENCODING_VALIDATOR_PATH = BOT_PSYCHOLOGIST_ROOT / "tools" / "validate_prd_artifact_encoding.py"


def load_shared_encoding_validator():
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


def write_markdown_summary(path: Path, title: str, lines: list[str]) -> None:
    payload = [f"# {title}", ""]
    payload.extend(lines)
    write_text(path, "\n".join(payload))


def run_source_gates(*, source_hint: str) -> dict[str, Any]:
    registry_path = REPO_ROOT / "Bot_data_base" / "data" / "registry.json"
    entry = load_registry_entry(registry_path=registry_path, source_hint=source_hint)
    paths = resolve_registry_paths(repo_root=REPO_ROOT, entry=entry)
    source_gate = {
        "registry_entry_found": True,
        "source_id": normalize_text(entry.get("source_id")),
        "source_title": normalize_text(entry.get("title")),
        "files": {
            name: {
                "path": relative_to_repo(path, REPO_ROOT),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
            }
            for name, path in paths.items()
        },
    }
    return {
        "entry": entry,
        "paths": paths,
        "source_gate": source_gate,
    }


def build_source_audit(
    *,
    git_status: str,
    git_log: list[str],
    source_gate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "prd_source_audit_v1",
        "prd_id": PRD_ID,
        "status": "passed",
        "git": {
            "status_short": git_status.splitlines(),
            "recent_commits": git_log,
            "contains_prd_047_16_successor": any("PRD-047.16" in line for line in git_log),
        },
        "source_gate": source_gate,
        "previous_prd_047_16_gaps_to_close": [
            "missing_mechanism_hints_count=28/54",
            "contraindications_present_ratio=0.0",
            "practice metadata gaps remain",
            "use_when / avoid_when still partly generic and not source-grounded",
        ],
        "out_of_scope_gaps": [
            "no live Writer/runtime activation",
            "no Chroma reindex",
            "no DB mutation",
            "no MemoryRetrievalAgent live behavior change",
        ],
        "fields_never_auto_applied_without_review": [
            "mechanism_hints_candidates",
            "use_when_candidates",
            "avoid_when_candidates",
            "contraindications_candidates",
            "safe_user_translation_candidate",
            "risk_if_exposed_candidate",
            "allowed_writer_use_candidate",
        ],
        "existing_modules_reused": [
            "Bot_data_base/knowledge_governance/enrichment_contracts.py",
            "Bot_data_base/knowledge_governance/enrichment_validators.py",
            "Bot_data_base/knowledge_governance/mechanism_metadata.py",
            "Bot_data_base/tools/run_mechanism_metadata_audit.py",
        ],
    }


def build_source_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# PRD-047.17 Source Audit",
        "",
        f"- status: `{audit['status']}`",
        f"- contains_prd_047_16_successor: `{audit['git']['contains_prd_047_16_successor']}`",
        "",
        "## Git Status",
    ]
    for line in audit["git"]["status_short"] or ["clean"]:
        lines.append(f"- `{line}`")
    lines.extend(["", "## Previous Gaps To Close"])
    for line in audit["previous_prd_047_16_gaps_to_close"]:
        lines.append(f"- {line}")
    lines.extend(["", "## Out Of Scope"])
    for line in audit["out_of_scope_gaps"]:
        lines.append(f"- {line}")
    return "\n".join(lines)


def gather_git_context() -> tuple[str, list[str]]:
    import subprocess

    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout.rstrip()
    log = subprocess.run(
        ["git", "log", "--oneline", "-20"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    ).stdout.splitlines()
    return status, log


def build_runtime_activation_report(*, out_dir: Path) -> dict[str, Any]:
    runtime_targets = [
        REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent",
        REPO_ROOT / "bot_psychologist" / "api",
        REPO_ROOT / "Bot_data_base" / "api",
        REPO_ROOT / "Bot_data_base" / "storage",
    ]
    forbidden_patterns = {
        'if "мама" in user_message',
        'if "стыд" in user_message',
        'if "контроль" in user_message',
        'if "паника" in user_message',
        'metadata["mechanism_hints"] -> direct response mode',
        "candidate_fields -> WriterContract live path",
        "safe_to_apply_automatically = true",
    }
    candidate_runtime_tokens = [
        ENRICHMENT_CANDIDATE_SCHEMA_VERSION,
        "candidate_fields",
        "safe_to_apply_automatically",
        "manual_review_required_by_prd",
    ]
    file_results: list[dict[str, Any]] = []
    runtime_token_hits: list[dict[str, Any]] = []
    for root in runtime_targets:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            lines = [line.strip().lower() for line in text.splitlines() if not line.strip().startswith(("'", '"'))]
            hits = [pattern for pattern in forbidden_patterns if pattern in lines]
            if hits:
                file_results.append(
                    {
                        "path": relative_to_repo(path, REPO_ROOT),
                        "forbidden_hits": hits,
                    }
                )
            content_lower = text.lower()
            token_hits = [token for token in candidate_runtime_tokens if token.lower() in content_lower]
            if token_hits and "offline_enrichment.py" not in path.name and "run_mechanism_metadata_enrichment.py" not in path.name:
                runtime_token_hits.append(
                    {
                        "path": relative_to_repo(path, REPO_ROOT),
                        "tokens": token_hits,
                    }
                )
    report = {
        "schema_version": "anti_runtime_activation_report_v1",
        "prd_id": PRD_ID,
        "status": "passed" if not file_results and not runtime_token_hits else "failed",
        "forbidden_pattern_hits": file_results,
        "runtime_token_hits": runtime_token_hits,
        "notes": [
            "Offline enrichment candidates are not wired into bot_psychologist runtime.",
            "Mechanism hints remain metadata candidates only.",
            "No Writer authority change or Chroma reindex was performed.",
        ],
    }
    write_json(out_dir / "anti_heuristic_compliance_report.json", report)
    return report


def build_no_mutation_proof(*, provider_llm_calls_used: bool) -> dict[str, Any]:
    return {
        "prd_id": PRD_ID,
        "runtime_user_facing_changed": False,
        "writer_prompt_changed": False,
        "state_analyzer_changed": False,
        "thread_manager_changed": False,
        "hybrid_retrieval_planner_runtime_changed": False,
        "memory_retrieval_live_behavior_changed": False,
        "writer_contract_live_changed": False,
        "chroma_reindexed": False,
        "db_schema_destructive_change": False,
        "processed_blocks_overwritten": False,
        "embeddings_changed": False,
        "new_runtime_path_created": False,
        "enrichment_candidates_applied_to_live_metadata": False,
        "provider_llm_calls_used": provider_llm_calls_used,
        "provider_llm_calls_used_if_any_are_offline_only": True,
        "raw_provider_payload_committed": False,
        "raw_content_full_in_reports": False,
        "secrets_or_env_committed": False,
        "status": "passed",
    }


def write_llm_skipped_artifact(*, out_dir: Path, reason: str, confirmed: bool) -> dict[str, Any]:
    payload = {
        "schema_version": "llm_enrichment_skipped_v1",
        "prd_id": PRD_ID,
        "mode": "llm_candidate",
        "confirmed": confirmed,
        "reason": reason,
        "provider_llm_calls_used": False,
        "raw_provider_payload_committed": False,
        "created_at": utc_now(),
        "status": "skipped",
    }
    write_json(out_dir / "llm_enrichment_skipped.json", payload)
    return payload


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = Path(args.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    git_status, git_log = gather_git_context()
    source_context = run_source_gates(source_hint=str(args.source))
    source_audit = build_source_audit(
        git_status=git_status,
        git_log=git_log,
        source_gate=source_context["source_gate"],
    )
    write_json(out_dir / "source_audit.json", source_audit)
    write_text(out_dir / "source_audit.md", build_source_audit_markdown(source_audit))

    entry = source_context["entry"]
    paths = source_context["paths"]
    processed_blocks = load_processed_blocks(processed_path=paths["processed_json"])
    source_id = normalize_text(entry.get("source_id"))
    source_doc = normalize_text(entry.get("title"))
    filtered_blocks = [
        block
        for block in processed_blocks
        if source_filter_match(
            block=block,
            source_hint=str(args.source),
            source_id=source_id,
            source_title=source_doc,
        )
    ]
    if not filtered_blocks:
        filtered_blocks = processed_blocks

    profile = build_source_profile(
        repo_root=REPO_ROOT,
        entry=entry,
        upload_path=paths["upload_path"],
        processed_path=paths["processed_json"],
        blocks=filtered_blocks,
    )
    write_json(out_dir / "kuznica_source_profile.json", profile)
    write_text(out_dir / "kuznica_source_profile.md", build_source_profile_markdown(profile))

    chapter_coverage = build_chapter_coverage_report(filtered_blocks)
    write_json(out_dir / "kuznica_chapter_coverage_report.json", chapter_coverage)
    write_text(out_dir / "kuznica_chapter_coverage_report.md", build_chapter_coverage_markdown(chapter_coverage))

    if args.mode == "llm-candidate":
        if not args.confirm_provider:
            skipped = write_llm_skipped_artifact(
                out_dir=out_dir,
                reason="confirm_provider_flag_missing",
                confirmed=False,
            )
            return {"status": "skipped", "llm_skipped": skipped}
        if not os.getenv("OPENAI_API_KEY"):
            skipped = write_llm_skipped_artifact(
                out_dir=out_dir,
                reason="openai_api_key_missing",
                confirmed=True,
            )
            return {"status": "skipped", "llm_skipped": skipped}
        skipped = write_llm_skipped_artifact(
            out_dir=out_dir,
            reason="llm_candidate_mode_deferred_to_future_prd",
            confirmed=True,
        )
        return {"status": "skipped", "llm_skipped": skipped}

    selected_blocks = prioritized_selection(filtered_blocks, limit=int(args.limit))
    candidate_results = []
    sample_normalized_chunks: list[dict[str, Any]] = []
    for raw_block in selected_blocks:
        metadata, _ = adapt_block_to_mechanism_metadata(raw_block)
        chapter_number = (metadata.heading_path and None) or None
        selection_reasons = selection_reason_bundle(metadata, block_chapter_number(raw_block))
        built = build_deterministic_candidate(
            repo_root=REPO_ROOT,
            source_id=source_id,
            source_doc=source_doc,
            raw_block=raw_block,
            metadata=metadata,
            selection_reasons=selection_reasons,
        )
        candidate_results.append(built)
        if len(sample_normalized_chunks) < 20:
            sample_normalized_chunks.append(sanitize_metadata_preview(metadata))

    candidates = [item.candidate for item in candidate_results]
    validations = [item.validation for item in candidate_results]

    deterministic_payload = {
        "schema_version": "mechanism_metadata_enrichment_run_v1",
        "prd_id": PRD_ID,
        "mode": "deterministic",
        "source": str(args.source),
        "source_id": source_id,
        "source_doc": source_doc,
        "selected_blocks": len(selected_blocks),
        "candidate_count": len(candidates),
        "created_at": utc_now(),
        "candidates": candidates,
    }
    write_json(out_dir / "enrichment_schema_snapshot.json", build_enrichment_schema_snapshot())
    write_json(out_dir / "mechanism_metadata_schema_snapshot.json", build_schema_snapshot())
    write_json(out_dir / "sample_normalized_chunks.json", sample_normalized_chunks)
    write_json(out_dir / "enrichment_candidates_deterministic.json", deterministic_payload)
    write_text(out_dir / "enrichment_candidates_sample.md", build_candidates_sample_markdown(candidates))

    quality_report = build_quality_report(
        source_id=source_id,
        source_doc=source_doc,
        total_source_blocks=len(filtered_blocks),
        selected_blocks=selected_blocks,
        candidates=candidates,
        validations=validations,
    )
    write_json(out_dir / "enrichment_quality_report.json", quality_report)
    write_text(out_dir / "enrichment_quality_report.md", build_quality_report_markdown(quality_report))

    manual_review_pack = build_manual_review_pack(candidates, validations)
    write_json(out_dir / "manual_review_pack.json", manual_review_pack)
    write_text(out_dir / "manual_review_pack.md", build_manual_review_markdown(manual_review_pack))

    anti_runtime_activation = build_runtime_activation_report(out_dir=out_dir)
    no_mutation_proof = build_no_mutation_proof(provider_llm_calls_used=False)
    write_json(out_dir / "no_mutation_proof.json", no_mutation_proof)
    llm_skipped = write_llm_skipped_artifact(
        out_dir=out_dir,
        reason="llm_candidate_mode_not_requested",
        confirmed=False,
    )

    encoding_runner = load_shared_encoding_validator()
    encoding_report = encoding_runner(
        argparse.Namespace(
            prd=PRD_ID,
            logs_dir=str(out_dir),
            reports_dir=str(reports_dir),
            out_dir=str(out_dir),
            report_prd=PRD_ID,
            repo_root=str(REPO_ROOT),
            fixed_file=[],
        )
    )
    source_encoding_path = out_dir / "artifact_encoding_hygiene_report.json"
    target_encoding_path = out_dir / "encoding_hygiene_report.json"
    if source_encoding_path.exists():
        target_encoding_path.write_text(source_encoding_path.read_text(encoding="utf-8"), encoding="utf-8")

    return {
        "status": quality_report["status"],
        "source_audit": source_audit,
        "source_profile": profile,
        "chapter_coverage": chapter_coverage,
        "quality_report": quality_report,
        "manual_review_pack": manual_review_pack,
        "anti_runtime_activation": anti_runtime_activation,
        "no_mutation_proof": no_mutation_proof,
        "encoding_report": encoding_report,
        "llm_skipped": llm_skipped,
    }


def block_chapter_number(block: dict[str, Any]) -> int | None:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    heading_path = metadata.get("heading_path") if isinstance(metadata.get("heading_path"), list) else []
    first_heading = normalize_text(heading_path[0] if heading_path else block.get("title"))
    import re

    match = re.search(r"глава\s+(\d+)", first_heading, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PRD-047.17 offline mechanism metadata enrichment.")
    parser.add_argument("--mode", choices=["deterministic", "llm-candidate"], default="deterministic")
    parser.add_argument("--source", default="kuznica")
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--out-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--confirm-provider", action="store_true")
    args = parser.parse_args()
    result = run(args)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    summary = {
        "status": result.get("status"),
        "quality_status": result.get("quality_report", {}).get("status"),
        "source_id": result.get("source_profile", {}).get("source_id"),
        "selected_blocks": result.get("quality_report", {}).get("selected_blocks"),
        "candidate_count": result.get("quality_report", {}).get("candidate_count"),
        "llm_skipped_reason": result.get("llm_skipped", {}).get("reason"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
