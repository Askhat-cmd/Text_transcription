# PRD-047.29 Trace Summary Report

Status: passed
Date: 2026-06-23

## Added Surface

`runtime_trace_summary_v1`

## Where It Appears

- raw multiagent debug payload from `orchestrator.py`
- `/api/debug/session/{session_id}/multiagent-trace`
- any trace consumer that reads the stored debug payload

## Compact Fields

- `entrypoint`
- `latest_turn_constraints`
- `latest_turn_constraints_v1`
- `kb_visible_to_writer`
- `semantic_cards_visible_to_writer`
- `overlay_apply_detected`
- `final_directive_mode`
- `practice_blocked_by_user_request`
- `warnings`
- `full_trace_available`

## Why This Helps

- The pilot owner can see the current-turn control state in seconds.
- Full deep trace remains intact for engineering debug.
- `no_internal_db` visibility leaks can now be surfaced as warnings if they ever recur.

## Validation

- unit: `tests/test_prd_047_29_runtime_trace_summary.py`
- API: `tests/api/test_prd_047_29_runtime_trace_summary_api.py`
- live: `TO_DO_LIST/logs/PRD-047.29/live_pilot_smoke_report.md`
