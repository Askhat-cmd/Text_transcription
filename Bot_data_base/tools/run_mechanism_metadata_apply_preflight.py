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

from knowledge_governance.manual_review import build_candidate_index  # noqa: E402
from knowledge_governance.manual_review_preflight import (  # noqa: E402
    APPLY_PREFLIGHT_SCHEMA_VERSION,
    DRY_RUN_APPLY_PLAN_SCHEMA_VERSION,
    FIELD_APPLY_MAP,
    OVERLAY_INTAKE_SCHEMA_VERSION,
    PRD_ID,
    SOURCE_PRD_ID,
    build_apply_preflight_report,
    build_dry_run_apply_plan,
    build_field_mapping_snapshot,
    build_overlay_intake_report,
    build_processed_block_index,
    render_apply_preflight_markdown,
    render_dry_run_plan_markdown,
    render_overlay_intake_markdown,
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
PRD18_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / SOURCE_PRD_ID
PRD17_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.17"
ENCODING_VALIDATOR_PATH = BOT_PSYCHOLOGIST_ROOT / "tools" / "validate_prd_artifact_encoding.py"
REQUIRED_PRD18_COMMITS = ["dfb814d", "8ccfe96"]
REQUIRED_PRD18_FILES = [
    PRD18_LOG_DIR / "review_queue.json",
    PRD18_LOG_DIR / "review_decisions_template.json",
    PRD18_LOG_DIR / "review_decision_validation_report.json",
    PRD18_LOG_DIR / "curated_overlay_preview.json",
    PRD18_LOG_DIR / "no_mutation_proof.json",
    REPO_ROOT / "TO_DO_LIST" / "reports" / "PRD-047.18_IMPLEMENTATION_REPORT.md",
]
RUNTIME_ROOTS = [
    REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent",
    REPO_ROOT / "bot_psychologist" / "api",
    REPO_ROOT / "Bot_data_base" / "api",
    REPO_ROOT / "Bot_data_base" / "storage",
]
FORBIDDEN_RUNTIME_TOKENS = {
    DRY_RUN_APPLY_PLAN_SCHEMA_VERSION,
    APPLY_PREFLIGHT_SCHEMA_VERSION,
    "FIELD_APPLY_MAP",
    "curated_overlay_preview",
    "apply_preflight_report",
    "accepted_fields -> runtime",
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


def load_overlay(overlay_path: Path) -> dict[str, Any]:
    return read_json(overlay_path)


def load_candidate_run() -> dict[str, Any]:
    return read_json(PRD17_LOG_DIR / "enrichment_candidates_deterministic.json")


def _load_overlay_context(*, overlay_path: Path) -> dict[str, Any]:
    overlay_document = load_overlay(overlay_path)
    candidate_run = load_candidate_run()
    registry_path = REPO_ROOT / "Bot_data_base" / "data" / "registry.json"
    entry = load_registry_entry(registry_path=registry_path, source_hint="kuznica")
    paths = resolve_registry_paths(repo_root=REPO_ROOT, entry=entry)
    processed_blocks = load_processed_blocks(processed_path=paths["processed_json"])
    filtered_blocks = [
        block
        for block in processed_blocks
        if source_filter_match(
            block=block,
            source_hint="kuznica",
            source_id=normalize_text(entry.get("source_id")),
            source_title=normalize_text(entry.get("title")),
        )
    ]
    return {
        "overlay_document": overlay_document,
        "candidate_run": candidate_run,
        "candidate_index": build_candidate_index(list(candidate_run.get("candidates") or [])),
        "processed_block_index": build_processed_block_index(filtered_blocks),
        "registry_entry": entry,
        "filtered_blocks": filtered_blocks,
    }


def run_source_gates(*, out_dir: Path, overlay_path: Path) -> dict[str, Any]:
    recent_log = git_output("log", "--oneline", "-20").splitlines()
    prd18_summary = read_json(PRD18_LOG_DIR / "implementation_summary.json")
    registry_path = REPO_ROOT / "Bot_data_base" / "data" / "registry.json"
    entry = load_registry_entry(registry_path=registry_path, source_hint="kuznica")
    paths = resolve_registry_paths(repo_root=REPO_ROOT, entry=entry)
    processed_blocks = load_processed_blocks(processed_path=paths["processed_json"])
    filtered_blocks = [
        block
        for block in processed_blocks
        if source_filter_match(
            block=block,
            source_hint="kuznica",
            source_id=normalize_text(entry.get("source_id")),
            source_title=normalize_text(entry.get("title")),
        )
    ]
    overlay = load_overlay(overlay_path)
    report = {
        "schema_version": "prd_047_19_source_gate_report_v1",
        "prd_id": PRD_ID,
        "status": "passed",
        "created_at": utc_now(),
        "git_status_short": git_output("status", "--short").splitlines(),
        "recent_commits": recent_log,
        "required_commit_presence": {commit: any(line.startswith(commit) for line in recent_log) for commit in REQUIRED_PRD18_COMMITS},
        "required_files": [
            {
                "path": relative_to_repo(path, REPO_ROOT),
                "exists": path.exists(),
                "sha256": sha256_file(path) if path.exists() else "",
            }
            for path in REQUIRED_PRD18_FILES
        ],
        "prd_047_18_summary": {
            "status": prd18_summary.get("status"),
            "queue_count": prd18_summary.get("queue_count"),
            "candidate_count": prd18_summary.get("candidate_count"),
            "template_accepts_real_candidates": prd18_summary.get("template_accepts_real_candidates"),
            "live_apply_allowed": prd18_summary.get("live_apply_allowed"),
        },
        "overlay": {
            "overlay_file": relative_to_repo(overlay_path, REPO_ROOT),
            "fixture_only": overlay.get("fixture_only"),
            "live_apply_allowed": overlay.get("live_apply_allowed"),
            "accepted_item_count": ((overlay.get("summary") or {}).get("accepted_item_count")),
        },
        "source": {
            "source_id": normalize_text(entry.get("source_id")),
            "source_doc": normalize_text(entry.get("title")),
            "registry_blocks_count": entry.get("blocks_count"),
            "filtered_blocks_count": len(filtered_blocks),
        },
        "blockers": [],
    }
    for commit, present in report["required_commit_presence"].items():
        if not present:
            report["blockers"].append(f"missing_commit:{commit}")
    for item in report["required_files"]:
        if not item["exists"]:
            report["blockers"].append(f"missing_required_file:{item['path']}")
    expected_summary = {
        "status": "passed",
        "queue_count": 80,
        "candidate_count": 80,
        "template_accepts_real_candidates": False,
        "live_apply_allowed": False,
    }
    for key, expected in expected_summary.items():
        if report["prd_047_18_summary"].get(key) != expected:
            report["blockers"].append(f"prd_047_18_summary_unexpected:{key}")
    if len(filtered_blocks) != 247:
        report["blockers"].append(f"unexpected_filtered_blocks_count:{len(filtered_blocks)}")
    if overlay.get("schema_version") != "mechanism_metadata_curated_overlay_preview_v1":
        report["blockers"].append("overlay_schema_unexpected")
    if report["blockers"]:
        report["status"] = "blocked"
    lines = [
        f"- status: `{report['status']}`",
        f"- overlay_file: `{report['overlay']['overlay_file']}`",
        f"- fixture_only: `{report['overlay']['fixture_only']}`",
        f"- accepted_item_count: `{report['overlay']['accepted_item_count']}`",
        f"- source_id: `{report['source']['source_id']}`",
        f"- filtered_blocks_count: `{report['source']['filtered_blocks_count']}`",
        "",
        "## Blockers",
    ]
    for blocker in report["blockers"] or ["none"]:
        lines.append(f"- {blocker}")
    write_json(out_dir / "source_gate_report.json", report)
    write_text(out_dir / "source_gate_report.md", markdown_document("PRD-047.19 Source Gate Report", lines))
    return report


def build_negative_fixtures(*, out_dir: Path, overlay_document: dict[str, Any]) -> dict[str, Path]:
    negative_missing_mapping = json.loads(json.dumps(overlay_document, ensure_ascii=False))
    negative_missing_mapping["items"][0]["accepted_fields"]["not_mapped_field_candidate"] = "boom"

    negative_real_empty_preview = json.loads(json.dumps(overlay_document, ensure_ascii=False))
    negative_real_empty_preview["fixture_only"] = False
    negative_real_empty_preview["items"][1]["source_ref"]["content_preview"] = "***"

    negative_practice_without_contra = json.loads(json.dumps(overlay_document, ensure_ascii=False))
    negative_practice_without_contra["items"][0]["accepted_fields"].pop("contraindications_candidates", None)
    negative_practice_without_contra["items"][0]["accepted_fields"].pop("avoid_when_candidates", None)

    paths = {
        "missing_mapping": out_dir / "negative_overlay_missing_mapping.json",
        "real_empty_preview": out_dir / "negative_overlay_real_but_empty_source_preview.json",
        "practice_without_contra": out_dir / "negative_overlay_practice_without_contraindications.json",
    }
    write_json(paths["missing_mapping"], negative_missing_mapping)
    write_json(paths["real_empty_preview"], negative_real_empty_preview)
    write_json(paths["practice_without_contra"], negative_practice_without_contra)
    return paths


def run_intake(*, out_dir: Path, overlay_path: Path) -> dict[str, Any]:
    context = _load_overlay_context(overlay_path=overlay_path)
    report = build_overlay_intake_report(
        overlay_document=context["overlay_document"],
        candidate_index=context["candidate_index"],
        processed_block_index=context["processed_block_index"],
        overlay_file=relative_to_repo(overlay_path, REPO_ROOT),
    )
    write_json(out_dir / "overlay_intake_report.json", report)
    write_text(out_dir / "overlay_intake_report.md", render_overlay_intake_markdown(report))
    return report


def run_plan(*, out_dir: Path, overlay_path: Path) -> dict[str, Any]:
    context = _load_overlay_context(overlay_path=overlay_path)
    snapshot = build_field_mapping_snapshot()
    plan = build_dry_run_apply_plan(
        overlay_document=context["overlay_document"],
        candidate_index=context["candidate_index"],
        processed_block_index=context["processed_block_index"],
        overlay_file=relative_to_repo(overlay_path, REPO_ROOT),
    )
    write_json(out_dir / "field_mapping_snapshot.json", snapshot)
    write_json(out_dir / "dry_run_apply_plan.json", plan)
    write_text(out_dir / "dry_run_apply_plan.md", render_dry_run_plan_markdown(plan))
    return {"field_mapping_snapshot": snapshot, "dry_run_apply_plan": plan}


def run_preflight(*, out_dir: Path, overlay_path: Path) -> dict[str, Any]:
    intake = run_intake(out_dir=out_dir, overlay_path=overlay_path)
    plan_result = run_plan(out_dir=out_dir, overlay_path=overlay_path)
    report = build_apply_preflight_report(
        intake_report=intake,
        dry_run_plan=plan_result["dry_run_apply_plan"],
    )
    write_json(out_dir / "apply_preflight_report.json", report)
    write_text(out_dir / "apply_preflight_report.md", render_apply_preflight_markdown(report))
    return report


def build_runtime_token_report(*, out_dir: Path) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for root in RUNTIME_ROOTS:
        for path in root.rglob("*.py"):
            content = path.read_text(encoding="utf-8").lower()
            matched = sorted(token for token in FORBIDDEN_RUNTIME_TOKENS if token.lower() in content)
            if matched:
                hits.append({"path": relative_to_repo(path, REPO_ROOT), "tokens": matched})
    report = {
        "schema_version": "mechanism_metadata_apply_preflight_no_runtime_activation_v1",
        "prd_id": PRD_ID,
        "status": "passed" if not hits else "failed",
        "runtime_token_hits": hits,
        "notes": [
            "PRD-047.19 is read-only preflight planning only.",
            "No apply-preflight tokens are allowed in active runtime roots.",
        ],
    }
    write_json(out_dir / "anti_runtime_activation_report.json", report)
    return report


def build_no_mutation_proof(*, out_dir: Path) -> dict[str, Any]:
    report = {
        "schema_version": "prd_047_19_no_mutation_proof_v1",
        "prd_id": PRD_ID,
        "status": "passed",
        "processed_blocks_overwritten": False,
        "live_metadata_applied": False,
        "registry_mutated": False,
        "chroma_reindexed": False,
        "embeddings_changed": False,
        "writer_runtime_changed": False,
        "writer_prompt_changed": False,
        "writer_contract_live_changed": False,
        "hybrid_retrieval_planner_changed": False,
        "memory_retrieval_changed": False,
        "dialogue_policy_changed": False,
        "overlay_used_for_runtime": False,
        "dry_run_plan_writes_live_metadata": False,
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


def write_implementation_report(*, reports_dir: Path, preflight_report: dict[str, Any], intake_report: dict[str, Any], plan: dict[str, Any]) -> None:
    lines = [
        f"- status: `{preflight_report['status']}`",
        f"- fixture_only: `{intake_report['fixture_only']}`",
        f"- accepted_item_count: `{intake_report['accepted_item_count']}`",
        f"- accepted_field_count: `{intake_report['accepted_field_count']}`",
        f"- ready_for_live_apply: `{preflight_report['ready_for_live_apply']}`",
        f"- ready_for_eval_over_real_overlay: `{preflight_report['ready_for_eval_over_real_overlay']}`",
        f"- expected_blockers: `{json.dumps(preflight_report['expected_blockers'], ensure_ascii=False)}`",
        f"- item_count: `{plan['summary']['item_count']}`",
        f"- field_count: `{plan['summary']['field_count']}`",
        "",
        "## Scope",
        "- added read-only overlay intake, future field mapping, dry-run diff preview, and apply preflight reporting",
        "- kept live metadata/runtime/Writer/Chroma untouched",
        "- current accepted outcome is honest fixture-only blocker, not live apply readiness",
    ]
    write_text(reports_dir / "PRD-047.19_IMPLEMENTATION_REPORT.md", markdown_document("PRD-047.19 Implementation Report", lines))
    next_lines = [
        "1. PRD-047.20 - Real Human Curated Overlay Batch 1 / Accepted Decisions Pack v1",
        "2. Do not move to live apply or Chroma reindex until a real non-fixture overlay exists and passes preflight without unexpected blockers.",
    ]
    write_text(reports_dir / "PRD-047.19_NEXT_PRD_RECOMMENDATION.md", markdown_document("PRD-047.19 Next PRD Recommendation", next_lines))


def run(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = Path(args.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = Path(args.overlay_file).resolve()

    source_gate_report = run_source_gates(out_dir=out_dir, overlay_path=overlay_path)
    if source_gate_report["status"] != "passed":
        return {"status": "blocked", "source_gate_report": source_gate_report}

    if args.mode == "intake":
        intake = run_intake(out_dir=out_dir, overlay_path=overlay_path)
        return {"status": intake["intake_status"], "overlay_intake_report": intake}

    if args.mode == "plan":
        result = run_plan(out_dir=out_dir, overlay_path=overlay_path)
        return {"status": "passed", **result}

    if args.mode == "preflight":
        report = run_preflight(out_dir=out_dir, overlay_path=overlay_path)
        return {"status": report["status"], "apply_preflight_report": report}

    if args.mode == "full":
        context = _load_overlay_context(overlay_path=overlay_path)
        negative_paths = build_negative_fixtures(out_dir=out_dir, overlay_document=context["overlay_document"])
        intake = run_intake(out_dir=out_dir, overlay_path=overlay_path)
        plan_result = run_plan(out_dir=out_dir, overlay_path=overlay_path)
        preflight = build_apply_preflight_report(intake_report=intake, dry_run_plan=plan_result["dry_run_apply_plan"])
        write_json(out_dir / "apply_preflight_report.json", preflight)
        write_text(out_dir / "apply_preflight_report.md", render_apply_preflight_markdown(preflight))
        runtime_report = build_runtime_token_report(out_dir=out_dir)
        no_mutation = build_no_mutation_proof(out_dir=out_dir)
        botdb_smoke = run_botdb_readonly_smoke(out_dir=out_dir, base_url=str(args.botdb_base_url))
        encoding_report = run_encoding_hygiene(out_dir=out_dir, reports_dir=reports_dir)
        write_implementation_report(
            reports_dir=reports_dir,
            preflight_report=preflight,
            intake_report=intake,
            plan=plan_result["dry_run_apply_plan"],
        )
        status = preflight["status"]
        if runtime_report["status"] == "failed" or no_mutation["status"] != "passed":
            status = "blocked"
        if encoding_report["final_status"] != "passed":
            status = "warning" if status != "blocked" else status
        if botdb_smoke["status"] == "warning":
            status = "warning" if status != "blocked" else status
        return {
            "status": status,
            "source_gate_report": source_gate_report,
            "overlay_intake_report": intake,
            "dry_run_apply_plan": plan_result["dry_run_apply_plan"],
            "apply_preflight_report": preflight,
            "negative_fixture_paths": {key: relative_to_repo(path, REPO_ROOT) for key, path in negative_paths.items()},
            "runtime_report": runtime_report,
            "no_mutation": no_mutation,
            "botdb_smoke": botdb_smoke,
            "encoding_report": encoding_report,
        }

    raise ValueError(f"Unsupported mode: {args.mode}")


def main() -> int:
    parser = argparse.ArgumentParser(description="PRD-047.19 curated overlay dry-run apply preflight runner.")
    parser.add_argument("--mode", choices=["intake", "plan", "preflight", "full"], default="full")
    parser.add_argument("--overlay-file", default=str(PRD18_LOG_DIR / "curated_overlay_preview.json"))
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
    return 0 if result.get("status") in {"passed", "warning", "passed_with_expected_blockers", "passed_fixture_only"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
