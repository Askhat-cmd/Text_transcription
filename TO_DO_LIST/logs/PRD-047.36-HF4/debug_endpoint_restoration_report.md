# PRD-047.36-HF4 Debug Endpoint Restoration Report

Date: 2026-07-01

## Endpoint behavior after HF4
- Fresh delivered turns:
  - exact `turn_index=N` lookup returns `200`
  - `exact_turn_match=true`
- Old pre-restart session after backend restart:
  - exact lookup returns `404`
  - `reason_code=debug_trace_expired_after_backend_restart`
  - `available_turn_indices` still reflect delivered history turns

## Conclusion
- HF4 preserved strict exact lookup and wrong-turn protection while restoring honest fresh-turn success and precise legacy/expired labeling.
