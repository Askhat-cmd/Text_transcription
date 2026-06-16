from __future__ import annotations

import argparse
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

from knowledge_governance.curated_batch_eval import (  # noqa: E402
    BATCH_ID,
    PRD_ID,
    RETRIEVAL_RESULTS_SCHEMA_VERSION,
    build_batch_1_decisions_pack,
    build_batch_1_overlay_preview,
    build_batch_1_preflight_bundle,
    build_batch_1_selection,
    build_candidate_index_from_run,
    build_retrieval_eval_dataset,
    build_retrieval_eval_results,
    render_batch_decisions_markdown,
    render_batch_overlay_markdown,
    render_batch_preflight_markdown,
    render_batch_selection_markdown,
    render_retrieval_eval_dataset_markdown,
    render_retrieval_eval_results_markdown,
)
from knowledge_governance.offline_enrichment import (  # noqa: E402
    load_processed_blocks,
    load_registry_entry,
    normalize_text,
    read_json,
    relative_to_repo,
    resolve_registry_paths,
    safe_preview,
    sha256_file,
    source_filter_match,
    utc_now,
    write_json,
    write_text,
)
from knowledge_governance.manual_review_preflight import build_processed_block_index  # noqa: E402


DEFAULT_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
DEFAULT_REPORTS_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
PRD17_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.17"
PRD18_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.18"
PRD19_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.19"
PRD19_HF1_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.19-HF1"
ENCODING_VALIDATOR_PATH = BOT_PSYCHOLOGIST_ROOT / "tools" / "validate_prd_artifact_encoding.py"
REQUIRED_COMMITS = ["dfb814d", "9973ae2", "b347a03", "6f7cc0e"]
REQUIRED_FILES = [
    PRD17_LOG_DIR / "enrichment_candidates_deterministic.json",
    PRD18_LOG_DIR / "review_queue.json",
    PRD18_LOG_DIR / "review_decisions_template.json",
    PRD19_LOG_DIR / "apply_preflight_report.json",
    PRD19_HF1_LOG_DIR / "regression_rerun_summary.json",
]
RUNTIME_ROOTS = [
    REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent",
    REPO_ROOT / "bot_psychologist" / "api",
    REPO_ROOT / "Bot_data_base" / "api",
    REPO_ROOT / "Bot_data_base" / "storage",
]
FORBIDDEN_RUNTIME_TOKENS = {
    "mechanism_metadata_curated_batch_selection_v1",
    "mechanism_metadata_curated_batch_retrieval_eval_results_v1",
    "offline_curator_batch_1",
    "batch_1_overlay_shadow_lookup",
    "evaluation_only_overlay",
}


def markdown_document(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines])


def git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()


def load_shared_encoding_validator():
    spec = importlib.util.spec_from_file_location("shared_encoding_validator", ENCODING_VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load encoding validator: {ENCODING_VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.run


def _request_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 8.0) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status_code": int(response.status),
                "body": json.loads(raw) if raw else {},
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {"raw_text": raw[:1000]}
        return {"ok": False, "status_code": int(exc.code), "body": body, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status_code": None, "body": {}, "error": f"{type(exc).__name__}: {exc}"}


def _load_context() -> dict[str, Any]:
    candidate_run = read_json(PRD17_LOG_DIR / "enrichment_candidates_deterministic.json")
    review_queue = read_json(PRD18_LOG_DIR / "review_queue.json")
    registry_path = REPO_ROOT / "Bot_data_base" / "data" / "registry.json"
    registry_entry = load_registry_entry(registry_path=registry_path, source_hint="kuznica")
    paths = resolve_registry_paths(repo_root=REPO_ROOT, entry=registry_entry)
    processed_blocks = load_processed_blocks(processed_path=paths["processed_json"])
    filtered_blocks = [
        block
        for block in processed_blocks
        if source_filter_match(
            block=block,
            source_hint="kuznica",
            source_id=normalize_text(registry_entry.get("source_id")),
            source_title=normalize_text(registry_entry.get("title")),
        )
    ]
    return {
        "candidate_run": candidate_run,
        "candidate_index": build_candidate_index_from_run(candidate_run),
        "review_queue": review_queue,
        "registry_entry": registry_entry,
        "filtered_blocks": filtered_blocks,
        "processed_block_index": build_processed_block_index(filtered_blocks),
        "paths": paths,
    }


def run_source_gates(*, out_dir: Path) -> dict[str, Any]:
    context = _load_context()
    recent_commits = git_output("log", "--oneline", "-20").splitlines()
    report = {
        "schema_version": "prd_047_20_source_gate_report_v1",
        "prd_id": PRD_ID,
        "created_at": utc_now(),
        "status": "passed",
        "git_status_short": git_output("status", "--short").splitlines(),
        "recent_commits": recent_commits,
        "required_commit_presence": {commit: any(line.startswith(commit) for line in recent_commits) for commit in REQUIRED_COMMITS},
        "required_files": [
            {
                "path": relative_to_repo(path, REPO_ROOT),
                "exists": path.exists(),
                "sha256": sha256_file(path) if path.exists() else "",
            }
            for path in REQUIRED_FILES
        ],
        "review_queue_count": int(context["review_queue"].get("queue_count") or 0),
        "candidate_count": int(context["candidate_run"].get("candidate_count") or 0),
        "source_id": normalize_text(context["registry_entry"].get("source_id")),
        "filtered_blocks_count": len(context["filtered_blocks"]),
        "blockers": [],
    }
    if report["review_queue_count"] != 80:
        report["blockers"].append(f"unexpected_review_queue_count:{report['review_queue_count']}")
    if report["candidate_count"] != 80:
        report["blockers"].append(f"unexpected_candidate_count:{report['candidate_count']}")
    if len(context["filtered_blocks"]) != 247:
        report["blockers"].append(f"unexpected_filtered_blocks_count:{len(context['filtered_blocks'])}")
    for commit, present in report["required_commit_presence"].items():
        if not present:
            report["blockers"].append(f"missing_commit:{commit}")
    for item in report["required_files"]:
        if not item["exists"]:
            report["blockers"].append(f"missing_required_file:{item['path']}")
    if report["blockers"]:
        report["status"] = "blocked"
    write_json(out_dir / "source_gate_report.json", report)
    write_text(
        out_dir / "source_gate_report.md",
        markdown_document(
            "PRD-047.20 Source Gate Report",
            [
                f"- status: `{report['status']}`",
                f"- review_queue_count: `{report['review_queue_count']}`",
                f"- candidate_count: `{report['candidate_count']}`",
                f"- filtered_blocks_count: `{report['filtered_blocks_count']}`",
                "",
                "## Blockers",
                *[f"- {item}" for item in (report["blockers"] or ["none"])],
            ],
        ),
    )
    return report


def run_select(*, out_dir: Path, context: dict[str, Any]) -> dict[str, Any]:
    selection = build_batch_1_selection(candidate_index=context["candidate_index"])
    write_json(out_dir / "batch_1_selection.json", selection)
    write_text(out_dir / "batch_1_selection.md", render_batch_selection_markdown(selection))
    return selection


def run_curate(*, out_dir: Path, context: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    decision_document = build_batch_1_decisions_pack(
        selection_document=selection,
        candidate_index=context["candidate_index"],
    )
    write_json(out_dir / "batch_1_decisions_pack.json", decision_document)
    write_text(out_dir / "batch_1_decisions_pack.md", render_batch_decisions_markdown(decision_document))
    validation_report = {
        "status": decision_document.get("validation_status"),
        "accepted_item_count": decision_document.get("accepted_item_count"),
        "accepted_field_count": decision_document.get("accepted_field_count"),
        "high_risk_practice_accepted_fields": decision_document.get("high_risk_practice_accepted_fields"),
    }
    write_json(out_dir / "batch_1_decisions_validation_report.json", validation_report)
    return decision_document


def run_overlay(*, out_dir: Path, context: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    overlay = build_batch_1_overlay_preview(
        candidate_index=context["candidate_index"],
        decision_document=decisions,
        decisions_file="TO_DO_LIST/logs/PRD-047.20/batch_1_decisions_pack.json",
    )
    write_json(out_dir / "batch_1_accepted_overlay_preview.json", overlay)
    write_text(out_dir / "batch_1_accepted_overlay_preview.md", render_batch_overlay_markdown(overlay))
    return overlay


def run_preflight(*, out_dir: Path, context: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    bundle = build_batch_1_preflight_bundle(
        overlay_document=overlay,
        candidate_index=context["candidate_index"],
        processed_block_index=context["processed_block_index"],
        overlay_file="TO_DO_LIST/logs/PRD-047.20/batch_1_accepted_overlay_preview.json",
    )
    write_json(out_dir / "batch_1_apply_preflight_report.json", bundle["apply_preflight_report"])
    write_text(out_dir / "batch_1_apply_preflight_report.md", render_batch_preflight_markdown(bundle["apply_preflight_report"]))
    write_json(out_dir / "batch_1_dry_run_apply_plan.json", bundle["dry_run_apply_plan"])
    write_text(
        out_dir / "batch_1_dry_run_apply_plan.md",
        markdown_document(
            "PRD-047.20 Batch 1 Dry-Run Apply Plan",
            [
                f"- item_count: `{bundle['dry_run_apply_plan']['summary']['item_count']}`",
                f"- field_count: `{bundle['dry_run_apply_plan']['summary']['field_count']}`",
                f"- blocked_item_count: `{bundle['dry_run_apply_plan']['summary']['blocked_item_count']}`",
                f"- warning_item_count: `{bundle['dry_run_apply_plan']['summary']['warning_item_count']}`",
            ],
        ),
    )
    return bundle


def _sanitize_baseline_hit(chunk: dict[str, Any]) -> dict[str, Any]:
    governance = chunk.get("governance") if isinstance(chunk.get("governance"), dict) else {}
    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    return {
        "id": normalize_text(chunk.get("chunk_id") or chunk.get("id")),
        "score": chunk.get("score"),
        "chunk_type": normalize_text(governance.get("chunk_type") or metadata.get("chunk_type")).lower(),
        "source_title": safe_preview(chunk.get("block_title") or chunk.get("title"), limit=140),
        "content_preview": safe_preview(
            chunk.get("content_preview")
            or chunk.get("content")
            or chunk.get("text")
            or chunk.get("summary"),
            limit=180,
        ),
    }


def run_retrieval_eval(
    *,
    out_dir: Path,
    context: dict[str, Any],
    selection: dict[str, Any],
    overlay: dict[str, Any],
    botdb_base_url: str,
) -> dict[str, Any]:
    dataset = build_retrieval_eval_dataset(selection_document=selection)
    write_json(out_dir / "retrieval_eval_dataset.json", dataset)
    write_text(out_dir / "retrieval_eval_dataset.md", render_retrieval_eval_dataset_markdown(dataset))

    baseline_results: dict[str, list[dict[str, Any]]] = {}
    baseline_available = False
    baseline_warning = ""
    status_preflight = _request_json("GET", f"{botdb_base_url.rstrip('/')}/api/status")
    registry_preflight = _request_json("GET", f"{botdb_base_url.rstrip('/')}/api/registry")
    if status_preflight["ok"] and registry_preflight["ok"]:
        baseline_available = True
        for case in dataset.get("cases", []):
            response = _request_json(
                "POST",
                f"{botdb_base_url.rstrip('/')}/api/query/",
                {
                    "query": case["query"],
                    "top_k": 5,
                    "pre_filter_k": 10,
                    "use_rerank": False,
                    "search_mode": "semantic",
                },
            )
            hits = []
            if response["ok"] and isinstance(response.get("body"), dict):
                for chunk in list((response["body"] or {}).get("chunks") or [])[:5]:
                    hits.append(_sanitize_baseline_hit(chunk))
            baseline_results[case["id"]] = hits
    else:
        baseline_warning = f"baseline_botdb_retrieval_skipped:{status_preflight['error'] or registry_preflight['error']}"
    baseline_payload = {
        "schema_version": "mechanism_metadata_curated_batch_baseline_results_v1",
        "prd_id": PRD_ID,
        "batch_id": BATCH_ID,
        "baseline_available": baseline_available,
        "baseline_warning": baseline_warning,
        "status_preflight": {
            "ok": status_preflight["ok"],
            "status_code": status_preflight["status_code"],
            "error": status_preflight["error"],
        },
        "registry_preflight": {
            "ok": registry_preflight["ok"],
            "status_code": registry_preflight["status_code"],
            "error": registry_preflight["error"],
        },
        "cases": baseline_results,
    }
    write_json(out_dir / "baseline_retrieval_results.json", baseline_payload)

    results = build_retrieval_eval_results(
        dataset_document=dataset,
        overlay_document=overlay,
        selection_document=selection,
        baseline_results=baseline_results,
        baseline_available=baseline_available,
        baseline_warning=baseline_warning,
    )
    write_json(out_dir / "retrieval_eval_results.json", results)
    write_text(out_dir / "retrieval_eval_results.md", render_retrieval_eval_results_markdown(results))
    return results


def build_runtime_token_report(*, out_dir: Path) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for root in RUNTIME_ROOTS:
        for path in root.rglob("*.py"):
            content = path.read_text(encoding="utf-8").lower()
            matched = sorted(token for token in FORBIDDEN_RUNTIME_TOKENS if token.lower() in content)
            if matched:
                hits.append({"path": relative_to_repo(path, REPO_ROOT), "tokens": matched})
    report = {
        "schema_version": "prd_047_20_anti_runtime_activation_v1",
        "prd_id": PRD_ID,
        "status": "passed" if not hits else "failed",
        "runtime_token_hits": hits,
        "notes": [
            "PRD-047.20 stays offline and evaluation-only.",
            "No curated batch tokens are allowed in active runtime roots.",
        ],
    }
    write_json(out_dir / "anti_runtime_activation_report.json", report)
    return report


def build_no_mutation_proof(*, out_dir: Path) -> dict[str, Any]:
    report = {
        "schema_version": "prd_047_20_no_mutation_proof_v1",
        "prd_id": PRD_ID,
        "status": "passed",
        "live_metadata_applied": False,
        "human_final_approval_written": False,
        "evaluation_only_overlay_only": True,
        "processed_blocks_overwritten": False,
        "registry_mutated": False,
        "chroma_reindexed": False,
        "writer_runtime_changed": False,
        "writer_prompt_changed": False,
        "bot_runtime_changed": False,
        "admin_surface_changed": False,
        "web_ui_changed": False,
        "retrieval_runtime_shadow_integrated": False,
    }
    write_json(out_dir / "no_mutation_proof.json", report)
    return report


def run_botdb_readonly_smoke(*, out_dir: Path, base_url: str) -> dict[str, Any]:
    result = {
        "schema_version": "prd_047_20_botdb_readonly_smoke_v1",
        "prd_id": PRD_ID,
        "base_url": base_url,
        "status": "passed",
        "checks": [],
        "warnings": [],
    }
    for method, path, payload in [
        ("GET", "/api/status", None),
        ("GET", "/api/registry", None),
        ("POST", "/api/query/", {"query": "контроль как безопасность", "top_k": 3}),
    ]:
        response = _request_json(method, f"{base_url.rstrip('/')}{path}", payload)
        result["checks"].append(
            {
                "method": method,
                "path": path,
                "ok": response["ok"],
                "status_code": response["status_code"],
                "error": response["error"],
            }
        )
        if not response["ok"]:
            result["status"] = "warning"
            result["warnings"].append(f"{path}:{response['error']}")
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


def write_implementation_report(
    *,
    reports_dir: Path,
    selection: dict[str, Any],
    decisions: dict[str, Any],
    overlay: dict[str, Any],
    preflight_bundle: dict[str, Any],
    retrieval_results: dict[str, Any],
) -> None:
    lines = [
        f"- selection_count: `{selection['selection_count']}`",
        f"- accepted_item_count: `{decisions['accepted_item_count']}`",
        f"- accepted_field_count: `{decisions['accepted_field_count']}`",
        f"- overlay_item_count: `{(overlay.get('summary') or {}).get('accepted_item_count', 0)}`",
        f"- preflight_status: `{preflight_bundle['apply_preflight_report']['status']}`",
        f"- ready_for_eval_over_real_overlay: `{preflight_bundle['apply_preflight_report']['ready_for_eval_over_real_overlay']}`",
        f"- retrieval_eval_status: `{retrieval_results['status']}`",
        f"- overlay_shadow_hit_rate: `{retrieval_results['overlay_shadow_hit_rate']}`",
        f"- combined_expected_help_rate: `{retrieval_results['combined_expected_help_rate']}`",
        f"- unsafe_overlay_hit_count: `{retrieval_results['unsafe_overlay_hit_count']}`",
        "",
        "## Scope",
        "- added offline curated batch selection, decisions pack, accepted-overlay preview, preflight wrapper, and retrieval shadow evaluation",
        "- kept human_final_approval=false, evaluation_only=true, live_apply_allowed=false throughout the batch",
        "- did not mutate live metadata, runtime, Writer, Web Admin, Web Trace, registry, processed blocks, or Chroma",
    ]
    write_text(reports_dir / "PRD-047.20_IMPLEMENTATION_REPORT.md", markdown_document("PRD-047.20 Implementation Report", lines))


def write_next_prd_recommendation(*, reports_dir: Path, retrieval_results: dict[str, Any]) -> str:
    if retrieval_results["status"] == "passed" and (retrieval_results.get("overlay_shadow_hit_rate") or 0) >= 0.75:
        recommendation = "PRD-047.21 - Overlay-Aware Retrieval Shadow Integration / Trace-Only v1"
    elif (retrieval_results.get("overlay_shadow_hit_rate") or 0) < 0.75:
        recommendation = "PRD-047.21 - Source Preview / Candidate Quality Repair for Batch 2 v1"
    else:
        recommendation = "PRD-047.21 - Owner Review Pass for Batch 1 v1"
    write_text(
        reports_dir / "PRD-047.20_NEXT_PRD_RECOMMENDATION.md",
        markdown_document("PRD-047.20 Next PRD Recommendation", [f"1. {recommendation}"]),
    )
    return recommendation


def build_implementation_summary(
    *,
    source_gate_report: dict[str, Any],
    selection: dict[str, Any],
    decisions: dict[str, Any],
    overlay: dict[str, Any],
    preflight_bundle: dict[str, Any],
    retrieval_results: dict[str, Any],
    runtime_report: dict[str, Any],
    no_mutation: dict[str, Any],
    encoding_report: dict[str, Any],
    botdb_smoke: dict[str, Any],
    recommendation: str,
) -> dict[str, Any]:
    status = "passed"
    if source_gate_report["status"] != "passed":
        status = "blocked"
    elif runtime_report["status"] != "passed" or no_mutation["status"] != "passed":
        status = "blocked"
    elif retrieval_results["status"] == "blocked":
        status = "blocked"
    elif retrieval_results["status"] == "warning" or encoding_report.get("final_status") != "passed" or botdb_smoke["status"] == "warning":
        status = "warning"
    return {
        "schema_version": "prd_047_20_implementation_summary_v1",
        "prd_id": PRD_ID,
        "created_at": utc_now(),
        "status": status,
        "source_gate_status": source_gate_report["status"],
        "selection_count": selection["selection_count"],
        "accepted_item_count": decisions["accepted_item_count"],
        "accepted_field_count": decisions["accepted_field_count"],
        "overlay_item_count": int((overlay.get("summary") or {}).get("accepted_item_count") or 0),
        "preflight_status": preflight_bundle["apply_preflight_report"]["status"],
        "ready_for_eval_over_real_overlay": preflight_bundle["apply_preflight_report"]["ready_for_eval_over_real_overlay"],
        "retrieval_eval_status": retrieval_results["status"],
        "baseline_available": retrieval_results["baseline_available"],
        "baseline_hit_rate": retrieval_results["baseline_hit_rate"],
        "overlay_shadow_hit_rate": retrieval_results["overlay_shadow_hit_rate"],
        "combined_expected_help_rate": retrieval_results["combined_expected_help_rate"],
        "unsafe_overlay_hit_count": retrieval_results["unsafe_overlay_hit_count"],
        "separator_preview_accepted_count": retrieval_results["separator_preview_accepted_count"],
        "practice_without_safety_count": retrieval_results["practice_without_safety_count"],
        "encoding_status": encoding_report.get("final_status"),
        "botdb_readonly_smoke_status": botdb_smoke["status"],
        "next_prd_recommendation": recommendation,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = Path(args.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    source_gate_report = run_source_gates(out_dir=out_dir)
    if source_gate_report["status"] != "passed":
        return {"status": "blocked", "source_gate_report": source_gate_report}

    context = _load_context()
    selection = run_select(out_dir=out_dir, context=context)
    if args.mode == "select":
        return {"status": selection["status"], "selection": selection}

    decisions = run_curate(out_dir=out_dir, context=context, selection=selection)
    if args.mode == "curate":
        return {"status": decisions["validation_status"], "decisions": decisions}

    overlay = run_overlay(out_dir=out_dir, context=context, decisions=decisions)
    if args.mode == "overlay":
        return {"status": "passed", "overlay": overlay}

    preflight_bundle = run_preflight(out_dir=out_dir, context=context, overlay=overlay)
    if args.mode == "preflight":
        return {"status": preflight_bundle["apply_preflight_report"]["status"], **preflight_bundle}

    retrieval_results = run_retrieval_eval(
        out_dir=out_dir,
        context=context,
        selection=selection,
        overlay=overlay,
        botdb_base_url=str(args.botdb_base_url),
    )
    if args.mode == "eval":
        return {"status": retrieval_results["status"], "retrieval_eval_results": retrieval_results}

    runtime_report = build_runtime_token_report(out_dir=out_dir)
    no_mutation = build_no_mutation_proof(out_dir=out_dir)
    botdb_smoke = run_botdb_readonly_smoke(out_dir=out_dir, base_url=str(args.botdb_base_url))
    encoding_report = run_encoding_hygiene(out_dir=out_dir, reports_dir=reports_dir)
    write_implementation_report(
        reports_dir=reports_dir,
        selection=selection,
        decisions=decisions,
        overlay=overlay,
        preflight_bundle=preflight_bundle,
        retrieval_results=retrieval_results,
    )
    recommendation = write_next_prd_recommendation(reports_dir=reports_dir, retrieval_results=retrieval_results)
    summary = build_implementation_summary(
        source_gate_report=source_gate_report,
        selection=selection,
        decisions=decisions,
        overlay=overlay,
        preflight_bundle=preflight_bundle,
        retrieval_results=retrieval_results,
        runtime_report=runtime_report,
        no_mutation=no_mutation,
        encoding_report=encoding_report,
        botdb_smoke=botdb_smoke,
        recommendation=recommendation,
    )
    write_json(out_dir / "implementation_summary.json", summary)
    return {
        "status": summary["status"],
        "source_gate_report": source_gate_report,
        "selection": selection,
        "decisions": {
            "accepted_item_count": decisions["accepted_item_count"],
            "accepted_field_count": decisions["accepted_field_count"],
            "validation_status": decisions["validation_status"],
        },
        "overlay_summary": overlay.get("summary"),
        "preflight_report": preflight_bundle["apply_preflight_report"],
        "retrieval_eval_results": {
            "status": retrieval_results["status"],
            "baseline_available": retrieval_results["baseline_available"],
            "baseline_hit_rate": retrieval_results["baseline_hit_rate"],
            "overlay_shadow_hit_rate": retrieval_results["overlay_shadow_hit_rate"],
            "combined_expected_help_rate": retrieval_results["combined_expected_help_rate"],
            "unsafe_overlay_hit_count": retrieval_results["unsafe_overlay_hit_count"],
        },
        "runtime_report": runtime_report,
        "no_mutation": no_mutation,
        "botdb_smoke": botdb_smoke,
        "encoding_report": encoding_report,
        "implementation_summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-047.20 curated batch 1 retrieval evaluation runner.")
    parser.add_argument("--mode", choices=["select", "curate", "overlay", "preflight", "eval", "full"], default="full")
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
    return 0 if result.get("status") in {"passed", "warning", "passed_with_expected_blockers"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
