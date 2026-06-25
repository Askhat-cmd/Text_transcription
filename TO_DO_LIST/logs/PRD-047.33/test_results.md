# Test Results - PRD-047.33

Date: 2026-06-25
Status: passed_with_warning

## Targeted PRD-047.33
- `python -m pytest tests/test_prd_047_33_answer_shape_calibration.py tests/test_prd_047_32_answer_verbosity.py tests/test_writer_first_prompt_assembly_v1.py -q`
- Result: `12 passed`

## PRD-047.32 preservation
- `python -m pytest tests/test_prd_047_32_runtime_truth_trace.py tests/test_prd_047_32_hybrid_shadow_noise.py tests/test_prd_047_32_answer_verbosity.py -q`
- Result: `8 passed`

## PRD-047.30 / PRD-047.31-HF1 preservation
- `python -m pytest tests/test_prd_047_30_writer_grounding_visibility.py tests/test_prd_047_31_hf1_practice_request_authority.py -q`
- Result: `11 passed`

## Acceptance / thread / dialogue-act regression subset
- `python -m pytest tests/test_final_answer_acceptance_gate_v1.py tests/multiagent/test_thread_manager.py tests/test_prd_047_26_hf1_dialogue_act_obligation.py -q`
- Result: `15 passed`

## Full suite
- `python -m pytest tests -q`
- Result: blocked by known unrelated import error:
  - `ImportError: cannot import name '_build_llm_prompts' from 'bot_agent.answer_adaptive'`
- Scope note: unchanged known blocker, not introduced by PRD-047.33.

## UI checks
- Skipped by design.
- Reason: no Web UI source file was changed in this PRD.
