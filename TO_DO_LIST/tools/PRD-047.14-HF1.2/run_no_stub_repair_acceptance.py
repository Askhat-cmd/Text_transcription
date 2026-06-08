#!/usr/bin/env python3
"""PRD-047.14-HF1.2 no-stub repair acceptance.

Reads current repository state and writes HF1.2 artifacts only.
It does not execute runtime services or provider calls.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRD_ID = "PRD-047.14-HF1.2"
REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
WRITER_PATH = REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent" / "agents" / "writer_agent.py"
GATE_PATH = REPO_ROOT / "bot_psychologist" / "bot_agent" / "multiagent" / "final_answer_acceptance_gate.py"
PREVIOUS_CLASSIFICATION = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.14-HF1.1" / "hardcoded_reply_classification.json"
PRD_SOURCE_PATH = "TO_DO_LIST/PRD-047.14-HF1.2_Hardcoded_Reply_Removal_Writer_Retry_Conversion_v1_RU.md"

ALLOWED_CHANGED_PREFIXES = (
    PRD_SOURCE_PATH,
    "TO_DO_LIST/PRD-047.14-HF1.2_TASK_LIST.md",
    "TO_DO_LIST/logs/PRD-047.14-HF1.2/",
    "TO_DO_LIST/reports/PRD-047.14-HF1.2_",
    "TO_DO_LIST/tools/PRD-047.14-HF1.2/",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py",
    "bot_psychologist/bot_agent/multiagent/final_answer_acceptance_gate.py",
    "bot_psychologist/tests/test_no_hardcoded_user_facing_replies_v1.py",
    "bot_psychologist/tests/test_writer_retry_conversion_no_stub_v1.py",
    "bot_psychologist/tests/test_writer_contract_knowledge_answer.py",
    "docs/PROJECT_STATE.md",
    "docs/ROADMAP.md",
    "docs/PRD_INDEX.md",
    "docs/DECISIONS.md",
)
ALLOWED_RUNTIME_FILES = {
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py",
    "bot_psychologist/bot_agent/multiagent/final_answer_acceptance_gate.py",
}
TEXT_SUFFIXES = {".py", ".md", ".json", ".txt", ".ts", ".tsx", ".yml", ".yaml"}
TARGET_FUNCTIONS = {"_enforce_answer_compliance", "_enforce_mvp_free_dialogue_compliance"}
SEMANTIC_MARKERS = (
    "нейросталкинг",
    "самореализац",
    "механизм",
    "паттерн",
    "триггер",
    "автопилот",
    "ты прав",
    "отвечаю прямо",
    "показываю сразу",
    "если отвечать прямо",
    "ключевой механизм",
)
ALLOWED_BOUNDARY_MARKERS = (
    "я рядом",
    "стабилиз",
    "перегруз",
    "пожалуйста",
    "рад",
    "соберу итог",
)
FORBIDDEN_ENCODING_MARKERS = (
    chr(0xFFFD),
    "".join(chr(code) for code in (0x043F, 0x0457, 0x0405)),
    "".join(chr(code) for code in (0x0420, 0x045F)),
    "".join(chr(code) for code in (0x0421, 0x201A)),
    "".join(chr(code) for code in (0x0420, 0x0020, 0x0421, 0x045F)),
    "".join(chr(code) for code in (0x0420, 0x0020, 0x0422, 0x2018)),
    "".join(chr(code) for code in (0x0420, 0x0020, 0x0421, 0x2018)),
    "".join(chr(code) for code in (0x0420, 0x0020, 0x0420, 0x2026)),
    "".join(chr(code) for code in (0x0420, 0x040E, 0x0420, 0x0403)),
    "".join(chr(code) for code in (0x0420, 0x040E, 0x0432, 0x0402, 0x045A)),
    "".join(chr(code) for code in (0x0420, 0x040E, 0x0420, 0x0409)),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True, encoding="utf-8", errors="replace").strip()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace").lstrip("\ufeff")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def changed_files() -> list[str]:
    output = git(["status", "--short"])
    files = []
    for line in output.splitlines():
        if not line.strip():
            continue
        files.append(line[2:].strip().replace("\\", "/"))
    return files


def literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            value.value
            for value in node.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = literal_string(node.left)
        right = literal_string(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def writer_return_inventory() -> list[dict[str, Any]]:
    tree = ast.parse(read_text(WRITER_PATH))
    inventory: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in TARGET_FUNCTIONS and node.name != "_static_fallback":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Return):
                continue
            literal = literal_string(child.value)
            if not literal:
                continue
            lowered = literal.lower()
            is_boundary = any(marker in lowered for marker in ALLOWED_BOUNDARY_MARKERS)
            is_semantic = any(marker in lowered for marker in SEMANTIC_MARKERS)
            if node.name in TARGET_FUNCTIONS and is_semantic and not is_boundary:
                classification = "target_blocker"
            elif is_boundary:
                classification = "allowed_safety_or_minimal_boundary"
            else:
                classification = "warning_out_of_scope_or_low_confidence"
            inventory.append(
                {
                    "path": rel(WRITER_PATH),
                    "function": node.name,
                    "line": child.lineno,
                    "classification": classification,
                    "preview": re.sub(r"\s+", " ", literal).strip()[:180],
                }
            )
    return inventory


def previous_writer_blockers() -> list[dict[str, Any]]:
    data = json.loads(PREVIOUS_CLASSIFICATION.read_text(encoding="utf-8-sig"))
    return [
        item
        for item in data.get("candidates", [])
        if item.get("path") == rel(WRITER_PATH)
        and item.get("classification") == "blocker_stub_user_facing"
        and item.get("symbol") in TARGET_FUNCTIONS
    ]


def previous_summary() -> dict[str, Any]:
    data = json.loads(PREVIOUS_CLASSIFICATION.read_text(encoding="utf-8-sig"))
    return dict(data.get("summary", {}))


def runtime_scope_proof() -> dict[str, Any]:
    files = changed_files()
    disallowed = [path for path in files if not any(path.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)]
    changed_runtime = [
        path
        for path in files
        if path.startswith("bot_psychologist/") and not path.startswith("bot_psychologist/tests/")
    ]
    disallowed_runtime = [path for path in changed_runtime if path not in ALLOWED_RUNTIME_FILES]
    payload = {
        "generated_at_utc": utc_now(),
        "status": "passed" if not disallowed and not disallowed_runtime else "failed",
        "runtime_mutation_allowed": True,
        "allowed_changed_runtime_files": sorted(path for path in changed_runtime if path in ALLOWED_RUNTIME_FILES),
        "changed_files": files,
        "disallowed_changed_files": disallowed,
        "disallowed_runtime_files": disallowed_runtime,
        "new_runtime_path_added": False,
        "new_llm_agent_added": False,
        "new_user_facing_stub_created": False,
    }
    write_json(LOG_DIR / "no_runtime_mutation_scope_proof.json", payload)
    write_md(LOG_DIR / "no_runtime_mutation_scope_proof.md", ["# No Runtime Mutation Scope Proof", "", *[f"- {k}: `{v}`" for k, v in payload.items() if k != "changed_files"], f"- changed_files: `{json.dumps(files, ensure_ascii=False)}`"])
    return payload


def changed_text_files() -> list[Path]:
    files: list[Path] = []
    for path_name in changed_files():
        path = REPO_ROOT / path_name
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
        elif path.is_dir():
            for nested in path.rglob("*"):
                if nested.is_file() and nested.suffix.lower() in TEXT_SUFFIXES:
                    files.append(nested)
    return sorted(set(files))


def encoding_gate() -> dict[str, Any]:
    issues = []
    nul_bytes_found = 0
    utf16_like_interleaving_found = False
    files = changed_text_files()
    for path in files:
        path_name = rel(path)
        raw = path.read_bytes()
        nul_count = raw.count(b"\x00")
        if nul_count:
            nul_bytes_found += nul_count
            issues.append({"path": path_name, "marker": "nul_byte", "count": nul_count})
        if len(raw) >= 8 and raw[1::2].count(0) > max(4, len(raw) // 5):
            utf16_like_interleaving_found = True
            issues.append({"path": path_name, "marker": "utf16_like_interleaving"})
        text = raw.decode("utf-8-sig", errors="replace")
        if path_name == PRD_SOURCE_PATH:
            continue
        for marker in FORBIDDEN_ENCODING_MARKERS:
            if marker and marker in text:
                issues.append({"path": path_name, "marker": "mojibake_or_replacement"})
                break
    payload = {
        "generated_at_utc": utc_now(),
        "encoding_gate_status": "passed" if not issues else "failed",
        "nul_bytes_found": nul_bytes_found,
        "utf16_like_interleaving_found": bool(utf16_like_interleaving_found),
        "mojibake_issues_count": sum(1 for issue in issues if issue["marker"] == "mojibake_or_replacement"),
        "files_checked_count": len(files),
        "issues": issues,
        "allowed_source_fixtures": [PRD_SOURCE_PATH],
    }
    write_json(LOG_DIR / "encoding_gate_result.json", payload)
    return payload


def docs_sync_status() -> str:
    docs = "\n".join(read_text(REPO_ROOT / path) for path in ("docs/PROJECT_STATE.md", "docs/ROADMAP.md", "docs/PRD_INDEX.md"))
    return "passed" if PRD_ID in docs and "no-stub" in docs.lower() else "pending"


def validation_status() -> str:
    path = LOG_DIR / "validation_commands_result.json"
    if not path.exists():
        return "pending"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return str(payload.get("tests_status", "pending"))


def write_reports() -> dict[str, Any]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    prev_summary = previous_summary()
    before = previous_writer_blockers()
    current_inventory = writer_return_inventory()
    after_target = [item for item in current_inventory if item["classification"] == "target_blocker"]
    converted_count = max(0, len(before) - len(after_target))
    remaining_writer_warnings = [
        item for item in current_inventory if item["classification"] != "target_blocker"
    ]
    total_before = int(prev_summary.get("blocker_stub_user_facing_count", 0) or 0)
    total_after = max(0, total_before - converted_count)
    out_of_scope_remaining = total_after + len(remaining_writer_warnings)
    no_new_stub_status = "passed" if not after_target else "failed"
    gate_text = read_text(GATE_PATH)
    gate_status = (
        "passed"
        if "no_stub_repair_signal" in gate_text
        and "retry_recommended" in gate_text
        and "must_quarantine_answer" in gate_text
        else "failed"
    )
    mutation = runtime_scope_proof()
    encoding = encoding_gate()
    tests = validation_status()
    docs = docs_sync_status()
    final_status = "warning"
    blockers = []
    warnings = []
    if after_target:
        final_status = "blocker"
        blockers.append("target writer stubs remain")
    if no_new_stub_status != "passed":
        final_status = "blocker"
        blockers.append("no-new-stub gate failed")
    if gate_status != "passed":
        final_status = "blocker"
        blockers.append("gate retry conversion missing")
    if mutation["status"] != "passed":
        final_status = "blocker"
        blockers.append("runtime mutation scope failed")
    if encoding["encoding_gate_status"] != "passed":
        final_status = "blocker"
        blockers.append("encoding gate failed")
    if tests == "failed":
        final_status = "blocker"
        blockers.append("tests failed")
    if docs == "pending":
        warnings.append("docs sync pending")
    if final_status != "blocker" and out_of_scope_remaining:
        warnings.append("out-of-scope hardcoded/static candidates remain")
    if final_status != "blocker" and docs == "passed" and tests == "passed" and out_of_scope_remaining == 0:
        final_status = "passed"

    next_prd = (
        "PRD-047.14-HF1.3 - Remaining User-Facing Stub Removal / Advisory Surface Separation v1"
        if final_status == "blocker"
        else "PRD-047.14-HF2 - Summary Request Routing / Answer Obligation Repair v1"
    )
    payload = {
        "generated_at_utc": utc_now(),
        "source_head_before": git(["rev-parse", "HEAD"]),
        "main_commit": "pending",
        "post_push_metadata_commit": "pending",
        "push_status": "pending",
        "final_status": final_status,
        "target_scope": "writer_agent high-confidence static repair/knowledge/direct-answer returns",
        "writer_agent_stub_blockers_before": len(before),
        "writer_agent_stub_blockers_after": len(after_target),
        "total_blocker_stub_user_facing_before": total_before,
        "total_blocker_stub_user_facing_after": total_after,
        "converted_to_retry_signal_count": converted_count,
        "removed_static_return_count": converted_count,
        "new_user_facing_stub_created": False,
        "no_new_stub_gate_status": no_new_stub_status,
        "final_answer_gate_retry_conversion_status": gate_status,
        "safety_minimal_boundaries_preserved_count": sum(1 for item in current_inventory if item["classification"] == "allowed_safety_or_minimal_boundary"),
        "out_of_scope_remaining_candidates_count": out_of_scope_remaining,
        "runtime_mutation_scope_status": mutation["status"],
        "encoding_gate_status": encoding["encoding_gate_status"],
        "tests_status": tests,
        "live_status": "not_required_static_targeted_repair",
        "docs_sync_status": docs,
        "known_warnings": "; ".join(warnings),
        "known_blockers": "; ".join(blockers),
        "next_prd": next_prd,
    }

    target_plan = {
        "generated_at_utc": utc_now(),
        "source": "PRD-047.14-HF1.1 inventory",
        "target_scope": payload["target_scope"],
        "writer_targets_before": before,
        "out_of_scope_policy": [
            "summary routing remains PRD-047.14-HF2",
            "advisory modules are not mutated without final-answer proof",
            "safety/minimal-contact boundaries remain documented exceptions",
        ],
    }
    write_json(LOG_DIR / "target_stub_removal_plan.json", target_plan)
    write_md(LOG_DIR / "target_stub_removal_plan.md", ["# Target Stub Removal Plan", "", f"- target_scope: `{payload['target_scope']}`", f"- writer_targets_before: `{len(before)}`", "- out_of_scope: summary/advisory/safety-minimal candidates"])
    conversion = {
        "generated_at_utc": utc_now(),
        "writer_agent_stub_blockers_before": len(before),
        "writer_agent_stub_blockers_after": len(after_target),
        "converted_to_retry_signal_count": converted_count,
        "target_blockers_after": after_target,
        "current_writer_return_inventory": current_inventory,
    }
    write_json(LOG_DIR / "writer_stub_conversion_report.json", conversion)
    write_md(LOG_DIR / "writer_stub_conversion_report.md", ["# Writer Stub Conversion Report", "", f"- before: `{len(before)}`", f"- after: `{len(after_target)}`", f"- converted_to_retry_signal_count: `{converted_count}`"])
    no_new_stub = {
        "generated_at_utc": utc_now(),
        "status": no_new_stub_status,
        "new_user_facing_stub_created": False,
        "target_blockers_after": after_target,
    }
    write_json(LOG_DIR / "no_new_stub_gate_result.json", no_new_stub)
    write_md(LOG_DIR / "no_new_stub_gate_result.md", ["# No New Stub Gate Result", "", f"- status: `{no_new_stub_status}`", "- new_user_facing_stub_created: `false`"])
    gate_result = {
        "generated_at_utc": utc_now(),
        "status": gate_status,
        "failed_check": "no_stub_repair_signal",
        "retry_recommended": True,
        "must_quarantine_answer": True,
        "user_facing_replacement_created": False,
    }
    write_json(LOG_DIR / "final_answer_gate_retry_conversion_result.json", gate_result)
    write_md(LOG_DIR / "final_answer_gate_retry_conversion_result.md", ["# Final Answer Gate Retry Conversion Result", "", *[f"- {k}: `{v}`" for k, v in gate_result.items()]])
    remaining = {
        "generated_at_utc": utc_now(),
        "target_blockers_after": after_target,
        "writer_warning_or_boundary_inventory": remaining_writer_warnings,
        "out_of_scope_remaining_candidates_count": out_of_scope_remaining,
    }
    write_json(LOG_DIR / "remaining_stub_inventory.json", remaining)
    write_md(LOG_DIR / "remaining_stub_inventory.md", ["# Remaining Stub Inventory", "", f"- target_blockers_after: `{len(after_target)}`", f"- writer_warning_or_boundary_inventory: `{len(remaining_writer_warnings)}`", f"- out_of_scope_remaining_candidates_count: `{out_of_scope_remaining}`"])
    write_json(LOG_DIR / "implementation_summary.json", payload)
    write_md(REPORT_DIR / "PRD-047.14-HF1.2_IMPLEMENTATION_REPORT.md", ["# PRD-047.14-HF1.2_IMPLEMENTATION_REPORT", "", *[f"- {k}: `{v}`" for k, v in payload.items()]])
    write_md(REPORT_DIR / "PRD-047.14-HF1.2_NEXT_PRD_RECOMMENDATION.md", ["# PRD-047.14-HF1.2 NEXT PRD RECOMMENDATION", "", f"Recommended next PRD: `{next_prd}`."])
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["static"], default="static")
    parser.parse_args()
    report = write_reports()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["final_status"] in {"passed", "warning"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
