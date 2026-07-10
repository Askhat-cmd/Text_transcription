# PRD-047.42-APPLY-4 Extraction Log

## Scope
- Source file: `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py`
- New module: `bot_psychologist/bot_agent/multiagent/agents/writer_agent_fallback_state_mixin.py`
- Pattern: `WriterAgentFallbackStateMixin`

## Moved Constants
- `_COST_PER_1K_TOKENS`
- `_RU_NAME_PATTERNS`
- `_EN_NAME_PATTERNS`

## Moved Methods
- `_repair_greeting_without_mechanism_lecture`
- `_resolve_one_step_or_no_practice_fallback`
- `_set_final_answer_shape_debug`
- `_defer_no_stub_repair`
- `_get_client`
- `_estimate_cost`
- `_apply_name_continuity`
- `_extract_user_name`

## Wiring
- `WriterAgent` now inherits from `WriterAgentFallbackStateMixin`.
- Existing `WriterAgent` call sites stay unchanged.
- Existing slice-2 delegates stay in `WriterAgent` because the moved methods still call:
  - `_strip_optional_followup_invitation`
  - `_build_no_practice_fallback_text`
  - `_normalize_name`
- `self._resolve_model()` stays in `WriterAgent`; `_estimate_cost()` continues to call it through normal inheritance lookup.
- `_PRACTICE_MARKERS` remains owned by `writer_agent.py` and is exposed to the mixin through the class attribute `WriterAgent._PRACTICE_MARKERS`.

## Behavioral Guard
- Method bodies were moved without logic edits.
- Focused before/after pytest evidence kept the same single pre-existing failure:
  - `test_semantic_hits_limit_to_two`
