# PRD-047.42 Next Recommendation

- If PRD-047.42 is accepted, open a follow-up decomposition PRD that moves one boundary block at a time with unchanged signatures and pre-recorded snapshot contracts.
- Keep `admin_routes.py` split separate from `writer_agent.py`; they have different blast radii and different caller graphs.
- Keep `writer_contract.to_prompt_context` decomposition especially conservative because it is the highest fan-out contract surface in the three-file set.
