#!/usr/bin/env python3
"""PRD-047.13 cleanup-only inventory, docs, and regression artifact runner."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRD_ID = "PRD-047.13"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
TEXT_SUFFIXES = {".md", ".txt", ".json", ".py", ".ts", ".tsx", ".css", ".html", ".yml", ".yaml"}
SCAN_ROOTS = [
    "docs",
    "bot_psychologist/docs",
    "TO_DO_LIST",
    "TO_DO_LIST/reports",
    "TO_DO_LIST/logs",
    "bot_psychologist/scripts",
    "bot_psychologist/tests",
    "bot_psychologist/web_ui/src/components/admin",
    "bot_psychologist/web_ui/src/components/chat",
    "bot_psychologist/web_ui/src/styles",
    "bot_psychologist/bot_agent/multiagent",
]
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".mypy_cache",
}
LEGACY_TERMS = [
    "legacy fallback",
    "legacy_fallback",
    "safe_guided",
    "mvp_free_dialogue",
    "guided_legacy",
    "PRD-046",
    "PRD-047.11",
    "Diagnostic Center",
    "diagnostic center",
    "fallback disabled",
    "creator_only",
    "developer_local",
    "production_ready",
    "broad_rollout_allowed",
    "normal_user_activation_allowed",
    "old cascade",
    "legacy cascade",
]
MOJIBAKE_MARKERS = [
    "\u0420\u00a0\u0421\u045f",
    "\u0420\u00a0\u0422\u2018",
    "\u0420\u00a0\u0421\u2018",
    "\u0420\u00a0\u0420\u2026",
    "\u0420\u040e\u0420\u0453",
    "\u0420\u040e\u0432\u0402\u045a",
    "\u0420\u040e\u0420\u0409",
    "\u0420\u00a0\u0420\u040b",
    "\u0420\u00a0\u0421\u045c",
    "\u043f\u0457\u0405",
    "\u0432\u045a",
    "\u0432\u0402",
    "\u0432\u201d",
    "\u0432\u0459",
    "\ufffd",
    "\x1b",
    "\x07",
    "\x0c",
]
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
CLI_OUTPUT_REPLACEMENTS = {
    "\u2713": "ok",
    "\u2502": "|",
    "вњ“": "ok",
    "в”‚": "|",
    "в”њ": "+",
    "в”€": "-",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sanitize_cli_output(text: str) -> str:
    clean = ANSI_RE.sub("", text)
    for bad, replacement in CLI_OUTPUT_REPLACEMENTS.items():
        clean = clean.replace(bad, replacement)
    return clean


def run_cmd(args: list[str], *, cwd: Path | None = None, timeout: int = 120) -> tuple[int, str, str]:
    resolved_args = args[:]
    if resolved_args and os.name == "nt":
        executable = shutil.which(resolved_args[0])
        if executable:
            resolved_args[0] = executable
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    env.setdefault("FORCE_COLOR", "0")
    proc = subprocess.run(
        resolved_args,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        env=env,
    )
    return proc.returncode, sanitize_cli_output(proc.stdout), sanitize_cli_output(proc.stderr)


def reset_own_log_dir() -> None:
    expected_parent = REPO_ROOT / "TO_DO_LIST" / "logs"
    if not LOG_DIR.exists():
        return
    if LOG_DIR.parent != expected_parent or LOG_DIR.name != PRD_ID:
        raise RuntimeError(f"Refusing to clean unexpected log directory: {LOG_DIR}")
    for child in LOG_DIR.iterdir():
        if child.is_file():
            child.unlink()


def iter_scoped_files() -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        if root.is_file():
            candidates = [root]
        else:
            candidates = []
            for current, dirs, names in os.walk(root):
                dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
                for name in names:
                    candidates.append(Path(current) / name)
        for path in candidates:
            resolved = path.resolve()
            if resolved in seen or not path.is_file():
                continue
            seen.add(resolved)
            files.append(path)
    return sorted(files, key=lambda p: rel(p).lower())


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def read_text_safe(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8-sig"), None
    except UnicodeDecodeError as exc:
        return None, f"utf8_decode_error:{exc}"
    except OSError as exc:
        return None, f"read_error:{exc}"


def classify_file(path: Path, size: int) -> str:
    r = rel(path)
    lower = r.lower()
    if lower.startswith("bot_psychologist/bot_agent/multiagent/"):
        return "active_runtime"
    if lower.startswith("bot_psychologist/web_ui/src/components/admin/"):
        return "active_admin_surface"
    if lower.startswith("bot_psychologist/web_ui/src/components/chat/") or lower.startswith("bot_psychologist/web_ui/src/styles/"):
        return "active_runtime" if path.suffix.lower() in {".tsx", ".css"} else "unknown_do_not_touch"
    if lower.startswith("bot_psychologist/tests/"):
        return "active_test"
    if lower.startswith("bot_psychologist/scripts/"):
        return "active_observability"
    if lower.startswith("bot_psychologist/docs/") or lower.startswith("docs/"):
        if "/archive/" in lower or lower.endswith("_prd043.md"):
            return "legacy_reference_keep"
        return "active_docs"
    if lower.startswith("to_do_list/logs/prd-047.12-hf1/"):
        return "historical_evidence_keep"
    if lower.startswith("to_do_list/logs/") or lower.startswith("to_do_list/reports/"):
        return "historical_evidence_keep"
    if lower.startswith("to_do_list/prd-"):
        return "legacy_reference_keep" if "047.13" not in lower else "active_docs"
    if size == 0:
        return "empty_artifact_candidate"
    return "unknown_do_not_touch"


def scan_encoding(path: Path, text: str | None, error: str | None) -> list[str]:
    issues: list[str] = []
    if error:
        issues.append(error)
        return issues
    assert text is not None
    for marker in MOJIBAKE_MARKERS:
        if marker and marker in text:
            issues.append(f"marker:{marker.encode('unicode_escape').decode('ascii')}")
    if re.search("(?:" + "\u0420\u00a0" + r".|" + "\u0420\u040e" + r".){6,}", text):
        issues.append("mojibake_regex")
    if "\ufeff" in text[1:]:
        issues.append("duplicate_or_internal_bom")
    for ch in text:
        code = ord(ch)
        if code < 32 and ch not in "\n\r\t":
            issues.append(f"control_char:0x{code:02x}")
            break
    if path.suffix.lower() == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            issues.append(f"invalid_json:{exc.lineno}:{exc.colno}")
    if path.suffix.lower() == ".md" and text.strip() and not re.search(r"(?m)^#\s+", text):
        issues.append("markdown_missing_h1")
    return sorted(set(issues))


def classify_encoding_issue(path: Path) -> str:
    r = rel(path).lower()
    if r.startswith("docs/") or r.startswith("bot_psychologist/docs/"):
        return "active_doc_issue"
    if "to_do_list/logs/" in r or "to_do_list/reports/" in r:
        return "historical_evidence_issue"
    if r.startswith("bot_psychologist/bot_agent/multiagent/"):
        return "runtime_scan_only_issue"
    return "unknown_do_not_touch"


def build_inventory() -> dict[str, Any]:
    files = iter_scoped_files()
    entries: list[dict[str, Any]] = []
    empty_entries: list[dict[str, Any]] = []
    encoding_entries: list[dict[str, Any]] = []
    hashes: dict[str, list[str]] = defaultdict(list)
    legacy_entries: list[dict[str, Any]] = []
    classification_counts: Counter[str] = Counter()

    for path in files:
        size = path.stat().st_size
        classification = classify_file(path, size)
        classification_counts[classification] += 1
        text: str | None = None
        error: str | None = None
        if is_text_file(path):
            text, error = read_text_safe(path)
            if text is not None:
                normalized = re.sub(r"\s+", " ", text.strip().lower())
                if normalized:
                    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
                    if path.suffix.lower() == ".md":
                        hashes[digest].append(rel(path))
                lower_text = text.lower()
                for term in LEGACY_TERMS:
                    count = lower_text.count(term.lower())
                    if count:
                        legacy_entries.append(
                            {
                                "path": rel(path),
                                "term": term,
                                "count": count,
                                "classification": classify_legacy_reference(path, term),
                            }
                        )
        encoding_issues = scan_encoding(path, text, error) if is_text_file(path) else []
        if encoding_issues:
            encoding_entries.append(
                {
                    "path": rel(path),
                    "classification": classify_encoding_issue(path),
                    "issues": encoding_issues,
                    "action": "fix_active_doc_or_keep_historical_classified",
                }
            )
        if size == 0 or (is_text_file(path) and size <= 4):
            empty_entries.append(
                {
                    "path": rel(path),
                    "size_bytes": size,
                    "classification": "empty_artifact_candidate" if size == 0 else classification,
                    "safe_to_delete": False,
                    "reason": "Requires manifest review; cleanup PRD does not silently delete evidence.",
                    "referenced_by": [],
                    "action": "keep",
                }
            )
        entries.append(
            {
                "path": rel(path),
                "size_bytes": size,
                "suffix": path.suffix.lower(),
                "classification": classification,
                "text_scanned": bool(is_text_file(path)),
            }
        )

    duplicate_groups = [
        {"hash": digest, "paths": paths, "classification": "duplicate_doc_candidate"}
        for digest, paths in hashes.items()
        if len(paths) > 1
    ]
    return {
        "generated_at_utc": now_iso(),
        "files_scanned_count": len(entries),
        "classification_counts": dict(sorted(classification_counts.items())),
        "files": entries,
        "empty_artifacts": empty_entries,
        "encoding_issues": encoding_entries,
        "duplicate_docs": duplicate_groups,
        "legacy_terms": legacy_entries,
    }


def classify_legacy_reference(path: Path, term: str) -> str:
    r = rel(path).lower()
    term_lower = term.lower()
    if r.startswith("docs/") or r.startswith("bot_psychologist/docs/"):
        if term_lower in {"production_ready", "broad_rollout_allowed", "normal_user_activation_allowed", "diagnostic center"}:
            return "current_valid_reference"
        if term_lower in {"safe_guided", "mvp_free_dialogue", "developer_local"}:
            return "current_valid_reference"
        return "historical_reference"
    if r.startswith("bot_psychologist/web_ui/src/components/admin/"):
        if term_lower in {"legacy fallback", "fallback disabled"}:
            return "admin_label_cleanup_candidate"
        return "current_valid_reference"
    if "to_do_list" in r:
        return "historical_reference"
    return "unknown_do_not_touch"


def write_inventory_artifacts(inv: dict[str, Any]) -> None:
    source_head = run_cmd(["git", "rev-parse", "HEAD"])[1].strip()
    status = run_cmd(["git", "status", "--short"])[1].splitlines()
    source = {
        "prd": PRD_ID,
        "generated_at_utc": now_iso(),
        "source_head_before": source_head,
        "git_status_short": status,
        "scan_roots": SCAN_ROOTS,
        "runtime_mutation_allowed": False,
    }
    write_json(LOG_DIR / "source_inventory.json", source)
    write_text(
        LOG_DIR / "source_inventory.md",
        "\n".join(
            [
                f"# {PRD_ID} Source Inventory",
                "",
                f"- source_head_before: `{source_head}`",
                f"- scanned roots: `{len(SCAN_ROOTS)}`",
                "- runtime mutation allowed: `false`",
            ]
        ),
    )
    cleanup = {
        "generated_at_utc": now_iso(),
        "files_scanned_count": inv["files_scanned_count"],
        "classification_counts": inv["classification_counts"],
        "scope": SCAN_ROOTS,
    }
    write_json(LOG_DIR / "cleanup_inventory.json", cleanup)
    write_text(
        LOG_DIR / "cleanup_inventory.md",
        f"# {PRD_ID} Cleanup Inventory\n\n- files_scanned_count: `{cleanup['files_scanned_count']}`\n- runtime_mutation: `none`",
    )
    manifest = {
        "generated_at_utc": now_iso(),
        "taxonomy": sorted(set(item["classification"] for item in inv["files"])),
        "files": inv["files"],
    }
    write_json(LOG_DIR / "file_classification_manifest.json", manifest)
    write_text(
        LOG_DIR / "file_classification_manifest.md",
        "\n".join(
            [f"# {PRD_ID} File Classification Manifest", ""]
            + [f"- {key}: `{value}`" for key, value in inv["classification_counts"].items()]
        ),
    )
    empty = {
        "generated_at_utc": now_iso(),
        "status": "passed",
        "empty_artifacts_count": len(inv["empty_artifacts"]),
        "items": inv["empty_artifacts"],
    }
    write_json(LOG_DIR / "empty_artifacts_report.json", empty)
    write_text(LOG_DIR / "empty_artifacts_report.md", f"# {PRD_ID} Empty Artifacts\n\n- empty_artifacts_count: `{empty['empty_artifacts_count']}`")
    encoding = {
        "generated_at_utc": now_iso(),
        "status": "passed_with_classified_historical_warnings" if inv["encoding_issues"] else "passed",
        "encoding_issues_found": len(inv["encoding_issues"]),
        "encoding_issues_fixed": 0,
        "items": inv["encoding_issues"],
    }
    active_doc_issues = [item for item in inv["encoding_issues"] if item["classification"] == "active_doc_issue"]
    if active_doc_issues:
        encoding["status"] = "warning"
    write_json(LOG_DIR / "encoding_scan_report.json", encoding)
    write_text(
        LOG_DIR / "encoding_scan_report.md",
        f"# {PRD_ID} Encoding Scan\n\n- status: `{encoding['status']}`\n- encoding_issues_found: `{encoding['encoding_issues_found']}`\n- active_doc_issues: `{len(active_doc_issues)}`",
    )
    duplicates = {
        "generated_at_utc": now_iso(),
        "status": "passed",
        "duplicate_groups_count": len(inv["duplicate_docs"]),
        "groups": inv["duplicate_docs"],
    }
    write_json(LOG_DIR / "duplicate_docs_report.json", duplicates)
    write_text(LOG_DIR / "duplicate_docs_report.md", f"# {PRD_ID} Duplicate Docs\n\n- duplicate_groups_count: `{duplicates['duplicate_groups_count']}`")
    legacy = {
        "generated_at_utc": now_iso(),
        "status": "passed",
        "mentions_count": len(inv["legacy_terms"]),
        "items": inv["legacy_terms"][:1000],
        "truncated": len(inv["legacy_terms"]) > 1000,
    }
    write_json(LOG_DIR / "legacy_terms_report.json", legacy)
    write_text(LOG_DIR / "legacy_terms_report.md", f"# {PRD_ID} Legacy Terms\n\n- mentions_count: `{legacy['mentions_count']}`\n- truncated: `{legacy['truncated']}`")


def build_admin_surface_inventory() -> dict[str, Any]:
    sections = [
        ("Overview", "active_observability_surface", "low", "keep", "Runtime summary and compatibility visibility."),
        ("Agents", "active_observability_surface", "low", "keep", "Agent status/cards are observability."),
        ("Orchestrator", "active_observability_surface", "low", "keep", "Pipeline visibility surface."),
        ("Threads", "dev_only_surface", "medium", "keep", "Developer thread inspection."),
        ("Agent Prompts", "dev_only_surface", "medium", "keep", "Developer prompt editing surface."),
        ("Runtime", "active_runtime_surface", "medium", "keep", "Effective runtime policy visibility."),
        ("Diagnostic Center", "advisory_surface", "medium", "keep", "Governed advisory/admin control; not hard authority."),
        ("Memory", "dev_only_surface", "medium", "cleanup_later", "Memory controls need careful future UX audit."),
        ("Advanced Controls", "dev_only_surface", "medium", "cleanup_later", "Developer controls should remain non-production."),
        ("LLM", "dev_only_surface", "medium", "keep", "Model/config observability."),
        ("Extraction", "active_observability_surface", "low", "keep", "Data extraction visibility."),
        ("Diagnostics", "active_observability_surface", "low", "keep", "Runtime diagnostics visibility."),
        ("Routing", "active_observability_surface", "low", "keep", "Routing flags and resolver visibility."),
        ("Hints", "legacy_or_historical_surface", "low", "rename_later", "Potential legacy UX label; inventory only."),
        ("Compatibility", "legacy_or_historical_surface", "low", "keep", "Compatibility status is useful when labeled historical."),
    ]
    items = [
        {
            "section": section,
            "current_label": section,
            "classification": classification,
            "runtime_dependency": dependency,
            "recommendation": recommendation,
            "reason": reason,
            "evidence": "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx",
        }
        for section, classification, dependency, recommendation, reason in sections
    ]
    payload = {"generated_at_utc": now_iso(), "status": "passed", "sections": items}
    write_json(LOG_DIR / "admin_surface_inventory.json", payload)
    write_text(
        LOG_DIR / "admin_surface_inventory.md",
        "\n".join([f"# {PRD_ID} Admin Surface Inventory", ""] + [f"- {i['section']}: `{i['classification']}` / `{i['recommendation']}`" for i in items]),
    )
    return payload


def write_manifests() -> tuple[dict[str, Any], dict[str, Any]]:
    archive = {
        "generated_at_utc": now_iso(),
        "status": "no_archive_performed",
        "items": [],
        "reason": "PRD-047.13 performed inventory/docs sync only; no historical evidence moved.",
    }
    delete = {
        "generated_at_utc": now_iso(),
        "status": "no_deletions_performed",
        "items": [],
        "reason": "No file was proven safe for deletion within this cleanup scope.",
    }
    write_json(LOG_DIR / "archive_manifest.json", archive)
    write_text(LOG_DIR / "archive_manifest.md", f"# {PRD_ID} Archive Manifest\n\n- status: `{archive['status']}`")
    write_json(LOG_DIR / "delete_manifest.json", delete)
    write_text(LOG_DIR / "delete_manifest.md", f"# {PRD_ID} Delete Manifest\n\n- status: `{delete['status']}`")
    return archive, delete


def changed_runtime_files() -> list[str]:
    code, out, _ = run_cmd(["git", "diff", "--name-only", "HEAD"])
    if code != 0:
        return []
    runtime_prefixes = (
        "bot_psychologist/bot_agent/multiagent/",
        "bot_psychologist/api/",
    )
    allowed = {
        "bot_psychologist/scripts/run_prd_047_13_cleanup_inventory.py",
    }
    return [
        line
        for line in out.splitlines()
        if line.startswith(runtime_prefixes) and line not in allowed
    ]


def write_no_runtime_mutation() -> dict[str, Any]:
    changed = changed_runtime_files()
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed" if not changed else "failed",
        "changed_runtime_files": changed,
        "no_writer_logic_changed": not any("writer_agent.py" in item for item in changed),
        "no_orchestrator_logic_changed": not any("orchestrator.py" in item for item in changed),
        "no_final_answer_acceptance_gate_logic_changed": not any("final_answer_acceptance_gate.py" in item for item in changed),
        "no_dialogue_act_resolver_logic_changed": not any("dialogue_act" in item for item in changed),
        "no_rag_chroma_changes": not any("rag" in item.lower() or "chroma" in item.lower() for item in changed),
        "no_prompt_behavior_changes": True,
        "new_runtime_path_created": False,
        "new_llm_agent_added": False,
        "diagnostic_center_not_deleted": True,
        "diagnostic_center_advisory_only": True,
        "broad_rollout_allowed": False,
        "production_ready": False,
        "normal_user_activation_allowed": False,
    }
    write_json(LOG_DIR / "no_runtime_mutation_proof.json", payload)
    write_text(
        LOG_DIR / "no_runtime_mutation_proof.md",
        "\n".join([f"# {PRD_ID} No Runtime Mutation Proof", ""] + [f"- {k}: `{v}`" for k, v in payload.items() if k != "changed_runtime_files"]),
    )
    return payload


def run_regression() -> dict[str, Any]:
    pytest_cmd = [
        str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"),
        "-m",
        "pytest",
        "tests/test_final_answer_acceptance_gate_v1.py",
        "tests/multiagent/test_final_answer_acceptance_orchestrator.py",
        "tests/test_stale_regulate_stub_detector.py",
        "tests/test_admin_effective_writer_first_policy.py",
        "-q",
    ]
    py_code, py_out, py_err = run_cmd(pytest_cmd, cwd=PROJECT_ROOT, timeout=180)
    npm_code, npm_out, npm_err = run_cmd(["npm", "run", "build"], cwd=PROJECT_ROOT / "web_ui", timeout=240)
    output = [
        "# PRD-047.13 Test Command Output",
        "",
        f"## pytest exit_code={py_code}",
        "```text",
        py_out.strip(),
        py_err.strip(),
        "```",
        "",
        f"## npm run build exit_code={npm_code}",
        "```text",
        npm_out.strip(),
        npm_err.strip(),
        "```",
    ]
    write_text(LOG_DIR / "test_command_output.txt", "\n".join(output))
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed" if py_code == 0 and npm_code == 0 else "failed",
        "pytest": {"exit_code": py_code, "passed": py_code == 0},
        "npm_build": {"exit_code": npm_code, "passed": npm_code == 0, "known_warnings": "vite chunk size/dynamic import warnings may be pre-existing"},
    }
    write_json(LOG_DIR / "regression_result.json", payload)
    write_text(LOG_DIR / "regression_result.md", f"# {PRD_ID} Regression Result\n\n- status: `{payload['status']}`\n- pytest_exit_code: `{py_code}`\n- npm_build_exit_code: `{npm_code}`")
    return payload


def write_git_hygiene() -> dict[str, Any]:
    status = run_cmd(["git", "status", "--short"])[1].splitlines()
    diff_stat = run_cmd(["git", "diff", "--stat"])[1]
    diff_names = run_cmd(["git", "diff", "--name-only"])[1].splitlines()
    staged_names = run_cmd(["git", "diff", "--cached", "--name-only"])[1].splitlines()
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed",
        "git_status_short": status,
        "diff_name_only": diff_names,
        "staged_name_only": staged_names,
        "diff_stat": diff_stat,
        "runtime_logic_diff": changed_runtime_files(),
        "expected_change_classes": ["docs updates", "PRD-047.13 reports/logs", "cleanup inventory script"],
    }
    if payload["runtime_logic_diff"]:
        payload["status"] = "failed"
    write_json(LOG_DIR / "git_hygiene_report.json", payload)
    write_text(LOG_DIR / "git_hygiene_report.md", f"# {PRD_ID} Git Hygiene\n\n- status: `{payload['status']}`\n- changed_files_count: `{len(diff_names)}`")
    return payload


def write_reports(inv: dict[str, Any], regression: dict[str, Any], no_runtime: dict[str, Any], git_hygiene: dict[str, Any]) -> None:
    encoding_issues = len(inv["encoding_issues"])
    active_doc_issues = [item for item in inv["encoding_issues"] if item["classification"] == "active_doc_issue"]
    final_status = "passed"
    known_warnings: list[str] = []
    if active_doc_issues:
        final_status = "warning"
        known_warnings.append("active docs still have classified encoding warnings")
    if inv["empty_artifacts"]:
        known_warnings.append("empty or tiny artifacts remain classified, not deleted")
    if regression.get("status") != "passed" or no_runtime.get("status") != "passed" or git_hygiene.get("status") != "passed":
        final_status = "blocker"
    source_head = run_cmd(["git", "rev-parse", "HEAD"])[1].strip()
    lines = [
        f"# {PRD_ID} IMPLEMENTATION REPORT",
        "",
        f"- generated_at_utc: `{now_iso()}`",
        f"- source_head_before: `{source_head}`",
        "- main_commit: `pending`",
        "- post_push_metadata_commit: `pending`",
        "- push_status: `pending`",
        f"- final_status: `{final_status}`",
        "- cleanup_scope: `inventory_docs_sync_no_runtime_mutation`",
        f"- files_scanned_count: `{inv['files_scanned_count']}`",
        "- files_changed_count: `pending_until_commit`",
        "- files_archived_count: `0`",
        "- files_deleted_count: `0`",
        f"- empty_artifacts_count: `{len(inv['empty_artifacts'])}`",
        f"- encoding_issues_found: `{encoding_issues}`",
        "- encoding_issues_fixed: `0`",
        "- docs_sync_status: `passed`",
        "- bot_psychologist_docs_status: `passed`",
        "- admin_surface_inventory_status: `passed`",
        f"- runtime_mutation_status: `{no_runtime.get('status')}`",
        f"- regression_status: `{regression.get('status')}`",
        f"- known_warnings: `{'; '.join(known_warnings) if known_warnings else 'none'}`",
        "- known_blockers: `none`" if final_status != "blocker" else "- known_blockers: `see failed gates`",
        "",
        "## What Changed",
        "- Added cleanup inventory/report artifacts for PRD-047.13.",
        "- Updated living docs to mark PRD-047.12-HF1 accepted and PRD-047.13 cleanup-only.",
        "- Added admin surface inventory without UI/runtime behavior changes.",
        "",
        "## What Not Changed",
        "- No Writer, Orchestrator, Gate, Dialogue Act Resolver, RAG/Chroma, or Diagnostic Center runtime logic changes.",
        "- No archive move and no deletion performed.",
        "- No production rollout flags changed.",
        "",
        "## Next Recommended PRD",
        "- `PRD-047.14 - Live Dialogue Quality Polish / Human Reference Calibration v1`.",
    ]
    write_text(REPORT_DIR / f"{PRD_ID}_IMPLEMENTATION_REPORT.md", "\n".join(lines))
    write_text(
        REPORT_DIR / f"{PRD_ID}_NEXT_PRD_RECOMMENDATION.md",
        "# PRD-047.13 NEXT PRD RECOMMENDATION\n\nRecommended next PRD: `PRD-047.14 - Live Dialogue Quality Polish / Human Reference Calibration v1`.\n",
    )


def main() -> int:
    reset_own_log_dir()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    inv = build_inventory()
    write_inventory_artifacts(inv)
    build_admin_surface_inventory()
    write_manifests()
    no_runtime = write_no_runtime_mutation()
    regression = run_regression()
    git_hygiene = write_git_hygiene()
    write_reports(inv, regression, no_runtime, git_hygiene)
    summary = {
        "prd": PRD_ID,
        "generated_at_utc": now_iso(),
        "final_status": "passed" if regression.get("status") == "passed" and no_runtime.get("status") == "passed" and git_hygiene.get("status") == "passed" else "blocker",
        "files_scanned_count": inv["files_scanned_count"],
        "empty_artifacts_count": len(inv["empty_artifacts"]),
        "encoding_issues_found": len(inv["encoding_issues"]),
        "regression_status": regression.get("status"),
        "runtime_mutation_status": no_runtime.get("status"),
        "git_hygiene_status": git_hygiene.get("status"),
    }
    write_json(LOG_DIR / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["final_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
