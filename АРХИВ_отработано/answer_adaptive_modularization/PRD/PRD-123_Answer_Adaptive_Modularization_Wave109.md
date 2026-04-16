# PRD-123: `answer_adaptive.py` Modularization (Wave 109)

## Context
`answer_adaptive.py` still carried a dense runtime initialization block (flags, snapshots, debug payload bootstrap).
To keep the facade thinner, this setup should live in runtime helpers.

## Scope (Wave 109)
Extract startup/context initialization into runtime helper with backward-compatible test hooks.

## Objectives
1. Reduce facade orchestration noise at function entry.
2. Preserve monkeypatch contract for output-validation enablement.
3. Keep full suite green.

## Technical Design
### `bot_agent/adaptive_runtime/runtime_misc_helpers.py`
- add `_prepare_adaptive_run_context(...)` which builds:
  - resolved `top_k`
  - start time/model info
  - runtime feature flags
  - pipeline/debug payload scaffolding
  - initial context placeholders
- keep compatibility hook via `output_validation_enabled_fn` callback.

### `bot_agent/answer_adaptive.py`
- replace inline initialization block with `_runtime_prepare_adaptive_run_context(...)` call.
- remove now-obsolete facade-only imports (`_build_config_snapshot`, `_init_debug_payloads`, extra flag readers).
- keep explicit sentinel line `level_adapter = None` to preserve regression contract expectations.

## Test Plan
Targeted:
- `tests/regression/test_no_level_based_prompting.py`
- `tests/integration/test_runtime_validation_receives_query_v1031.py`
- `tests/integration/test_generation_validation_separation.py`
- `tests/integration/test_sparse_output_triggers_regeneration_hint.py`
- `tests/integration/test_degraded_mode_without_retrieval.py`
- `tests/unit/test_sd_runtime_disabled.py`
- `tests/test_retrieval_pipeline_simplified.py`
- `tests/unit/test_curious_not_auto_informational.py`
- `tests/unit/test_user_level_adapter_removed.py`
- `tests/unit/test_sd_legacy_final_cleanup_prompt_context.py`

Full:
- `pytest -q`
