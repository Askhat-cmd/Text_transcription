# PRD-047.42-APPLY-6 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-7 - writer_agent.py _call_llm decomposition slice 1`
- rationale:
  - start with the smallest pre-provider extraction edge identified in this map, not with provider dispatch;
  - the best first cut candidate is the isolated runtime/system-prompt block at `892-901`, optionally together with one or two pure detector/default-formatting helpers earlier in the method;
  - keep `create_agent_completion(...)` plus result parsing for later dedicated PRDs once the preparation block is no longer a single giant mixed method.
