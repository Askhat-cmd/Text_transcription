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
from bot_agent.multiagent.agents.writer_agent_enforce_slice7 import EnforceBlockBPart2Result


PRD_ID = "PRD-047.42-APPLY-28"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
NORMALIZED_TIMESTAMP = "normalized_for_prd_047_42_apply_28"
HISTORICAL_HEAD = "c4a447a7"
WRITER_AGENT_REL_PATH = "bot_psychologist/bot_agent/multiagent/agents/writer_agent.py"
WRITER_AGENT_PATH = REPO_ROOT / WRITER_AGENT_REL_PATH
APPLY_20_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-20"
APPLY_21_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-21"
APPLY_22_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-22"
APPLY_23_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-23"
APPLY_24_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-24"
APPLY_25_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-25"
APPLY_26_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-26"
APPLY_27_LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.42-APPLY-27"
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
]
EXPECTED_FIELD_ORDER = [
    "outcome",
    "return_text",
]
EXPECTED_OUTCOMES = [
    "not_matched",
    "mechanism_explanation_repair_g7",
    "one_step_g8",
    "first_item_extraction_g9",
    "sentence_parts_one_step_g9",
    "question_marker_one_step_g9",
    "no_step_marker_one_step_g9",
    "safety_grounding_g10",
    "active_line_correction_repair_g10",
    "active_line_mechanism_repair_g10",
    "practice_suppression_meaning_repair_g10",
    "active_line_revoicing_correction_repair_g11",
    "active_line_revoicing_mechanism_repair_g11",
    "revoicing_strip_g11",
    "known_concept_correlation_repair_g12",
    "known_concept_neurostalking_repair_g12",
    "known_concept_self_realization_repair_g12",
]
BLOCK_B_PART2_HISTORICAL_START_LINE = 883
BLOCK_B_PART2_HISTORICAL_END_LINE = 999
METHOD_END_HISTORICAL_LINE = 1000


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
    module_name = f"bot_agent.multiagent.agents._prd_047_42_apply_28_before_{HISTORICAL_HEAD}"
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
        "schema_version": "prd_047_42_apply_28_enforce_slice7_snapshot_v1",
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
    prior_log_dirs = [
        APPLY_20_LOG_DIR,
        APPLY_21_LOG_DIR,
        APPLY_22_LOG_DIR,
        APPLY_23_LOG_DIR,
        APPLY_24_LOG_DIR,
        APPLY_25_LOG_DIR,
        APPLY_26_LOG_DIR,
        APPLY_27_LOG_DIR,
    ]
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
        f"- APPLY-20..27 logs diff result: `{len(prior_log_changed)} changed paths`",
        "",
        "## Protected Diff Result",
        "",
        "- `git diff --name-only -- <protected files>` returned empty output."
        if not protected_changed
        else "- Unexpected protected diffs detected.",
        "",
        "## Prior PRD Log Immutability",
        "",
        "- `git diff --name-only -- TO_DO_LIST/logs/PRD-047.42-APPLY-20 .. PRD-047.42-APPLY-27` returned empty output."
        if not prior_log_changed
        else "- Unexpected APPLY-20..27 log diffs detected.",
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
    method_end_line = historical_lines[METHOD_END_HISTORICAL_LINE - 1]
    method_end_untouched_marker = method_end_line.strip() == "return text"
    self_call_lines = [
        f"{BLOCK_B_PART2_HISTORICAL_START_LINE + offset}: {line}"
        for offset, line in enumerate(
            historical_lines[BLOCK_B_PART2_HISTORICAL_START_LINE - 1 : BLOCK_B_PART2_HISTORICAL_END_LINE]
        )
        if "self." in line
    ]
    last_debug_lines = [
        f"{BLOCK_B_PART2_HISTORICAL_START_LINE + offset}: {line}"
        for offset, line in enumerate(
            historical_lines[BLOCK_B_PART2_HISTORICAL_START_LINE - 1 : BLOCK_B_PART2_HISTORICAL_END_LINE]
        )
        if "self.last_debug" in line
    ]
    lines = [
        "# Grep Proof",
        "",
        f"- PRD: `{PRD_ID}`",
        f"- Historical source revision checked: `{HISTORICAL_HEAD}`",
        f"- Historical Block B Part 2 window checked: lines `{BLOCK_B_PART2_HISTORICAL_START_LINE}-{BLOCK_B_PART2_HISTORICAL_END_LINE}`",
        f"- `self.last_debug` direct writes found in window: `{len(last_debug_lines)}` (expected: 0 - the method's only direct write was closed in APPLY-27)",
        f"- `self.` lines found in window: `{len(self_call_lines)}`",
        f"- Historical line `{METHOD_END_HISTORICAL_LINE}` is exactly `return text` (method end, untouched): `{method_end_untouched_marker}`",
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
            "# PRD-047.42-APPLY-28 Implementation Report",
            "",
            f"- PRD: `{PRD_ID}`",
            "- Status: `accepted_pending_delivery_metadata`",
            "- Delivery: `main_commit_pending`",
            "",
            "## Scope Delivered",
            "",
            "- Added `writer_agent_enforce_slice7.py` with `EnforceBlockBPart2Result` and `_classify_enforce_block_b_part2(...)` - a pure classifier helper (no `self` access) returning one of seventeen tags (16 significant outcomes plus `not_matched`).",
            "- Moved Block B Part 2 (`883-999`, groups 7-12: `mechanism_explanation_repair`, the one-step cascade including first-list-item extraction, active-line practice-suppression repairs, mechanical-revoicing repairs, and the third known-concept signal cluster) from `_enforce_answer_compliance` into the helper.",
            "- Group 9's nested 'maybe-return inside maybe-return' pattern is preserved exactly: `if list_like:` wraps `if first_item:` with no `else` at either level, so `list_like=True` with `first_item=None` (e.g. a bare list marker with no content) falls through to the `sentence_parts` check instead of exiting the group - verified by a dedicated edge-case test.",
            "- `not_matched` is not dispatched at all in `writer_agent.py` - there is no corresponding `if`, so control falls through directly to the pre-existing `return text` at line 1000 (unchanged, the physical end of the method).",
            "- Called the module-level (non-`self`) `starts_with_mechanical_revoicing` function directly inside the helper via `from ..active_line import starts_with_mechanical_revoicing` - no circular import, matching `writer_agent.py`'s own import path.",
            "- Kept all `self`-methods (`_defer_no_stub_repair`, `_resolve_one_step_or_no_practice_fallback`) exclusively on the call site; the helper never calls or receives them.",
            "- Preserved four distinct 'one-step-like' classifier tags (`one_step_g8`, `sentence_parts_one_step_g9`, `question_marker_one_step_g9`, `no_step_marker_one_step_g9`) that dispatch to the same `self`-call with identical arguments, merged only at the call site.",
            "- `first_item_extraction_g9` and `revoicing_strip_g11` compute `return_text` inside the helper, matching the original inline computations exactly.",
            "- Added direct tests covering all 16 significant outcomes, `not_matched` with correct final dispatch to `return text`, the group 9 edge case, `return_text` computation for both computed outcomes, and a group 8 vs. group 9 priority-resolution case.",
            "- Added a historical-before/live-after snapshot runner reusing the APPLY-20 17-case harness by import.",
            "",
            "## Honest Boundary",
            "",
            "- This PRD closes Block B in full. The entire `_enforce_answer_compliance` method (`576-1000` at this HEAD) is now fully decomposed. The next boundary is a different method entirely: `_enforce_mvp_free_dialogue_compliance`, which has not been mapped at all and needs its own from-scratch reconnaissance.",
        ]
    )


def build_next_recommendation() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-28 Next Recommendation",
            "",
            "- recommended_next_prd: `PRD-047.42-APPLY-29 (or a boundary-mapping PRD) - _enforce_mvp_free_dialogue_compliance boundary mapping`",
            "- rationale:",
            "  - `_enforce_answer_compliance` decomposition is now complete across all APPLY-21..28 slices; there is no more content to extract from that method;",
            "  - `_enforce_mvp_free_dialogue_compliance` (a separate method, ~225 lines at last estimate before this PRD) has never been mapped - assumptions about its structure should not be carried over from `_enforce_answer_compliance`'s decomposition, per the project's standing 'no map trust without fresh reconnaissance' principle (the APPLY-20 map itself underestimated family widths twice);",
            "  - once that method closes, the lightweight Epoch 2 gate (owner decision #4) opens on Scenario A completion, pending confirmation that no hidden complexity surfaces during that method's reconnaissance.",
        ]
    )


def write_reports(output_dir: Path = OUT_DIR, *, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> dict[str, Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    before_payload = build_before_snapshot(generated_at_utc=generated_at_utc)
    after_payload = build_after_snapshot(generated_at_utc=generated_at_utc)
    before_path = output_dir / "enforce_slice7_snapshot_before.json"
    after_path = output_dir / "enforce_slice7_snapshot_after.json"
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
