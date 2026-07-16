# Extraction Log

- PRD: `PRD-047.42-APPLY-16`
- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice9.py`.
- Shape choice: one helper function plus one typed dataclass with the `33` computed values from the final mapped render families.
- Boundary rule: `mvp_free_dialogue_overrides=mvp_override_block` remains inline because it is a pure passthrough and not a computation target.
- Mirrored semantic trap preserved exactly: `constraint_resolution_profile` keeps the passed local `dialogue_profile` as its default, not a fresh `ctx.get(...)` expression.
- Integration rule: `_call_llm` adds one helper call after `slice8_inputs`, then uses explicit `slice9_inputs.<field>` references with no `locals()` mutation and no prompt-template rewrite.
- Series closure: after this PRD, the mapped `WRITER_USER_TEMPLATE.format(...)` decomposition series is complete and only core required fields plus pure passthroughs remain inline.
