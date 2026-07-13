# Extraction Log

- PRD: `PRD-047.42-APPLY-12`
- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice5.py`.
- Shape choice: one helper function plus one typed dataclass with the `23` computed values from the mapped slice-5 argument families.
- Boundary rule: the 4 pure passthrough kwargs stay inline in `WRITER_USER_TEMPLATE.format(...)`: `writer_kb_payload_text`, `practice_ban_instruction`, `known_concept_clarification_ban`, and `external_surveillance_frame_ban`.
- Integration rule: `_call_llm` adds one helper call after `slice4_inputs`, then uses explicit `slice5_inputs.<field>` references with no `locals()` mutation and no prompt-template rewrite.
- Semantics rule: ctx-provided values still win even when they are empty strings, because the helper copies the original `str(ctx.get(..., fallback))` expressions exactly.
