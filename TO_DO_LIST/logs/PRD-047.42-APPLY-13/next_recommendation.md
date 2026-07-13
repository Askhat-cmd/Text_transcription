# PRD-047.42-APPLY-13 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-14 - writer_agent.py _call_llm fresh_chat_and_context_package + active_line slice`
- rationale:
  - this PRD removes the simplest remaining ctx-only pair of argument families from the inline render with no passthrough exceptions;
  - the next low-risk move is the roadmap pair `fresh_chat_and_context_package + active_line` before touching prompt constraint append, runtime settings, provider dispatch, or response unpack;
  - provider dispatch and `_enforce_*` methods remain intentionally deferred until the render spine shrinks further.
