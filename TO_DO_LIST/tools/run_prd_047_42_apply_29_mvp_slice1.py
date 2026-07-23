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
from bot_agent.multiagent.agents.writer_agent_mvp_slice1 import MvpPart1Result


PRD_ID = "PRD-047.42-APPLY-29"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
NORMALIZED_TIMESTAMP = "normalized_for_prd_047_42_apply_29"
HISTORICAL_HEAD = "05c9de9"
WRITER_AGENT_REL_PATH = "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py"
WRITER_AGENT_PATH = REPO_ROOT / WRITER_AGENT_REL_PATH
PRIOR_LOG_DIRS = [
    REPO_ROOT / "TO_DO_LIST" / "logs" / f"PRD-047.42-APPLY-{n}" for n in range(20, 29)
]
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
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice1.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice2.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice3.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice4.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice5.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice6.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice7.py",
]
EXPECTED_FIELD_ORDER = [
    "outcome",
    "updated_text",
    "updated_lowered_text",
    "return_text",
    "computed_target",
    "last_debug_patch",
]
EXPECTED_OUTCOMES = [
    "not_matched",
    "repair_answer_last_question",
    "repair_user_dissatisfaction",
    "contextual_followup_short_phrase",
    "contextual_followup_example",
    "contextual_followup_direct",
    "safety_grounding_literal",
    "safety_grounding_passthrough",
    "sanitized_direct_no_forced_practice",
    "one_step",
    "structured_summary",
    "sarcasm_negative_feedback_repair",
    "direct_concrete_request_repair",
    "direct_no_forced_question",
    "practice_forbidden_sanitized",
    "practice_forbidden_repair_needed",
    "practice_forbidden_repair_default",
]
MVP_PART1_HISTORICAL_START_LINE = 1019
MVP_PART1_HISTORICAL_END_LINE = 1126


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
    return proc.stdout.lstrip("﻿")


def _load_historical_writer_agent_class() -> type:
    source = _git_show_text(HISTORICAL_HEAD, WRITER_AGENT_REL_PATH)
    module_name = f"bot_agent.multiagent.agents._prd_047_42_apply_29_before_{HISTORICAL_HEAD}"
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
        "schema_version": "prd_047_42_apply_29_mvp_slice1_snapshot_v1",
        "generated_at_utc": generated_at_utc,
        "metadata": {
            "case_count": len(cases_payload),
            "historical_head": HISTORICAL_HEAD,
            "field_count": len(EXPECTED_FIELD_ORDER),
            "outcome_count": len(EXPECTED_OUTCOMES),
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
        ["git", "diff", "--name-only", "--", *[str(path.relative_to(REPO_ROOT)) for path in PRIOR_LOG_DIRS]],
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
        f"- APPLY-20..28 logs diff result: `{len(prior_log_changed)} changed paths`",
        "",
        "## Protected Diff Result",
        "",
        "- `git diff --name-only -- <protected files>` returned empty output."
        if not protected_changed
        else "- Unexpected protected diffs detected.",
        "",
        "## Prior PRD Log Immutability",
        "",
        "- `git diff --name-only -- TO_DO_LIST/logs/PRD-047.42-APPLY-20 .. PRD-047.42-APPLY-28` returned empty output."
        if not prior_log_changed
        else "- Unexpected APPLY-20..28 log diffs detected.",
        "",
        "## Protected Blob Hashes",
        "",
        *hash_lines,
    ]
    if protected_changed:
        lines.extend(["", "## Unexpected Protected Diffs", "", *[f"- `{path}`" for path in protected_changed]])
    if prior_log_changed:
        lines.extend(["", "## Unexpected Prior Log Diffs", "", *[f"- `{path}`" for path in prior_log_changed]])
    return "\n".join(lines)


def build_grep_proof() -> str:
    historical_lines = _git_show_text(HISTORICAL_HEAD, WRITER_AGENT_REL_PATH).splitlines()
    window = historical_lines[MVP_PART1_HISTORICAL_START_LINE - 1 : MVP_PART1_HISTORICAL_END_LINE]
    last_debug_lines = [
        f"{MVP_PART1_HISTORICAL_START_LINE + offset}: {line}"
        for offset, line in enumerate(window)
        if "self.last_debug" in line
    ]
    dead_code_line = historical_lines[MVP_PART1_HISTORICAL_START_LINE - 2]
    dead_code_confirmed = "offer_repair_context" in dead_code_line
    lines = [
        "# Grep Proof",
        "",
        f"- PRD: `{PRD_ID}`",
        f"- Historical source revision checked: `{HISTORICAL_HEAD}`",
        f"- Historical MVP Part 1 window checked: lines `{MVP_PART1_HISTORICAL_START_LINE}-{MVP_PART1_HISTORICAL_END_LINE}`",
        f"- `self.last_debug` direct writes found in window: `{len(last_debug_lines)}` (expected: 4 - two branches x two keys each, group J)",
        f"- Line `{MVP_PART1_HISTORICAL_START_LINE - 1}` confirmed to be the dead-code `offer_repair_context` assignment (not carried into the helper): `{dead_code_confirmed}`",
        "",
        "## Historical self.last_debug Lines In Window",
        "",
    ]
    if last_debug_lines:
        lines.extend(f"- `{entry}`" for entry in last_debug_lines)
    else:
        lines.append("- none")
    return "\n".join(lines)


def build_implementation_report() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-29 Implementation Report",
            "",
            f"- PRD: `{PRD_ID}`",
            "- Status: `accepted_pending_delivery_metadata`",
            "- Delivery: `main_commit_pending`",
            "",
            "## Scope Delivered",
            "",
            "- Added `writer_agent_mvp_slice1.py` with `MvpPart1Result` and `_classify_mvp_part1(...)` - a pure classifier helper (no `self` access) returning one of seventeen tags (16 significant outcomes plus `not_matched`), covering the first 108 lines of `_enforce_mvp_free_dialogue_compliance` (groups A-J).",
            "- Group B's in-place `text`/`lowered_text` mutation is carried through the result as `updated_text`/`updated_lowered_text`, always populated regardless of outcome; the caller reassigns both immediately after the classifier call, before checking `outcome` - the first occurrence of this pattern in the decomposition series.",
            "- Group A's computed `target` (last direct question or user message) is returned as `computed_target` and used for `must_answer` on the call site.",
            "- Group J's two physically distinct branches (1118-1122 and 1123-1126) that write the identical `last_debug` pair under different conditions stay as two distinct classifier tags (`practice_forbidden_repair_needed`, `practice_forbidden_repair_default`), merged only at the call site's shared dispatch branch.",
            "- `offer_repair_context` (line 1018) is confirmed dead code (computed, never read anywhere in the method) and is deliberately NOT carried into the helper, per the PRD's explicit instruction to document rather than fix inherited dead code.",
            "- Kept all `self`-methods (`_defer_no_stub_repair`, `_resolve_one_step_or_no_practice_fallback`, `_set_final_answer_shape_debug`, `_strip_optional_followup_invitation`) exclusively on the call site.",
            "- `detect_stale_stub` (module-level, non-`self`) is called directly inside the helper, matching `writer_agent.py`'s own import path.",
            "- Added direct tests covering all 16 significant outcomes, `not_matched`, the group B text/lowered_text mutation, and `computed_target` for both group A branches.",
            "- Added a historical-before/live-after snapshot runner reusing the APPLY-20 17-case harness by import.",
            "",
            "## Honest Boundary",
            "",
            "- This PRD closes Part 1 (groups A-J, `1019-1126`) of `_enforce_mvp_free_dialogue_compliance`. Groups K-P plus the method's final unconditional fallback remain inline in `writer_agent.py` and are the next boundary (APPLY-30), whose exact line numbers must be re-verified against live HEAD after this PRD merges, per the PRD's own explicit instruction.",
        ]
    )


def build_next_recommendation() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-29 Next Recommendation",
            "",
            "- recommended_next_prd: `PRD-047.42-APPLY-30 - _enforce_mvp_free_dialogue_compliance Part 2 (groups K-P + final fallback)`",
            "- rationale:",
            "  - Part 1 is now fully extracted with full 17-case coverage and zero side effects in the helper layer;",
            "  - groups K-P plus the method's unconditional final fallback remain inline and are the last remaining unextracted surface of `_enforce_mvp_free_dialogue_compliance`;",
            "  - line numbers for Part 2 must be re-verified against live HEAD after this PRD merges (they will shift), per the project's standing 'no map trust without fresh reconnaissance' principle.",
        ]
    )


def write_reports(output_dir: Path = OUT_DIR, *, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> dict[str, Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    before_payload = build_before_snapshot(generated_at_utc=generated_at_utc)
    after_payload = build_after_snapshot(generated_at_utc=generated_at_utc)
    before_path = output_dir / "mvp_slice1_snapshot_before.json"
    after_path = output_dir / "mvp_slice1_snapshot_after.json"
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
