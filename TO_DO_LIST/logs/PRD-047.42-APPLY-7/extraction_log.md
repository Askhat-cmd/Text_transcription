# Extraction Log

- PRD: `PRD-047.42-APPLY-7`
- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice1.py`.
- Shape choice: one helper function plus one typed dataclass, not two separate helpers.
- Reason: the two mapped clusters are adjacent, both depend only on `ctx`, and both feed the same downstream `_call_llm` namespace; one helper keeps the cut visible without creating a second micro-boundary immediately.
- Return strategy: explicit named fields through `CallLLMSlice1Inputs`, then explicit field-by-field unpacking inside `_call_llm`.
- `practice_gate` deliberately stays local inside the helper because the PRD dependency graph marked it `local_only`; exporting it would widen the surface without any downstream consumer.
- No `locals().update()`, no implicit namespace injection, and no `self.last_debug` mutation were introduced in the extracted slice.
