# PRD-047.42-APPLY next recommendation

- recommended_next_prd: `PRD-047.42-APPLY-2`
- topic: writer_agent.py decomposition using the accepted PRD-047.42 boundary map and the same snapshot-first discipline
- rationale:
  - `admin_routes.py` is now safely decomposed with `0` route-level behavior drift
  - the remaining high-risk god files are still `writer_agent.py` and `writer_contract.py`
  - `writer_agent.py` should go before `writer_contract.py` only if the project wants to keep prompt-shape serialization (`WriterContract.to_prompt_context`) for the most conservative final step

- alternative_next_prd: `PRD-047.42b`
- alternative_topic: `diagnostic_center_* boundary mapping`
- alternative_rationale:
  - choose this instead if the goal is to finish all remaining Stage-1 maps before any further runtime decomposition
