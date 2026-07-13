# PRD-047.42-APPLY-12 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-13 - writer_agent.py _call_llm final_answer_directive + legacy_and_grounding_visibility slice`
- rationale:
  - this PRD removes the second pair of computed argument families from the inline render while keeping the mandatory passthrough kwargs in place;
  - the next low-risk move is the adjacent family pair already named in the roadmap, before touching runtime settings, provider dispatch, or response unpack;
  - provider dispatch and `_enforce_*` methods remain intentionally deferred until the render spine shrinks further.
