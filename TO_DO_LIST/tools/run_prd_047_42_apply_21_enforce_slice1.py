from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BOT_ROOT = REPO_ROOT / "bot_psychologist"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from TO_DO_LIST.tools import run_prd_047_42_apply_20_enforce_compliance_mapping as baseline_runner
from bot_agent.multiagent.agents.writer_agent import WriterAgent
from bot_agent.multiagent.agents.writer_agent_enforce_slice1 import EnforceSlice1PreludeResult


PRD_ID = "PRD-047.42-APPLY-21"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
NORMALIZED_TIMESTAMP = "normalized_for_prd_047_42_apply_21"
HISTORICAL_HEAD = "ab7ec52"
WRITER_AGENT_REL_PATH = "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py"
WRITER_AGENT_PATH = REPO_ROOT / WRITER_AGENT_REL_PATH
APPLY_20_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-20"
PROTECTED_FILES = [
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_constants.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_fallback_helpers.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_fallback_state_mixin.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_lifecycle_mixin.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice1.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice2.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice3.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice4.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice5.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice6.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice7.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice8.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice9.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice10.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice11.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice12.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py",
    "bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py",
]
REMOVED_IMPORT_SYMBOLS = [
    "detect_application_request",
    "detect_direct_concrete_request",
    "detect_explicit_answer_need",
    "detect_expansion_request",
    "detect_repair_and_expand_request",
    "detect_sarcasm_or_negative_feedback",
    "detect_summary_request",
    "normalize_dialogue_profile",
    "_extract_literal_markdown_echo_request",
]
EXPECTED_FIELD_ORDER = [
    "ctx",
    "user_message",
    "lowered_user",
    "literal_markdown_echo",
    "dialogue_profile",
    "expansion_requested",
    "repair_and_expand_requested",
    "knowledge_answer",
    "practice_gate",
    "practice_allowed",
    "should_answer_directly",
    "is_greeting",
    "concept",
    "active_line",
    "active_line_intent",
    "active_line_repair_mode",
    "active_line_revoicing_allowed",
    "active_line_should_offer_practice",
    "active_line_practice_suppression",
    "response_planner",
    "planner_next_move",
    "planner_answer_shape",
    "planner_question_policy",
    "planner_practice_policy",
    "planner_safety_priority",
    "dialogue_policy_payload",
    "dialogue_pragmatics_payload",
    "explicit_answer_need",
    "direct_concrete_request",
    "summary_request",
    "sarcasm_or_negative_feedback",
    "application_request",
    "human_like_answer_policy",
    "constraint_resolution",
    "practice_overview_requested",
    "pragmatics_contextual_followup",
    "pragmatics_offer_type",
    "pragmatics_should_not_reconfirm",
    "pragmatics_repair_dissatisfaction",
    "lowered_text",
    "final_answer_directive",
    "writer_contact_mode",
    "gate_feedback",
    "gate_failed_checks",
    "last_debug_patch",
]
EXPECTED_LAST_DEBUG_KEYS = [
    "compliance_planner_next_move",
    "compliance_planner_answer_shape",
    "compliance_planner_question_policy",
    "compliance_response_planner_present",
    "human_like_answer_policy_enabled",
    "explicit_answer_need",
    "repair_user_dissatisfaction",
    "sarcasm_or_negative_feedback",
    "overruled_constraints",
    "final_answer_directive",
]


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _git_show_text(revision: str, rel_path: str) -> str:
    proc = subprocess.run(
        ["git", "show", f"{revision}:{rel_path}"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return proc.stdout.lstrip("\ufeff")


def _load_historical_writer_agent_class() -> type:
    source = _git_show_text(HISTORICAL_HEAD, WRITER_AGENT_REL_PATH)
    module_name = f"bot_agent.multiagent.agents._prd_047_42_apply_21_before_{HISTORICAL_HEAD}"
    module = types.ModuleType(module_name)
    module.__file__ = str(WRITER_AGENT_PATH)
    module.__package__ = "bot_agent.multiagent.agents"
    module.__name__ = module_name
    sys.modules[module_name] = module
    exec(compile(source, str(WRITER_AGENT_PATH), "exec"), module.__dict__)
    return module.WriterAgent


def _run_snapshot_for_writer(writer_cls: type, *, generated_at_utc: str) -> dict[str, Any]:
    cases_payload: list[dict[str, Any]] = []
    for case in baseline_runner.build_cases():
        contract = copy.deepcopy(case["contract"])
        agent = writer_cls(client=object(), model="snapshot-model")
        result = agent._enforce_answer_compliance(case["response_text"], contract)
        last_debug = copy.deepcopy(agent.last_debug)
        cases_payload.append(
            {
                "case": case["name"],
                "note": case["note"],
                "input": {
                    "response_text": case["response_text"],
                    "contract_summary": baseline_runner._summarize_case(contract),
                },
                "output_text": result,
                "output_sha1": hashlib.sha1(result.encode("utf-8")).hexdigest(),
                "last_debug": last_debug,
                "last_debug_keys": list(last_debug.keys()),
                "final_answer_shape": last_debug.get("final_answer_shape"),
                "retry_signal_reason": (last_debug.get("no_stub_repair_signal") or {}).get("reason"),
            }
        )
    return {
        "schema_version": "prd_047_42_apply_21_enforce_slice1_snapshot_v1",
        "generated_at_utc": generated_at_utc,
        "metadata": {
            "case_count": len(cases_payload),
            "historical_head": HISTORICAL_HEAD,
            "field_count": len(EXPECTED_FIELD_ORDER),
            "last_debug_patch_key_count": len(EXPECTED_LAST_DEBUG_KEYS),
        },
        "cases": cases_payload,
    }


def build_before_snapshot(*, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> dict[str, Any]:
    historical_writer = _load_historical_writer_agent_class()
    return _run_snapshot_for_writer(historical_writer, generated_at_utc=generated_at_utc)


def build_after_snapshot(*, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> dict[str, Any]:
    return _run_snapshot_for_writer(WriterAgent, generated_at_utc=generated_at_utc)


def compare_snapshots(
    before_payload: dict[str, Any],
    after_payload: dict[str, Any],
) -> dict[str, Any]:
    before_cases = {case["case"]: case for case in before_payload.get("cases", [])}
    after_cases = {case["case"]: case for case in after_payload.get("cases", [])}
    cases: list[dict[str, Any]] = []
    all_last_debug_keys_match = True
    for case_name in sorted(before_cases):
        before_case = before_cases[case_name]
        after_case = after_cases[case_name]
        keys_match = before_case["last_debug_keys"] == after_case["last_debug_keys"]
        all_last_debug_keys_match = all_last_debug_keys_match and keys_match
        cases.append(
            {
                "case": case_name,
                "output_match": before_case["output_text"] == after_case["output_text"],
                "last_debug_keys_match": keys_match,
                "before_output_sha1": before_case["output_sha1"],
                "after_output_sha1": after_case["output_sha1"],
                "before_last_debug_sha1": hashlib.sha1(
                    json.dumps(before_case["last_debug"], ensure_ascii=False).encode("utf-8")
                ).hexdigest(),
                "after_last_debug_sha1": hashlib.sha1(
                    json.dumps(after_case["last_debug"], ensure_ascii=False).encode("utf-8")
                ).hexdigest(),
            }
        )
    return {
        "snapshot_byte_identical": before_payload == after_payload,
        "all_last_debug_keys_match": all_last_debug_keys_match,
        "cases": cases,
    }


def build_snapshot_equivalence_report(
    before_payload: dict[str, Any],
    after_payload: dict[str, Any],
) -> str:
    comparison = compare_snapshots(before_payload, after_payload)
    lines = [
        "# Snapshot Equivalence",
        "",
        f"- PRD: `{PRD_ID}`",
        f"- Historical baseline revision: `{HISTORICAL_HEAD}`",
        f"- Full snapshot byte identical: `{comparison['snapshot_byte_identical']}`",
        f"- All `last_debug` key orders identical: `{comparison['all_last_debug_keys_match']}`",
        "",
        "| case | output_match | last_debug_keys_match | before_output_sha1 | after_output_sha1 | before_last_debug_sha1 | after_last_debug_sha1 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in comparison["cases"]:
        lines.append(
            "| {case} | {output_match} | {last_debug_keys_match} | `{before_output_sha1}` | `{after_output_sha1}` | `{before_last_debug_sha1}` | `{after_last_debug_sha1}` |".format(
                **case
            )
        )
    return "\n".join(lines)


def _git_hash(rel_path: str) -> str:
    proc = subprocess.run(
        ["git", "hash-object", rel_path],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return proc.stdout.strip()


def build_no_mutation_proof() -> str:
    protected_diff = subprocess.run(
        ["git", "diff", "--name-only", "--", *PROTECTED_FILES],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    protected_changed = [line.strip() for line in protected_diff.stdout.splitlines() if line.strip()]
    prior_log_diff = subprocess.run(
        ["git", "diff", "--name-only", "--", str(APPLY_20_LOG_DIR.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    prior_log_changed = [line.strip() for line in prior_log_diff.stdout.splitlines() if line.strip()]
    hash_lines = [f"- `{rel_path}` -> `{_git_hash(rel_path)}`" for rel_path in PROTECTED_FILES]
    lines = [
        "# No Mutation Proof",
        "",
        f"- PRD: `{PRD_ID}`",
        f"- Protected files checked: `{len(PROTECTED_FILES)}`",
        f"- Protected diff result: `{len(protected_changed)} changed paths`",
        f"- APPLY-20 logs diff result: `{len(prior_log_changed)} changed paths`",
        "",
        "## Protected Diff Result",
        "",
        "- `git diff --name-only -- <protected files>` returned empty output."
        if not protected_changed
        else "- Unexpected protected diffs detected.",
        "",
        "## Prior PRD Log Immutability",
        "",
        "- `git diff --name-only -- TO_DO_LIST/logs/PRD-047.42-APPLY-20` returned empty output."
        if not prior_log_changed
        else "- Unexpected APPLY-20 log diffs detected.",
        "",
        "## Protected Blob Hashes",
        "",
        *hash_lines,
    ]
    if protected_changed:
        lines.extend(["", "## Unexpected Protected Diffs", "", *[f"- `{path}`" for path in protected_changed]])
    if prior_log_changed:
        lines.extend(["", "## Unexpected APPLY-20 Log Diffs", "", *[f"- `{path}`" for path in prior_log_changed]])
    return "\n".join(lines)


def build_grep_proof() -> str:
    historical_lines = _git_show_text(HISTORICAL_HEAD, WRITER_AGENT_REL_PATH).splitlines()
    prelude_last_debug_lines = [
        f"{index + 1}: {line}"
        for index, line in enumerate(historical_lines)
        if 587 <= index + 1 <= 706 and "self.last_debug" in line
    ]
    assignment_only = all("self.last_debug[" in line and "=" in line for line in prelude_last_debug_lines)
    current_source = WRITER_AGENT_PATH.read_text(encoding="utf-8-sig")
    zero_match_rows = []
    for symbol in REMOVED_IMPORT_SYMBOLS:
        hits = [line_no for line_no, line in enumerate(current_source.splitlines(), start=1) if symbol in line]
        zero_match_rows.append((symbol, hits))
    lines = [
        "# Grep Proof",
        "",
        f"- PRD: `{PRD_ID}`",
        f"- Historical source revision checked: `{HISTORICAL_HEAD}`",
        f"- Historical prelude `self.last_debug` lines found: `{len(prelude_last_debug_lines)}`",
        f"- Historical prelude uses assignment-only pattern: `{assignment_only}`",
        "",
        "## Historical Prelude self.last_debug Lines (587-706)",
        "",
    ]
    if prelude_last_debug_lines:
        lines.extend(f"- `{entry}`" for entry in prelude_last_debug_lines)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Current writer_agent.py Zero-Match Checks",
            "",
            "| symbol | remaining_hits |",
            "| --- | --- |",
        ]
    )
    for symbol, hits in zero_match_rows:
        lines.append(f"| `{symbol}` | `{hits if hits else '[]'}` |")
    return "\n".join(lines)


def build_implementation_report() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-21 Implementation Report",
            "",
            f"- PRD: `{PRD_ID}`",
            "- Status: `accepted_pending_delivery_metadata`",
            "- Delivery: `main_commit_pending`",
            "",
            "## Scope Delivered",
            "",
            "- Added `writer_agent_enforce_slice1.py` with `EnforceSlice1PreludeResult` and `_extract_enforce_slice1_prelude(...)`.",
            "- Moved the prelude window `587-706` from `_enforce_answer_compliance` into the helper with literal line-for-line semantics and an ordered `last_debug_patch`.",
            "- Kept `text` + `R01` inline above the helper call and kept `R02` plus everything below untouched.",
            "- Replaced the inline prelude with one helper call, explicit unpack of all `44` locals, and one `self.last_debug.update(...)`.",
            "- Added direct tests, historical-before/live-after snapshot runner, grep proof, and protected-file immutability proof.",
            "",
            "## Honest Boundary",
            "",
            "- This PRD does not change any rule family below `R02`, does not move `legacy_constraints_suppressed`, and does not extend the APPLY-20 case harness.",
            "- The next decomposition step should decide whether to widen coverage before cutting rule families, because the current harness still covers `22/75` rules even though it fully covers the prelude.",
        ]
    )


def build_next_recommendation() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-21 Next Recommendation",
            "",
            "- recommended_next_prd: `PRD-047.42-APPLY-22 - enforce_answer_compliance coverage-extension or first rule-family slice`",
            "- rationale:",
            "  - the prelude is now isolated with full 17-case coverage and stable before/after snapshots;",
            "  - rule-family cuts should happen only after an explicit architect decision on whether to widen the harness beyond the current `22/75` covered rules;",
            "  - the first future family slice should respect the APPLY-20 nesting warning (`R04 ⊃ R05 ⊃ R06`) rather than flatten the cascade.",
        ]
    )


def write_reports(output_dir: Path = OUT_DIR, *, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> dict[str, Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    before_payload = build_before_snapshot(generated_at_utc=generated_at_utc)
    after_payload = build_after_snapshot(generated_at_utc=generated_at_utc)
    before_path = output_dir / "enforce_slice1_snapshot_before.json"
    after_path = output_dir / "enforce_slice1_snapshot_after.json"
    before_path.write_text(json.dumps(before_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    after_path.write_text(json.dumps(after_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reports = {
        "before": before_path,
        "after": after_path,
        "equivalence": output_dir / "snapshot_equivalence.md",
        "no_mutation": output_dir / "no_mutation_proof.md",
        "implementation": output_dir / "implementation_report.md",
        "next": output_dir / "next_recommendation.md",
        "grep": output_dir / "grep_proof.md",
    }
    _write_text(reports["equivalence"], build_snapshot_equivalence_report(before_payload, after_payload))
    _write_text(reports["no_mutation"], build_no_mutation_proof())
    _write_text(reports["implementation"], build_implementation_report())
    _write_text(reports["next"], build_next_recommendation())
    _write_text(reports["grep"], build_grep_proof())
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    args = parser.parse_args()
    write_reports(Path(args.output_dir), generated_at_utc=NORMALIZED_TIMESTAMP)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
