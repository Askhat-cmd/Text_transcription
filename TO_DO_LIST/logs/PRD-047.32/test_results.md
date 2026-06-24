# PRD-047.32 Test Results

Status: passed_with_warning
Date: 2026-06-24

## Passed
- `.\.venv\Scripts\python.exe -m py_compile bot_agent\multiagent\dialogue_act_resolver.py bot_agent\multiagent\writer_context_package.py bot_agent\multiagent\dialogue_policy.py bot_agent\multiagent\agents\writer_agent_prompts.py` - passed.
- `.\.venv\Scripts\python.exe -m py_compile bot_psychologist\bot_agent\multiagent\writer_context_package.py bot_psychologist\bot_agent\multiagent\writer_kb_payload.py bot_psychologist\bot_agent\multiagent\runtime_trace_summary.py bot_psychologist\bot_agent\multiagent\hybrid_retrieval_planner.py bot_psychologist\bot_agent\multiagent\dialogue_policy.py bot_psychologist\bot_agent\multiagent\orchestrator.py bot_psychologist\api\debug_routes.py bot_psychologist\api\models.py` - passed.
- `python -m pytest tests\test_prd_047_30_writer_grounding_visibility.py tests\test_prd_047_31_hf1_practice_request_authority.py -q` - `11 passed, 3 warnings`.
- `python -m pytest tests\test_prd_047_32_runtime_truth_trace.py tests\test_prd_047_32_hybrid_shadow_noise.py tests\test_prd_047_32_answer_verbosity.py -q` - `8 passed`.
- `python -m pytest tests\test_final_answer_acceptance_gate_v1.py tests\multiagent\test_thread_manager.py tests\test_prd_047_26_hf1_dialogue_act_obligation.py -q` - `15 passed, 14 warnings`.
- `npm run lint` in `bot_psychologist/web_ui` - passed.
- `npm test -- MultiAgentTraceWidget` in `bot_psychologist/web_ui` - `14 passed`.
- `npm run build` in `bot_psychologist/web_ui` - passed.
- `python tools\validate_prd_artifact_encoding.py --prd PRD-047.32 ...` - passed: `files_checked=8`, `utf8_decode_error_count=0`, `mojibake_warning_count=0`, `replacement_char_warning_count=0`.

## Full Suite Warning
- `python -m pytest tests -q` still stops during collection on unrelated known blocker:
  `ImportError: cannot import name '_build_llm_prompts' from 'bot_agent.answer_adaptive'`.
- This is the same blocker allowed by PRD-047.32 and was not introduced by this PRD.

## Known Non-Blocking Warnings
- Existing `datetime.utcnow()` deprecation warnings in thread-manager tests.
- Existing Vite build warnings: dynamic import/static import chunking and chunk size over 500 kB.
