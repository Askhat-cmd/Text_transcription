# PRD-047.36 Implementation Report

## Outcome
- PRD status: `BLOCKER`
- Final live gate verdict: `BLOCKER`
- Authoritative final live run:
  - backend: `http://127.0.0.1:8001`
  - frontend: `http://localhost:3000`
  - backend health: `200`
  - frontend status: `200`

## What Was Added
- Read-only readiness-gate runner:
  - `bot_psychologist/tools/run_prd_047_36_owner_pilot_readiness_gate.py`
- Gate helper library:
  - `bot_psychologist/tools/prd_047_36_owner_pilot_readiness_gate_lib.py`
- Targeted PRD tests:
  - `tests/test_prd_047_36_owner_pilot_readiness_gate.py`
  - `tests/test_prd_047_36_payload_excerpt_integrity.py`
  - `tests/test_prd_047_36_delivery_spot_check_contract.py`
  - `tests/test_prd_047_36_trace_consistency.py`
- Evidence artifacts:
  - `scenario_results.json`
  - `scenario_matrix.md`
  - `payload_excerpt_integrity_report.md`
  - `final_answer_delivery_spot_check.md`
  - `trace_consistency_report.md`
  - `live_owner_readiness_report.md`
  - `live_turn_exports/`
  - `prompt_canvases/`

## Minimal Code Scope
- Added gate-only reporting and classification logic.
- Added one trace-only consistency cleanup in `writer_context_package.py`:
  - if payload/runtime recover a near-exact match without raw-source top-k match, trace now emits:
    - `loss_stage=recovered_without_raw_source_match`
    - `loss_reason=payload_recovered_from_runtime_candidate_without_raw_source_top_k_match`
- Added acceptance-gate extraction into the readiness runner so delivery evidence now explains whether a memory gap was caused by quarantine.

## Final Scenario Result
- `PASS`: `S1`, `S2`, `S3`, `S4`, `S5`, `S7`, `S9`, `S10`, `S11`, `S12`, `S13`
- `PASS_WITH_WARNING`: `S6`, `S14`
- `BLOCKER`: `S8`

## Real Blocker
- `S8` no-practice request is still violated.
- Latest live answer:
  - `Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут.`
- This is a direct contradiction of the scenario contract and of the PRD latest-turn/no-practice boundary.

## Important Readiness Warning
- Delivery persistence is not fully freeze-ready even when visible answers look acceptable.
- In the final authoritative run, acceptance-gate quarantine prevented saved-memory parity for:
  - `S1`
  - `S2`
  - `S7`
  - `S8`
  - `S12`
- In those cases `API answer` was visible, but `saved memory assistant message` was empty because the turn was quarantined by `final_answer_acceptance_gate_v1`.
- This does not replace the main blocker, but it means PRD-047.36 cannot claim full delivery-integrity proof for all benign owner-pilot turns.

## Stability Note
- `S11` failed in an earlier live rerun during implementation and passed in the final authoritative rerun.
- Final authoritative result is `PASS`, but the creative latest-turn path should be treated as not yet fully stable.

## Source-Proof Result
- `S6` and `S14` stayed honest `PASS_WITH_WARNING` with `source_missing_expected`.
- The current runtime can now distinguish:
  - source available and visible to payload
  - source missing in raw/runtime top-k
  - recovered payload path without raw-source top-k match

## Decision
- PRD-047.36 does not authorize a silent behavior fix here.
- The readiness gate is complete and honest.
- The next step should be one narrow HF, not a broader architecture change.
