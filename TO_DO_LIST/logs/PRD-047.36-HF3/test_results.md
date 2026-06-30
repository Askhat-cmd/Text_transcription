# PRD-047.36-HF3 Test Results

## Targeted Backend
- `python -m pytest tests/api/test_multiagent_trace_storage_consistency.py -q`
- result: `4 passed`

## Backend Preservation
- `python -m pytest tests/api/test_multiagent_trace_storage_consistency.py tests/api/test_multiagent_trace_contract.py tests/api/test_users_history_by_session.py tests/test_multiagent_trace.py -q`
- result: `23 passed`

## Frontend Targeted
- `npm test -- --run src/hooks/useMultiAgentTrace.test.ts src/components/chat/Message.test.ts`
- result: `4 passed`

## Frontend Preservation
- `npm test -- --run src/hooks/useChat.test.ts`
- result: `5 passed`

## Typecheck / Build
- `npm run lint` -> passed
- `npm run build` -> passed

## Known Global Debt
- Full `python -m pytest tests -q` was not re-run in this PRD because the historical unrelated `_build_llm_prompts` import blocker is already known and unchanged by HF3.
