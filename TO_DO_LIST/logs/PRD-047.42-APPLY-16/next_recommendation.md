# PRD-047.42-APPLY-16 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-17 - writer_agent.py _call_llm prompt constraint append + debug bookkeeping slice`
- rationale:
  - this PRD closes the full `WRITER_USER_TEMPLATE.format(...)` decomposition series and leaves the next low-risk `_call_llm` cluster immediately after the render call boundary;
  - the next bounded move should target `prompt_constraint_append_and_debug_bookkeeping` before runtime settings, provider dispatch, or response unpack/return logic;
  - provider dispatch, response parsing, and `_enforce_*` methods remain intentionally deferred until the remaining `_call_llm` clusters are cut in order.
