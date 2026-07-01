# PRD-047.36-HF4 Owner Regression Evidence

Date: 2026-07-01

## Owner-visible blocker before HF4
- Supplied owner screenshots showed `Trace unavailable` under fresh and old assistant turns in Web Chat.
- The UI displayed `requested_turn_missing` for delivered turns that should have had trace.
- `available turns` could collapse to incomplete subsets like `[1]` or `[1, 3]` while more assistant turns were already visible.

## Local reproduction notes
- Early HF4 browser runs reproduced the same user-visible failure class.
- Before the final repair, the post-restart new-chat flow could reopen the wrong active session after reload, which reproduced the same owner symptom even when backend exact trace existed.
- Final HF4 live smoke replaced that failure with:
  - fresh trace restored for all fresh turns;
  - precise `debug_trace_expired_after_backend_restart` only for old in-memory traces after backend restart.

## Evidence files
- `fresh_chat_before_reload.png`
- `fresh_chat_after_reload.png`
- `old_session_after_restart.png`
- `new_chat_after_restart_before_reload.png`
- `new_chat_after_restart_after_reload.png`
