# Extraction Log

- PRD: `PRD-047.42-APPLY-13`
- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice6.py`.
- Shape choice: one helper function plus one typed dataclass with the `22` computed values from the mapped slice-6 argument families.
- Boundary rule: unlike APPLY-12, there are no passthrough exceptions here; every mapped kwarg is computed through `ctx.get(..., literal_default)` logic and therefore belongs inside the helper.
- Integration rule: `_call_llm` adds one helper call after `slice5_inputs`, then uses explicit `slice6_inputs.<field>` references with no `locals()` mutation and no prompt-template rewrite.
- Semantics rule: each moved expression is copied exactly from the pre-refactor inline `WRITER_USER_TEMPLATE.format(...)` block, including bool normalization and literal defaults.
