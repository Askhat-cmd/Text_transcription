# PRD-047.42-APPLY-8 Test Output Summary

## Before

- `pytest bot_psychologist/tests/contract/test_prd_047_42_apply_6_call_llm_boundary_mapping.py -q`
  - result: `1 failed, 3 passed`
  - broken test: `test_variable_inventory_contains_expected_spine_variables`
  - failure shape: `writer_kb_payload_text.scope` drifted from `writer_prompt_input` to `local_only` because the test was analyzing live post-slice `_call_llm` structure.

## After

- `pytest bot_psychologist/tests/contract/test_prd_047_42_apply_6_call_llm_boundary_mapping.py -q`
  - result: `4 passed`

- `pytest bot_psychologist/tests/contract/test_prd_047_42_apply_7_call_llm_slice1.py -q`
  - result: `2 passed`

- focused writer subset
  - command: `pytest -q bot_psychologist/tests/contract/test_prd_047_42_apply_6_call_llm_boundary_mapping.py bot_psychologist/tests/contract/test_prd_047_42_apply_7_call_llm_slice1.py bot_psychologist/tests/multiagent/test_writer_agent.py bot_psychologist/tests/multiagent/test_writer_agent_call_llm_slice1.py bot_psychologist/tests/multiagent/test_writer_agent_constants.py bot_psychologist/tests/multiagent/test_writer_agent_fallback_helpers.py bot_psychologist/tests/multiagent/test_writer_agent_fallback_state_mixin.py bot_psychologist/tests/multiagent/test_writer_agent_lifecycle_mixin.py`
  - result: `1 failed, 62 passed, 58 warnings`
  - unchanged pre-existing failure: `test_semantic_hits_limit_to_two`

## Default-Path Compatibility Proof

- `TO_DO_LIST/logs/PRD-047.42-APPLY-8/live_inventory_before.json`
- `TO_DO_LIST/logs/PRD-047.42-APPLY-8/live_inventory_after.json`
- byte comparison result: `MATCH`

## Frozen Baseline Proof

- fixture path: `bot_psychologist/tests/contract/fixtures/prd_047_42_apply_6_variable_inventory_baseline.json`
- provenance: `source_commit=e5f5f32`
- generation path: direct function call to `build_variable_inventory(source_text=...)`
- red-line compliance: no standalone `run_prd_*.py` execution was used to generate the fixture.
