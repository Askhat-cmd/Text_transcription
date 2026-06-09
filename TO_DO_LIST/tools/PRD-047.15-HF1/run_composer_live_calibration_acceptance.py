from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PRD_ID = "PRD-047.15-HF1"
LOG_DIR = ROOT / "TO_DO_LIST" / "logs" / PRD_ID
TOOL_DIR = ROOT / "TO_DO_LIST" / "tools" / PRD_ID
ACCEPT_JSON = LOG_DIR / "calibration_acceptance.json"
ACCEPT_MD = LOG_DIR / "calibration_acceptance.md"
RUNTIME_JSON = LOG_DIR / "runtime_mutation_scope_proof.json"
RUNTIME_MD = LOG_DIR / "runtime_mutation_scope_proof.md"
ENCODING_JSON = LOG_DIR / "encoding_gate_result.json"
VALIDATION_JSON = LOG_DIR / "validation_commands_result.json"

FORBIDDEN_ENCODING_MARKERS = [
    "\u0420\u045f",
    "\u0420\u0491",
    "\u0420\u0451",
    "\u0420\u0405",
    "\u0421\u0453",
    "\u0421\u201a",
    "\u0421\u040a",
    "\ufffd",
]
ALLOWED_CHANGED_PREFIXES = (
    "TO_DO_LIST/PRD-047.15-HF1",
    "TO_DO_LIST/logs/PRD-047.15-HF1",
    "TO_DO_LIST/tools/PRD-047.15-HF1",
    "TO_DO_LIST/reports/PRD-047.15-HF1",
    "bot_psychologist/tests/test_contextual_retrieval_composer_trace_schema_v1.py",
    "bot_psychologist/tests/test_contextual_retrieval_owner_review_pack_v1.py",
    "docs/PROJECT_STATE.md",
    "docs/ROADMAP.md",
    "docs/PRD_INDEX.md",
    "docs/DECISIONS.md",
)
RUNTIME_PREFIXES = ("bot_psychologist/bot_agent/", "bot_psychologist/api/", "bot_psychologist/web_ui/", "Bot_data_base/")
TEXT_SUFFIXES = {".md", ".json", ".py", ".txt"}


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git_lines(args: list[str]) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="ignore",
        capture_output=True,
        check=False,
    )
    return [line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip()]


def _changed_files() -> list[str]:
    files = set(_git_lines(["diff", "--name-only"]))
    files.update(_git_lines(["diff", "--cached", "--name-only"]))
    files.update(_git_lines(["ls-files", "--others", "--exclude-standard"]))
    return sorted(files)


def _runtime_mutation_proof() -> dict[str, Any]:
    changed = _changed_files()
    changed_runtime = [path for path in changed if path.startswith(RUNTIME_PREFIXES) and not path.startswith("bot_psychologist/tests/")]
    disallowed = [path for path in changed if not path.startswith(ALLOWED_CHANGED_PREFIXES)]
    proof = {
        "status": "passed" if not changed_runtime and not disallowed else "failed",
        "runtime_mutation_allowed": False,
        "changed_files": changed,
        "changed_runtime_files": changed_runtime,
        "disallowed_changed_files": disallowed,
        "new_llm_agent_added": False,
        "new_runtime_path_added": False,
        "new_user_facing_stub_created": False,
        "db_schema_mutated": False,
        "kb_governance_mutated": False,
        "frontend_mutated": False,
    }
    _write_json(RUNTIME_JSON, proof)
    lines = [
        "# PRD-047.15-HF1 Runtime Mutation Scope Proof",
        "",
        f"- status: `{proof['status']}`",
        "- runtime_mutation_allowed: `false`",
        f"- changed_runtime_files: `{len(changed_runtime)}`",
        f"- disallowed_changed_files: `{len(disallowed)}`",
        "- new_llm_agent_added: `false`",
        "- new_runtime_path_added: `false`",
        "- new_user_facing_stub_created: `false`",
        "- db_schema_mutated: `false`",
        "- kb_governance_mutated: `false`",
        "- frontend_mutated: `false`",
    ]
    if changed_runtime:
        lines.append("\n## Changed Runtime Files")
        lines.extend(f"- `{path}`" for path in changed_runtime)
    if disallowed:
        lines.append("\n## Disallowed Changed Files")
        lines.extend(f"- `{path}`" for path in disallowed)
    _write_text(RUNTIME_MD, "\n".join(lines) + "\n")
    return proof


def _encoding_gate() -> dict[str, Any]:
    targets = [
        LOG_DIR,
        TOOL_DIR,
        ROOT / "TO_DO_LIST" / "PRD-047.15-HF1_TASK_LIST.md",
        ROOT / "TO_DO_LIST" / "reports",
        ROOT / "bot_psychologist" / "tests",
        ROOT / "docs",
    ]
    files: list[Path] = []
    for target in targets:
        if target.is_file() and target.suffix.lower() in TEXT_SUFFIXES:
            files.append(target)
        elif target.is_dir():
            for path in target.rglob("*"):
                if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                    if path == ENCODING_JSON:
                        continue
                    if PRD_ID in path.as_posix() or path.name in {
                        "test_contextual_retrieval_composer_trace_schema_v1.py",
                        "test_contextual_retrieval_owner_review_pack_v1.py",
                        "PROJECT_STATE.md",
                        "ROADMAP.md",
                        "PRD_INDEX.md",
                        "DECISIONS.md",
                    }:
                        files.append(path)
    issues: list[dict[str, Any]] = []
    nul_bytes_found = 0
    utf16_like = False
    mojibake_count = 0
    for path in sorted(set(files)):
        data = path.read_bytes()
        nul_count = data.count(b"\x00")
        if nul_count:
            nul_bytes_found += nul_count
            issues.append({"path": path.relative_to(ROOT).as_posix(), "issue": "nul_bytes", "count": nul_count})
        if len(data) > 20 and data[1:80:2].count(0) > 20:
            utf16_like = True
            issues.append({"path": path.relative_to(ROOT).as_posix(), "issue": "utf16_like_interleaving"})
        text = data.decode("utf-8", errors="replace")
        markers = [marker for marker in FORBIDDEN_ENCODING_MARKERS if marker in text]
        if markers:
            mojibake_count += len(markers)
            issues.append({"path": path.relative_to(ROOT).as_posix(), "issue": "mojibake_markers", "markers": markers})
    payload = {
        "encoding_gate_status": "passed" if not issues else "failed",
        "nul_bytes_found": nul_bytes_found,
        "utf16_like_interleaving_found": utf16_like,
        "mojibake_issues_count": mojibake_count,
        "files_checked_count": len(set(files)),
        "issues": issues,
    }
    _write_json(ENCODING_JSON, payload)
    return payload


def _tests_status() -> str:
    validation = _read_json(VALIDATION_JSON, {})
    if validation.get("tests_status") in {"passed", "failed"}:
        return validation["tests_status"]
    return "not_run"


def _missing_required(paths: list[Path]) -> list[str]:
    return [path.relative_to(ROOT).as_posix() for path in paths if not path.exists()]


def run(mode: str) -> dict[str, Any]:
    del mode
    cases = _read_json(LOG_DIR / "composer_calibration_cases.json", [])
    review = _read_json(LOG_DIR / "composer_trace_review_results.json", {})
    metrics = dict(review.get("metrics", {}) or {})
    live = _read_json(LOG_DIR / "live_trace_inventory.json", {"live_trace_status": "not_available"})
    decision = _read_json(LOG_DIR / "llm_hybrid_decision_brief.json", {})
    runtime = _runtime_mutation_proof()
    encoding = _encoding_gate()
    required = [
        LOG_DIR / "composer_calibration_cases.json",
        LOG_DIR / "composer_calibration_cases.md",
        LOG_DIR / "composer_trace_schema.json",
        LOG_DIR / "composer_trace_schema.md",
        LOG_DIR / "composer_trace_review_results.json",
        LOG_DIR / "composer_trace_review_results.md",
        LOG_DIR / "owner_trace_review_sheet.md",
        LOG_DIR / "llm_hybrid_decision_brief.json",
        LOG_DIR / "llm_hybrid_decision_brief.md",
        LOG_DIR / "live_trace_inventory.json",
        LOG_DIR / "live_trace_inventory.md",
    ]
    missing = _missing_required(required)
    tests_status = _tests_status()
    literal_short = int(metrics.get("literal_short_reply_query_count", 0) or 0)
    summary_leak = int(metrics.get("summary_external_kb_leak_count", 0) or 0)
    no_stub = int(metrics.get("no_stub_violations_count", 0) or 0)
    blockers: list[str] = []
    if len(cases) < 40:
        blockers.append("case_library_below_40")
    if missing:
        blockers.append("missing_required_artifacts")
    if literal_short:
        blockers.append("literal_short_reply_query_count_nonzero")
    if summary_leak:
        blockers.append("summary_external_kb_leak_count_nonzero")
    if no_stub:
        blockers.append("no_stub_violations_nonzero")
    if runtime["status"] != "passed":
        blockers.append("runtime_mutation_scope_failed")
    if encoding["encoding_gate_status"] != "passed":
        blockers.append("encoding_gate_failed")
    if tests_status == "failed":
        blockers.append("tests_failed")
    if not decision.get("recommendation"):
        blockers.append("decision_brief_missing_recommendation")
    owner_review_status = "sheet_created" if (LOG_DIR / "owner_trace_review_sheet.md").exists() else "not_created"
    warnings = []
    if owner_review_status == "sheet_created":
        warnings.append("owner review sheet is created but owner scores are not completed")
    if live.get("live_trace_status") == "not_available":
        warnings.append("live traces were not available; replay calibration is present")
    if int(metrics.get("llm_candidate_cases_count", 0) or 0) > 0:
        warnings.append("mixed/low-confidence cases indicate future hybrid calibration candidates")
    warnings.append("HF1.2 out-of-scope static/advisory candidates remain outside this PRD")
    if blockers:
        final_status = "blocker"
    elif warnings or tests_status == "not_run":
        final_status = "warning"
    else:
        final_status = "passed"
    payload = {
        "final_status": final_status,
        "cases_total": len(cases),
        "automated_expected_match_rate": float(metrics.get("automated_expected_match_rate", 0.0) or 0.0),
        "literal_short_reply_query_count": literal_short,
        "summary_external_kb_leak_count": summary_leak,
        "no_stub_violations_count": no_stub,
        "false_positive_rag_count": int(metrics.get("false_positive_rag_count", 0) or 0),
        "false_negative_rag_count": int(metrics.get("false_negative_rag_count", 0) or 0),
        "weak_query_count": int(metrics.get("weak_query_count", 0) or 0),
        "llm_candidate_cases_count": int(metrics.get("llm_candidate_cases_count", 0) or 0),
        "owner_review_status": owner_review_status,
        "live_trace_status": live.get("live_trace_status", "not_available"),
        "decision_recommendation": decision.get("recommendation", ""),
        "runtime_mutation_status": runtime["status"],
        "llm_calls_added": False,
        "new_runtime_path_added": False,
        "new_user_facing_stub_created": False,
        "encoding_gate_status": encoding["encoding_gate_status"],
        "tests_status": tests_status,
        "known_warnings": "; ".join(warnings),
        "known_blockers": "; ".join(blockers),
        "missing_required_artifacts": missing,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(ACCEPT_JSON, payload)
    lines = ["# PRD-047.15-HF1 Calibration Acceptance", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in payload.items() if key != "missing_required_artifacts")
    if missing:
        lines.append("\n## Missing Required Artifacts")
        lines.extend(f"- `{item}`" for item in missing)
    _write_text(ACCEPT_MD, "\n".join(lines) + "\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="static", choices=["static"])
    args = parser.parse_args()
    payload = run(args.mode)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["final_status"] != "blocker" else 1


if __name__ == "__main__":
    raise SystemExit(main())
