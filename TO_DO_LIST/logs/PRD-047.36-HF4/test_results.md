# PRD-047.36-HF4 Test Results

Date: 2026-07-01

## Targeted backend HF4
- `python -m pytest tests/api/test_prd_047_36_hf4_trace_persistence_every_turn.py tests/api/test_prd_047_36_hf4_trace_session_key_mapping.py tests/api/test_prd_047_36_hf4_trace_turn_number_alignment.py -q`
- Result: `4 passed`

## Backend preservation subset
- `python -m pytest tests/api/test_multiagent_trace_storage_consistency.py tests/api/test_multiagent_trace_contract.py tests/api/test_users_history_by_session.py tests/test_multiagent_trace.py -q`
- Result: `23 passed`

## Acceptance / writer preservation subset
- `python -m pytest tests/test_final_answer_acceptance_gate_v1.py tests/multiagent/test_writer_agent.py -q`
- Result: `1 failed, 34 passed`
- Unrelated historical failure:
  - `tests/multiagent/test_writer_agent.py::test_semantic_hits_limit_to_two`

## Frontend targeted/preservation subset
- `npm test -- --run src/services/api.stream.test.ts src/hooks/useChat.test.ts src/hooks/useMultiAgentTrace.test.ts src/components/chat/Message.test.ts`
- Result: `23 passed`

## Frontend typecheck/build
- `npm run lint` -> passed
- `npm run build` -> passed

## Live smoke
- `python tools/run_prd_047_36_hf4_trace_restoration_smoke.py`
- Result: `PASS`
