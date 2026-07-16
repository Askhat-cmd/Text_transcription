from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BOT_ROOT = REPO_ROOT / "bot_psychologist"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from TO_DO_LIST.tools import run_prd_047_42_apply_6_call_llm_boundary_mapping as baseline_runner


PRD_ID = "PRD-047.42-APPLY-19"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
NORMALIZED_TIMESTAMP = "normalized_for_prd_047_42_apply_19"
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
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_fallback_state_mixin.py",
    "bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py",
]


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def build_normalized_snapshot(*, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> dict[str, Any]:
    payload = baseline_runner.asyncio.run(baseline_runner.build_snapshot_baseline())
    payload["generated_at_utc"] = generated_at_utc
    return payload


def write_snapshot(path: Path, *, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> Path:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            build_normalized_snapshot(generated_at_utc=generated_at_utc),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _hash_prompt(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _first_line_diff(before_text: str, after_text: str) -> str:
    before_lines = before_text.splitlines()
    after_lines = after_text.splitlines()
    for index, (before_line, after_line) in enumerate(zip(before_lines, after_lines), start=1):
        if before_line != after_line:
            return f"line {index}: before={before_line!r} after={after_line!r}"
    if len(before_lines) != len(after_lines):
        return f"line-count mismatch: before={len(before_lines)} after={len(after_lines)}"
    return "no difference"


def compare_snapshot_payloads(before_payload: dict[str, Any], after_payload: dict[str, Any]) -> dict[str, Any]:
    before_cases = {case["case"]: case for case in before_payload.get("cases", [])}
    after_cases = {case["case"]: case for case in after_payload.get("cases", [])}
    case_names = sorted(set(before_cases) | set(after_cases))
    cases: list[dict[str, Any]] = []
    all_user_prompts_match = True
    for case_name in case_names:
        before_case = before_cases.get(case_name, {})
        after_case = after_cases.get(case_name, {})
        before_prompt = str(before_case.get("last_debug", {}).get("user_prompt", ""))
        after_prompt = str(after_case.get("last_debug", {}).get("user_prompt", ""))
        prompt_match = before_prompt == after_prompt
        all_user_prompts_match = all_user_prompts_match and prompt_match
        cases.append(
            {
                "case": case_name,
                "user_prompt_match": prompt_match,
                "before_user_prompt_sha1": _hash_prompt(before_prompt),
                "after_user_prompt_sha1": _hash_prompt(after_prompt),
                "before_user_prompt_line_count": len(before_prompt.splitlines()),
                "after_user_prompt_line_count": len(after_prompt.splitlines()),
                "first_diff": _first_line_diff(before_prompt, after_prompt),
            }
        )
    return {
        "snapshot_byte_identical": before_payload == after_payload,
        "all_user_prompts_match": all_user_prompts_match,
        "cases": cases,
    }


def build_user_prompt_equivalence_report(before_payload: dict[str, Any], after_payload: dict[str, Any]) -> str:
    comparison = compare_snapshot_payloads(before_payload, after_payload)
    lines = [
        "# User Prompt Equivalence",
        "",
        f"- PRD: `{PRD_ID}`",
        f"- Full snapshot byte identical: `{comparison['snapshot_byte_identical']}`",
        f"- All `user_prompt` values identical: `{comparison['all_user_prompts_match']}`",
        "",
        "| case | prompt_match | before_sha1 | after_sha1 | before_lines | after_lines | first_diff |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in comparison["cases"]:
        lines.append(
            "| {case} | {user_prompt_match} | `{before_user_prompt_sha1}` | `{after_user_prompt_sha1}` | {before_user_prompt_line_count} | {after_user_prompt_line_count} | {first_diff} |".format(
                **case
            )
        )
    return "\n".join(lines)


def build_no_mutation_proof() -> str:
    diff_proc = subprocess.run(
        ["git", "diff", "--name-only", "--", *PROTECTED_FILES],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    changed = [line.strip() for line in diff_proc.stdout.splitlines() if line.strip()]
    hash_lines: list[str] = []
    for rel_path in PROTECTED_FILES:
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
        hash_lines.append(f"- `{rel_path}` -> `{proc.stdout.strip()}`")

    lines = [
        "# No Mutation Proof",
        "",
        f"- PRD: `{PRD_ID}`",
        "- Scope rule: only the final response-unpack / cost / debug-tail cluster moved; provider dispatch stays inline and protected helpers remain unchanged.",
        f"- Protected files checked: `{len(PROTECTED_FILES)}`",
        f"- Protected diff result: `{len(changed)} changed paths`",
        "",
    ]
    if changed:
        lines.extend(["## Unexpected Protected Diffs", ""])
        lines.extend(f"- `{path}`" for path in changed)
        lines.append("")
    else:
        lines.extend(
            [
                "## Protected Diff Result",
                "",
                "- `git diff --name-only -- <protected files>` returned empty output.",
                "",
            ]
        )
    lines.extend(["## Protected Blob Hashes", "", *hash_lines])
    return "\n".join(lines)


def build_extraction_log() -> str:
    return "\n".join(
        [
            "# Extraction Log",
            "",
            f"- PRD: `{PRD_ID}`",
            "- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice12.py`.",
            "- Shape choice: one helper function plus one frozen dataclass result carrying the original `result.text` object and one ordered `13`-key `last_debug_patch` dictionary.",
            "- Timing rule: helper imports the module `time` and calls `time.perf_counter()` directly so the snapshot harness can keep monkeypatching the shared module attribute and forcing `duration_ms=123`.",
            "- Callable rule: helper does not know about `self`; `_call_llm` passes `self._estimate_cost` as a bound callable and the helper invokes it once with the exact keyword arguments `tokens_prompt=` and `tokens_completion=`.",
            "- Boundary rule: `await create_agent_completion(...)` and `return llm_response` stay inline in `_call_llm` exactly as required by owner decision #3 and this PRD.",
            "- Order rule: the `13` debug keys stay in original insertion order so snapshot JSON bytes remain stable.",
        ]
    )


def build_implementation_report() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-19 Implementation Report",
            "",
            f"- PRD: `{PRD_ID}`",
            "- Status: `accepted_pending_delivery_metadata`",
            "- Delivery: `main_commit_pending`",
            "",
            "## Scope Delivered",
            "",
            "- Added `writer_agent_call_llm_slice12.py` with `CallLLMSlice12ResponseUnpackAndCostResult` and `_apply_call_llm_slice12_response_unpack_cost_and_bookkeeping(...)`.",
            "- Moved the final `_call_llm` cluster that unpacks the provider result, extracts `tokens_*`, estimates cost, computes `duration_ms`, and assembles the ordered `last_debug` tail patch.",
            "- Kept `await create_agent_completion(...)` inline, kept `return llm_response` inline, and preserved the exact `13` patch keys plus the exact keyword-call boundary into `_estimate_cost`.",
            "- Added direct unit tests and a runner that prove full snapshot identity, exact `user_prompt` identity, deterministic `duration_ms=123`, and protected-file non-mutation.",
            "",
            "## Honest Boundary",
            "",
            "- This PRD does not change prompts, provider dispatch, `_enforce_*` methods, `writer_agent_fallback_state_mixin.py`, `writer_agent_lifecycle_mixin.py`, `writer_contract.py`, or the admin decomposition files.",
            "- The canonical broad writer subset outcome must be recorded honestly after implementation; this report starts in pending-delivery state until the wider verification is captured.",
            "- After accepted delivery of this PRD, `_call_llm` is considered structurally complete and the next default track becomes boundary mapping for `_enforce_answer_compliance`.",
        ]
    )


def build_next_recommendation() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-19 Next Recommendation",
            "",
            "- recommended_next_prd: `PRD-047.42-APPLY-20 - writer_agent.py _enforce_answer_compliance boundary mapping`",
            "- rationale:",
            "  - APPLY-19 closes the final movable cluster of `_call_llm`; provider dispatch intentionally stays inline by owner decision #3;",
            "  - the next high-risk giant method in the Scenario A line is `_enforce_answer_compliance`, so the safe next step is a read-only boundary-mapping PRD before any code transfer;",
            "  - `_enforce_mvp_free_dialogue_compliance` should remain behind `_enforce_answer_compliance` in that sequence.",
        ]
    )


def write_reports(output_dir: Path = OUT_DIR, *, generated_at_utc: str = NORMALIZED_TIMESTAMP) -> dict[str, Path]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = {
        "snapshot": write_snapshot(output_dir / "call_llm_snapshot_after.json", generated_at_utc=generated_at_utc),
        "no_mutation": output_dir / "no_mutation_proof.md",
        "extraction": output_dir / "extraction_log.md",
        "implementation": output_dir / "implementation_report.md",
        "next": output_dir / "next_recommendation.md",
    }
    _write_text(reports["no_mutation"], build_no_mutation_proof())
    _write_text(reports["extraction"], build_extraction_log())
    _write_text(reports["implementation"], build_implementation_report())
    _write_text(reports["next"], build_next_recommendation())
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--snapshot-only", action="store_true")
    parser.add_argument("--snapshot-path", default="")
    parser.add_argument("--match-before", default="")
    parser.add_argument("--comparison-report", default="")
    args = parser.parse_args()

    generated_at_utc = NORMALIZED_TIMESTAMP
    before_payload: dict[str, Any] | None = None
    if args.match_before:
        before_payload = json.loads(Path(args.match_before).read_text(encoding="utf-8"))
        generated_at_utc = str(before_payload.get("generated_at_utc", NORMALIZED_TIMESTAMP))

    if args.snapshot_only:
        output = (
            Path(args.snapshot_path)
            if args.snapshot_path
            else Path(args.output_dir) / "call_llm_snapshot_after.json"
        ).resolve()
        write_snapshot(output, generated_at_utc=generated_at_utc)
        if before_payload is not None:
            after_payload = json.loads(output.read_text(encoding="utf-8"))
            comparison = compare_snapshot_payloads(before_payload, after_payload)
            if args.comparison_report:
                _write_text(
                    Path(args.comparison_report).resolve(),
                    build_user_prompt_equivalence_report(before_payload, after_payload),
                )
            if not comparison["snapshot_byte_identical"]:
                print(output.relative_to(REPO_ROOT))
                return 1
        print(output.relative_to(REPO_ROOT))
        return 0

    reports = write_reports(Path(args.output_dir).resolve(), generated_at_utc=generated_at_utc)
    for path in reports.values():
        print(path.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
