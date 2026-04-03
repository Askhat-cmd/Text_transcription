# TASKLIST_10.2_Legacy_Runtime_Purge_PROGRESS

Execution progress for `PRD_10.2_Legacy_Runtime_Purge.md`.

## Rules

- Strict phase order: `0 -> 1 -> 2 -> 3 -> 4 -> 5`.
- Move to next phase only after green tests for current phase.
- If tests fail, fix inside current phase.
- Scope discipline: purge legacy runtime only, no new product features.

## Phase Status

- [x] Phase 0 - Purge Baseline
- [x] Phase 1 - SD Runtime Purge
- [x] Phase 2 - Path Builder Purge
- [x] Phase 3 - Streaming Neo Alignment
- [ ] Phase 4 - Metadata and Trace Cleanup
- [ ] Phase 5 - Regression Hardening and Runtime Proof

## Phase Details

### Phase 0 - Purge Baseline

- [x] Inventory of legacy touchpoints (SD / path_builder / user_level / stream divergence).
- [x] Baseline metadata/trace inventory.
- [x] Added inventory tests:
- [x] `tests/inventory/test_runtime_legacy_touchpoints_map.py`
- [x] `tests/inventory/test_live_metadata_field_inventory.py`
- [x] `tests/inventory/test_streaming_runtime_divergence_inventory.py`
- [x] Ran phase tests.

### Phase 1 - SD Runtime Purge

- [x] Removed SD influence from runtime generation/metadata/trace when `DISABLE_SD_RUNTIME=true`.
- [x] Removed SD prompt overlay injection in runtime response generation.
- [x] Updated stream done payload/debug trace to strip SD fields when SD runtime disabled.
- [x] Added regression test for stream contract without SD.
- [x] Ran phase tests.

### Phase 2 - Path Builder Purge

- [x] Removed automatic `path_builder` from default adaptive flow.
- [x] Switched default `include_path` to `false` in API model/runtime/UI.
- [x] Added route guard: `inform/reflect/contact_hold/regulate` do not trigger path builder.
- [x] Added regression tests for default behavior and explicit flag forwarding.
- [x] Ran phase tests.

### Phase 3 - Streaming Neo Alignment

- [x] Brought `/questions/adaptive-stream` to same runtime truth as `/questions/adaptive`.
- [x] Removed legacy route/gate assumptions from stream path.
- [x] Synced stream metadata/trace semantics with adaptive runtime behavior.
- [x] Added integration/regression tests for stream parity.
- [x] Ran phase tests.

### Phase 4 - Metadata and Trace Cleanup

- [ ] Final cleanup of legacy SD/user_level fields in live metadata.
- [ ] Final cleanup of misleading trace sections from disabled modules.
- [ ] Update metadata/trace contract tests.
- [ ] Run phase tests.

### Phase 5 - Regression Hardening and Runtime Proof

- [ ] Run extended regression/e2e set for purge iteration.
- [ ] Confirm with runtime logs: no routine legacy execution.
- [ ] Verify degraded fallback behavior.
- [ ] Update post-purge documentation.

## Execution Journal

- `2026-04-03`: Initialized progress file, started Phase 0.
- `2026-04-03`: Phase 0 done. Added inventory baseline tests/fixture, run result: `7 passed`.
- `2026-04-03`: Started Phase 1. Began SD cleanup in `response_generator`, `answer_adaptive`, `api/routes`.
- `2026-04-03`: Phase 1 done. Added `tests/regression/test_streaming_sd_runtime_disabled_contract.py`; target run: `10 passed`.
- `2026-04-03`: Phase 2 done. Removed automatic path-builder side effect in default flow; added `tests/regression/test_default_adaptive_path_builder_purge.py`; target run: `10 passed`.
- `2026-04-03`: Phase 3 done. Reworked `/questions/adaptive-stream` to delegate to `answer_question_adaptive` (single route truth); added `tests/integration/test_streaming_neo_alignment_v102.py`; target run: `14 passed`.
