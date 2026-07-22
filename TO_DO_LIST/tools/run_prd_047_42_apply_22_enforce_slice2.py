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
from bot_agent.multiagent.agents.writer_agent_enforce_slice2 import EnforceSlice2SecondPreludeResult


PRD_ID = "PRD-047.42-APPLY-22"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
NORMALIZED_TIMESTAMP = "normalized_for_prd_047_42_apply_22"
HISTORICAL_HEAD = "f730754e"
WRITER_AGENT_REL_PATH = "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py"
WRITER_AGENT_PATH = REPO_ROOT / WRITER_AGENT_REL_PATH
APPLY_20_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-20"
APPLY_21_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-21"
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
]
REMOVED_IMPORT_SYMBOLS = [
    "evaluate_concrete_answer_fit",
]
EXPECTED_FIELD_ORDER = [
    "last_debug_patch",
    "close_gently_triggered",
    "answer_obligation",
    "last_direct_question",
    "last_offer_summary",
    "offer_repair_context",
    "concept_question",
    "has_unsolicited_practice",
    "has_question",
    "asks_define_known_term",
    "has_external_surveillance_frame",
    "user_requests_no_question",
    "user_requests_no_practice",
    "user_repair_signal",
    "user_step_request",
    "canned_step_disallowed",
    "user_mechanism_request",
    "answer_fit",
]
TRUE_BRANCH_LAST_DEBUG_KEYS = [
    "legacy_constraints_suppressed",
    "question_forced",
    "practice_forced",
    "microstep_forced",
    "canned_step_disallowed",
]
FALSE_BRANCH_LAST_DEBUG_KEYS = [
    "legacy_constraints_suppressed",
    "question_forced",
    "practice_forced",
    "microstep_forced",
    "canned_step_disallowed",
    "answer_fit_evaluator",
]
TRUE_BRANCH_FULL_LAST_DEBUG_TAIL = TRUE_BRANCH_LAST_DEBUG_KEYS + ["final_answer_shape"]


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
    module_name = f"bot_agent.multiagent.agents._prd_047_42_apply_22_before_{HISTORICAL_HEAD}"
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
        "schema_version": "prd_047_42_apply_22_enforce_slice2_snapshot_v1",
        "generated_at_utc": generated_at_utc,
        "metadata": {
            "case_count": len(cases_payload),
            "historical_head": HISTORICAL_HEAD,
            "field_count": len(EXPECTED_FIELD_ORDER),
            "true_branch_last_debug_key_count": len(TRUE_BRANCH_LAST_DEBUG_KEYS),
            "false_branch_last_debug_key_count": len(FALSE_BRANCH_LAST_DEBUG_KEYS),
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
        [
            "git",
            "diff",
            "--name-only",
            "--",
            str(APPLY_20_LOG_DIR.relative_to(REPO_ROOT)),
            str(APPLY_21_LOG_DIR.relative_to(REPO_ROOT)),
        ],
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
        f"- APPLY-20/APPLY-21 logs diff result: `{len(prior_log_changed)} changed paths`",
        "",
        "## Protected Diff Result",
        "",
        "- `git diff --name-only -- <protected files>` returned empty output."
        if not protected_changed
        else "- Unexpected protected diffs detected.",
        "",
        "## Prior PRD Log Immutability",
        "",
        "- `git diff --name-only -- TO_DO_LIST/logs/PRD-047.42-APPLY-20 TO_DO_LIST/logs/PRD-047.42-APPLY-21` returned empty output."
        if not prior_log_changed
        else "- Unexpected APPLY-20/APPLY-21 log diffs detected.",
        "",
        "## Protected Blob Hashes",
        "",
        *hash_lines,
    ]
    if protected_changed:
        lines.extend(["", "## Unexpected Protected Diffs", "", *[f"- `{path}`" for path in protected_changed]])
    if prior_log_changed:
        lines.extend(["", "## Unexpected APPLY-20/APPLY-21 Log Diffs", "", *[f"- `{path}`" for path in prior_log_changed]])
    return "\n".join(lines)


def build_grep_proof() -> str:
    historical_lines = _git_show_text(HISTORICAL_HEAD, WRITER_AGENT_REL_PATH).splitlines()
    slice2_last_debug_lines = [
        f"{index + 1}: {line}"
        for index, line in enumerate(historical_lines)
        if 628 <= index + 1 <= 700 and "self.last_debug" in line
    ]
    assignment_only = all("self.last_debug[" in line and "=" in line for line in slice2_last_debug_lines)
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
        f"- Historical slice2 window `self.last_debug` lines found: `{len(slice2_last_debug_lines)}`",
        f"- Historical slice2 window uses assignment-only pattern: `{assignment_only}`",
        "",
        "## Historical slice2 window self.last_debug Lines (628-700)",
        "",
    ]
    if slice2_last_debug_lines:
        lines.extend(f"- `{entry}`" for entry in slice2_last_debug_lines)
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
            "# PRD-047.42-APPLY-22 Implementation Report",
            "",
            f"- PRD: `{PRD_ID}`",
            "- Status: `accepted_pending_delivery_metadata`",
            "- Delivery: `main_commit_pending`",
            "",
            "## Scope Delivered",
            "",
            "- Added `writer_agent_enforce_slice2.py` with `EnforceSlice2SecondPreludeResult` and `_extract_enforce_slice2_second_prelude_and_close_gently(...)` (mechanic d: extract-and-maybe-return).",
            "- Moved the second prelude + inlined R03 window `628-700` from `_enforce_answer_compliance` into the helper with literal line-for-line semantics, an ordered `last_debug_patch` (5 keys on the `close_gently` early-return branch, 6 keys otherwise), and a boolean `close_gently_triggered` flag.",
            "- Kept `self._set_final_answer_shape_debug` and `self._build_gentle_close_reply` calls inline in `writer_agent.py`, executed strictly after `self.last_debug.update(slice2_result.last_debug_patch)`, to preserve the historical `self.last_debug` key order (`final_answer_shape` sixth, not first).",
            "- Passed the three module-level marker tuples (`_PRACTICE_MARKERS`, `_KNOWN_CONCEPT_CLARIFICATION_MARKERS`, `_EXTERNAL_SURVEILLANCE_MARKERS`) into the helper as parameters instead of importing them, avoiding a circular import (law Z-3: no new structure for one PRD).",
            "- Kept `R02` (`623-627`) and `R04` (`702+`) untouched, immediately above and below the helper call.",
            "- Removed the now-unused `evaluate_concrete_answer_fit` import from `writer_agent.py` (its only call site moved into the helper).",
            "- Added direct tests covering both branches of the patch (5 vs 6 keys, exact order), an integration test proving `final_answer_shape` lands sixth (not first) in the true branch, and a marker-parameter substitution test.",
            "- Added a historical-before/live-after snapshot runner reusing the APPLY-20 17-case harness by import.",
            "",
            "## Honest Boundary",
            "",
            "- This PRD closes family 1 (`intake_and_obligation_prelude`, `R01-R03`) of `_enforce_answer_compliance`: `text`/`R01` inline, slice1 (first prelude), `R02` inline, slice2 (second prelude + `R03`).",
            "- Rule families `R04+` remain untouched; boundaries for the next family must be re-verified against the live HEAD rather than trusted from the APPLY-20 map, per the boundary-underestimation finding recorded in the v4.25 master plan update.",
        ]
    )


def build_next_recommendation() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-22 Next Recommendation",
            "",
            "- recommended_next_prd: `PRD-047.42-APPLY-23 - family 2 (obligation_specific_repairs_before_profile_split, originally R04-R16) boundary re-verification and first slice`",
            "- rationale:",
            "  - family 1 (`R01-R03`) is now fully extracted with a first branching (mechanic d) helper and full 17-case coverage;",
            "  - the APPLY-20 map underestimated family 1's true width once already (a hidden second wave of locals plus a nested rule); the next family's boundaries must be re-scouted against live HEAD, not trusted literally from the map;",
            "  - the architect should decide whether to widen harness coverage before cutting family 2, given the same underestimation risk noted in the v4.25 master plan update.",
        ]
    )


def write_reports(output_dir: Path = OUT_DIR, *, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> dict[str, Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    before_payload = build_before_snapshot(generated_at_utc=generated_at_utc)
    after_payload = build_after_snapshot(generated_at_utc=generated_at_utc)
    before_path = output_dir / "enforce_slice2_snapshot_before.json"
    after_path = output_dir / "enforce_slice2_snapshot_after.json"
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
