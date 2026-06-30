# Debug Endpoint Exact Lookup Report

## Endpoint
- `GET /api/debug/session/{session_id}/multiagent-trace`

## Pre-HF3
- Explicit `turn_index` miss could silently return latest available trace.
- Unknown session lookup could drift across unrelated in-memory debug keys.

## HF3 Contract
- Exact requested turn returns `200` with:
  - `trace_availability.status=available`
  - `requested_turn_index`
  - `resolved_turn_index`
  - `exact_turn_match`
  - `available_turn_indices`
- Missing requested turn returns `404` with:
  - `detail="No multiagent trace found for requested turn"`
  - `trace_availability.status=unavailable`
  - `reason_code=requested_turn_missing`
  - `available_turn_indices=[...]`

## Verification
- Targeted backend tests:
  - exact lookup consistency passed
  - structured unavailable payload passed
  - cross-session latest-trace leak prevention passed
- Live smoke after backend restart:
  - exact `turn_index=1` -> `200 available exact_turn_match=true`
  - missing `turn_index=999` -> `404 unavailable requested_turn_missing`
