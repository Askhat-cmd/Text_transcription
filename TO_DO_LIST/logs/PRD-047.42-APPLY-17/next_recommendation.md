# PRD-047.42-APPLY-17 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-18 - writer_agent.py _call_llm runtime settings + system prompt selection slice`
- rationale:
  - this PRD removes the prompt-constraint append and ordered debug-bookkeeping cluster immediately after the render call boundary;
  - the next bounded move should target `runtime_settings_and_system_prompt_selection`, including the post-render `dialogue_profile` normalization seam, before provider dispatch or response unpack/return logic;
  - provider dispatch, response parsing, and `_enforce_*` methods remain intentionally deferred until the remaining `_call_llm` clusters are cut in order.
