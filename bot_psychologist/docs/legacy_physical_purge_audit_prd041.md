# PRD-041 Legacy Physical Purge Audit

## Scope

Import graph snapshot for legacy cascade candidates before physical purge.

## Classification Table

| Path | Category | Current imports/callers | Action | Reason |
|---|---|---|---|---|
| `bot_agent/answer_adaptive.py` | `KEEP_COMPAT_SHIM` | Public import via `bot_agent.__init__`, direct tests/imports | shrink to tiny shim | Public compatibility surface remains, legacy body must be removed |
| `bot_agent/adaptive_runtime/` | `DELETE_NOW` | Imported only by legacy body in `answer_adaptive.py`; no active runtime entrypoint imports | delete directory | Legacy stage implementation no longer used after multiagent cutover |
| `bot_agent/state_classifier.py` | `REVIEW` | Imported by `diagnostics_classifier.py`, `path_builder.py`, many tests | keep for now | Not safe to delete in PRD-041 without wider refactor |
| `bot_agent/route_resolver.py` | `REVIEW` | Used by legacy tests/fixtures and helper flows | keep for now | Requires separate contract cleanup before delete |
| `bot_agent/decision/` | `REVIEW` | Used by dedicated decision tests/scripts; imported by legacy path | keep for now | Not active runtime-critical, but still referenced by non-PRD041 suites |
| `bot_agent/response/` | `REVIEW` | Used by response tests and scripts; imported by legacy path | keep for now | Requires dedicated response-surface migration before delete |
| `bot_agent/fast_detector.py` | `KEEP_ACTIVE` | Imported by `state_classifier.py`; config/runtime flags and admin UI reference | keep | Active dependency chain for state-classifier surface |
| `bot_agent/user_level_types.py` | `KEEP_ACTIVE` | Imported by `path_builder.py` (active) | keep | Shared type used outside legacy cascade |
| `bot_agent/memory_v12.py` | `KEEP_ACTIVE` | Imported by `memory_updater.py` and `memory_context.py` | keep | Active memory snapshot dependency |

## Notes

- Import graph helper: `bot_psychologist/scripts/legacy_import_graph.py`
- Key removal boundary for PRD-041:
  - remove `_answer_question_adaptive_legacy_cascade` body
  - remove all `adaptive_runtime` imports from `answer_adaptive.py`
  - remove physical directory `bot_agent/adaptive_runtime/`
