# PRD-047.42-APPLY-8 Implementation Report

- PRD: `PRD-047.42-APPLY-8`
- Status: `accepted`
- Delivery: `main_commit=e615581`

## Scope Delivered

- Added optional `source_text: str | None = None` support to `_extract_call_llm_node()` and `build_variable_inventory()` in `TO_DO_LIST/tools/run_prd_047_42_apply_6_call_llm_boundary_mapping.py`.
- Kept the default live analysis path unchanged when `source_text` is not provided.
- Generated a frozen APPLY-6 variable-inventory baseline fixture at `bot_psychologist/tests/contract/fixtures/prd_047_42_apply_6_variable_inventory_baseline.json`.
- Recorded fixture provenance explicitly with `source_commit=e5f5f32`.
- Rewrote only `test_variable_inventory_contains_expected_spine_variables` to read the frozen fixture instead of re-parsing the live `_call_llm` structure.

## Honest Boundary

- No production code moved and no `_call_llm` slice was started in this PRD.
- `writer_agent.py`, `writer_agent_call_llm_slice1.py`, all writer helper/mixin files, `writer_contract.py`, `admin_routes.py`, and the `10` admin split modules stayed out of scope.
- `test_boundary_sections_cover_call_llm_without_gaps` stayed untouched as required.

## Evidence Summary

- APPLY-6 contract before fix: `1 failed, 3 passed`
- APPLY-6 contract after fix: `4 passed`
- APPLY-7 contract after fix: `2 passed`
- focused writer subset after fix: `1 failed, 62 passed, 58 warnings`
- unchanged pre-existing failure: `test_semantic_hits_limit_to_two`
- `live_inventory_before.json == live_inventory_after.json`
- protected diff gate: `0 changed paths`

## Key Decision

- Historical structure is now tested against a frozen baseline, not against re-parsed live `_call_llm` shape.
- The same analyzer remains available for future reports through the optional `source_text` path, so the PRD fixes test debt without deleting useful tooling.
