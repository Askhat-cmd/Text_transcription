# Extraction Log

- PRD: `PRD-047.42-APPLY-19`
- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice12.py`.
- Shape choice: one helper function plus one frozen dataclass result carrying the original `result.text` object and one ordered `13`-key `last_debug_patch` dictionary.
- Timing rule: helper imports the module `time` and calls `time.perf_counter()` directly so the snapshot harness can keep monkeypatching the shared module attribute and forcing `duration_ms=123`.
- Callable rule: helper does not know about `self`; `_call_llm` passes `self._estimate_cost` as a bound callable and the helper invokes it once with the exact keyword arguments `tokens_prompt=` and `tokens_completion=`.
- Boundary rule: `await create_agent_completion(...)` and `return llm_response` stay inline in `_call_llm` exactly as required by owner decision #3 and this PRD.
- Order rule: the `13` debug keys stay in original insertion order so snapshot JSON bytes remain stable.
