# PRD-047.42-APPLY-17 Implementation Report

- PRD: `PRD-047.42-APPLY-17`
- Status: `accepted_with_warning`
- Delivery: `main_commit_pending`

## Scope Delivered

- Added `writer_agent_call_llm_slice10.py` with `CallLLMSlice10PromptConstraintAndDebugBookkeepingResult` and `_apply_call_llm_slice10_prompt_constraint_and_debug_bookkeeping(...)`.
- Moved the post-render `_call_llm` cluster that conditionally appends `prompt_section` and records ordered prompt/debug bookkeeping out of the inline method body.
- Kept the one ordered `last_debug_patch` exact, including the insertion order of all `18` keys and the by-reference `overruled_constraints` passthrough.
- Removed the direct `format_prompt_constraint_section_v1` import from `writer_agent.py` because the helper module becomes its only remaining user.
- Added direct unit tests and a runner that prove both prompt-section branches plus full-snapshot and exact `user_prompt` equivalence.

## Honest Boundary

- This PRD does not change `WRITER_USER_TEMPLATE` text, render kwargs, runtime settings, provider dispatch, response parsing, `_enforce_*` methods, `writer_contract.py`, or the admin decomposition files.
- The accepted snapshot harness still exercises only the no-append branch; the append branch is covered explicitly by direct helper tests in this PRD.
- The canonical broad writer subset is environment-sensitive in the owner workspace: a direct owner-workspace rerun currently reports `14 failed, 212 passed, 2004 deselected, 346 warnings`, because `5` previously known failing writer tests pass under the full local sibling-workspace context.
- The required clean baseline was still reproduced on an isolated clean worktree carrying the same APPLY-17 tracked source/test files: `19 failed, 207 passed, 2004 deselected, 190 warnings`, with the same `19` known failure ids named by the PRD.

## Verification

- direct slice-10 helper tests passed `3/3`.
- slice-10 contract runner tests passed `3/3`.
- `py_compile` passed for `writer_agent.py`, `writer_agent_call_llm_slice10.py`, and `run_prd_047_42_apply_17_call_llm_slice10.py`.
- `call_llm_snapshot_before.json == call_llm_snapshot_after.json` is byte-identical.
- `user_prompt_equivalence.md` confirms byte-identical exact prompt text and matching SHA1 values across all `3` accepted scenarios.
- `no_mutation_proof.md` reports `0 changed paths` across the `25` protected files.
- `rg -n "format_prompt_constraint_section_v1" bot_psychologist/bot_agent/multiagent/agents/writer_agent.py` returned no matches after extraction, so the direct import was removed legitimately.
- clean isolated broad writer rerun reproduced the required `19` known pre-existing failures.
- clean-tree historical APPLY-6..17 contract rerun is deferred to the post-commit clean-tree verification pass because APPLY-6 self-checks its own no-mutation proof and sees the main workspace diff before the implementation commit exists.
