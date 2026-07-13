# PRD-047.42-APPLY-14 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-15 - writer_agent.py _call_llm response_planner + dialogue_profile_and_pragmatics slice`
- rationale:
  - this PRD removes the next fully ctx-driven pair of render families from the inline prompt assembly with no passthrough exceptions;
  - the next low-risk move is the roadmap pair `response_planner + dialogue_profile_and_pragmatics` before touching retrieval decision, human-like answer policy, prompt constraint append, runtime settings, provider dispatch, or response unpack;
  - provider dispatch and `_enforce_*` methods remain intentionally deferred until the render spine shrinks further.
