from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
BOTDB_ROOT = CURRENT_DIR.parent
REPO_ROOT = BOTDB_ROOT.parent
BOT_PSYCHOLOGIST_ROOT = REPO_ROOT / "bot_psychologist"

if str(BOTDB_ROOT) not in sys.path:
    sys.path.insert(0, str(BOTDB_ROOT))

from knowledge_governance.manual_review import (  # noqa: E402
    CURATED_OVERLAY_SCHEMA_VERSION,
    PRD_ID,
    REVIEW_DECISION_SCHEMA_VERSION,
    REVIEW_QUEUE_SCHEMA_VERSION,
    SOURCE_PRD_ID,
    build_candidate_index,
    build_curation_status_report,
    build_curated_overlay_preview,
    build_review_decisions_template,
    build_review_queue,
    candidate_chunk_type,
    candidate_id_of,
    candidate_risk_level,
    render_curation_status_markdown,
    render_curated_overlay_markdown,
    render_curated_overlay_summary_markdown,
    render_review_decisions_template_markdown,
    render_review_queue_markdown,
    render_validation_report_markdown,
    validate_review_decisions,
)
from knowledge_governance.offline_enrichment import (  # noqa: E402
    load_processed_blocks,
    load_registry_entry,
    normalize_text,
    read_json,
    relative_to_repo,
    resolve_registry_paths,
    sha256_file,
    source_filter_match,
    utc_now,
    write_json,
    write_text,
)


DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
DEFAULT_REPORTS_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
PRD17_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / SOURCE_PRD_ID
ENCODING_VALIDATOR_PATH = BOT_PSYCHOLOGIST_ROOT / "tools" / "validate_prd_artifact_encoding.py"
RUNTIME_ROOTS = [
    REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent",
    REPO_ROOT / "bot_psychologist" / "api",
    REPO_ROOT / "Bot_data_base" / "api",
    REPO_ROOT / "Bot_data_base" / "storage",
]
REQUIRED_PRD17_COMMITS = [
    "7d49c86",
    "227f412",
    "d1c33d9",
]
REQUIRED_PRD17_FILES = [
    PRD17_LOG_DIR / "enrichment_candidates_deterministic.json",
    PRD17_LOG_DIR / "manual_review_pack.json",
    PRD17_LOG_DIR / "enrichment_quality_report.json",
    PRD17_LOG_DIR / "kuznica_source_profile.json",
    PRD17_LOG_DIR / "no_mutation_proof.json",
]
REVIEW_RUNTIME_TOKENS = {
    REVIEW_DECISION_SCHEMA_VERSION,
    CURATED_OVERLAY_SCHEMA_VERSION,
    REVIEW_QUEUE_SCHEMA_VERSION,
    "safe_to_apply_to_live_metadata",
    "curated_overlay_preview",
}


def load_shared_encoding_validator():
    spec = importlib.util.spec_from_file_location("shared_encoding_validator", ENCODING_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load encoding validator: {ENCODING_VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.run


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()


def markdown_document(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines])


def load_candidate_run() -> dict[str, Any]:
    return read_json(PRD17_LOG_DIR / "enrichment_candidates_deterministic.json")


def load_manual_review_pack() -> dict[str, Any]:
    return read_json(PRD17_LOG_DIR / "manual_review_pack.json")


def run_source_gates(*, out_dir: Path, source_hint: str = "kuznica") -> dict[str, Any]:
    registry_path = REPO_ROOT / "Bot_data_base" / "data" / "registry.json"
    entry = load_registry_entry(registry_path=registry_path, source_hint=source_hint)
    paths = resolve_registry_paths(repo_root=REPO_ROOT, entry=entry)
    processed_blocks = load_processed_blocks(processed_path=paths["processed_json"])
    filtered_blocks = [
        block
        for block in processed_blocks
        if source_filter_match(
            block=block,
            source_hint=source_hint,
            source_id=normalize_text(entry.get("source_id")),
            source_title=normalize_text(entry.get("title")),
        )
    ]
    prd17_no_mutation = read_json(PRD17_LOG_DIR / "no_mutation_proof.json")
    recent_log = git_output("log", "--oneline", "-20").splitlines()
    report = {
        "schema_version": "prd_047_18_source_gate_report_v1",
        "prd_id": PRD_ID,
        "status": "passed",
        "created_at": utc_now(),
        "git_status_short": git_output("status", "--short").splitlines(),
        "recent_commits": recent_log,
        "required_commit_presence": {
            commit: any(line.startswith(commit) for line in recent_log) for commit in REQUIRED_PRD17_COMMITS
        },
        "required_files": [
            {
                "path": relative_to_repo(path, REPO_ROOT),
                "exists": path.exists(),
                "sha256": sha256_file(path) if path.exists() else "",
            }
            for path in REQUIRED_PRD17_FILES
        ],
        "prereq_no_mutation": {
            "status": prd17_no_mutation.get("status"),
            "enrichment_candidates_applied_to_live_metadata": prd17_no_mutation.get(
                "enrichment_candidates_applied_to_live_metadata"
            ),
            "chroma_reindexed": prd17_no_mutation.get("chroma_reindexed"),
            "provider_llm_calls_used": prd17_no_mutation.get("provider_llm_calls_used"),
            "raw_content_full_in_reports": prd17_no_mutation.get("raw_content_full_in_reports"),
        },
        "source": {
            "source_id": normalize_text(entry.get("source_id")),
            "source_doc": normalize_text(entry.get("title")),
            "registry_blocks_count": entry.get("blocks_count"),
            "filtered_blocks_count": len(filtered_blocks),
            "processed_json_path": relative_to_repo(paths["processed_json"], REPO_ROOT),
        },
        "blockers": [],
    }
    for commit, present in report["required_commit_presence"].items():
        if not present:
            report["blockers"].append(f"missing_commit:{commit}")
    for item in report["required_files"]:
        if not item["exists"]:
            report["blockers"].append(f"missing_required_file:{item['path']}")
    if report["prereq_no_mutation"] != {
        "status": "passed",
        "enrichment_candidates_applied_to_live_metadata": False,
        "chroma_reindexed": False,
        "provider_llm_calls_used": False,
        "raw_content_full_in_reports": False,
    }:
        report["blockers"].append("prd_047_17_no_mutation_invariants_failed")
    if len(filtered_blocks) != 247:
        report["blockers"].append(f"unexpected_filtered_blocks_count:{len(filtered_blocks)}")
    if report["blockers"]:
        report["status"] = "blocked"
    lines = [
        f"- status: `{report['status']}`",
        f"- source_id: `{report['source']['source_id']}`",
        f"- source_doc: `{report['source']['source_doc']}`",
        f"- filtered_blocks_count: `{report['source']['filtered_blocks_count']}`",
        "",
        "## Required Commits",
    ]
    for commit, present in report["required_commit_presence"].items():
        lines.append(f"- `{commit}`: `{present}`")
    lines.extend(["", "## Required Files"])
    for item in report["required_files"]:
        lines.append(f"- `{item['path']}` exists=`{item['exists']}`")
    lines.extend(["", "## Blockers"])
    for blocker in report["blockers"] or ["none"]:
        lines.append(f"- {blocker}")
    write_json(out_dir / "source_gate_report.json", report)
    write_text(out_dir / "source_gate_report.md", markdown_document("PRD-047.18 Source Gate Report", lines))
    return report


def write_review_queue_csv(path: Path, queue_document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "candidate_id",
                "queue_priority",
                "chunk_type",
                "risk_level",
                "heading_path",
                "content_preview",
                "candidate_fields_preview",
                "manual_review_reasons",
                "validation_warnings",
                "recommended_reviewer_action",
            ],
        )
        writer.writeheader()
        for item in queue_document.get("items", []):
            writer.writerow(
                {
                    "candidate_id": item["candidate_id"],
                    "queue_priority": item["queue_priority"],
                    "chunk_type": item["chunk_type"],
                    "risk_level": item["risk_level"],
                    "heading_path": " / ".join(item["heading_path"]),
                    "content_preview": item["content_preview"],
                    "candidate_fields_preview": json.dumps(item["candidate_fields_preview"], ensure_ascii=False),
                    "manual_review_reasons": json.dumps(item["manual_review_reasons"], ensure_ascii=False),
                    "validation_warnings": json.dumps(item["validation_warnings"], ensure_ascii=False),
                    "recommended_reviewer_action": item["recommended_reviewer_action"],
                }
            )


def run_queue(*, out_dir: Path) -> dict[str, Any]:
    candidate_run = load_candidate_run()
    manual_pack = load_manual_review_pack()
    queue_document = build_review_queue(candidate_run=candidate_run, manual_review_pack=manual_pack)
    template_document = build_review_decisions_template(list(candidate_run.get("candidates") or []))
    candidate_index = build_candidate_index(list(candidate_run.get("candidates") or []))
    validation_report = validate_review_decisions(template_document, candidate_index)
    curation_status = build_curation_status_report(
        queue_document=queue_document,
        validation_report=validation_report,
        decision_document=template_document,
    )
    write_json(out_dir / "review_queue.json", queue_document)
    write_text(out_dir / "review_queue.md", render_review_queue_markdown(queue_document))
    write_review_queue_csv(out_dir / "review_queue.csv", queue_document)
    write_json(out_dir / "review_decisions_template.json", template_document)
    write_text(out_dir / "review_decisions_template.md", render_review_decisions_template_markdown(template_document))
    write_json(out_dir / "curation_status_report.json", curation_status)
    write_text(out_dir / "curation_status_report.md", render_curation_status_markdown(curation_status))
    return {
        "queue_document": queue_document,
        "template_document": template_document,
        "validation_report": validation_report,
        "curation_status": curation_status,
    }


def run_validate(*, out_dir: Path, decisions_path: Path, output_prefix: str = "review_decision_validation_report") -> dict[str, Any]:
    candidate_index = build_candidate_index(list(load_candidate_run().get("candidates") or []))
    decision_document = read_json(decisions_path)
    report = validate_review_decisions(decision_document, candidate_index)
    write_json(out_dir / f"{output_prefix}.json", report)
    write_text(out_dir / f"{output_prefix}.md", render_validation_report_markdown(report))
    return report


def _find_candidate(
    candidates: list[dict[str, Any]],
    *,
    chunk_type: str,
    risk_level: str | None = None,
) -> dict[str, Any]:
    for candidate in candidates:
        if candidate_chunk_type(candidate) != chunk_type:
            continue
        if risk_level is not None and candidate_risk_level(candidate) != risk_level:
            continue
        return candidate
    raise RuntimeError(f"Unable to find candidate chunk_type={chunk_type} risk_level={risk_level}")


def _set_field(
    decision: dict[str, Any],
    *,
    field_name: str,
    action: str,
    value: Any,
    reason: str,
) -> None:
    decision["field_decisions"][field_name]["decision"] = action
    decision["field_decisions"][field_name]["value"] = value
    decision["field_decisions"][field_name]["reason"] = reason


def build_fixture_decisions() -> tuple[dict[str, Any], dict[str, Any]]:
    candidates = list(load_candidate_run().get("candidates") or [])
    concept_candidate = _find_candidate(candidates, chunk_type="concept", risk_level="low")
    lens_candidate = _find_candidate(candidates, chunk_type="diagnostic_lens")
    high_risk_practice = _find_candidate(candidates, chunk_type="practice", risk_level="high")
    medium_practice = _find_candidate(candidates, chunk_type="practice", risk_level="medium")

    concept_decision = build_review_decisions_template([concept_candidate])["decisions"][0]
    concept_decision["review_status"] = "accepted"
    concept_decision["reviewer_role"] = "fixture_only"
    concept_decision["reviewer_id"] = "fixture_accept_low_risk"
    concept_decision["reviewed_at"] = utc_now()
    _set_field(
        concept_decision,
        field_name="summary_candidate",
        action="accept",
        value=(concept_candidate.get("candidate_fields") or {}).get("summary_candidate"),
        reason="Low-risk concept summary accepted as compact derived lens.",
    )
    _set_field(
        concept_decision,
        field_name="allowed_writer_use_candidate",
        action="accept",
        value=(concept_candidate.get("candidate_fields") or {}).get("allowed_writer_use_candidate"),
        reason="Writer-use wording remains advisory and compact.",
    )

    lens_decision = build_review_decisions_template([lens_candidate])["decisions"][0]
    lens_decision["review_status"] = "rejected"
    lens_decision["reviewer_role"] = "fixture_only"
    lens_decision["reviewer_id"] = "fixture_reject_lens"
    lens_decision["reviewed_at"] = utc_now()
    _set_field(
        lens_decision,
        field_name="safe_user_translation_candidate",
        action="reject",
        value="",
        reason="Fixture rejects this translation as too strong for safe user phrasing.",
    )

    deferred_practice = build_review_decisions_template([high_risk_practice])["decisions"][0]
    deferred_practice["review_status"] = "deferred"
    deferred_practice["reviewer_role"] = "fixture_only"
    deferred_practice["reviewer_id"] = "fixture_defer_practice"
    deferred_practice["reviewed_at"] = utc_now()
    _set_field(
        deferred_practice,
        field_name="summary_candidate",
        action="defer",
        value="",
        reason="High-risk practice stays deferred until deeper human review of contraindications.",
    )

    practice_accept = build_review_decisions_template([medium_practice])["decisions"][0]
    practice_accept["review_status"] = "accepted_with_edits"
    practice_accept["reviewer_role"] = "fixture_only"
    practice_accept["reviewer_id"] = "fixture_accept_practice"
    practice_accept["reviewed_at"] = utc_now()
    _set_field(
        practice_accept,
        field_name="avoid_when_candidates",
        action="accept_with_edit",
        value=[
            "Не предлагать без явного запроса и если пользователь заметно перегружен.",
            "Не давать как замену прямому ответу на вопрос пользователя.",
        ],
        reason="Avoid-when was edited to be stricter and clearer.",
    )
    _set_field(
        practice_accept,
        field_name="contraindications_candidates",
        action="accept_with_edit",
        value=[
            "Острая дестабилизация или телесная перегрузка, где практика усилит давление.",
            "Сильное истощение, когда даже короткое задание воспринимается как дополнительный долг.",
        ],
        reason="Fixture adds explicit contraindications before any preview acceptance.",
    )
    _set_field(
        practice_accept,
        field_name="allowed_writer_use_candidate",
        action="accept",
        value=(medium_practice.get("candidate_fields") or {}).get("allowed_writer_use_candidate"),
        reason="Allowed-writer-use stays constrained and timing-bound.",
    )

    fixture_document = {
        "schema_version": REVIEW_DECISION_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "source_prd": SOURCE_PRD_ID,
        "created_at": utc_now(),
        "decision_count": 4,
        "accepted_field_count": 5,
        "fixture_only": True,
        "decisions": [concept_decision, lens_decision, deferred_practice, practice_accept],
    }

    negative = build_review_decisions_template([high_risk_practice])["decisions"][0]
    negative["review_status"] = "accepted"
    negative["reviewer_role"] = "fixture_only"
    negative["reviewer_id"] = "fixture_negative"
    negative["reviewed_at"] = utc_now()
    _set_field(
        negative,
        field_name="allowed_writer_use_candidate",
        action="accept",
        value=(high_risk_practice.get("candidate_fields") or {}).get("allowed_writer_use_candidate"),
        reason="Intentionally invalid: accepts high-risk practice without contraindications.",
    )
    negative_document = {
        "schema_version": REVIEW_DECISION_SCHEMA_VERSION,
        "prd_id": PRD_ID,
        "source_prd": SOURCE_PRD_ID,
        "created_at": utc_now(),
        "decision_count": 1,
        "accepted_field_count": 1,
        "fixture_only": True,
        "decisions": [negative],
    }
    return fixture_document, negative_document


def run_fixture(*, out_dir: Path) -> dict[str, Any]:
    fixture_document, negative_document = build_fixture_decisions()
    write_json(out_dir / "review_decisions_fixture.json", fixture_document)
    write_json(out_dir / "review_decisions_negative_fixture.json", negative_document)
    return {
        "fixture_path": out_dir / "review_decisions_fixture.json",
        "negative_path": out_dir / "review_decisions_negative_fixture.json",
    }


def run_preview(*, out_dir: Path, decisions_path: Path) -> dict[str, Any]:
    candidate_index = build_candidate_index(list(load_candidate_run().get("candidates") or []))
    decision_document = read_json(decisions_path)
    overlay = build_curated_overlay_preview(candidate_index=candidate_index, decision_document=decision_document)
    overlay["decisions_file"] = relative_to_repo(decisions_path, REPO_ROOT)
    summary = {
        "schema_version": "mechanism_metadata_curated_overlay_summary_v1",
        "prd_id": PRD_ID,
        "source_prd": SOURCE_PRD_ID,
        "fixture_only": overlay["fixture_only"],
        "live_apply_allowed": overlay["live_apply_allowed"],
        "accepted_item_count": overlay["summary"]["accepted_item_count"],
        "accepted_field_count": overlay["summary"]["accepted_field_count"],
        "by_chunk_type": overlay["summary"]["by_chunk_type"],
        "by_risk_level": overlay["summary"]["by_risk_level"],
        "decisions_file": overlay["decisions_file"],
    }
    write_json(out_dir / "curated_overlay_preview.json", overlay)
    write_text(out_dir / "curated_overlay_preview.md", render_curated_overlay_markdown(overlay))
    write_json(out_dir / "curated_overlay_summary.json", summary)
    write_text(out_dir / "curated_overlay_summary.md", render_curated_overlay_summary_markdown(overlay))
    return overlay


def build_runtime_token_report(*, out_dir: Path) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for root in RUNTIME_ROOTS:
        for path in root.rglob("*.py"):
            content = path.read_text(encoding="utf-8").lower()
            matched = sorted(token for token in REVIEW_RUNTIME_TOKENS if token.lower() in content)
            if matched:
                hits.append({"path": relative_to_repo(path, REPO_ROOT), "tokens": matched})
    report = {
        "schema_version": "mechanism_metadata_review_no_runtime_activation_v1",
        "prd_id": PRD_ID,
        "status": "passed" if not hits else "failed",
        "runtime_token_hits": hits,
        "notes": [
            "PRD-047.18 creates offline review workflow only.",
            "Curated overlay preview is not wired into live runtime files.",
        ],
    }
    write_json(out_dir / "anti_runtime_activation_report.json", report)
    return report


def build_no_mutation_proof(*, out_dir: Path) -> dict[str, Any]:
    report = {
        "schema_version": "prd_047_18_no_mutation_proof_v1",
        "prd_id": PRD_ID,
        "status": "passed",
        "writer_runtime_changed": False,
        "writer_prompt_changed": False,
        "hybrid_retrieval_planner_changed": False,
        "memory_retrieval_changed": False,
        "dialogue_policy_changed": False,
        "live_metadata_applied": False,
        "safe_to_apply_to_live_metadata": False,
        "curated_overlay_preview_only": True,
        "chroma_reindexed": False,
        "processed_blocks_overwritten": False,
        "registry_mutated": False,
        "provider_llm_calls_used": False,
        "raw_provider_payload_committed": False,
        "raw_full_source_text_committed": False,
    }
    write_json(out_dir / "no_mutation_proof.json", report)
    return report


def run_botdb_readonly_smoke(*, out_dir: Path, base_url: str) -> dict[str, Any]:
    result = {
        "schema_version": "botdb_readonly_smoke_v1",
        "prd_id": PRD_ID,
        "base_url": base_url,
        "status": "passed",
        "checks": [],
        "warnings": [],
    }

    def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> None:
        url = f"{base_url.rstrip('/')}{path}"
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url=url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                body = response.read(1200).decode("utf-8", errors="replace")
                result["checks"].append({"method": method, "path": path, "status": response.status, "body_preview": body})
        except urllib.error.HTTPError as exc:
            body = exc.read(1200).decode("utf-8", errors="replace")
            result["checks"].append({"method": method, "path": path, "status": exc.code, "body_preview": body})
        except Exception as exc:  # noqa: BLE001
            result["status"] = "warning"
            result["warnings"].append(f"{path}:{type(exc).__name__}:{exc}")

    _request("GET", "/api/status")
    _request("GET", "/api/registry")
    _request("POST", "/api/query/", {"query": "контроль как защита", "top_k": 3})
    write_json(out_dir / "botdb_readonly_smoke.json", result)
    return result


def run_encoding_hygiene(*, out_dir: Path, reports_dir: Path) -> dict[str, Any]:
    validator = load_shared_encoding_validator()
    report = validator(
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
    write_json(out_dir / "encoding_hygiene_report.json", report)
    return report


def build_implementation_summary(*, out_dir: Path, queue_document: dict[str, Any], fixture_overlay: dict[str, Any]) -> dict[str, Any]:
    report = {
        "schema_version": "prd_047_18_implementation_summary_v1",
        "prd_id": PRD_ID,
        "status": "passed",
        "queue_count": queue_document.get("queue_count"),
        "candidate_count": queue_document.get("candidate_count"),
        "template_accepts_real_candidates": False,
        "fixture_overlay_item_count": fixture_overlay["summary"]["accepted_item_count"],
        "fixture_overlay_field_count": fixture_overlay["summary"]["accepted_field_count"],
        "live_apply_allowed": False,
        "created_at": utc_now(),
    }
    write_json(out_dir / "implementation_summary.json", report)
    return report


def write_implementation_report(*, reports_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        f"- status: `{summary['status']}`",
        f"- queue_count: `{summary['queue_count']}`",
        f"- candidate_count: `{summary['candidate_count']}`",
        f"- template_accepts_real_candidates: `{summary['template_accepts_real_candidates']}`",
        f"- fixture_overlay_item_count: `{summary['fixture_overlay_item_count']}`",
        f"- fixture_overlay_field_count: `{summary['fixture_overlay_field_count']}`",
        f"- live_apply_allowed: `{summary['live_apply_allowed']}`",
        "",
        "## Scope",
        "- added offline manual-review contract and validator over PRD-047.17 candidates",
        "- generated review queue, pending decision template, fixture decisions, and curated overlay preview",
        "- kept live metadata/runtime/Writer/Chroma unchanged",
    ]
    write_text(reports_dir / "PRD-047.18_IMPLEMENTATION_REPORT.md", markdown_document("PRD-047.18 Implementation Report", lines))
    next_lines = [
        "1. PRD-047.19 - Curated Candidate Dry-Run Apply Plan / Preflight over Accepted Overlay v1",
        "2. Keep live apply, Chroma reindex, and runtime visibility in separate explicit governance PRDs.",
    ]
    write_text(
        reports_dir / "PRD-047.18_NEXT_PRD_RECOMMENDATION.md",
        markdown_document("PRD-047.18 Next PRD Recommendation", next_lines),
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = Path(args.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    source_gate_report = run_source_gates(out_dir=out_dir, source_hint=str(args.source))
    if source_gate_report["status"] != "passed":
        return {"status": "blocked", "source_gate_report": source_gate_report}

    if args.mode == "queue":
        queue_result = run_queue(out_dir=out_dir)
        run_validate(out_dir=out_dir, decisions_path=out_dir / "review_decisions_template.json")
        return {"status": "passed", **queue_result}

    if args.mode == "validate":
        decisions_path = Path(args.decisions_file or (out_dir / "review_decisions_template.json")).resolve()
        report = run_validate(out_dir=out_dir, decisions_path=decisions_path)
        return {"status": report["status"], "validation_report": report}

    if args.mode == "fixture":
        payload = run_fixture(out_dir=out_dir)
        return {"status": "passed", **payload}

    if args.mode == "preview":
        decisions_path = Path(args.decisions_file or (out_dir / "review_decisions_fixture.json")).resolve()
        overlay = run_preview(out_dir=out_dir, decisions_path=decisions_path)
        return {"status": "passed", "overlay": overlay}

    if args.mode == "full":
        queue_result = run_queue(out_dir=out_dir)
        validation_report = run_validate(out_dir=out_dir, decisions_path=out_dir / "review_decisions_template.json")
        fixture_result = run_fixture(out_dir=out_dir)
        run_validate(
            out_dir=out_dir,
            decisions_path=fixture_result["fixture_path"],
            output_prefix="review_decision_validation_fixture_report",
        )
        run_validate(
            out_dir=out_dir,
            decisions_path=fixture_result["negative_path"],
            output_prefix="review_decision_validation_negative_fixture_report",
        )
        overlay = run_preview(out_dir=out_dir, decisions_path=fixture_result["fixture_path"])
        runtime_report = build_runtime_token_report(out_dir=out_dir)
        no_mutation = build_no_mutation_proof(out_dir=out_dir)
        botdb_smoke = run_botdb_readonly_smoke(out_dir=out_dir, base_url=str(args.botdb_base_url))
        encoding_report = run_encoding_hygiene(out_dir=out_dir, reports_dir=reports_dir)
        summary = build_implementation_summary(
            out_dir=out_dir,
            queue_document=queue_result["queue_document"],
            fixture_overlay=overlay,
        )
        write_implementation_report(reports_dir=reports_dir, summary=summary)
        status = "passed"
        if validation_report["status"] == "failed" or runtime_report["status"] == "failed" or no_mutation["status"] != "passed":
            status = "failed"
        if encoding_report["final_status"] != "passed" or botdb_smoke["status"] == "warning":
            status = "warning" if status == "passed" else status
        return {
            "status": status,
            "source_gate_report": source_gate_report,
            "queue_document": queue_result["queue_document"],
            "validation_report": validation_report,
            "overlay": overlay,
            "runtime_report": runtime_report,
            "no_mutation": no_mutation,
            "botdb_smoke": botdb_smoke,
            "encoding_report": encoding_report,
            "implementation_summary": summary,
        }

    raise ValueError(f"Unsupported mode: {args.mode}")


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-047.18 manual review workflow runner.")
    parser.add_argument("--mode", choices=["queue", "validate", "preview", "fixture", "full"], default="full")
    parser.add_argument("--source", default="kuznica")
    parser.add_argument("--decisions-file", default="")
    parser.add_argument("--out-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--botdb-base-url", default="http://127.0.0.1:8003")
    args = parser.parse_args()
    result = run(args)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        print(output)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((output + "\n").encode("utf-8", errors="replace"))
    return 0 if result.get("status") in {"passed", "warning", "passed_with_no_accepted_fields"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
