# PRD-047.42-APPLY-10 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-11 - writer_agent.py _call_llm writer_user_template_render split prep`
- rationale:
  - this PRD validates the first state-coupled `_call_llm` move through a debug-patch boundary and proves full `last_debug` identity across the accepted snapshot scenarios;
  - the next remaining giant responsibility is the `WRITER_USER_TEMPLATE.format(...)` render path, which must be decomposed in smaller argument-family slices rather than one move;
  - provider dispatch and response unpack remain intentionally deferred until the render spine is no longer the largest mixed block in `_call_llm`.
