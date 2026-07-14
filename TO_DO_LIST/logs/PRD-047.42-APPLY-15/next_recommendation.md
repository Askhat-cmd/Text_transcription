# PRD-047.42-APPLY-15 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-16 - writer_agent.py _call_llm retrieval decision + human-like answer policy + final answer shape slice`
- rationale:
  - this PRD removes the next fully ctx-driven pair of render families from the inline prompt assembly while preserving the intentionally separate `dialogue_profile` `ctx.get(...)` expression;
  - the final render-slice PRD should close the remaining `WRITER_USER_TEMPLATE.format(...)` families before moving to prompt constraint append, runtime settings, provider dispatch, or response unpack;
  - provider dispatch and `_enforce_*` methods remain intentionally deferred until the render spine is closed.
