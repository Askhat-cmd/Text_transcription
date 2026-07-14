# Extraction Log

- PRD: `PRD-047.42-APPLY-15`
- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice8.py`.
- Shape choice: one helper function plus one typed dataclass with the `30` computed values from the mapped slice-8 argument families.
- Boundary rule: there are no passthrough exceptions here; every mapped kwarg is still computed through `ctx.get(..., literal_default)` logic and therefore belongs inside the helper.
- Semantic trap preserved exactly: `dialogue_profile` in this slice remains a fresh `ctx.get("dialogue_profile", "safe_guided") or "safe_guided"` expression inside the helper, not a reuse of the earlier local variable with the same name.
- Integration rule: `_call_llm` adds one helper call after `slice7_inputs`, then uses explicit `slice8_inputs.<field>` references with no `locals()` mutation and no prompt-template rewrite.
