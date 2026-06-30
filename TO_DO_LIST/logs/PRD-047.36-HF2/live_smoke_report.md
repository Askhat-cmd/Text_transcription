# PRD-047.36-HF2 Live Smoke Report

## Backend
- Restarted backend via canonical script:
  - `bot_psychologist/tools/start_pilot_web_chat_backend.ps1`
- Health check:
  - `http://127.0.0.1:8001/api/v1/health`
  - result: `200 healthy`

## Frontend
- Restarted Vite dev server in `bot_psychologist/web_ui`
- Verified:
  - `http://localhost:3000`
  - result: `HTTP 200`

## Live Retrieval Recall Audit
- Command:
  - `python tools/run_prd_047_36_hf2_retrieval_recall_audit.py --backend-base-url http://127.0.0.1:8001 --botdb-base-url http://127.0.0.1:8003`
- Result summary:
  - `A4`, `A6`: `PASS_source_found_and_payload_visible`
  - `A1`, `A2`, `A3`, `A7`, `A8`: `FAIL_raw_source_missing`
  - `A5`: `INCONCLUSIVE_missing_trace_or_insufficient_fields`

## Public Answer Cleanliness
- Final answers in the sampled live audit remained free of DB/chunk/trace/internal-system wording.
- Runtime truth trace showed previews only, not raw full payload dumps.

## Smoke Status
- `passed_with_warning`
- Warning reason:
  - remaining misses are source-coverage/runtime-top-k issues, not silent trace gaps.
