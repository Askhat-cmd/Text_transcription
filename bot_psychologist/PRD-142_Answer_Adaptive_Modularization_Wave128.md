# PRD-142: `answer_adaptive.py` Modularization (Wave 128)

## Context
`runtime_misc_helpers.py` still mixes orchestration stages with an internal LLM-generation mini-pipeline. This makes the core runtime file harder to read and slows future cleanup waves.

## Scope (Wave 128)
Extract the LLM-cycle helper block from `runtime_misc_helpers.py` into a dedicated module:
- `_generate_llm_with_trace`
- `_run_validation_retry_generation`
- `_collect_llm_session_metrics`
- `_build_prompt_stack_override`
- `_run_llm_generation_cycle`
- `_format_and_validate_llm_answer`

New module:
- `bot_agent/adaptive_runtime/llm_runtime_helpers.py`

## Objectives
1. Reduce cognitive load in `runtime_misc_helpers.py`.
2. Keep function contracts unchanged for current callsites.
3. Preserve runtime behavior and test stability.

## Technical Design
### Files
- `bot_agent/adaptive_runtime/llm_runtime_helpers.py` (new)
- `bot_agent/adaptive_runtime/runtime_misc_helpers.py`

### Changes
- Move helper implementations without logic change.
- Import moved helpers into `runtime_misc_helpers.py`.
- Keep all callsites and signatures intact.
- Remove now-unused typing imports from `runtime_misc_helpers.py`.

## Test Plan
Targeted:
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/unit/test_query_is_passed_to_output_validation_policy_v1031.py`
- `tests/contract/test_prompt_stack_contract_v2.py`
- `tests/unit/test_prompt_stack_order.py`
- `tests/regression/test_trace_reflects_real_execution_only.py`
- `tests/regression/test_no_level_based_prompting.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/test_retrieval_pipeline_simplified.py`

Full:
- `pytest -q` (with local TMP/TEMP override)
