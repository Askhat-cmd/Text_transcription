# PRD-047.42-APPLY-18 Implementation Report

- PRD: `PRD-047.42-APPLY-18`
- Status: `accepted_with_warning`
- Delivery: `main_commit_pending`

## Scope Delivered

- Added `writer_agent_call_llm_slice11.py` with `CallLLMSlice11RuntimeSettingsAndSystemPromptResult` and `_apply_call_llm_slice11_runtime_settings_and_system_prompt(...)`.
- Moved the post-render `_call_llm` cluster that reassigns `dialogue_profile`, resolves runtime settings, selects `system_prompt`, and records ordered prompt/debug bookkeeping out of the inline method body.
- Kept the one ordered `last_debug_patch` exact, including the insertion order of the `2` keys and the keyword-call boundary into `_resolve_runtime_settings`.
- Removed `WRITER_SYSTEM` and `WRITER_SYSTEM_MVP_FREE_DIALOGUE` from `writer_agent.py` if and only if the helper module became their only remaining user there.
- Added direct unit tests and a runner that prove both `system_prompt` branches plus full-snapshot and exact `user_prompt` equivalence.

## Honest Boundary

- This PRD does not change `WRITER_USER_TEMPLATE` text, prompt-constraint logic, provider dispatch, response parsing, `_enforce_*` methods, `writer_agent_lifecycle_mixin.py`, `writer_agent_prompts.py`, `writer_contract.py`, or the admin decomposition files.
- The accepted snapshot harness still proves the same exact prompt surface and full `last_debug`; the namesake reassignment and callable semantics are covered explicitly by direct helper tests in this PRD.
- The canonical broad writer subset is environment-sensitive in the owner workspace: a direct owner-workspace rerun currently reports `14 failed, 215 passed, 2007 deselected, 346 warnings`, because `5` previously known failing writer tests pass under the full local sibling-workspace context.
- The required isolated baseline was still reproduced on a clean worktree carrying the same APPLY-18 tracked source/test files: `19 failed, 210 passed, 2007 deselected, 190 warnings`, with the same `19` known failure ids named by the PRD.

## Verification

- direct slice-11 helper tests passed `3/3`.
- slice-11 contract runner tests passed `3/3`.
- `py_compile` passed for `writer_agent.py`, `writer_agent_call_llm_slice11.py`, and `run_prd_047_42_apply_18_call_llm_slice11.py`.
- `call_llm_snapshot_before.json == call_llm_snapshot_after.json` is byte-identical.
- `user_prompt_equivalence.md` confirms byte-identical exact prompt text and matching SHA1 values across all `3` accepted scenarios.
- `no_mutation_proof.md` reports `0 changed paths` across the `16` protected files, including unchanged `writer_agent_lifecycle_mixin.py` and `writer_agent_prompts.py`.
- zero-match grep confirmed that `WRITER_SYSTEM` and `WRITER_SYSTEM_MVP_FREE_DIALOGUE` have no remaining direct usage in `writer_agent.py` after extraction.
- clean isolated broad writer rerun reproduced the required `19` known pre-existing failures.
- clean-tree historical APPLY-6..18 contract rerun is deferred to the post-commit clean-tree verification pass because APPLY-6 self-checks its own no-mutation proof and sees the main workspace diff before the implementation commit exists.
