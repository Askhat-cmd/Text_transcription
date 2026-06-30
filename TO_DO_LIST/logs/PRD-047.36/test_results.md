# PRD-047.36 Test Results

## Targeted PRD Tests
- `python -m pytest tests/test_prd_047_36_owner_pilot_readiness_gate.py tests/test_prd_047_36_payload_excerpt_integrity.py tests/test_prd_047_36_delivery_spot_check_contract.py tests/test_prd_047_36_trace_consistency.py -q`
- Result: `10 passed`

## Preservation Subset
- `python -m pytest tests/test_prd_047_36_hf2_source_chunk_match_trace.py tests/test_prd_047_35_hidden_knowledge_competence.py tests/test_prd_047_35_public_user_mode.py tests/test_prd_047_34_latest_turn_authority.py tests/test_prd_047_32_runtime_truth_trace.py tests/test_prd_047_30_writer_grounding_visibility.py tests/test_final_answer_acceptance_gate_v1.py -q`
- Result: `31 passed`

## Full Suite Audit
- `python -m pytest tests -q`
- Result: `blocked by unrelated historical failure`
- First failure:
  - `tests/regression/test_no_sd_required_by_response_flow.py`
  - `ImportError: cannot import name '_build_llm_prompts' from 'bot_agent.answer_adaptive'`

## Live Gate Run
- Command:
  - `python bot_psychologist/tools/run_prd_047_36_owner_pilot_readiness_gate.py --backend-base-url http://127.0.0.1:8001 --frontend-base-url http://localhost:3000`
- Result:
  - overall verdict: `BLOCKER`
  - backend health: `200`
  - frontend status: `200`

## Final Scenario Statuses
- `S1 PASS`
- `S2 PASS`
- `S3 PASS`
- `S4 PASS`
- `S5 PASS`
- `S6 PASS_WITH_WARNING`
- `S7 PASS`
- `S8 BLOCKER`
- `S9 PASS`
- `S10 PASS`
- `S11 PASS`
- `S12 PASS`
- `S13 PASS`
- `S14 PASS_WITH_WARNING`
