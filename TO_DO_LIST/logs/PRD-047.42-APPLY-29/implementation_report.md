# PRD-047.42-APPLY-29 Implementation Report

- PRD: `PRD-047.42-APPLY-29`
- Status: `accepted`
- Delivery: `main_commit=27861f4`, `push_status=pushed_to_origin_main`

## Scope Delivered

- Added `writer_agent_mvp_slice1.py` with `MvpPart1Result` and `_classify_mvp_part1(...)` - a pure classifier helper (no `self` access) returning one of seventeen tags (16 significant outcomes plus `not_matched`), covering the first 108 lines of `_enforce_mvp_free_dialogue_compliance` (groups A-J).
- Group B's in-place `text`/`lowered_text` mutation is carried through the result as `updated_text`/`updated_lowered_text`, always populated regardless of outcome; the caller reassigns both immediately after the classifier call, before checking `outcome` - the first occurrence of this pattern in the decomposition series.
- Group A's computed `target` (last direct question or user message) is returned as `computed_target` and used for `must_answer` on the call site.
- Group J's two physically distinct branches (1118-1122 and 1123-1126) that write the identical `last_debug` pair under different conditions stay as two distinct classifier tags (`practice_forbidden_repair_needed`, `practice_forbidden_repair_default`), merged only at the call site's shared dispatch branch.
- `offer_repair_context` (line 1018) is confirmed dead code (computed, never read anywhere in the method) and is deliberately NOT carried into the helper, per the PRD's explicit instruction to document rather than fix inherited dead code.
- Kept all `self`-methods (`_defer_no_stub_repair`, `_resolve_one_step_or_no_practice_fallback`, `_set_final_answer_shape_debug`, `_strip_optional_followup_invitation`) exclusively on the call site.
- `detect_stale_stub` (module-level, non-`self`) is called directly inside the helper, matching `writer_agent.py`'s own import path.
- Added direct tests covering all 16 significant outcomes, `not_matched`, the group B text/lowered_text mutation, and `computed_target` for both group A branches.
- Added a historical-before/live-after snapshot runner reusing the APPLY-20 17-case harness by import.

## Honest Boundary

- This PRD closes Part 1 (groups A-J, `1019-1126`) of `_enforce_mvp_free_dialogue_compliance`. Groups K-P plus the method's final unconditional fallback remain inline in `writer_agent.py` and are the next boundary (APPLY-30), whose exact line numbers must be re-verified against live HEAD after this PRD merges, per the PRD's own explicit instruction.

## Verification Summary

- Direct helper tests: `24 passed`
- APPLY-29 contract tests: `2 passed`
- Historical clean-tree rerun `APPLY-6..29`: `141 passed, 1 warning` - fully green
- Canonical isolated writer baseline: `19 failed, 334 passed, 2034 deselected, 190 warnings`
- Owner workspace canonical writer run: `14 failed, 339 passed, 2034 deselected, 346 warnings`
- Group B mutation confirmed to carry through even when the group falls through without returning (`text="хочешь узнать больше?"` -> `updated_text="хочешь узнать больше."`, `outcome="not_matched"`).
- `offer_repair_context` (line 1018) confirmed to have zero reads anywhere in the method, matching the PRD's documented dead-code finding.
