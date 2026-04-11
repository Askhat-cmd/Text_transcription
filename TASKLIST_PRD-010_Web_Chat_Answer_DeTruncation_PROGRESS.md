# TASKLIST PRD-010 Web Chat answer de-truncation

Reference: `PRD-010_Web_Chat_Answer_DeTruncation.md`

## Stage 1: Diagnostics
- [x] Confirm symptom from user evidence (trace vs chat)
- [x] Confirm truncation exists in persisted backend `bot_response`
- [x] Isolate root cause candidate in formatter policy

## Stage 2: Implementation
- [x] Update formatter to avoid default sentence truncation
- [x] Keep explicit brevity path for "кратко/коротко" requests

## Stage 3: Tests
- [x] Update existing formatter tests
- [x] Add regression test for non-brief short query
- [x] Run `pytest -q tests/test_response_formatter.py`
- [x] Run `npm run test -- src/services/api.stream.test.ts`

## Stage 4: Runtime verification
- [x] Execute representative query through runtime path
- [x] Verify final `bot_response` length/ending in sqlite
- [x] Verify no abrupt truncation in Web UI flow

## Stage 5: Closeout
- [x] Document final result and changed files
- [ ] Keep local only (no commit/push)

## Verification results
- `pytest -q tests/test_response_formatter.py` -> `8 passed`
- `npm run test -- src/services/api.stream.test.ts` -> `14 passed`
- Runtime probes (`/api/v1/questions/adaptive`) now persist complete endings in sqlite:
  - `de_truncation_probe_fix2_0`: len=302, tail ends with `.`
  - `de_truncation_probe_fix2_1`: len=278, tail ends with `.`
  - `de_truncation_probe_fix2_2`: len=262, tail ends with `.`
  - `de_truncation_probe_final_after_restore`: len=242, tail ends with `.`
