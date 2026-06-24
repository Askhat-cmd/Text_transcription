# PRD-047.32 Live Owner Web Chat Trace Report

Status: passed_with_warning
Date: 2026-06-24

## Restart And Health
- Killed stale listeners on `:8001` and `:3000`.
- Restarted backend via `bot_psychologist/tools/start_pilot_web_chat_backend.ps1`.
- Restarted frontend via `npm run dev -- --host 127.0.0.1 --port 3000`.
- Health check passed: `status=healthy`, `data_source=api`, `bot_data_base_api=available`, `blocks_loaded=247`.
- Raw scripted smoke summary: `TO_DO_LIST/logs/PRD-047.32/live_owner_web_chat_trace_raw.json`.

## Key Trace Differences
- Before: Web Chat showed `Чанки в Writer` over `memory.semantic_hits`, which could imply retrieved candidates were sent to Writer.
- After: Web Chat shows `Retrieval candidates / trace-only` and points the owner to `Runtime Truth Trace` / `Writer KB Payload` for actual Writer-visible payload.
- Before: Hybrid Planner invalid JSON looked like an unscoped fallback/failure.
- After: invalid planner output is surfaced as `planner_shadow_status=shadow_invalid_json` or `shadow_invalid_plan`, `planner_fallback_scope=shadow_only`, and `json_decode_error_affected_production_answer=false`.
- Before: direct `Что во внутренней базе...` phrasing could be treated as stale contextual follow-up.
- After: direct source wording routes to Writer-visible KB payload in live smoke.

## Live Smoke Result
- `mandatory_1_greeting`: answer length `602`, Writer payload `0`, planner `valid`.
- `mandatory_2_resistance`: answer length `1770`, Writer payload `0`, planner `shadow_invalid_plan`, production unaffected.
- `mandatory_3_anger_boss`: answer length `1397`, Writer payload `0`, planner `shadow_invalid_json`, production unaffected.
- `mandatory_4_practice`: answer length `1495`, Writer payload `1`, grounding `explicit_practice_request_narrow_grounding`.
- `mandatory_5_long_term_practice`: answer length `965`, Writer payload `1`, grounding `explicit_practice_request_narrow_grounding`.
- `extra_a_support`: answer length `1251`, Writer payload `0`, compact support improved and stayed within soft target.
- `extra_b_no_practice_explain`: answer length `2233`, Writer payload `0`; still above soft target, warning kept.
- `extra_c_direct_kb_source`: answer length `2114`, Writer payload `1`; direct KB/source path works after marker repair.
- `extra_d_no_internal_db`: answer length `1927`, Writer payload `0`; no internal DB payload leak.
- `extra_e_new_thread_practice`: answer length `355`, Writer payload `0`; answered with one bounded practice, trace reason `direct_one_step_no_kb_needed`.

## Required Statements
- The misleading `Чанки в Writer` owner label was fixed. The candidate list is no longer presented as actual Writer payload.
- `JSONDecodeError` can still appear as a shadow planner status, but owner trace marks it shadow-only and production answer affected is `false`.
- Explicit practice path still works: mandatory practice turns produced `practice_request`, `provide_one_bounded_practice`, and Writer payload count `1` in the owner scenario.
- Broad KB remains hidden by default on ordinary support turns: support smoke had Writer payload `0`.
- Direct KB/source path still works: direct internal-base question produced Writer payload `1`.

## Answer Quality Notes
- Support/no-internal-db answers are shorter than pre-fix smoke and less mechanism-heavy.
- No-practice explanation remains longer than the `600_1400` soft target. This is a bounded warning, not a trace/runtime blocker.
