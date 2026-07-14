# PRD-047.42-APPLY-15 Implementation Report

- PRD: `PRD-047.42-APPLY-15`
- Status: `accepted_pending_delivery_metadata`
- Delivery: `main_commit_pending`

## Scope Delivered

- Added `writer_agent_call_llm_slice8.py` with `CallLLMSlice8ResponsePlannerAndDialoguePragmaticsInputs` and `_extract_call_llm_slice8_response_planner_and_dialogue_pragmatics(...)`.
- Moved the mapped `_call_llm` prompt-argument families `response_planner` and `dialogue_profile_and_pragmatics` out of the inline `WRITER_USER_TEMPLATE.format(...)` call.
- Kept every moved value as an exact copy of the original `ctx.get(..., literal_default)` expression family, including the intentionally separate `dialogue_profile` `ctx.get(...)` expression inside this slice.
- Added direct unit tests and a runner that proves full-snapshot plus exact `user_prompt` equivalence.

## Honest Boundary

- This PRD does not change `WRITER_USER_TEMPLATE` text, prompt ordering, last_debug handling, provider dispatch, response parsing, `writer_contract.py`, or the admin decomposition files.
- The known focused baseline failure `test_semantic_hits_limit_to_two` is expected to remain pre-existing if behavior stayed stable.
