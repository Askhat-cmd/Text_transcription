# PRD-047.34 Live Owner Smoke Report

Status: `passed_with_warning`  
Raw artifact: `TO_DO_LIST/logs/PRD-047.34/live_owner_smoke_raw.json`

## Runtime restart

- Backend restarted on `:8001`
- Health check passed:
  - `status=healthy`
  - `data_source=api`
  - `bot_data_base_api=available`
- Frontend restarted separately via direct Vite launch and answered `HTTP 200` on `http://127.0.0.1:3000`

## Scenario A - exact Chat5 failure

Observed:
- turn 2:
  - `must_answer_source=direct_source`
  - `writer_contact_mode=direct_kb`
  - payload `2`
- turn 3:
  - `must_answer_source=latest_turn`
  - `answer_target=latest_turn`
  - `writer_contact_mode=free_writer_contact`
  - payload `0`
  - previous KB question demoted

Result:
- exact stale KB continuation failure did not repeat

## Scenario B - support after anger/practice

Observed:
- turn 3:
  - `must_answer_source=explicit_practice`
  - `writer_contact_mode=bounded_practice`
  - payload `1`
- turn 4:
  - `must_answer_source=latest_turn`
  - `answer_target=latest_turn`
  - `writer_contact_mode=free_writer_contact`
  - payload `0`
  - `no_practice` boundary active

Result:
- latest support request won
- stale practice task did not remain active
- forced canned one-step fallback no longer appeared

## Scenario C - explicit continuation exception

Observed:
- turn 2:
  - `must_answer_source=explicit_continue_previous`
  - `answer_target=previous_open_loop`
  - `writer_contact_mode=structured_answer`
  - payload `2`

Result:
- explicit continuation path preserved

## Scenario D - no internal DB hard boundary

Observed:
- turn 1:
  - `must_answer_source=latest_turn`
  - `answer_target=latest_turn`
  - payload `0`

Result:
- no-internal-db boundary preserved

## Honest warning

- Automated live smoke passed the required A-D authority checks.
- The remaining warning for PRD status is global test-suite debt outside this PRD, not a smoke failure.
