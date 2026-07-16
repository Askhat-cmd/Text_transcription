# PRD-047.42-APPLY-18 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-19 - writer_agent.py _call_llm provider dispatch slice`
- rationale:
  - this PRD removes the runtime-settings and system-prompt-selection cluster immediately before provider dispatch;
  - the next bounded move should target the standalone async `create_agent_completion(...)` dispatch cluster before the response-unpack/cost/return tail;
  - response parsing, cost accounting, and `_enforce_*` methods remain intentionally deferred until the remaining `_call_llm` clusters are cut in order.
