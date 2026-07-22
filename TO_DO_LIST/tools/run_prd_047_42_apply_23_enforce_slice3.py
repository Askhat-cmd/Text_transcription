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
from bot_agent.multiagent.agents.writer_agent_enforce_slice3 import EnforceSlice3BoundedPracticeResult


PRD_ID = "PRD-047.42-APPLY-23"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
NORMALIZED_TIMESTAMP = "normalized_for_prd_047_42_apply_23"
HISTORICAL_HEAD = "ff9489c2"
WRITER_AGENT_REL_PATH = "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py"
WRITER_AGENT_PATH = REPO_ROOT / WRITER_AGENT_REL_PATH
APPLY_20_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-20"
APPLY_21_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-21"
APPLY_22_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-22"
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
]
REMOVED_IMPORT_SYMBOLS: list[str] = []
EXPECTED_FIELD_ORDER = ["outcome"]
EXPECTED_OUTCOMES = ["not_matched", "be_strong", "defer_repair", "strip_followup"]
INTERNAL_LOCAL_NAMES = [
    "practice_anchor_present",
    "practice_step_present",
    "practice_multistep",
]
R04_HISTORICAL_START_LINE = 666
R04_HISTORICAL_END_LINE = 696


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
    module_name = f"bot_agent.multiagent.agents._prd_047_42_apply_23_before_{HISTORICAL_HEAD}"
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
        "schema_version": "prd_047_42_apply_23_enforce_slice3_snapshot_v1",
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
    prior_log_dirs = [APPLY_20_LOG_DIR, APPLY_21_LOG_DIR, APPLY_22_LOG_DIR]
    prior_log_diff = subprocess.run(
        ["git", "diff", "--name-only", "--", *[str(path.relative_to(REPO_ROOT)) for path in prior_log_dirs]],
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
        f"- APPLY-20/APPLY-21/APPLY-22 logs diff result: `{len(prior_log_changed)} changed paths`",
        "",
        "## Protected Diff Result",
        "",
        "- `git diff --name-only -- <protected files>` returned empty output."
        if not protected_changed
        else "- Unexpected protected diffs detected.",
        "",
        "## Prior PRD Log Immutability",
        "",
        "- `git diff --name-only -- TO_DO_LIST/logs/PRD-047.42-APPLY-20 TO_DO_LIST/logs/PRD-047.42-APPLY-21 TO_DO_LIST/logs/PRD-047.42-APPLY-22` returned empty output."
        if not prior_log_changed
        else "- Unexpected APPLY-20/APPLY-21/APPLY-22 log diffs detected.",
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
    r04_window = historical_lines[R04_HISTORICAL_START_LINE - 1 : R04_HISTORICAL_END_LINE]
    r04_window_text = "\n".join(r04_window)
    below_r04_lines = historical_lines[R04_HISTORICAL_END_LINE:]
    internal_local_rows = []
    for name in INTERNAL_LOCAL_NAMES:
        in_window_hits = [
            R04_HISTORICAL_START_LINE + offset
            for offset, line in enumerate(r04_window)
            if name in line
        ]
        below_hits = [
            R04_HISTORICAL_END_LINE + 1 + offset
            for offset, line in enumerate(below_r04_lines)
            if name in line
        ]
        internal_local_rows.append((name, in_window_hits, below_hits))
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
        f"- Historical R04 window checked: lines `{R04_HISTORICAL_START_LINE}-{R04_HISTORICAL_END_LINE}`",
        "",
        "## Internal Locals Never Read Below R04",
        "",
        "| local | hits inside R04 window | hits below R04 window |",
        "| --- | --- | --- |",
    ]
    for name, in_window_hits, below_hits in internal_local_rows:
        lines.append(f"| `{name}` | `{in_window_hits}` | `{below_hits if below_hits else '[]'}` |")
    all_clean = all(not below_hits for _, _, below_hits in internal_local_rows)
    lines.extend(
        [
            "",
            f"- All three internal locals have zero reads below R04: `{all_clean}`",
            "",
            "## Current writer_agent.py Zero-Match Checks",
            "",
            "| symbol | remaining_hits |",
            "| --- | --- |",
        ]
    )
    if zero_match_rows:
        for symbol, hits in zero_match_rows:
            lines.append(f"| `{symbol}` | `{hits if hits else '[]'}` |")
    else:
        lines.append("| _(none removed this PRD)_ | `[]` |")
    return "\n".join(lines)


def build_implementation_report() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-23 Implementation Report",
            "",
            f"- PRD: `{PRD_ID}`",
            "- Status: `accepted_pending_delivery_metadata`",
            "- Delivery: `main_commit_pending`",
            "",
            "## Scope Delivered",
            "",
            "- Added `writer_agent_enforce_slice3.py` with `EnforceSlice3BoundedPracticeResult` and `_classify_enforce_slice3_bounded_practice(...)` - a pure classifier helper with zero `self` access and zero `last_debug` writes, returning one of four outcomes: `not_matched`, `be_strong`, `defer_repair`, `strip_followup`.",
            "- Moved rule `R04` (`provide_one_bounded_practice`) from `_enforce_answer_compliance` into the helper, keeping all three `self`-calls (`_set_final_answer_shape_debug`, `_defer_no_stub_repair`, `_strip_optional_followup_invitation`) and the literal `be_strong` response text inline in `writer_agent.py`.",
            "- Boundary note: the PRD's approximate line reference (`666-692`) was stale by 4 lines against live HEAD; the actual block is `666-696`, purely because the `be_strong` literal response is split across 3 string literals in current formatting. The textual boundary markers (opening `if`, closing `return`, and `R07` immediately after) matched the PRD's Step 2/3 code verbatim, so this was recorded as an honest re-verification, not a STOP.",
            "- Confirmed by grep that `practice_anchor_present`, `practice_step_present`, and `practice_multistep` are never read outside the extracted window.",
            "- Kept `R07` (`if literal_markdown_echo:`, historically line 698) untouched immediately below the helper call.",
            "- Added direct tests covering all four classifier outcomes plus a purity/idempotency check.",
            "- Added a historical-before/live-after snapshot runner reusing the APPLY-20 17-case harness by import.",
            "",
            "## Honest Boundary",
            "",
            "- This PRD closes only `R04` of family 2 (`obligation_specific_repairs_before_profile_split`). `R07-R16` (the literal markdown echo plus four obligation-specific repair rules) remain untouched and are the next candidate slice, per law Z-4 (small steps where risk grows with size).",
        ]
    )


def build_next_recommendation() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-23 Next Recommendation",
            "",
            "- recommended_next_prd: `PRD-047.42-APPLY-24 - family 2 continuation (R07-R16)`",
            "- rationale:",
            "  - `R04` is now fully extracted as a pure classifier with full 17-case coverage and zero side effects;",
            "  - `R07-R16` boundaries must be re-verified against live HEAD before cutting, per the same re-verification discipline used in this PRD and in APPLY-21/APPLY-22;",
            "  - if any `R07-R16` rule shares `last_debug` writes with a neighboring rule, the full mechanic (d) from APPLY-22 should be used instead of the simplified classifier mechanic from this PRD.",
        ]
    )


def write_reports(output_dir: Path = OUT_DIR, *, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> dict[str, Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    before_payload = build_before_snapshot(generated_at_utc=generated_at_utc)
    after_payload = build_after_snapshot(generated_at_utc=generated_at_utc)
    before_path = output_dir / "enforce_slice3_snapshot_before.json"
    after_path = output_dir / "enforce_slice3_snapshot_after.json"
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
