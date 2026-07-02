# HF6 Test Results

- targeted backend subset:
  - `python -m pytest tests/test_prd_047_36_hf6_boundary_trace_contract.py tests/test_prd_047_36_hf6_no_internal_db_trace_integrity.py tests/test_prd_047_36_hf6_no_practice_trace_integrity.py -q`
  - result: `6 passed`
- preservation subset:
  - `python -m pytest tests/test_prd_047_36_hf5_selected_knowledge_admission_contract.py tests/test_prd_047_36_hf5_direct_concept_followup_kb_visibility.py tests/test_prd_047_36_post_hf_readiness_gate_contract.py tests/test_prd_047_35_hidden_knowledge_competence.py tests/test_prd_047_35_public_user_mode.py tests/test_final_answer_acceptance_gate_v1.py -q`
  - result: `26 passed`
- HF4/API preservation subset:
  - `python -m pytest tests/api/test_prd_047_36_hf4_trace_persistence_every_turn.py tests/api/test_multiagent_trace_storage_consistency.py -q`
  - result: `5 passed`
- frontend subset:
  - `npm test -- --run src/hooks/useChat.test.ts src/hooks/useMultiAgentTrace.test.ts src/components/chat/Message.test.ts`
  - result: `9 passed`
- frontend typecheck:
  - `npm run lint`
  - result: `passed`
- frontend production build:
  - `npm run build`
  - result: `passed_with_existing_chunk_warning`
- live smoke:
  - `python tools/run_prd_047_36_hf6_boundary_trace_integrity.py`
  - result: `PASS`

## Known Historical Residual

Full `python -m pytest tests -q` was not used as the acceptance gate here because the repository still carries the previously documented unrelated historical blocker:
- `_build_llm_prompts` import failure outside HF6 scope
