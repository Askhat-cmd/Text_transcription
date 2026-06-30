# PRD-047.36-HF2 Test Results

## Targeted
- `python -m pytest tests/test_prd_047_36_hf2_source_chunk_match_trace.py -q`
  - `4 passed`
- `python -m pytest tests/test_prd_047_32_runtime_truth_trace.py tests/test_prd_047_35_hidden_knowledge_competence.py -q`
  - `5 passed`
- `npm test -- MultiAgentTraceWidget`
  - `15 passed`

## Preservation / Regression
- `python -m pytest tests/test_prd_047_34_latest_turn_authority.py tests/test_prd_047_33_answer_shape_calibration.py tests/test_prd_047_32_runtime_truth_trace.py tests/test_prd_047_32_hybrid_shadow_noise.py tests/test_prd_047_32_answer_verbosity.py tests/test_prd_047_31_hf1_practice_request_authority.py tests/test_prd_047_30_runtime_trace_summary.py tests/test_prd_047_30_writer_grounding_visibility.py tests/test_prd_047_30_writer_contract_authority.py tests/test_prd_047_35_hidden_knowledge_competence.py tests/test_prd_047_35_public_user_mode.py tests/test_prd_047_35_wake_depth_reference_behavior.py tests/test_final_answer_acceptance_gate_v1.py tests/test_prd_047_26_hf1_acceptance_gate.py tests/api/test_prd_047_30_writer_grounding_visibility_api.py -q`
  - `58 passed`
  - warnings only: known datetime deprecations and sklearn cache-version warnings

## Frontend
- `npm run lint`
  - passed
- `npm run build`
  - passed with existing chunk-size warnings only

## Known Unrelated Failures
- `python -m pytest tests/ui/test_runtime_tab_shows_effective_runtime_truth.py -q`
  - failed on existing assertion: `Effective Runtime Truth` label is absent from `AdminPanel.tsx`
- `python -m pytest tests -q`
  - blocked during collection by existing unrelated import error:
  - `ImportError: cannot import name '_build_llm_prompts' from 'bot_agent.answer_adaptive'`

## Conclusion
- PRD-targeted and required preservation tests passed.
- Remaining failures are unrelated pre-existing blockers and are reported honestly.
