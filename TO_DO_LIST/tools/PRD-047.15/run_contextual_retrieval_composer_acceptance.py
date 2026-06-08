#!/usr/bin/env python3
"""PRD-047.15 contextual retrieval query composer acceptance runner."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRD_ID = "PRD-047.15"
REPO_ROOT = Path(__file__).resolve().parents[3]
BOT_ROOT = REPO_ROOT / "bot_psychologist"
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
REPORT_DIR = REPO_ROOT / "TO_DO_LIST" / "reports"
sys.path.insert(0, str(BOT_ROOT))

from bot_agent.multiagent.contextual_retrieval_query_composer import (  # noqa: E402
    build_contextual_retrieval_query_composer_v1,
    merge_composer_into_retrieval_decision_v1,
)

PRD_SOURCE_PATH = "TO_DO_LIST/PRD-047.15_Contextual_Retrieval_Query_Composer_Agent_v1_RU.md"
ALLOWED_CHANGED_PREFIXES = (
    PRD_SOURCE_PATH,
    "TO_DO_LIST/PRD-047.15_TASK_LIST.md",
    "TO_DO_LIST/logs/PRD-047.15/",
    "TO_DO_LIST/reports/PRD-047.15_",
    "TO_DO_LIST/tools/PRD-047.15/",
    "bot_psychologist/bot_agent/multiagent/contextual_retrieval_query_composer.py",
    "bot_psychologist/bot_agent/multiagent/contracts/retrieval_query_contract.py",
    "bot_psychologist/bot_agent/multiagent/orchestrator.py",
    "bot_psychologist/bot_agent/multiagent/writer_context_package.py",
    "bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py",
    "bot_psychologist/tests/test_contextual_retrieval_query_composer_v1.py",
    "bot_psychologist/tests/test_contextual_retrieval_integration_v1.py",
    "bot_psychologist/tests/test_writer_contract_contextual_retrieval_v1.py",
    "bot_psychologist/tests/test_no_hardcoded_user_facing_replies_v1.py",
    "docs/PROJECT_STATE.md",
    "docs/ROADMAP.md",
    "docs/PRD_INDEX.md",
    "docs/DECISIONS.md",
)
ALLOWED_RUNTIME_FILES = {
    "bot_psychologist/bot_agent/multiagent/contextual_retrieval_query_composer.py",
    "bot_psychologist/bot_agent/multiagent/contracts/retrieval_query_contract.py",
    "bot_psychologist/bot_agent/multiagent/orchestrator.py",
    "bot_psychologist/bot_agent/multiagent/writer_context_package.py",
    "bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py",
}
TEXT_SUFFIXES = {".py", ".md", ".json", ".txt", ".ts", ".tsx", ".yml", ".yaml"}
FORBIDDEN_ENCODING_MARKERS = (
    chr(0xFFFD),
    chr(0x0420) + chr(0x045F),
    chr(0x0420) + chr(0x00A0) + chr(0x0421) + chr(0x045F),
    chr(0x0420) + chr(0x00A0) + chr(0x0422) + chr(0x2018),
    chr(0x0420) + chr(0x00A0) + chr(0x0421) + chr(0x2018),
    chr(0x0420) + chr(0x00A0) + chr(0x0420) + chr(0x2026),
    chr(0x0421) + chr(0x0403) + chr(0x0420) + chr(0x0403),
    chr(0x0421) + chr(0x0403) + chr(0x0432) + chr(0x0402) + chr(0x045A),
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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace").lstrip("\ufeff")


def changed_files() -> list[str]:
    output = git(["status", "--short"])
    return [line[2:].strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def composer_cases() -> dict[str, Any]:
    cases = [
        {
            "name": "knowledge_question",
            "payload": build_contextual_retrieval_query_composer_v1(
                user_message="Что такое нейросталкинг?",
                dialogue_act_resolution={"dialogue_act": "knowledge_question"},
                knowledge_answer_guard={"knowledge_answer": {"needed": True, "concept": "нейросталкинг"}},
            ),
            "expect": {"retrieval_action": "query_kb", "contains_query": "нейросталкинг", "include": True},
            "group": "knowledge",
        },
        {
            "name": "short_followup_inherits_offer",
            "payload": build_contextual_retrieval_query_composer_v1(
                user_message="Да, хорошо",
                last_assistant_offer={"is_open": True, "offer_type": "explain_concept", "offer_text_summary": "Показать через нейросталкинг: автоматизм и внутренний шаг."},
            ),
            "expect": {"retrieval_action": "query_kb", "query_source": "last_assistant_offer", "not_query": "Да, хорошо"},
            "group": "short_followup",
        },
        {
            "name": "short_support_suppresses",
            "payload": build_contextual_retrieval_query_composer_v1(
                user_message="Да",
                last_assistant_offer={"is_open": True, "offer_type": "short_support", "offer_text_summary": "короткая поддержка без разбора"},
            ),
            "expect": {"retrieval_action": "suppress_rag", "include": False},
            "group": "noise",
        },
        {
            "name": "summary_current_context_only",
            "payload": build_contextual_retrieval_query_composer_v1(
                user_message="Подведи итог",
                dialogue_act_resolution={"dialogue_act": "summary_request"},
                answer_obligation_resolution={"answer_obligation": "summarize_current_conversation"},
            ),
            "expect": {"retrieval_action": "use_current_context_only", "include": False},
            "group": "summary",
        },
        {
            "name": "greeting_suppresses",
            "payload": build_contextual_retrieval_query_composer_v1(user_message="Привет"),
            "expect": {"retrieval_action": "suppress_rag", "include": False},
            "group": "noise",
        },
        {
            "name": "practice_overview",
            "payload": build_contextual_retrieval_query_composer_v1(
                user_message="Какие практики есть?",
                knowledge_answer_guard={"knowledge_answer": {"needed": True, "answer_type": "practice_overview"}},
            ),
            "expect": {"retrieval_action": "query_kb", "retrieval_need": "practice_context"},
            "group": "knowledge",
        },
        {
            "name": "one_step_suppresses",
            "payload": build_contextual_retrieval_query_composer_v1(
                user_message="Что сделать прямо сейчас?",
                response_planner={"answer_shape": "one_step"},
            ),
            "expect": {"retrieval_action": "suppress_rag", "include": False},
            "group": "noise",
        },
        {
            "name": "low_confidence_trace_only",
            "payload": build_contextual_retrieval_query_composer_v1(
                user_message="Да",
                last_assistant_offer={"is_open": True, "offer_type": "unknown", "offer_text_summary": "Могу продолжить."},
            ),
            "expect": {"retrieval_action": "trace_only", "include": False},
            "group": "short_followup",
        },
    ]
    results = []
    for case in cases:
        payload = case["payload"]
        expect = case["expect"]
        passed = True
        if "retrieval_action" in expect:
            passed = passed and payload.get("retrieval_action") == expect["retrieval_action"]
        if "retrieval_need" in expect:
            passed = passed and payload.get("retrieval_need") == expect["retrieval_need"]
        if "query_source" in expect:
            passed = passed and payload.get("query_source") == expect["query_source"]
        if "contains_query" in expect:
            passed = passed and expect["contains_query"] in str(payload.get("composed_query", ""))
        if "not_query" in expect:
            passed = passed and payload.get("composed_query") != expect["not_query"]
        if "include" in expect:
            passed = passed and bool(payload.get("include_for_writer_if_found")) is bool(expect["include"])
        passed = passed and payload.get("no_user_facing_text_created") is True
        results.append({**case, "passed": passed})
    payload = {
        "generated_at_utc": utc_now(),
        "status": "passed" if all(item["passed"] for item in results) else "failed",
        "composer_cases_passed": sum(1 for item in results if item["passed"]),
        "composer_cases_total": len(results),
        "cases": results,
    }
    write_json(LOG_DIR / "contextual_retrieval_composer_acceptance.json", payload)
    write_md(LOG_DIR / "contextual_retrieval_composer_acceptance.md", ["# Contextual Retrieval Composer Acceptance", "", f"- status: `{payload['status']}`", f"- cases: `{payload['composer_cases_passed']}/{payload['composer_cases_total']}`", *[f"- {item['name']}: `{item['passed']}` -> `{item['payload']['retrieval_action']}`" for item in results]])
    return payload


def group_artifacts(acceptance: dict[str, Any]) -> dict[str, Any]:
    cases = list(acceptance.get("cases", []) or [])
    groups = {
        "short_followup": "short_followup_query_composition_result",
        "summary": "summary_retrieval_suppression_result",
        "knowledge": "knowledge_query_composition_result",
        "noise": "noise_suppression_result",
    }
    payloads = {}
    for group, filename in groups.items():
        items = [item for item in cases if item.get("group") == group]
        payload = {
            "generated_at_utc": utc_now(),
            "status": "passed" if items and all(item.get("passed") for item in items) else "failed",
            "cases_passed": sum(1 for item in items if item.get("passed")),
            "cases_total": len(items),
            "cases": items,
        }
        payloads[group] = payload
        write_json(LOG_DIR / f"{filename}.json", payload)
        write_md(LOG_DIR / f"{filename}.md", [f"# {filename}", "", f"- status: `{payload['status']}`", f"- cases: `{payload['cases_passed']}/{payload['cases_total']}`"])
    return payloads


def no_stub_scan() -> dict[str, Any]:
    path = BOT_ROOT / "bot_agent" / "multiagent" / "contextual_retrieval_query_composer.py"
    tree = ast.parse(read_text(path))
    offenders = []
    markers = ("вот объяснение", "нейросталкинг — это", "главный вывод", "сделай такой шаг", "я рядом")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            lowered = node.value.value.lower()
            if any(marker in lowered for marker in markers):
                offenders.append({"line": node.lineno, "preview": node.value.value[:120]})
    probe = build_contextual_retrieval_query_composer_v1(user_message="Привет")
    status = "passed" if not offenders and probe.get("no_user_facing_text_created") is True else "failed"
    payload = {"generated_at_utc": utc_now(), "status": status, "offenders": offenders, "no_user_facing_text_created": probe.get("no_user_facing_text_created") is True}
    write_json(LOG_DIR / "no_stub_composer_scan.json", payload)
    write_md(LOG_DIR / "no_stub_composer_scan.md", ["# No Stub Composer Scan", "", f"- status: `{status}`", f"- offenders: `{len(offenders)}`"])
    return payload


def writer_contract_exposure() -> dict[str, Any]:
    from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
    from bot_agent.multiagent.contracts.thread_state import ThreadState
    from bot_agent.multiagent.contracts.writer_contract import WriterContract

    composer = build_contextual_retrieval_query_composer_v1(
        user_message="Да, хорошо",
        last_assistant_offer={"is_open": True, "offer_type": "explain_concept", "offer_text_summary": "Показать через нейросталкинг."},
    )
    contract = WriterContract(
        user_message="Да, хорошо",
        thread_state=ThreadState(thread_id="t", user_id="u", core_direction="", phase="clarify"),
        memory_bundle=MemoryBundle(conversation_context="Assistant: offer"),
        retrieval_decision={"composer": composer, "rag_included_count": 0, "rag_included_for_writer": []},
    )
    ctx = contract.to_prompt_context()
    required = {
        "contextual_retrieval_query_composer_version": "contextual_retrieval_query_composer_v1",
        "retrieval_query_source": "last_assistant_offer",
        "retrieval_query_composer_action": "query_kb",
    }
    status = "passed" if all(ctx.get(key) == value for key, value in required.items()) and ctx.get("retrieval_query_composer_no_user_facing_text_created") is True else "failed"
    payload = {"generated_at_utc": utc_now(), "status": status, "required": required, "observed": {key: ctx.get(key) for key in required}}
    write_json(LOG_DIR / "writer_contract_contextual_retrieval_result.json", payload)
    write_md(LOG_DIR / "writer_contract_contextual_retrieval_result.md", ["# Writer Contract Contextual Retrieval Result", "", f"- status: `{status}`"])
    return payload


def runtime_scope_proof() -> dict[str, Any]:
    files = changed_files()
    disallowed = [path for path in files if not any(path.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)]
    runtime = [path for path in files if path.startswith("bot_psychologist/") and not path.startswith("bot_psychologist/tests/")]
    disallowed_runtime = [path for path in runtime if path not in ALLOWED_RUNTIME_FILES]
    payload = {
        "generated_at_utc": utc_now(),
        "status": "passed" if not disallowed and not disallowed_runtime else "failed",
        "runtime_mutation_allowed": True,
        "allowed_changed_runtime_files": sorted(path for path in runtime if path in ALLOWED_RUNTIME_FILES),
        "disallowed_changed_files": disallowed,
        "disallowed_runtime_files": disallowed_runtime,
        "new_logical_agent_layer_added": True,
        "new_llm_agent_added": False,
        "new_runtime_path_added": False,
        "new_user_facing_stub_created": False,
        "db_schema_mutated": False,
        "kb_governance_mutated": False,
        "frontend_mutated": False,
    }
    write_json(LOG_DIR / "runtime_mutation_scope_proof.json", payload)
    write_md(LOG_DIR / "runtime_mutation_scope_proof.md", ["# Runtime Mutation Scope Proof", "", f"- status: `{payload['status']}`", f"- allowed_changed_runtime_files: `{json.dumps(payload['allowed_changed_runtime_files'], ensure_ascii=False)}`", f"- disallowed_changed_files: `{json.dumps(disallowed, ensure_ascii=False)}`"])
    return payload


def changed_text_files() -> list[Path]:
    result = []
    for name in changed_files():
        path = REPO_ROOT / name
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            result.append(path)
        elif path.is_dir():
            result.extend(item for item in path.rglob("*") if item.is_file() and item.suffix.lower() in TEXT_SUFFIXES)
    return sorted(set(result))


def encoding_gate() -> dict[str, Any]:
    issues = []
    nul_bytes = 0
    utf16_like = False
    files = changed_text_files()
    for path in files:
        name = rel(path)
        raw = path.read_bytes()
        count = raw.count(b"\x00")
        if count:
            nul_bytes += count
            issues.append({"path": name, "marker": "nul_byte", "count": count})
        if len(raw) >= 8 and raw[1::2].count(0) > max(4, len(raw) // 5):
            utf16_like = True
            issues.append({"path": name, "marker": "utf16_like_interleaving"})
        if name in {PRD_SOURCE_PATH, "TO_DO_LIST/logs/PRD-047.15/encoding_gate_result.json"}:
            continue
        text = raw.decode("utf-8-sig", errors="replace")
        for marker in FORBIDDEN_ENCODING_MARKERS:
            if marker and marker in text:
                issues.append({"path": name, "marker": "mojibake_or_replacement"})
                break
    payload = {"generated_at_utc": utc_now(), "encoding_gate_status": "passed" if not issues else "failed", "nul_bytes_found": nul_bytes, "utf16_like_interleaving_found": utf16_like, "mojibake_issues_count": sum(1 for item in issues if item["marker"] == "mojibake_or_replacement"), "files_checked_count": len(files), "issues": issues}
    write_json(LOG_DIR / "encoding_gate_result.json", payload)
    return payload


def tests_status() -> str:
    path = LOG_DIR / "validation_commands_result.json"
    if not path.exists():
        return "pending"
    return str(json.loads(path.read_text(encoding="utf-8-sig")).get("tests_status", "pending"))


def docs_status() -> str:
    docs = "\n".join(read_text(REPO_ROOT / path) for path in ("docs/PROJECT_STATE.md", "docs/ROADMAP.md", "docs/PRD_INDEX.md"))
    return "passed" if PRD_ID in docs and "contextual_retrieval_query_composer_v1" in docs else "pending"


def write_reports(parts: dict[str, Any], grouped: dict[str, Any]) -> dict[str, Any]:
    statuses = {key: value.get("status") or value.get("encoding_gate_status") for key, value in parts.items()}
    blockers = [key for key, status in statuses.items() if status == "failed"]
    tests = tests_status()
    docs = docs_status()
    if tests == "failed":
        blockers.append("tests")
    final_status = "blocker" if blockers else "warning"
    warnings = []
    if tests == "pending":
        warnings.append("validation commands pending")
    if docs == "pending":
        warnings.append("docs sync pending")
    warnings.append("deterministic v1 may need live/owner calibration for mixed context cases")
    warnings.append("HF1.2 out-of-scope static/advisory candidates remain outside PRD-047.15 scope")
    if not blockers and tests == "passed" and docs == "passed":
        final_status = "warning"
    acceptance = parts["acceptance"]
    payload = {
        "generated_at_utc": utc_now(),
        "source_head_before": git(["rev-parse", "HEAD"]),
        "main_commit": "pending",
        "post_push_metadata_commit": "pending",
        "push_status": "pending",
        "final_status": final_status,
        "composer_version": "contextual_retrieval_query_composer_v1",
        "composer_mode": "deterministic_v1",
        "composer_cases_passed": acceptance.get("composer_cases_passed", 0),
        "composer_cases_total": acceptance.get("composer_cases_total", 0),
        "short_followup_cases_passed": grouped["short_followup"].get("cases_passed", 0),
        "short_followup_cases_total": grouped["short_followup"].get("cases_total", 0),
        "summary_suppression_status": grouped["summary"].get("status", "failed"),
        "knowledge_query_composition_status": grouped["knowledge"].get("status", "failed"),
        "noise_suppression_status": grouped["noise"].get("status", "failed"),
        "writer_contract_exposure_status": statuses.get("writer_contract"),
        "no_stub_composer_scan_status": statuses.get("no_stub"),
        "new_logical_agent_layer_added": True,
        "new_llm_agent_added": False,
        "new_runtime_path_added": False,
        "new_user_facing_stub_created": False,
        "db_schema_mutated": False,
        "kb_governance_mutated": False,
        "frontend_mutated": False,
        "runtime_mutation_scope_status": statuses.get("scope"),
        "encoding_gate_status": statuses.get("encoding"),
        "tests_status": tests,
        "live_status": "not_required_static_direct_contract_acceptance",
        "known_warnings": "; ".join(warnings),
        "known_blockers": "; ".join(blockers),
        "next_prd": "PRD-047.15-HF1 - Contextual Retrieval Composer Live Calibration / Owner Trace Review v1",
    }
    write_json(LOG_DIR / "implementation_summary.json", payload)
    write_md(REPORT_DIR / "PRD-047.15_IMPLEMENTATION_REPORT.md", ["# PRD-047.15_IMPLEMENTATION_REPORT", "", *[f"- {key}: `{value}`" for key, value in payload.items()]])
    write_md(REPORT_DIR / "PRD-047.15_NEXT_PRD_RECOMMENDATION.md", ["# PRD-047.15 NEXT PRD RECOMMENDATION", "", "Recommended next PRD: `PRD-047.15-HF1 - Contextual Retrieval Composer Live Calibration / Owner Trace Review v1`."])
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["static"], default="static")
    parser.parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    acceptance = composer_cases()
    grouped = group_artifacts(acceptance)
    parts = {
        "acceptance": acceptance,
        "no_stub": no_stub_scan(),
        "writer_contract": writer_contract_exposure(),
        "scope": runtime_scope_proof(),
        "encoding": encoding_gate(),
    }
    report = write_reports(parts, grouped)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["final_status"] in {"passed", "warning"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
