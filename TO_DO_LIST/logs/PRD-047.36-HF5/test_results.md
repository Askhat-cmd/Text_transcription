# PRD-047.36-HF5 Test Results

Date: 2026-07-01

## Targeted HF5
- `python -m pytest tests/test_prd_047_36_hf5_selected_knowledge_admission_contract.py tests/test_prd_047_36_hf5_direct_concept_followup_kb_visibility.py -q`
- Result: `5 passed`

## Backend preservation subsets
- `python -m pytest tests/api/test_prd_047_36_hf4_trace_persistence_every_turn.py tests/api/test_multiagent_trace_storage_consistency.py -q`
- Result: `5 passed`
- `python -m pytest tests/test_prd_047_36_hf2_source_chunk_match_trace.py -q`
- Result: `4 passed`
- `python -m pytest tests/test_prd_047_35_hidden_knowledge_competence.py tests/test_prd_047_35_public_user_mode.py -q`
- Result: `5 passed`
- `python -m pytest tests/test_final_answer_acceptance_gate_v1.py -q`
- Result: `7 passed`

## Frontend preservation subset
- `npm test -- --run src/hooks/useChat.test.ts src/hooks/useMultiAgentTrace.test.ts src/components/chat/Message.test.ts`
- Result: `9 passed`

## Frontend typecheck/build
- `npm run lint`
- Result: passed
- `npm run build`
- Result: passed

## Tooling sanity
- `python -m py_compile bot_psychologist/tools/run_prd_047_36_hf5_direct_concept_followup_kb_visibility.py`
- Result: passed

## Live smoke
- `python tools/run_prd_047_36_hf5_direct_concept_followup_kb_visibility.py`
- Result: `PASS`

## Full suite residual blocker
- `python -m pytest tests -q`
- Result: `ERROR during collection`
- Unrelated historical blocker:
  - `tests/regression/test_no_sd_required_by_response_flow.py`
  - `ImportError: cannot import name '_build_llm_prompts' from 'bot_agent.answer_adaptive'`

