# PRD-047.42-APPLY-13 Implementation Report

- PRD: `PRD-047.42-APPLY-13`
- Status: `accepted_pending_delivery_metadata`
- Delivery: `main_commit_pending`

## Scope Delivered

- Added `writer_agent_call_llm_slice6.py` with `CallLLMSlice6FinalAnswerDirectiveAndLegacyInputs` and `_extract_call_llm_slice6_final_answer_directive_and_legacy(...)`.
- Moved the mapped `_call_llm` prompt-argument families `final_answer_directive` and `legacy_and_grounding_visibility` out of the inline `WRITER_USER_TEMPLATE.format(...)` call.
- Kept every moved value as an exact copy of the original `ctx.get(..., literal_default)` expression family, with no new dependencies on other locals.
- Added direct unit tests and a runner that proves full-snapshot plus exact `user_prompt` equivalence.

## Honest Boundary

- This PRD does not change `WRITER_USER_TEMPLATE` text, prompt ordering, last_debug handling, provider dispatch, response parsing, `writer_contract.py`, or the admin decomposition files.
- The known focused baseline failure `test_semantic_hits_limit_to_two` is expected to remain pre-existing if behavior stayed stable.
