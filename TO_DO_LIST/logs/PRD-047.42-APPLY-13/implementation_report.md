# PRD-047.42-APPLY-13 Implementation Report

- PRD: `PRD-047.42-APPLY-13`
- Status: `accepted`
- Delivery: `main_commit=3291a40`

## Scope Delivered

- Added `writer_agent_call_llm_slice6.py` with `CallLLMSlice6FinalAnswerDirectiveAndLegacyInputs` and `_extract_call_llm_slice6_final_answer_directive_and_legacy(...)`.
- Moved the mapped `_call_llm` prompt-argument families `final_answer_directive` and `legacy_and_grounding_visibility` out of the inline `WRITER_USER_TEMPLATE.format(...)` call.
- Kept every moved value as an exact copy of the original `ctx.get(..., literal_default)` expression family, with no new dependencies on other locals.
- Added direct unit tests and a runner that proves full-snapshot plus exact `user_prompt` equivalence.
- Main implementation commit was pushed to `origin/main`.

## Verification

- `call_llm_snapshot_before.json == call_llm_snapshot_after.json` byte-for-byte.
- `user_prompt_equivalence.md` confirms `3/3` exact prompt matches with identical SHA1 hashes.
- Direct helper tests passed `3/3`.
- Clean-tree historical contract rerun passed `19/19` across APPLY-6 + APPLY-7 + APPLY-9 + APPLY-10 + APPLY-11 + APPLY-12 + APPLY-13.

## Honest Boundary

- This PRD does not change `WRITER_USER_TEMPLATE` text, prompt ordering, last_debug handling, provider dispatch, response parsing, `writer_contract.py`, or the admin decomposition files.
- The known focused baseline failure `test_semantic_hits_limit_to_two` remains outside this PRD scope and unchanged by the accepted snapshot proof.
