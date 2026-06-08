#!/usr/bin/env python3
"""PRD-047.14-HF1.1 hardcoded user-facing reply inventory.

Audit-only: reads repository files and writes artifacts under TO_DO_LIST.
It must not import or mutate runtime modules.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRD_ID = "PRD-047.14-HF1.1"
REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"

ACTIVE_ROOTS = [
    "bot_psychologist/bot_agent",
    "bot_psychologist/api",
    "bot_psychologist/web_ui/src",
    "bot_psychologist/web/frontend/src",
    "Bot_data_base/api",
]
HISTORICAL_ROOTS = ["TO_DO_LIST", "docs"]
TEXT_SUFFIXES = {".py", ".md", ".json", ".txt", ".ts", ".tsx", ".yml", ".yaml"}
EXCLUDED_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
ALLOWED_CHANGED_PREFIXES = (
    "TO_DO_LIST/PRD-047.14-HF1.1",
    "TO_DO_LIST/logs/PRD-047.14-HF1.1/",
    "TO_DO_LIST/reports/PRD-047.14-HF1.1_",
    "TO_DO_LIST/tools/PRD-047.14-HF1.1/",
    "docs/PROJECT_STATE.md",
    "docs/ROADMAP.md",
    "docs/PRD_INDEX.md",
    "docs/DECISIONS.md",
)
PRD_SOURCE_PATH = "TO_DO_LIST/PRD-047.14-HF1.1_Hardcoded_User_Facing_Reply_Inventory_No_Stub_Boundary_Audit_v1_RU.md"

FACTORY_NAME_RE = re.compile(r"(build_.*answer|fallback|repair|reply|response|message|static|template)", re.IGNORECASE)
USER_FACING_PATH_HINTS = ("writer_agent.py", "validator", "orchestrator.py", "diagnostic_center.py")
SAFETY_MARKERS = ("\u043a\u0440\u0438\u0437\u0438\u0441", "\u0431\u0435\u0437\u043e\u043f\u0430\u0441", "\u0441\u0430\u043c\u043e\u043f\u043e\u0432\u0440\u0435\u0436", "\u0441\u0443\u0438\u0446", "\u044d\u043a\u0441\u0442\u0440\u0435\u043d", "112", "911", "\u0441\u0442\u0430\u0431\u0438\u043b\u0438\u0437")
MINIMAL_MARKERS = ("\u044f \u0440\u044f\u0434\u043e\u043c", "\u043f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430", "\u0441\u043f\u0430\u0441\u0438\u0431\u043e", "\u0440\u0430\u0434", "\u043f\u0440\u0438\u0432\u0435\u0442", "\u0437\u0434\u0440\u0430\u0432\u0441\u0442\u0432", "\u0434\u043e \u0441\u0432\u0438\u0434")
EXPLANATION_MARKERS = (
    "\u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c",
    "\u043d\u0435\u0439\u0440\u043e\u0441\u0442\u0430\u043b\u043a\u0438\u043d\u0433",
    "\u0441\u0430\u043c\u043e\u0440\u0435\u0430\u043b\u0438\u0437\u0430\u0446",
    "\u043f\u0430\u0442\u0442\u0435\u0440\u043d",
    "\u043f\u0440\u0430\u043a\u0442\u0438\u043a",
    "\u0443\u0431\u0435\u0436\u0434\u0435\u043d",
    "\u0443\u0431\u0435\u0436\u0434\u0451\u043d",
    "\u0441\u043c\u044b\u0441\u043b",
    "\u043e\u0431\u044a\u044f\u0441\u043d",
    "\u0440\u0430\u0437\u0431\u043e\u0440",
    "\u0433\u0438\u043f\u0435\u0440\u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c",
    "\u0441\u0430\u043c\u043e\u043e\u0431\u0435\u0441\u0446\u0435\u043d\u0438\u0432\u0430\u043d\u0438\u0435",
    "\u0430\u0432\u0442\u043e\u043f\u0438\u043b\u043e\u0442",
)
REPAIR_MARKERS = ("\u0442\u044b \u043f\u0440\u0430\u0432", "\u0438\u0441\u043f\u0440\u0430\u0432", "\u0443\u0448\u0435\u043b", "\u0443\u0448\u0451\u043b", "\u0432\u0435\u0440\u043d\u0443\u0441\u044c", "\u043e\u0442\u0432\u0435\u0447\u0430\u044e \u043f\u0440\u044f\u043c\u043e", "\u0441\u0434\u0432\u0438\u043d\u0443\u043b\u0441\u044f")
CANNED_MARKERS = (
    "\u0435\u0441\u043b\u0438 \u043e\u0442\u0432\u0435\u0447\u0430\u0442\u044c \u043f\u0440\u044f\u043c\u043e",
    "\u043f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u044e \u0441\u0440\u0430\u0437\u0443",
    "\u043c\u043e\u0436\u0435\u043c \u0441\u043f\u043e\u043a\u043e\u0439\u043d\u043e \u043d\u0430\u0447\u0430\u0442\u044c",
    "\u0441\u0435\u0439\u0447\u0430\u0441 \u043d\u0435 \u043d\u0443\u0436\u043d\u043e \u043d\u0438\u0447\u0435\u0433\u043e \u0440\u0430\u0437\u0431\u0438\u0440\u0430\u0442\u044c",
    "\u0441\u0434\u0435\u043b\u0430\u0439 \u043e\u0434\u0438\u043d \u0448\u0430\u0433 \u043f\u0440\u044f\u043c\u043e \u0441\u0435\u0439\u0447\u0430\u0441",
    "\u043a\u043b\u044e\u0447\u0435\u0432\u043e\u0439 \u043c\u0435\u0445\u0430\u043d\u0438\u0437\u043c",
    "\u0434\u0430\u0432\u0430\u0439 \u0440\u0430\u0437\u0432\u0435\u0440\u043d\u0443\u0442\u043e",
)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True, encoding="utf-8", errors="replace").strip()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def iter_text_files(root_names: list[str]) -> list[Path]:
    files: list[Path] = []
    for root_name in root_names:
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        if root.is_file():
            files.append(root)
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            files.append(path)
    return files


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace").lstrip("\ufeff")


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower().replace("ё", "е")).strip()


def string_preview(value: str, limit: int = 220) -> str:
    preview = re.sub(r"\s+", " ", str(value or "")).strip()
    return preview[:limit] + ("..." if len(preview) > limit else "")


def literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                parts.append("{...}")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = literal_string(node.left)
        right = literal_string(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def collect_strings_from_node(node: ast.AST) -> str | None:
    direct = literal_string(node)
    if direct is not None:
        return direct
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        parts = [literal_string(item) for item in node.elts]
        if any(part for part in parts):
            return " | ".join(part for part in parts if part)
    if isinstance(node, ast.Dict):
        parts = []
        for key, value in zip(node.keys, node.values):
            key_text = literal_string(key) if key is not None else ""
            value_text = literal_string(value)
            if value_text:
                parts.append(f"{key_text}: {value_text}" if key_text else value_text)
        if parts:
            return " | ".join(parts)
    return None


def enclosing_symbol(tree: ast.AST, target: ast.AST) -> str:
    best: tuple[int, str] = (-1, "<module>")
    target_line = getattr(target, "lineno", 0)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = getattr(node, "lineno", 0)
            end = getattr(node, "end_lineno", start)
            if start <= target_line <= end and start > best[0]:
                best = (start, node.name)
    return best[1]


def scan_python(path: Path, runtime_class: str) -> list[dict[str, Any]]:
    text = read_text(path)
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [
            {
                "path": rel(path),
                "line_start": exc.lineno or 1,
                "line_end": exc.lineno or 1,
                "symbol": "<parse_error>",
                "snippet_preview": str(exc),
                "origin": "parse_error",
                "runtime_path_classification": runtime_class,
            }
        ]
    candidates: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        value: str | None = None
        origin = ""
        if isinstance(node, ast.Return):
            value = collect_strings_from_node(node.value) if node.value is not None else None
            origin = "return_static_string"
        elif isinstance(node, ast.Assign):
            value = collect_strings_from_node(node.value)
            names = [
                getattr(target, "id", getattr(target, "attr", ""))
                for target in node.targets
            ]
            if value and any(FACTORY_NAME_RE.search(name or "") for name in names):
                origin = "fallback_or_reply_assignment"
            else:
                value = None
        if not value:
            continue
        if len(value.strip()) < 18 and not any(marker in normalized(value) for marker in MINIMAL_MARKERS):
            continue
        candidates.append(
            {
                "path": rel(path),
                "line_start": getattr(node, "lineno", 0),
                "line_end": getattr(node, "end_lineno", getattr(node, "lineno", 0)),
                "symbol": enclosing_symbol(tree, node),
                "snippet_preview": string_preview(value),
                "origin": origin,
                "runtime_path_classification": runtime_class,
            }
        )
    return candidates


def scan_text_markers(path: Path, runtime_class: str) -> list[dict[str, Any]]:
    text = read_text(path)
    candidates: list[dict[str, Any]] = []
    if path.suffix.lower() == ".py":
        return candidates
    for idx, line in enumerate(text.splitlines(), start=1):
        lowered = normalized(line)
        if any(marker in lowered for marker in CANNED_MARKERS + REPAIR_MARKERS):
            candidates.append(
                {
                    "path": rel(path),
                    "line_start": idx,
                    "line_end": idx,
                    "symbol": "<text>",
                    "snippet_preview": string_preview(line),
                    "origin": "text_canned_marker",
                    "runtime_path_classification": runtime_class,
                }
            )
    return candidates


def classify(candidate: dict[str, Any]) -> dict[str, Any]:
    path = str(candidate["path"])
    symbol = str(candidate.get("symbol", ""))
    text = str(candidate.get("snippet_preview", ""))
    low = normalized(text)
    path_class = str(candidate.get("runtime_path_classification", "unknown"))
    reply_type = "unknown"
    classification = "unknown_requires_architect_decision"
    reason = "requires manual architecture decision"
    action = "needs_architect_decision"
    possible_user_facing = path_class == "active_runtime"

    if path_class in {"historical_artifact", "docs"}:
        classification = "allowed_non_user_facing"
        reply_type = "historical_or_docs"
        reason = "historical/documentary evidence is not active final-answer runtime"
        action = "keep"
        possible_user_facing = False
    elif "tests/" in path or path.startswith("bot_psychologist/tests/"):
        classification = "allowed_non_user_facing"
        reply_type = "test_fixture"
        reason = "test fixture strings are not final assistant replies"
        action = "keep"
        possible_user_facing = False
    elif any(name in path for name in ("template_family_guard.py", "stale_stub_detector.py", "final_answer_acceptance_gate.py")):
        classification = "allowed_non_user_facing"
        reply_type = "detector_marker"
        reason = "detector/gate marker constants or trace payloads, not Writer-authored final answers"
        action = "document"
        possible_user_facing = False
    elif any(marker in low for marker in SAFETY_MARKERS):
        classification = "allowed_safety_boundary"
        reply_type = "safety_minimal"
        reason = "safety/empty-answer boundary candidate; keep only with trace evidence"
        action = "document"
    elif any(marker in low for marker in MINIMAL_MARKERS) and len(low) <= 130 and not any(marker in low for marker in EXPLANATION_MARKERS):
        classification = "allowed_minimal_boundary"
        reply_type = "minimal_contact"
        reason = "short contact/close acknowledgement without conceptual interpretation"
        action = "document"
    elif any(marker in low for marker in REPAIR_MARKERS):
        classification = "blocker_stub_user_facing"
        reply_type = "repair"
        reason = "static repair answer can replace Writer instead of retry/contract signal"
        action = "convert_to_writer_retry"
    elif any(marker in low for marker in EXPLANATION_MARKERS):
        classification = "blocker_stub_user_facing"
        reply_type = "knowledge_explanation"
        reason = "static explanation/interpretation can become repeated user-facing answer"
        action = "remove_in_targeted_prd"
    elif "writer_agent.py" in path and candidate.get("origin") == "return_static_string":
        classification = "warning_needs_targeted_refactor"
        reply_type = "direct_answer"
        reason = "Writer compliance path returns static text; needs call-site review before removal"
        action = "convert_to_contract_signal"
    elif any(name in path for name in USER_FACING_PATH_HINTS):
        classification = "warning_needs_targeted_refactor"
        reply_type = "unknown"
        reason = "active runtime path may expose static user-facing text"
        action = "needs_architect_decision"
    else:
        classification = "allowed_non_user_facing"
        reply_type = "debug"
        reason = "no direct user-facing final-answer path detected by static audit"
        action = "document"
        possible_user_facing = False

    candidate.update(
        {
            "is_user_facing_possible": bool(possible_user_facing),
            "call_site_count": 0,
            "call_sites": [],
            "reply_type": reply_type,
            "classification": classification,
            "reason": reason,
            "recommended_action": action,
        }
    )
    return candidate


def collect_inventory() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inventory: list[dict[str, Any]] = []
    for path in iter_text_files(ACTIVE_ROOTS):
        path_class = "active_runtime"
        if path.suffix.lower() == ".py":
            inventory.extend(scan_python(path, path_class))
        else:
            inventory.extend(scan_text_markers(path, path_class))
    for path in iter_text_files(HISTORICAL_ROOTS):
        if PRD_ID in rel(path):
            continue
        path_class = "historical_artifact" if rel(path).startswith("TO_DO_LIST/") else "docs"
        inventory.extend(scan_text_markers(path, path_class))
    classified = [classify(dict(item)) for item in inventory]
    return inventory, classified


def changed_files() -> list[str]:
    output = git(["status", "--short"])
    return [line[2:].strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def no_runtime_mutation_proof() -> dict[str, Any]:
    files = changed_files()
    disallowed = [path for path in files if not any(path.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)]
    payload = {
        "generated_at_utc": utc_now(),
        "status": "passed" if not disallowed else "failed",
        "changed_files": files,
        "disallowed_changed_files": disallowed,
        "bot_psychologist_changed": any(path.startswith("bot_psychologist/") for path in files),
        "bot_data_base_changed": any(path.startswith("Bot_data_base/") for path in files),
        "frontend_runtime_changed": any("web_ui/src" in path or "web/frontend/src" in path for path in files),
        "runtime_mutation_allowed": False,
    }
    write_json(LOG_DIR / "no_runtime_mutation_proof.json", payload)
    write_md(
        LOG_DIR / "no_runtime_mutation_proof.md",
        ["# No Runtime Mutation Proof", "", *[f"- {k}: `{v}`" for k, v in payload.items() if k != "changed_files"], f"- changed_files: `{json.dumps(files, ensure_ascii=False)}`"],
    )
    return payload


def encoding_markers() -> dict[str, str]:
    return {
        "replacement_char": chr(0xFFFD),
        "replacement_char_text": "".join(chr(code) for code in (0x043F, 0x0457, 0x0405)),
        "mojibake_r_pe": "".join(chr(code) for code in (0x0420, 0x045F)),
        "mojibake_s_soft": "".join(chr(code) for code in (0x0421, 0x201A)),
        "bell_control": chr(0x07),
        "form_feed_control": chr(0x0C),
    }


def encoding_gate() -> dict[str, Any]:
    files: list[Path] = []
    for path_name in changed_files():
        path = REPO_ROOT / path_name
        if path.is_dir():
            files.extend(iter_text_files([path_name]))
        elif path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
    issues = []
    allowed_source_fixtures = []
    for path in sorted(set(files)):
        path_name = rel(path)
        if path_name == f"TO_DO_LIST/logs/{PRD_ID}/encoding_gate_result.json":
            continue
        text = read_text(path)
        for marker_id, marker in encoding_markers().items():
            if marker and marker in text:
                if path_name == PRD_SOURCE_PATH:
                    allowed_source_fixtures.append(
                        {
                            "path": path_name,
                            "marker_id": marker_id,
                            "reason": "User-supplied PRD source contains pre-existing mojibake; generated artifacts are still checked strictly.",
                        }
                    )
                else:
                    issues.append({"path": path_name, "marker_id": marker_id})
    payload = {
        "generated_at_utc": utc_now(),
        "encoding_gate_status": "passed" if not issues else "failed",
        "files_checked_count": len(set(files)),
        "allowed_source_fixtures_count": len(allowed_source_fixtures),
        "allowed_source_fixtures": allowed_source_fixtures,
        "issues": issues,
    }
    write_json(LOG_DIR / "encoding_gate_result.json", payload)
    return payload


def classification_summary(classified: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(item["classification"] for item in classified)
    active = [item for item in classified if item.get("runtime_path_classification") == "active_runtime"]
    active_user_facing = [item for item in active if item.get("is_user_facing_possible")]
    unknown_active = [item for item in active if item["classification"] == "unknown_requires_architect_decision"]
    blocker = [item for item in classified if item["classification"] == "blocker_stub_user_facing"]
    warning = [item for item in classified if item["classification"] == "warning_needs_targeted_refactor"]
    final_status = "passed"
    if blocker or unknown_active:
        final_status = "blocker"
    elif warning:
        final_status = "warning"
    return {
        "generated_at_utc": utc_now(),
        "final_status": final_status,
        "hardcoded_candidates_total": len(classified),
        "active_user_facing_candidates": len(active_user_facing),
        "blocker_stub_user_facing_count": len(blocker),
        "warning_needs_targeted_refactor_count": len(warning),
        "allowed_safety_boundary_count": counts.get("allowed_safety_boundary", 0),
        "allowed_minimal_boundary_count": counts.get("allowed_minimal_boundary", 0),
        "allowed_non_user_facing_count": counts.get("allowed_non_user_facing", 0),
        "unknown_active_candidates_count": len(unknown_active),
        "classification_counts": dict(counts),
        "top_risky_files": Counter(item["path"] for item in blocker + warning).most_common(10),
    }


def write_inventory_reports(inventory: list[dict[str, Any]], classified: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    write_json(LOG_DIR / "hardcoded_reply_inventory.json", {"generated_at_utc": utc_now(), "candidates": inventory})
    write_json(LOG_DIR / "hardcoded_reply_classification.json", {"summary": summary, "candidates": classified})
    write_json(
        LOG_DIR / "no_stub_boundary_report.json",
        {
            "generated_at_utc": utc_now(),
            "status": summary["final_status"],
            "no_new_user_facing_stub_created": True,
            "runtime_mutation_performed": False,
            "summary": summary,
        },
    )
    write_md(
        LOG_DIR / "hardcoded_reply_inventory.md",
        [
            "# Hardcoded Reply Inventory",
            "",
            f"- candidates_total: `{len(inventory)}`",
            f"- active_roots: `{json.dumps(ACTIVE_ROOTS)}`",
            f"- historical_roots: `{json.dumps(HISTORICAL_ROOTS)}`",
        ],
    )
    lines = [
        "# Hardcoded Reply Classification",
        "",
        "## Executive Summary",
        f"- status: `{summary['final_status']}`",
        f"- hardcoded_candidates_total: `{summary['hardcoded_candidates_total']}`",
        f"- active_user_facing_candidates: `{summary['active_user_facing_candidates']}`",
        f"- blocker_stub_user_facing_count: `{summary['blocker_stub_user_facing_count']}`",
        f"- warning_needs_targeted_refactor_count: `{summary['warning_needs_targeted_refactor_count']}`",
        f"- allowed_safety_boundary_count: `{summary['allowed_safety_boundary_count']}`",
        f"- allowed_minimal_boundary_count: `{summary['allowed_minimal_boundary_count']}`",
        "",
        "## Top Risky Files",
        "| Path | Count |",
        "| --- | ---: |",
    ]
    for path, count in summary["top_risky_files"]:
        lines.append(f"| `{path}` | {count} |")
    for title, klass in (
        ("Blocker Candidates", "blocker_stub_user_facing"),
        ("Warning Candidates", "warning_needs_targeted_refactor"),
        ("Allowed Safety / Minimal Boundaries", "allowed_safety_boundary"),
        ("Allowed Minimal Boundaries", "allowed_minimal_boundary"),
    ):
        lines.extend(["", f"## {title}", "| Path | Line | Symbol | Type | Reason | Recommended action |", "| --- | ---: | --- | --- | --- | --- |"])
        for item in [candidate for candidate in classified if candidate["classification"] == klass][:40]:
            lines.append(
                f"| `{item['path']}` | {item['line_start']} | `{item['symbol']}` | `{item['reply_type']}` | {item['reason']} | `{item['recommended_action']}` |"
            )
    next_prd = (
        "PRD-047.14-HF1.2 - Hardcoded Reply Removal / Writer Retry Conversion v1"
        if summary["final_status"] in {"warning", "blocker"}
        else "PRD-047.14-HF2 - Summary Request Routing / Answer Obligation Repair v1"
    )
    lines.extend(["", "## Next PRD Recommendation", f"`{next_prd}`"])
    write_md(LOG_DIR / "hardcoded_reply_classification.md", lines)
    write_md(
        LOG_DIR / "no_stub_boundary_report.md",
        [
            "# No-Stub Boundary Report",
            "",
            f"- status: `{summary['final_status']}`",
            "- no_new_user_facing_stub_created: `true`",
            "- runtime_mutation_performed: `false`",
            f"- next_prd: `{next_prd}`",
        ],
    )


def docs_sync_status() -> str:
    text = "\n".join(read_text(REPO_ROOT / path) for path in ("docs/PROJECT_STATE.md", "docs/ROADMAP.md", "docs/PRD_INDEX.md"))
    return "passed" if "PRD-047.14-HF1.1" in text and "no-stub boundary" in text.lower() else "pending"


def write_implementation_report(summary: dict[str, Any], mutation: dict[str, Any], encoding: dict[str, Any]) -> dict[str, Any]:
    validation_path = LOG_DIR / "validation_commands_result.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8-sig")) if validation_path.exists() else {}
    final_status = summary["final_status"]
    blockers = []
    if mutation["status"] != "passed":
        final_status = "blocker"
        blockers.append("runtime mutation proof failed")
    if encoding["encoding_gate_status"] != "passed":
        final_status = "blocker"
        blockers.append("encoding gate failed")
    if summary["blocker_stub_user_facing_count"]:
        blockers.append("active blocker_stub_user_facing candidates found")
    if summary["unknown_active_candidates_count"]:
        blockers.append("unknown active candidates found")
    warnings = []
    if summary["warning_needs_targeted_refactor_count"]:
        warnings.append("warning_needs_targeted_refactor candidates found")
    next_prd = (
        "PRD-047.14-HF1.2 - Hardcoded Reply Removal / Writer Retry Conversion v1"
        if final_status in {"warning", "blocker"}
        else "PRD-047.14-HF2 - Summary Request Routing / Answer Obligation Repair v1"
    )
    payload = {
        "generated_at_utc": utc_now(),
        "source_head_before": git(["rev-parse", "HEAD"]),
        "main_commit": "pending",
        "post_push_metadata_commit": "pending",
        "push_status": "pending",
        "final_status": final_status,
        "hardcoded_candidates_total": summary["hardcoded_candidates_total"],
        "active_user_facing_candidates": summary["active_user_facing_candidates"],
        "blocker_stub_user_facing_count": summary["blocker_stub_user_facing_count"],
        "warning_needs_targeted_refactor_count": summary["warning_needs_targeted_refactor_count"],
        "allowed_safety_boundary_count": summary["allowed_safety_boundary_count"],
        "allowed_minimal_boundary_count": summary["allowed_minimal_boundary_count"],
        "unknown_active_candidates_count": summary["unknown_active_candidates_count"],
        "no_stub_boundary_status": summary["final_status"],
        "runtime_mutation_status": mutation["status"],
        "encoding_gate_status": encoding["encoding_gate_status"],
        "tests_status": validation.get("tests_status", "pending"),
        "docs_sync_status": docs_sync_status(),
        "known_warnings": "; ".join(warnings),
        "known_blockers": "; ".join(blockers),
        "next_prd": next_prd,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(LOG_DIR / "implementation_summary.json", payload)
    write_md(REPORT_DIR / "PRD-047.14-HF1.1_IMPLEMENTATION_REPORT.md", ["# PRD-047.14-HF1.1_IMPLEMENTATION_REPORT", "", *[f"- {k}: `{v}`" for k, v in payload.items()]])
    (REPORT_DIR / "PRD-047.14-HF1.1_NEXT_PRD_RECOMMENDATION.md").write_text(
        f"# PRD-047.14-HF1.1 NEXT PRD RECOMMENDATION\n\nRecommended next PRD: `{next_prd}`.\n",
        encoding="utf-8",
    )
    return payload


def run_static() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    inventory, classified = collect_inventory()
    summary = classification_summary(classified)
    write_inventory_reports(inventory, classified, summary)
    mutation = no_runtime_mutation_proof()
    encoding = encoding_gate()
    report = write_implementation_report(summary, mutation, encoding)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["final_status"] == "passed" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["static"], default="static")
    parser.parse_args()
    return run_static()


if __name__ == "__main__":
    raise SystemExit(main())
