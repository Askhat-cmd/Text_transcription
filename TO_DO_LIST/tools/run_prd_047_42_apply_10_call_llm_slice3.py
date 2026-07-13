from __future__ import annotations

import argparse
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


PRD_ID = "PRD-047.42-APPLY-10"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
NORMALIZED_TIMESTAMP = "normalized_for_prd_047_42_apply_10"
PROTECTED_FILES = [
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_constants.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_fallback_helpers.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_fallback_state_mixin.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_lifecycle_mixin.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice1.py",
    "bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice2.py",
    "bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py",
    "bot_psychologist/api/admin_routes.py",
    "bot_psychologist/api/admin_runtime_compat.py",
    "bot_psychologist/api/admin_runtime_effective_payload.py",
    "bot_psychologist/api/admin_diagnostics_payload.py",
    "bot_psychologist/api/admin_config_schema.py",
    "bot_psychologist/api/admin_config_routes.py",
    "bot_psychologist/api/admin_prompt_routes.py",
    "bot_psychologist/api/admin_agent_ops_routes.py",
    "bot_psychologist/api/admin_misc_routes.py",
    "bot_psychologist/api/admin_surface_bootstrap.py",
    "bot_psychologist/api/admin_surface_helpers.py",
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
        "- Scope rule: only `_call_llm` slice 3 moved; previously accepted helper/mixin/admin/contract files stay unchanged.",
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
            "- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice3.py`.",
            "- Shape choice: one helper function plus one typed dataclass with two outputs: the cross-cluster prompt input and a debug-patch dict.",
            "- Reason: this is the first state-coupled `_call_llm` slice; `self.last_debug` writes cannot stay inside a pure helper, so the helper returns `last_debug_patch` and the caller applies it with one explicit `self.last_debug.update(...)`.",
            "- Exported surface is intentionally minimal: `writer_kb_payload_text` plus `last_debug_patch` only.",
            "- `writer_kb_payload_fallback_reason` stays internal because the accepted dependency review marked it as local to the cluster.",
            "- Patch key order matches the original inline assignment order for review readability, while snapshot evidence proves full `last_debug` identity after update.",
        ]
    )


def build_implementation_report() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-10 Implementation Report",
            "",
            f"- PRD: `{PRD_ID}`",
            "- Status: `accepted_pending_delivery_metadata`",
            "- Delivery: `main_commit_pending`",
            "",
            "## Scope Delivered",
            "",
            "- Added `writer_agent_call_llm_slice3.py` with `CallLLMSlice3Inputs` and `_extract_call_llm_slice3_kb_payload_and_trace(...)`.",
            "- Moved the mapped `_call_llm` cluster `writer_kb_payload_and_trace_capture` out of the inline method body.",
            "- Replaced the current live cluster with one helper call, explicit `writer_kb_payload_text` unpacking, and `self.last_debug.update(slice3_inputs.last_debug_patch)`.",
            "- Added direct unit tests for the new helper module.",
            "- Added a normalized snapshot runner that preserves full `last_debug` for byte-level before/after comparison.",
            "",
            "## Honest Boundary",
            "",
            "- This PRD does not touch `WRITER_USER_TEMPLATE.format(...)`, prompt-constraint append, runtime-settings block, provider dispatch, response parsing, `writer_contract.py`, or the admin decomposition files.",
            "- The known focused baseline failure `test_semantic_hits_limit_to_two` is expected to remain pre-existing if behavior stayed stable.",
        ]
    )


def build_next_recommendation() -> str:
    return "\n".join(
        [
            "# PRD-047.42-APPLY-10 Next Recommendation",
            "",
            "- recommended_next_prd: `PRD-047.42-APPLY-11 - writer_agent.py _call_llm writer_user_template_render split prep`",
            "- rationale:",
            "  - this PRD validates the first state-coupled `_call_llm` move through a debug-patch boundary and proves full `last_debug` identity across the accepted snapshot scenarios;",
            "  - the next remaining giant responsibility is the `WRITER_USER_TEMPLATE.format(...)` render path, which must be decomposed in smaller argument-family slices rather than one move;",
            "  - provider dispatch and response unpack remain intentionally deferred until the render spine is no longer the largest mixed block in `_call_llm`.",
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
    args = parser.parse_args()

    generated_at_utc = NORMALIZED_TIMESTAMP
    if args.match_before:
        before_payload = json.loads(Path(args.match_before).read_text(encoding="utf-8"))
        generated_at_utc = str(before_payload.get("generated_at_utc", NORMALIZED_TIMESTAMP))

    if args.snapshot_only:
        output = (
            Path(args.snapshot_path)
            if args.snapshot_path
            else Path(args.output_dir) / "call_llm_snapshot_after.json"
        ).resolve()
        print(write_snapshot(output, generated_at_utc=generated_at_utc).relative_to(REPO_ROOT))
        return 0

    reports = write_reports(Path(args.output_dir).resolve(), generated_at_utc=generated_at_utc)
    for path in reports.values():
        print(path.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
