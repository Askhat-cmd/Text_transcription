# PRD-047.42-APPLY-11 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-12 - writer_agent.py _call_llm prompt-argument slice 5`
- rationale:
  - this PRD proves the first large argument-family extraction inside `WRITER_USER_TEMPLATE.format(...)` can stay byte-identical on full snapshot and exact `user_prompt` evidence;
  - the next low-risk argument families remain the already-computed writer KB / knowledge / philosophy / freedom values, which should also be moved as explicit builder outputs rather than touching the template itself;
  - provider dispatch, response unpack, and `_enforce_*` methods remain intentionally deferred until the render spine shrinks further.
