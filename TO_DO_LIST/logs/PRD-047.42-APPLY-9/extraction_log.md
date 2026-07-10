# Extraction Log

- PRD: `PRD-047.42-APPLY-9`
- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice2.py`.
- Shape choice: one helper function plus one typed dataclass with only the 5 variables that cross the cluster boundary.
- Reason: the PRD dependency audit confirmed the other 9 detector/intermediate names are `local_only` and should not widen the `_call_llm` namespace.
- Return strategy: explicit named fields through `CallLLMSlice2Inputs`, then explicit field-by-field unpacking inside `_call_llm`.
- `practice_overview_requested`, `examples_requested`, `numbered_list_requested`, `expansion_requested`, `direct_concrete_request`, `summary_request`, `application_request`, `rich_user_request`, and `mvp_overrides_payload` deliberately stay internal to the helper.
- No `locals().update()`, no implicit namespace injection, and no `self.last_debug` mutation were introduced in the extracted slice.
