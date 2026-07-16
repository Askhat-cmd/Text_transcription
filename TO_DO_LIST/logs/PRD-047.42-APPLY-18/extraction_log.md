# Extraction Log

- PRD: `PRD-047.42-APPLY-18`
- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice11.py`.
- Shape choice: one helper function plus one frozen dataclass result carrying reassigned `dialogue_profile`, resolved `runtime_settings`, selected `system_prompt`, and one ordered `last_debug_patch` dictionary.
- Reassignment rule: helper receives the old local `dialogue_profile` as default input, normalizes the ctx override if present, and returns the new value so `_call_llm` rebinds the local variable explicitly.
- Callable rule: helper does not know about `self`; `_call_llm` passes `self._resolve_runtime_settings` as a bound callable and the helper invokes it once with the keyword argument `dialogue_profile=`.
- Order rule: the `2` debug keys inside `last_debug_patch` stay in the original insertion order so snapshot JSON bytes remain stable.
- Import cleanup rule: `WRITER_SYSTEM` and `WRITER_SYSTEM_MVP_FREE_DIALOGUE` should disappear from `writer_agent.py` only if zero-match grep confirms they have no remaining usage there, while `WRITER_USER_TEMPLATE` must remain.
