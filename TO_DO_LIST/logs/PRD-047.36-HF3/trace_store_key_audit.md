# Trace Store Key Audit

## Files Inspected
- `bot_psychologist/api/session_store.py`
- `bot_psychologist/api/debug_routes.py`

## Pre-HF3 Behavior
- `SessionStore.find_multiagent_debug()` accepted candidate keys but, when candidates missed, continued searching all known debug keys in the in-memory store.
- `GET /api/debug/session/{session_id}/multiagent-trace?turn_index=N` also applied a latest-trace fallback when exact turn `N` was absent.
- Combined effect:
  - exact turn lookup was not owner-safe;
  - a wrong-session or latest-turn trace could be returned instead of an honest missing result.

## HF3 Repair
- Added `SessionStore.get_multiagent_debug_turn_indices()`.
- Changed `SessionStore.find_multiagent_debug(..., include_all_keys=False)` so debug lookup stays candidate-scoped by default.
- `get_multiagent_trace()` now:
  - uses candidate-only lookup;
  - collects `available_turn_indices`;
  - returns structured unavailable metadata instead of latest-trace fallback when explicit `turn_index` is missing.

## Result
- Exact trace lookup is now scoped to the requested session identity set.
- Missing exact turn now produces explicit owner/debug evidence instead of silent drift.
