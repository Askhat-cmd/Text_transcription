# Live Smoke Report

## Runner
- `bot_psychologist/tools/run_prd_047_36_hf3_trace_availability_smoke.py`

## Environment
- backend: `http://127.0.0.1:8001`
- frontend: `http://localhost:3000`
- backend required one restart to pick up HF3 code before final authoritative run

## Final Authoritative Result
- verdict: `PASS`
- backend health: `200 healthy`
- frontend: `200`
- adaptive test turn: `200`
- exact trace lookup `turn_index=1`: `200`
- exact availability: `status=available`, `exact_turn_match=true`
- missing trace lookup `turn_index=999`: `404`
- missing availability: `status=unavailable`, `reason_code=requested_turn_missing`, `available_turn_indices=[1]`

## Artifact
- machine-readable result: `TO_DO_LIST/logs/PRD-047.36-HF3/live_smoke_result.json`
