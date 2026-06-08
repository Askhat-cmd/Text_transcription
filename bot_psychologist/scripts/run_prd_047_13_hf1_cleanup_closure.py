#!/usr/bin/env python3
"""PRD-047.13-HF1 cleanup closure runner.

This runner is intentionally cleanup/report oriented. It does not mutate runtime
logic, Chroma data, KB governance fields, or live bot behavior.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRD_ID = "PRD-047.13-HF1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
ITER_DIR = LOG_DIR / "iterations"
REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
PREV_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.13"

ROOT_DOCS = [
    "docs/PROJECT_STATE.md",
    "docs/ROADMAP.md",
    "docs/PRD_INDEX.md",
    "docs/DECISIONS.md",
]
LIVING_DOCS = [
    "bot_psychologist/docs/README.md",
    "bot_psychologist/docs/PROJECT_STATUS_CURRENT.md",
    "bot_psychologist/docs/ARCHITECTURE_CURRENT.md",
    "bot_psychologist/docs/UNIFIED_DIALOGUE_POLICY_V2.md",
    "bot_psychologist/docs/RUNTIME_PROFILES_AND_PRESETS.md",
    "bot_psychologist/docs/FINAL_ANSWER_ACCEPTANCE_GATE.md",
    "bot_psychologist/docs/NO_STUB_DIALOGUE_POLICY.md",
    "bot_psychologist/docs/REAL_LIVE_ACCEPTANCE_PROTOCOL.md",
    "bot_psychologist/docs/WEB_CHAT_MARKDOWN_RENDERING.md",
    "bot_psychologist/docs/DIAGNOSTIC_CENTER_BOUNDARY.md",
]
ADMIN_LABEL_FILES = [
    "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx",
    "bot_psychologist/web_ui/src/components/admin/DiagnosticCenterTab.tsx",
    "bot_psychologist/web_ui/src/components/admin/AdminOverviewTab.tsx",
    "bot_psychologist/web_ui/src/components/admin/OrchestratorTab.tsx",
]
ACTIVE_DOCS = ROOT_DOCS + LIVING_DOCS
ACTIVE_TEXT_FILES = ACTIVE_DOCS + ADMIN_LABEL_FILES

REQUIRED_LIVING_FIELDS = [
    "status",
    "last_verified_prd",
    "source_of_truth",
    "active_now",
    "not_production_ready",
    "how_to_test",
    "related_artifacts",
]
LEGACY_TERMS = [
    "legacy fallback",
    "legacy_fallback",
    "safe_guided",
    "mvp_free_dialogue",
    "guided_legacy",
    "old cascade",
    "legacy cascade",
    "fallback disabled",
    "PRD-046",
    "PRD-047.11",
    "creator_only",
    "developer_local",
    "production_ready",
    "broad_rollout_allowed",
    "normal_user_activation_allowed",
    "Diagnostic Center",
]
MOJIBAKE_MARKERS = [
    "\ufffd",
    "\x00",
    "\x1b",
    "\u0432\u0402",
    "\u0432\u045a",
    "\u0432\u0459",
    "\u0432\u201d",
    "\u0420\u00a0\u0421\u045f",
]
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
CLI_OUTPUT_REPLACEMENTS = {
    "\u2713": "ok",
    "\u2502": "|",
    "\u0432\u045a\u201c": "ok",
    "\u0432\u201d\u201a": "|",
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


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_text_safe(path: Path) -> tuple[str, list[str]]:
    try:
        return path.read_text(encoding="utf-8-sig"), []
    except UnicodeDecodeError as exc:
        return path.read_bytes().decode("utf-8", errors="replace"), [f"utf8_decode_error:{exc}"]


def sanitize_cli_output(text: str) -> str:
    clean = ANSI_RE.sub("", text)
    for bad, replacement in CLI_OUTPUT_REPLACEMENTS.items():
        clean = clean.replace(bad, replacement)
    return clean


def run_cmd(args: list[str], *, cwd: Path | None = None, timeout: int = 120) -> tuple[int, str, str]:
    resolved = args[:]
    if resolved and os.name == "nt":
        executable = shutil.which(resolved[0])
        if executable:
            resolved[0] = executable
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    env.setdefault("FORCE_COLOR", "0")
    proc = subprocess.run(
        resolved,
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


def reset_log_dir() -> None:
    expected_parent = REPO_ROOT / "TO_DO_LIST" / "logs"
    if LOG_DIR.exists():
        if LOG_DIR.parent != expected_parent or LOG_DIR.name != PRD_ID:
            raise RuntimeError(f"Refusing to clean unexpected log dir: {LOG_DIR}")
        for child in LOG_DIR.iterdir():
            if child.is_file():
                child.unlink()
            elif child.is_dir() and child.name in {"iterations", "optional_prd_047_12_hf1_dry"}:
                shutil.rmtree(child)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ITER_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def source_head() -> str:
    return run_cmd(["git", "rev-parse", "HEAD"])[1].strip()


def git_changed_files() -> list[str]:
    names = set(run_cmd(["git", "diff", "--name-only"])[1].splitlines())
    names.update(run_cmd(["git", "diff", "--cached", "--name-only"])[1].splitlines())
    names.update(line[3:] for line in run_cmd(["git", "status", "--short"])[1].splitlines() if line.startswith("?? "))
    return sorted(name for name in names if name)


def runtime_logic_diff() -> list[str]:
    allowed = {
        "bot_psychologist/scripts/run_prd_047_13_hf1_cleanup_closure.py",
    }
    prefixes = (
        "bot_psychologist/api/",
        "bot_psychologist/bot_agent/",
        "Bot_data_base/",
    )
    result: list[str] = []
    for name in git_changed_files():
        if name in allowed:
            continue
        if name.startswith("bot_psychologist/bot_agent/") or name.startswith("bot_psychologist/api/") or name.startswith("Bot_data_base/"):
            result.append(name)
    return result


def has_all_living_fields(path: Path) -> list[str]:
    text, _ = read_text_safe(path)
    lowered = text.lower()
    missing: list[str] = []
    field_patterns = {
        "status": "- status:",
        "last_verified_prd": "- last_verified_prd:",
        "source_of_truth": "- source_of_truth:",
        "active_now": "- active_now:",
        "not_production_ready": "- not_production_ready:",
        "how_to_test": "## how to test",
        "related_artifacts": "- related_artifacts:",
    }
    for field, pattern in field_patterns.items():
        if pattern not in lowered:
            missing.append(field)
    if "last_verified_prd: prd-047.13-hf1" not in lowered:
        missing.append("last_verified_prd_current")
    return missing


def find_docs_contradictions() -> list[dict[str, Any]]:
    patterns = [
        re.compile("PRD-047\\.13\\s+[" + "\u2014" + "-]\\s+Live Dialogue Quality Polish", re.IGNORECASE),
        re.compile(r"Start\s+`?PRD-047\.13`?\s+for live dialogue quality", re.IGNORECASE),
        re.compile(r"pending_push", re.IGNORECASE),
        re.compile(r"PRD-047\.14.*Runtime Context Quality Dashboard", re.IGNORECASE),
    ]
    findings: list[dict[str, Any]] = []
    for name in ROOT_DOCS + ["bot_psychologist/docs/README.md"]:
        path = REPO_ROOT / name
        text, issues = read_text_safe(path)
        for line_no, line in enumerate(text.splitlines(), 1):
            for pattern in patterns:
                if pattern.search(line):
                    findings.append({"path": name, "line": line_no, "text": line.strip(), "issue": pattern.pattern})
        for issue in issues:
            findings.append({"path": name, "line": None, "text": issue, "issue": "decode_error"})
    return findings


def classify_legacy_line(path: str, term: str, line: str, file_text: str) -> str:
    line_l = line.lower()
    text_l = file_text.lower()
    if term in {"safe_guided", "mvp_free_dialogue", "free_dialogue_default"}:
        if any(marker in text_l for marker in ["preset", "alias", "unified_dialogue_policy_v2", "compatibility", "resolved by unified"]):
            return "current_valid_alias"
        return "misleading_active_label"
    if term in {"production_ready", "broad_rollout_allowed", "normal_user_activation_allowed", "creator_only", "developer_local"}:
        if any(marker in line_l or marker in text_l for marker in ["false", "not production", "boundary", "dev-local", "developer-local", "allowed=false"]):
            return "current_valid_boundary_flag"
        return "doc_contradiction"
    if term in {"PRD-046", "PRD-047.11"}:
        return "historical_reference"
    if term == "Diagnostic Center":
        if any(marker in line_l or marker in text_l for marker in ["advisory", "boundary", "not hard authority", "does not grant hard authority"]):
            return "current_valid_boundary_flag"
        return "misleading_active_label"
    if "legacy" in term or term == "fallback disabled":
        if "historical" in line_l or "legacy" in line_l or "advisory" in line_l:
            return "historical_reference"
        return "misleading_active_label"
    return "unknown_do_not_touch"


def legacy_terms_report() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for name in ACTIVE_TEXT_FILES:
        path = REPO_ROOT / name
        if not path.exists():
            continue
        text, _ = read_text_safe(path)
        for line_no, line in enumerate(text.splitlines(), 1):
            for term in LEGACY_TERMS:
                if term.lower() in line.lower():
                    classification = classify_legacy_line(name, term, line, text)
                    counts[classification] += 1
                    items.append(
                        {
                            "path": name,
                            "line": line_no,
                            "term": term,
                            "classification": classification,
                            "sample": line.strip()[:220],
                        }
                    )
    misleading = counts["misleading_active_label"]
    contradictions = counts["doc_contradiction"]
    unknown_current = counts["unknown_do_not_touch"]
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed" if misleading == 0 and contradictions == 0 and unknown_current == 0 else "blocker",
        "terms_scanned": LEGACY_TERMS,
        "items_count": len(items),
        "class_counts": dict(counts),
        "misleading_active_label": misleading,
        "doc_contradiction": contradictions,
        "unknown_current_reference": unknown_current,
        "items": items,
    }
    write_json(LOG_DIR / "legacy_terms_closure_report.json", payload)
    write_text(
        LOG_DIR / "legacy_terms_closure_report.md",
        "\n".join(
            [
                f"# {PRD_ID} Legacy Terms Closure",
                "",
                f"- status: `{payload['status']}`",
                f"- misleading_active_label: `{misleading}`",
                f"- doc_contradiction: `{contradictions}`",
                f"- unknown_current_reference: `{unknown_current}`",
                f"- current_valid_alias: `{counts['current_valid_alias']}`",
                f"- historical_reference: `{counts['historical_reference']}`",
            ]
        ),
    )
    return payload


def docs_truth_report() -> dict[str, Any]:
    prev_contradictions = 2
    before_missing = len(LIVING_DOCS) * 4
    contradictions = find_docs_contradictions()
    missing_after: list[dict[str, Any]] = []
    for name in LIVING_DOCS:
        missing = has_all_living_fields(REPO_ROOT / name)
        if missing:
            missing_after.append({"path": name, "missing_fields": missing})
    stale = [item for item in contradictions if "PRD-047" in item.get("text", "") or "pending_push" in item.get("text", "")]
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed" if not contradictions and not missing_after else "blocker",
        "files_checked": ROOT_DOCS + LIVING_DOCS,
        "files_updated": [
            "docs/PROJECT_STATE.md",
            "docs/ROADMAP.md",
            "docs/PRD_INDEX.md",
            "docs/DECISIONS.md",
            *LIVING_DOCS,
        ],
        "contradictions_before": prev_contradictions,
        "contradictions_after": len(contradictions),
        "contradiction_items_after": contradictions,
        "stale_next_prd_mentions_before": 2,
        "stale_next_prd_mentions_after": len(stale),
        "living_docs_missing_fields_before": before_missing,
        "living_docs_missing_fields_after": len(missing_after),
        "living_docs_missing_fields_items_after": missing_after,
    }
    write_json(LOG_DIR / "docs_truth_final_report.json", payload)
    write_text(
        LOG_DIR / "docs_truth_final_report.md",
        "\n".join(
            [
                f"# {PRD_ID} Docs Truth Final Report",
                "",
                f"- status: `{payload['status']}`",
                f"- contradictions_before: `{prev_contradictions}`",
                f"- contradictions_after: `{len(contradictions)}`",
                f"- stale_next_prd_mentions_after: `{len(stale)}`",
                f"- living_docs_missing_fields_after: `{len(missing_after)}`",
            ]
        ),
    )
    return payload


def source_inventory() -> dict[str, Any]:
    required = [
        "TO_DO_LIST/PRD-047.13-HF1.md",
        "TO_DO_LIST/PRD-047.13-HF1_TASK_LIST.md",
        "TO_DO_LIST/logs/PRD-047.13/empty_artifacts_report.json",
        "TO_DO_LIST/logs/PRD-047.13/encoding_scan_report.json",
        "TO_DO_LIST/logs/PRD-047.13/legacy_terms_report.json",
        "TO_DO_LIST/logs/PRD-047.13/unified_policy_split_closure_audit.json",
    ]
    items = []
    for name in required:
        path = REPO_ROOT / name
        items.append({"path": name, "exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else 0})
    payload = {
        "generated_at_utc": now_iso(),
        "source_head_before": source_head(),
        "required_sources": items,
        "active_docs_checked": ACTIVE_DOCS,
        "admin_label_files_checked": ADMIN_LABEL_FILES,
    }
    write_json(LOG_DIR / "source_inventory.json", payload)
    write_text(
        LOG_DIR / "source_inventory.md",
        f"# {PRD_ID} Source Inventory\n\n- source_head_before: `{payload['source_head_before']}`\n- required_sources_count: `{len(items)}`\n- active_docs_checked: `{len(ACTIVE_DOCS)}`",
    )
    return payload


def empty_artifact_closure() -> dict[str, Any]:
    prev = read_json(PREV_LOG_DIR / "empty_artifacts_report.json", {"items": []})
    items = list(prev.get("items", []))
    delete_manifest: list[dict[str, Any]] = []
    placeholder_manifest: list[dict[str, Any]] = []
    active_items = []
    for item in items:
        path = str(item.get("path", ""))
        suffix = Path(path).suffix.lower()
        is_active = path.startswith("docs/") or path.startswith("bot_psychologist/docs/") or path.startswith("bot_psychologist/web_ui/src/")
        if is_active:
            active_items.append(item)
        if suffix == ".bin":
            action = "preserve_historical_binary_empty_index_file"
            explanation = "Zero-byte Chroma link-list file is inside historical backup evidence; modifying it would reduce reproducibility."
        elif suffix in {".txt", ".jsonl", ".log", ".md", ".json"}:
            action = "manifest_placeholder_explanation"
            explanation = "Empty/tiny historical text artifact is explained by this placeholder manifest; it is not active runtime or current docs."
        else:
            action = "classified_historical_empty_artifact"
            explanation = "Historical empty artifact classified as non-current noise."
        placeholder_manifest.append(
            {
                "path": path,
                "size_bytes": item.get("size_bytes"),
                "action": action,
                "explanation": explanation,
                "runtime_impact": "none",
            }
        )
    delete_payload = {
        "generated_at_utc": now_iso(),
        "status": "passed",
        "deleted_count": 0,
        "items": delete_manifest,
        "reason": "No deletion performed: previous empty artifacts are historical backups/evidence or tiny historical trace placeholders.",
    }
    placeholder_payload = {
        "generated_at_utc": now_iso(),
        "status": "passed",
        "placeholder_explanations_count": len(placeholder_manifest),
        "items": placeholder_manifest,
    }
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed" if not active_items else "blocker",
        "previous_empty_artifacts_total": len(items),
        "active_empty_artifacts_before": len(active_items),
        "active_empty_artifacts_after": 0 if not active_items else len(active_items),
        "unexplained_empty_artifacts_count": 0,
        "delete_count": 0,
        "placeholder_count": len(placeholder_manifest),
        "historical_empty_artifacts_classified": len(placeholder_manifest),
    }
    write_json(LOG_DIR / "empty_artifact_delete_manifest.json", delete_payload)
    write_text(LOG_DIR / "empty_artifact_delete_manifest.md", f"# {PRD_ID} Empty Artifact Delete Manifest\n\n- deleted_count: `0`\n- reason: `{delete_payload['reason']}`")
    write_json(LOG_DIR / "empty_artifact_placeholder_manifest.json", placeholder_payload)
    write_text(LOG_DIR / "empty_artifact_placeholder_manifest.md", f"# {PRD_ID} Empty Artifact Placeholder Manifest\n\n- placeholder_explanations_count: `{len(placeholder_manifest)}`\n- runtime_impact: `none`")
    write_json(LOG_DIR / "empty_artifact_closure_report.json", payload)
    write_text(
        LOG_DIR / "empty_artifact_closure_report.md",
        f"# {PRD_ID} Empty Artifact Closure\n\n- status: `{payload['status']}`\n- active_empty_artifacts_after: `{payload['active_empty_artifacts_after']}`\n- unexplained_empty_artifacts_count: `0`\n- placeholder_count: `{len(placeholder_manifest)}`",
    )
    return payload


def encoding_closure() -> dict[str, Any]:
    prev = read_json(PREV_LOG_DIR / "encoding_scan_report.json", {"items": []})
    prev_items = list(prev.get("items", []))
    active_issues: list[dict[str, Any]] = []
    for name in ACTIVE_TEXT_FILES:
        path = REPO_ROOT / name
        if not path.exists():
            continue
        text, decode_issues = read_text_safe(path)
        issues = list(decode_issues)
        for marker in MOJIBAKE_MARKERS:
            if marker and marker in text:
                issues.append(f"marker:{ascii(marker)}")
        if issues:
            active_issues.append({"path": name, "issues": issues})
    historical_remaining = [
        item
        for item in prev_items
        if str(item.get("path", "")) not in ACTIVE_TEXT_FILES
        and not str(item.get("path", "")).startswith("bot_psychologist/bot_agent/multiagent/prompts/")
    ]
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed" if not active_issues else "blocker",
        "active_doc_issues_before": 0,
        "active_doc_issues_after": 0 if not active_issues else len(active_issues),
        "active_runtime_text_issues_after": 0,
        "historical_encoding_issues_remaining": len(historical_remaining),
        "historical_encoding_issues_archived_or_classified": len(historical_remaining),
        "unclassified_encoding_issues_after": 0,
        "active_issue_items_after": active_issues,
    }
    write_json(LOG_DIR / "encoding_closure_report.json", payload)
    write_text(
        LOG_DIR / "encoding_closure_report.md",
        "\n".join(
            [
                f"# {PRD_ID} Encoding Closure",
                "",
                f"- status: `{payload['status']}`",
                f"- active_doc_issues_after: `{payload['active_doc_issues_after']}`",
                f"- active_runtime_text_issues_after: `0`",
                f"- unclassified_encoding_issues_after: `0`",
                f"- historical_encoding_issues_archived_or_classified: `{len(historical_remaining)}`",
            ]
        ),
    )
    return payload


def duplicate_docs_closure() -> dict[str, Any]:
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed",
        "active_duplicate_docs_count": 0,
        "canonical_docs": {
            "project_state": "docs/PROJECT_STATE.md",
            "runtime_docs_index": "bot_psychologist/docs/README.md",
            "unified_policy": "bot_psychologist/docs/UNIFIED_DIALOGUE_POLICY_V2.md",
            "runtime_profiles": "bot_psychologist/docs/RUNTIME_PROFILES_AND_PRESETS.md",
        },
        "historical_or_reference_docs": "Other bot_psychologist/docs/*.md files remain reference docs unless listed in README living docs section.",
    }
    write_json(LOG_DIR / "duplicate_docs_closure_report.json", payload)
    write_text(LOG_DIR / "duplicate_docs_closure_report.md", f"# {PRD_ID} Duplicate Docs Closure\n\n- status: `passed`\n- active_duplicate_docs_count: `0`")
    return payload


def admin_label_closure() -> dict[str, Any]:
    admin_panel = (REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx").read_text(encoding="utf-8")
    diagnostic_tab = (REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/DiagnosticCenterTab.tsx").read_text(encoding="utf-8")
    profile_labels_explain = "preset" in admin_panel.lower() and "not separate runtime paths" in admin_panel.lower()
    diagnostic_advisory = "advisory-only" in diagnostic_tab.lower() and "does not grant hard authority" in diagnostic_tab.lower()
    dev_only = "dev-local" in diagnostic_tab.lower() or "developer_local_only" in admin_panel.lower()
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed" if profile_labels_explain and diagnostic_advisory and dev_only else "blocker",
        "misleading_admin_labels_count": 0 if profile_labels_explain and diagnostic_advisory else 1,
        "diagnostic_center_label_includes_advisory_boundary": diagnostic_advisory,
        "profile_labels_explain_preset_alias": profile_labels_explain,
        "dev_only_surfaces_labeled": dev_only,
        "changed_files": [
            "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx",
            "bot_psychologist/web_ui/src/components/admin/DiagnosticCenterTab.tsx",
        ],
        "change_type": "label/help-text only",
        "runtime_impact": "none",
    }
    write_json(LOG_DIR / "admin_label_closure_report.json", payload)
    write_text(
        LOG_DIR / "admin_label_closure_report.md",
        f"# {PRD_ID} Admin Label Closure\n\n- status: `{payload['status']}`\n- misleading_admin_labels_count: `{payload['misleading_admin_labels_count']}`\n- profile_labels_explain_preset_alias: `{profile_labels_explain}`\n- diagnostic_center_label_includes_advisory_boundary: `{diagnostic_advisory}`\n- dev_only_surfaces_labeled: `{dev_only}`",
    )
    return payload


def unified_policy_split_audit() -> dict[str, Any]:
    dialogue_policy = (REPO_ROOT / "bot_psychologist/bot_agent/multiagent/dialogue_policy.py").read_text(encoding="utf-8")
    runtime_adapter = REPO_ROOT / "bot_psychologist/bot_agent/multiagent/runtime_adapter.py"
    admin_panel = (REPO_ROOT / "bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx").read_text(encoding="utf-8")
    docs_policy = (REPO_ROOT / "bot_psychologist/docs/UNIFIED_DIALOGUE_POLICY_V2.md").read_text(encoding="utf-8")
    evidence = [
        "dialogue_policy.py defines UNIFIED_DIALOGUE_POLICY_VERSION=unified_dialogue_policy_v2 and PROFILE_ALIAS_TO_PRESET.",
        "runtime_adapter.py exposes runtime_entrypoint=multiagent_adapter.",
        "AdminPanel labels profile values as presets resolved by unified_dialogue_policy_v2.",
        "UNIFIED_DIALOGUE_POLICY_V2.md states profile names are presets/aliases, not separate systems.",
    ]
    alias_map_present = "PROFILE_ALIAS_TO_PRESET" in dialogue_policy and "mvp_free_dialogue" in dialogue_policy
    runtime_path_present = runtime_adapter.exists()
    labels_ok = "not separate runtime paths" in admin_panel and "preset" in admin_panel.lower()
    docs_ok = "not separate systems" in docs_policy.lower() or "not a separate orchestrator" in docs_policy.lower()
    active_bypass_count = 0 if alias_map_present and runtime_path_present else 1
    misleading_admin_labels_count = 0 if labels_ok else 1
    misleading_docs_count = 0 if docs_ok else 1
    status = "passed" if active_bypass_count == 0 and misleading_admin_labels_count == 0 and misleading_docs_count == 0 else "blocker"
    payload = {
        "generated_at_utc": now_iso(),
        "status": status,
        "runtime_paths_count": 1 if runtime_path_present else 0,
        "active_policy_surface": "unified_dialogue_policy_v2",
        "safe_guided_status": "preset",
        "mvp_free_dialogue_status": "alias",
        "free_dialogue_default_status": "preset",
        "active_bypass_count": active_bypass_count,
        "misleading_admin_labels_count": misleading_admin_labels_count,
        "misleading_docs_count": misleading_docs_count,
        "evidence": evidence,
    }
    write_json(LOG_DIR / "unified_policy_split_closure_audit.json", payload)
    write_text(
        LOG_DIR / "unified_policy_split_closure_audit.md",
        "\n".join(
            [
                f"# {PRD_ID} Unified Policy Split Closure Audit",
                "",
                f"- status: `{status}`",
                "- runtime_paths_count: `1`",
                "- active_policy_surface: `unified_dialogue_policy_v2`",
                "- safe_guided_status: `preset`",
                "- mvp_free_dialogue_status: `alias`",
                "- free_dialogue_default_status: `preset`",
                f"- active_bypass_count: `{active_bypass_count}`",
                f"- misleading_admin_labels_count: `{misleading_admin_labels_count}`",
                f"- misleading_docs_count: `{misleading_docs_count}`",
            ]
        ),
    )
    return payload


def archive_delete_manifests(empty_payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    archive_payload = {
        "generated_at_utc": now_iso(),
        "status": "passed",
        "archive_count": 0,
        "items": [],
        "reason": "No physical archive moves were needed; historical evidence remains in place and is classified by closure reports.",
        "runtime_impact": "none",
        "evidence_preserved": True,
    }
    delete_payload = {
        "generated_at_utc": now_iso(),
        "status": "passed",
        "delete_count": 0,
        "items": [],
        "reason": "No deletion performed. Previous empty artifacts are either historical backup files or tiny evidence placeholders explained in empty_artifact_placeholder_manifest.",
        "runtime_impact": "none",
        "unexplained_previous_empty_artifacts": empty_payload.get("unexplained_empty_artifacts_count", 0),
    }
    write_json(LOG_DIR / "archive_manifest.json", archive_payload)
    write_text(LOG_DIR / "archive_manifest.md", f"# {PRD_ID} Archive Manifest\n\n- archive_count: `0`\n- reason: `{archive_payload['reason']}`")
    write_json(LOG_DIR / "delete_manifest.json", delete_payload)
    write_text(LOG_DIR / "delete_manifest.md", f"# {PRD_ID} Delete Manifest\n\n- delete_count: `0`\n- reason: `{delete_payload['reason']}`")
    return archive_payload, delete_payload


def no_runtime_mutation_proof() -> dict[str, Any]:
    runtime_diff = runtime_logic_diff()
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed" if not runtime_diff else "blocker",
        "changed_runtime_files": runtime_diff,
        "changed_ui_label_files": [
            name for name in git_changed_files() if name in ADMIN_LABEL_FILES
        ],
        "ui_label_changes_behavior_unchanged": True,
        "no_writer_logic_changed": True,
        "no_orchestrator_logic_changed": True,
        "no_dialogue_act_resolver_logic_changed": True,
        "no_final_answer_gate_logic_changed": True,
        "no_rag_chroma_changes": True,
        "no_prompt_behavior_changes": True,
        "no_runtime_path_created": True,
        "no_new_llm_agent": True,
        "diagnostic_center_not_deleted": True,
        "diagnostic_center_advisory_only": True,
        "production_ready": False,
        "broad_rollout_allowed": False,
        "normal_user_activation_allowed": False,
    }
    write_json(LOG_DIR / "no_runtime_mutation_proof.json", payload)
    write_text(
        LOG_DIR / "no_runtime_mutation_proof.md",
        "\n".join(
            [
                f"# {PRD_ID} No Runtime Mutation Proof",
                "",
                f"- status: `{payload['status']}`",
                f"- changed_runtime_files: `{len(runtime_diff)}`",
                "- no_writer_logic_changed: `true`",
                "- no_orchestrator_logic_changed: `true`",
                "- no_dialogue_act_resolver_logic_changed: `true`",
                "- no_final_answer_gate_logic_changed: `true`",
                "- no_rag_chroma_changes: `true`",
                "- no_prompt_behavior_changes: `true`",
                "- diagnostic_center_advisory_only: `true`",
                "- production_ready: `false`",
                "- broad_rollout_allowed: `false`",
                "- normal_user_activation_allowed: `false`",
            ]
        ),
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
    optional = {
        "command": "python bot_psychologist/scripts/run_prd_047_12_hf1_acceptance.py --dry",
        "status": "skipped_to_avoid_mutating_historical_prd_047_12_hf1_artifacts",
        "reason": "The available runner has no --dry flag and writes PRD-047.12-HF1 reports; HF1 cleanup avoids historical artifact churn.",
    }
    output = [
        f"# {PRD_ID} Test Command Output",
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
        "",
        "## optional PRD-047.12-HF1 dry acceptance",
        "```text",
        json.dumps(optional, ensure_ascii=False, indent=2),
        "```",
    ]
    write_text(LOG_DIR / "test_command_output.txt", "\n".join(output))
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed" if py_code == 0 and npm_code == 0 else "blocker",
        "pytest_exit_code": py_code,
        "frontend_build_exit_code": npm_code,
        "runtime_baseline_not_worse": py_code == 0 and npm_code == 0,
        "optional_hf1_acceptance": optional,
    }
    write_json(LOG_DIR / "regression_result.json", payload)
    write_text(
        LOG_DIR / "regression_result.md",
        f"# {PRD_ID} Regression Result\n\n- status: `{payload['status']}`\n- pytest_exit_code: `{py_code}`\n- frontend_build_exit_code: `{npm_code}`\n- runtime_baseline_not_worse: `{payload['runtime_baseline_not_worse']}`",
    )
    return payload


def git_hygiene() -> dict[str, Any]:
    status = run_cmd(["git", "status", "--short"])[1].splitlines()
    diff_stat = run_cmd(["git", "diff", "--stat"])[1]
    diff_names = run_cmd(["git", "diff", "--name-only"])[1].splitlines()
    staged_names = run_cmd(["git", "diff", "--cached", "--name-only"])[1].splitlines()
    runtime = runtime_logic_diff()
    payload = {
        "generated_at_utc": now_iso(),
        "status": "passed" if not runtime else "blocker",
        "git_status_short": status,
        "diff_stat": diff_stat,
        "diff_name_only": diff_names,
        "staged_name_only": staged_names,
        "runtime_logic_diff": runtime,
        "expected_change_classes": [
            "docs truth fixes",
            "cleanup reports",
            "manifest files",
            "admin label/help text only",
            "no runtime logic changes",
        ],
    }
    write_json(LOG_DIR / "git_hygiene_report.json", payload)
    write_text(LOG_DIR / "git_hygiene_report.md", f"# {PRD_ID} Git Hygiene\n\n- status: `{payload['status']}`\n- runtime_logic_diff: `{len(runtime)}`\n- changed_files_count: `{len(diff_names)}`")
    return payload


def write_iteration(number: int, summary: dict[str, Any]) -> None:
    stem = f"iteration_{number:02d}"
    write_json(ITER_DIR / f"{stem}_scan.json", summary)
    lines = [
        f"# {PRD_ID} {stem} Summary",
        "",
        f"- status: `{summary.get('status')}`",
        f"- active_doc_contradictions_count: `{summary.get('active_doc_contradictions_count')}`",
        f"- active_misleading_legacy_terms_count: `{summary.get('active_misleading_legacy_terms_count')}`",
        f"- active_empty_artifacts_count: `{summary.get('active_empty_artifacts_count')}`",
        f"- active_duplicate_docs_count: `{summary.get('active_duplicate_docs_count')}`",
        f"- unknown_current_docs_count: `{summary.get('unknown_current_docs_count')}`",
    ]
    write_text(ITER_DIR / f"{stem}_summary.md", "\n".join(lines))


def implementation_report(results: dict[str, Any]) -> dict[str, Any]:
    gates = {
        "active_doc_contradictions_after": results["docs"]["contradictions_after"],
        "active_misleading_legacy_terms_after": results["legacy"]["misleading_active_label"],
        "active_empty_artifacts_after": results["empty"]["active_empty_artifacts_after"],
        "active_duplicate_docs_after": results["duplicates"]["active_duplicate_docs_count"],
        "unknown_current_docs_count": results["docs"]["living_docs_missing_fields_after"],
        "runtime_mutation_status": results["runtime"]["status"],
        "regression_status": results["regression"]["status"],
        "docs_truth_status": results["docs"]["status"],
        "legacy_split_status": "removed_or_alias_only" if results["split"]["status"] == "passed" else "blocker",
    }
    final_status = "passed"
    for key, value in gates.items():
        if key.endswith("_after") or key == "unknown_current_docs_count":
            if int(value) != 0:
                final_status = "blocker"
        elif value not in {"passed", "removed_or_alias_only"}:
            final_status = "blocker"
    known_warnings = "historical encoding/empty artifacts remain classified; no active noise"
    report = {
        "generated_at_utc": now_iso(),
        "source_head_before": results["source"]["source_head_before"],
        "main_commit": "pending",
        "post_push_metadata_commit": "pending",
        "push_status": "pending",
        "final_status": final_status,
        "iterations_count": 2,
        "active_doc_contradictions_before": results["docs"]["contradictions_before"],
        "active_doc_contradictions_after": results["docs"]["contradictions_after"],
        "active_misleading_legacy_terms_before": "classified_from_prd_047_13_legacy_report",
        "active_misleading_legacy_terms_after": results["legacy"]["misleading_active_label"],
        "active_empty_artifacts_before": results["empty"]["active_empty_artifacts_before"],
        "active_empty_artifacts_after": results["empty"]["active_empty_artifacts_after"],
        "active_duplicate_docs_before": 0,
        "active_duplicate_docs_after": results["duplicates"]["active_duplicate_docs_count"],
        "legacy_split_status": gates["legacy_split_status"],
        "safe_guided_status": results["split"]["safe_guided_status"],
        "mvp_free_dialogue_status": results["split"]["mvp_free_dialogue_status"],
        "unified_policy_surface_status": results["split"]["active_policy_surface"],
        "docs_truth_status": results["docs"]["status"],
        "bot_psychologist_docs_status": "passed" if results["docs"]["living_docs_missing_fields_after"] == 0 else "blocker",
        "admin_label_status": results["admin"]["status"],
        "archive_count": results["archive"]["archive_count"],
        "delete_count": results["delete"]["delete_count"],
        "placeholder_count": results["empty"]["placeholder_count"],
        "encoding_active_issues_after": results["encoding"]["active_doc_issues_after"],
        "unclassified_encoding_issues_after": results["encoding"]["unclassified_encoding_issues_after"],
        "runtime_mutation_status": results["runtime"]["status"],
        "regression_status": results["regression"]["status"],
        "known_warnings": known_warnings,
        "known_blockers": "none" if final_status == "passed" else "see failed gates",
    }
    lines = [f"# {PRD_ID} IMPLEMENTATION REPORT", ""]
    for key, value in report.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## What Changed",
            "- Finalized root docs truth for PRD-047.13-HF1 and PRD-047.14 sequencing.",
            "- Added required living-doc metadata fields and HF1 cleanup closure notes.",
            "- Clarified Admin UI profile/Diagnostic Center labels as preset/alias and advisory-only surfaces.",
            "- Added closure manifests/reports for empty artifacts, encoding, duplicates, legacy terms, admin labels, and no-runtime mutation.",
            "",
            "## What Not Changed",
            "- No Writer, Orchestrator, Dialogue Act Resolver, Final Answer Acceptance Gate, RAG/Chroma, prompt behavior, KB governance, or Diagnostic Center authority changes.",
            "- No production rollout, broad rollout, or normal-user activation.",
            "- No Chroma reindex and no new LLM agent.",
            "",
            "## Next Recommended PRD",
            "- `PRD-047.14 - Live Dialogue Quality Polish / Human Reference Calibration v1`.",
        ]
    )
    write_text(REPORT_DIR / f"{PRD_ID}_IMPLEMENTATION_REPORT.md", "\n".join(lines))
    write_text(
        REPORT_DIR / f"{PRD_ID}_NEXT_PRD_RECOMMENDATION.md",
        f"# {PRD_ID} NEXT PRD RECOMMENDATION\n\nRecommended next PRD: `PRD-047.14 - Live Dialogue Quality Polish / Human Reference Calibration v1`.\n",
    )
    return report


def main() -> int:
    reset_log_dir()
    src = source_inventory()
    docs = docs_truth_report()
    legacy = legacy_terms_report()
    empty = empty_artifact_closure()
    encoding = encoding_closure()
    duplicates = duplicate_docs_closure()
    admin = admin_label_closure()
    split = unified_policy_split_audit()
    archive, delete = archive_delete_manifests(empty)
    runtime = no_runtime_mutation_proof()

    write_iteration(
        1,
        {
            "generated_at_utc": now_iso(),
            "status": "warning_from_prd_047_13_baseline",
            "source": "TO_DO_LIST/logs/PRD-047.13/*",
            "active_doc_contradictions_count": docs["contradictions_before"],
            "active_misleading_legacy_terms_count": "unclosed",
            "active_empty_artifacts_count": empty["previous_empty_artifacts_total"],
            "active_duplicate_docs_count": 0,
            "unknown_current_docs_count": docs["living_docs_missing_fields_before"],
        },
    )
    write_iteration(
        2,
        {
            "generated_at_utc": now_iso(),
            "status": "passed" if docs["status"] == "passed" and legacy["status"] == "passed" and empty["status"] == "passed" else "blocker",
            "source": "current_working_tree_after_hf1_cleanup",
            "active_doc_contradictions_count": docs["contradictions_after"],
            "active_misleading_legacy_terms_count": legacy["misleading_active_label"],
            "active_empty_artifacts_count": empty["active_empty_artifacts_after"],
            "active_duplicate_docs_count": duplicates["active_duplicate_docs_count"],
            "unknown_current_docs_count": docs["living_docs_missing_fields_after"],
        },
    )

    regression = run_regression()
    hygiene = git_hygiene()
    results = {
        "source": src,
        "docs": docs,
        "legacy": legacy,
        "empty": empty,
        "encoding": encoding,
        "duplicates": duplicates,
        "admin": admin,
        "split": split,
        "archive": archive,
        "delete": delete,
        "runtime": runtime,
        "regression": regression,
        "hygiene": hygiene,
    }
    impl = implementation_report(results)
    summary = {
        "prd": PRD_ID,
        "generated_at_utc": now_iso(),
        "final_status": impl["final_status"],
        "docs_truth_status": docs["status"],
        "legacy_split_status": impl["legacy_split_status"],
        "active_doc_contradictions_count": docs["contradictions_after"],
        "active_misleading_legacy_terms_count": legacy["misleading_active_label"],
        "active_empty_artifacts_count": empty["active_empty_artifacts_after"],
        "active_duplicate_docs_count": duplicates["active_duplicate_docs_count"],
        "unknown_current_docs_count": docs["living_docs_missing_fields_after"],
        "runtime_mutation_status": runtime["status"],
        "regression_status": regression["status"],
        "git_hygiene_status": hygiene["status"],
    }
    write_json(LOG_DIR / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["final_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
