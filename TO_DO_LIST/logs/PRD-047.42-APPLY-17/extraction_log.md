# Extraction Log

- PRD: `PRD-047.42-APPLY-17`
- Physical placement: new module `bot_psychologist/bot_agent/multiagent/agents/writer_agent_call_llm_slice10.py`.
- Shape choice: one helper function plus one frozen dataclass result carrying the final `user_prompt` and one ordered `last_debug_patch` dictionary.
- Mutation rule: helper computes the conditional prompt-section append and returns the final `user_prompt`; `_call_llm` reassigns the local prompt explicitly and applies exactly one `self.last_debug.update(...)`.
- Order rule: the `18` debug keys inside `last_debug_patch` stay in the original insertion order so snapshot JSON bytes remain stable.
- Boundary rule: `overruled_constraints` is passed through by reference, not copied, and `start_ts` plus the following runtime/provider/response clusters stay out of scope.
- Import cleanup rule: `format_prompt_constraint_section_v1` moved behind the new helper module, so the direct import disappears from `writer_agent.py` once no other usage remains.
