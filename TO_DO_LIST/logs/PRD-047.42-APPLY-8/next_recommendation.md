# PRD-047.42-APPLY-8 Next Recommendation

- recommended_next_prd: `continue _call_llm decomposition with the next mapped pre-provider cluster`
- rationale:
  - the stale structural test debt from APPLY-6 is now closed and should not block further `_call_llm` slices;
  - before the next real slice, refresh the live line bounds of `request_detectors_and_mvp_override_block` (or the chosen next cluster) against the current `writer_agent.py`, because APPLY-7 already shortened `_call_llm`;
  - keep provider dispatch and response parsing deferred until the prompt-preparation body is no longer one giant mixed block.
