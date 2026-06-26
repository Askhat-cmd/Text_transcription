# PRD-047.35 Test Results

Status: completed with honest blocker notes

## Targeted PRD tests

- `python -m pytest tests/test_prd_047_35_hidden_knowledge_competence.py tests/test_prd_047_35_public_user_mode.py tests/test_prd_047_35_wake_depth_reference_behavior.py -q`
  - `8 passed`

## Required preservation subset

- `python -m pytest tests/test_prd_047_34_latest_turn_authority.py -q`
  - `8 passed`

- `python -m pytest tests/test_prd_047_33_answer_shape_calibration.py tests/test_prd_047_32_runtime_truth_trace.py -q`
  - `11 passed`

- `python -m pytest tests/test_prd_047_30_writer_grounding_visibility.py tests/test_prd_047_31_hf1_practice_request_authority.py -q`
  - `11 passed`

- `python -m pytest tests/test_final_answer_acceptance_gate_v1.py tests/multiagent/test_thread_manager.py tests/test_prd_047_26_hf1_dialogue_act_obligation.py -q`
  - `15 passed`

## Additional touched-module regression

- `python -m pytest tests/test_response_planner.py tests/test_writer_contract_response_planner.py tests/multiagent/test_writer_contract.py -q`
  - `10 passed`

## Full-suite honesty

- `python -m pytest tests -q`
  - blocked by historical unrelated import error:
    - `ImportError: cannot import name '_build_llm_prompts' from 'bot_agent.answer_adaptive'`

## Live runtime smoke

- backend restart health check on `127.0.0.1:8001/api/v1/health` passed
- frontend restart answered `HTTP 200` on `127.0.0.1:3000`
- owner smoke runner executed after restart and produced `TO_DO_LIST/logs/PRD-047.35/live_owner_smoke_raw.json`
