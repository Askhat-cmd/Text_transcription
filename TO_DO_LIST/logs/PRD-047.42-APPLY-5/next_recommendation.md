# PRD-047.42-APPLY-5 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-6 - writer_agent.py _call_llm decomposition slice 1`
- rationale:
  - the lifecycle spine is now extracted, so the largest remaining active `writer_agent.py` risk is `_call_llm`;
  - `_call_llm` is still the biggest remaining method at roughly `803` lines and mixes prompt-context normalization, retrieval payload shaping, runtime settings usage, provider dispatch, and trace bookkeeping;
  - unlike the slice completed here, `_call_llm` should not be moved as one block.

- recommended_split_order:
  1. isolate the lowest-risk pure/default-seeding and formatting helpers first;
  2. keep provider dispatch and response parsing for a later dedicated slice;
  3. leave `_enforce_answer_compliance` and `writer_contract.to_prompt_context` out of scope until `_call_llm` is no longer a giant mixed method.
