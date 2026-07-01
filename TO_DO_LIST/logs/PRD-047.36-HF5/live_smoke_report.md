# PRD-047.36-HF5 Live Smoke Report

Date: 2026-07-01
Status: `PASS`
Runner: `python tools/run_prd_047_36_hf5_direct_concept_followup_kb_visibility.py`

## Runtime
- backend: `http://127.0.0.1:8001`
- frontend: `http://localhost:3000`
- backend health: `healthy`
- frontend probe: `200`

## Scenario results
- `S-HF5-1` greeting
  - verdict: `PASS`
  - retrieval action: `suppress_rag`
  - grounding reason: `greeting_or_contact`
  - Writer payload: `0`
- `S-HF5-2` direct concept question
  - verdict: `PASS`
  - grounding reason: `direct_knowledge_question`
  - selected semantic card: `program_imperfect_self_v1`
  - Writer payload: `2`
- `S-HF5-3` Chat 12 direct concept follow-up
  - verdict: `PASS`
  - retrieval action: `query_kb`
  - composer reason: `direct_concept_followup_selected_knowledge`
  - grounding reason: `direct_concept_followup`
  - selected cards:
    - `program_imperfect_self_v1`
    - `control_as_safety_v1`
    - `fact_vs_interpretation_v1`
  - Writer payload: `2`
- `S-HF5-4` Neurostalking follow-up
  - verdict: `PASS`
  - grounding reason: `direct_concept_followup`
  - selected cards:
    - `neurostalking_basic_lens_v1`
    - `program_imperfect_self_v1`
  - Writer payload: `2`
- `S-HF5-5` detailed modeling
  - verdict: `PASS`
  - grounding reason: `direct_knowledge_question`
  - Writer payload: `2`
- `S-HF5-6` no-internal-db boundary
  - verdict: `PASS`
  - grounding reason: `latest_turn_no_internal_db`
  - Writer payload: `0`

## Acceptance conclusion
- Failing Chat 12 scenario is repaired.
- Selected relevant concept knowledge is no longer left trace-only with Writer payload `0`.
- `grounding_reason=no_clear_retrieval_need` no longer wins on the repaired concept follow-up.
- `no_internal_db` remains intact.
- No public internal-language leak was observed in any live checked answer.

## Honest residual note
- Full `python -m pytest tests -q` still fails on the historical unrelated import blocker:
  - `tests/regression/test_no_sd_required_by_response_flow.py`
  - `ImportError: cannot import name '_build_llm_prompts'`

