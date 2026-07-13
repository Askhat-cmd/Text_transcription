# Extraction Log

- PRD: `PRD-047.42-APPLY-11`
- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice4.py`.
- Shape choice: one helper function plus one typed dataclass with `39` extracted prompt-argument values.
- Boundary rule: `conversation_context=formatted_context` intentionally stays inline inside `WRITER_USER_TEMPLATE.format(...)` between the diagnostic/writer-move family and the context-budget family.
- Semantics rule: `writer_move_instruction_summary` intentionally stays as raw `ctx.get(...) or "нет"` with no new `str()` wrapper.
- Downstream integration keeps explicit field-by-field unpacking inside the same single `WRITER_USER_TEMPLATE.format(...)` call; no `locals()` mutation and no prompt-template rewrite.
