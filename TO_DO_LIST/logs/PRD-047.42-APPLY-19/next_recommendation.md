# PRD-047.42-APPLY-19 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-20 - writer_agent.py _enforce_answer_compliance boundary mapping`
- rationale:
  - APPLY-19 closes the final movable cluster of `_call_llm`; provider dispatch intentionally stays inline by owner decision #3;
  - the next high-risk giant method in the Scenario A line is `_enforce_answer_compliance`, so the safe next step is a read-only boundary-mapping PRD before any code transfer;
  - `_enforce_mvp_free_dialogue_compliance` should remain behind `_enforce_answer_compliance` in that sequence.
