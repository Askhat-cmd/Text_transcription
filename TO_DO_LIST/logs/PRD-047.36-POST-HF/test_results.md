# PRD-047.36-POST-HF Test Results

## Required checks
- `python -m py_compile bot_psychologist/tools/run_prd_047_36_post_hf_owner_readiness_gate.py` -> `passed`
- `python -m pytest bot_psychologist/tests/test_prd_047_36_post_hf_readiness_gate_contract.py -q` -> `3 passed`
- `python -m pytest tests/test_prd_047_36_hf5_selected_knowledge_admission_contract.py tests/test_prd_047_36_hf5_direct_concept_followup_kb_visibility.py -q` -> `5 passed`
- `python -m pytest tests/api/test_prd_047_36_hf4_trace_persistence_every_turn.py tests/api/test_multiagent_trace_storage_consistency.py -q` -> `5 passed`
- `python -m pytest tests/test_prd_047_35_hidden_knowledge_competence.py tests/test_prd_047_35_public_user_mode.py -q` -> `5 passed`
- `python -m pytest tests/test_final_answer_acceptance_gate_v1.py -q` -> `7 passed`
- `npm test -- --run src/hooks/useChat.test.ts src/hooks/useMultiAgentTrace.test.ts src/components/chat/Message.test.ts` -> `9 passed`
- `npm run lint` -> `passed`
- `npm run build` -> `passed_with_existing_chunk_warnings`
- `python tools/run_prd_047_36_post_hf_owner_readiness_gate.py` -> `completed`, final gate verdict `BLOCKED`

## Additional check
- `python -m pytest tests -q` -> `blocked_by_historical_unrelated_import_error`
  - `ImportError: cannot import name '_build_llm_prompts' from 'bot_agent.answer_adaptive'`
  - failing collection target: `tests/regression/test_no_sd_required_by_response_flow.py`
