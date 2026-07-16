# PRD-047.42-APPLY-16 Implementation Report

- PRD: `PRD-047.42-APPLY-16`
- Status: `accepted_pending_delivery_metadata`
- Delivery: `main_commit_pending`

## Scope Delivered

- Added `writer_agent_call_llm_slice9.py` with `CallLLMSlice9RetrievalHumanLikeAndFinalShapeInputs` and `_extract_call_llm_slice9_retrieval_human_like_and_final_shape(...)`.
- Moved the mapped `_call_llm` prompt-argument families `retrieval_decision`, `human_like_answer_policy`, and `final_answer_shape_and_constraint_resolution` out of the inline `WRITER_USER_TEMPLATE.format(...)` call.
- Kept the mirrored trap exact: `constraint_resolution_profile` still uses the passed local `dialogue_profile` as its default instead of a fresh `ctx.get(...)` lookup.
- Kept `mvp_free_dialogue_overrides=mvp_override_block` inline as the mandated pure passthrough that closes the render series without widening the helper surface.
- Added direct unit tests and a runner that proves full-snapshot plus exact `user_prompt` equivalence.
- Closed the full `WRITER_USER_TEMPLATE.format(...)` extraction roadmap from APPLY-11 through APPLY-16; only passthrough/core-required-field remnants remain inside the render call.

## Honest Boundary

- This PRD does not change `WRITER_USER_TEMPLATE` text, prompt ordering, last_debug handling, prompt-constraint append logic, runtime settings, provider dispatch, response parsing, `writer_contract.py`, or the admin decomposition files.
- Focused slice proofs are green, but the broad writer subset currently reports `12 failed, 211 passed, 346 warnings` with `PYTHONPATH=bot_psychologist`; those failures are outside the touched slice-9 surface and are recorded as current suite background rather than evidence of prompt-render regression.
- The known focused baseline failure `test_semantic_hits_limit_to_two` remains part of that broader background and is not introduced by this PRD.
- This PRD closes the `WRITER_USER_TEMPLATE.format(...)` extraction roadmap only; the remaining `_call_llm` clusters stay out of scope.
