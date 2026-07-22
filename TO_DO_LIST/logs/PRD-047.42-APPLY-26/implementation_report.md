# PRD-047.42-APPLY-26 Implementation Report

- PRD: `PRD-047.42-APPLY-26`
- Status: `accepted`
- Delivery: `main_commit=ad12bf8`, `push_status=pushed_to_origin_main`

## Scope Delivered

- Added `writer_agent_enforce_slice5.py` with `EnforceSlice5Result` and `_classify_enforce_slice5_block_a(...)` - a pure classifier helper (no `self` access) returning one of fifteen outcomes covering greeting/low-resource/safety/support/clarify-one-point/user-repair-signal rules.
- Moved Block A (`756-821`, the entire self-contained tail before the 'known concept answer-first path' comment) from `_enforce_answer_compliance` into the helper in one batched slice, per the owner's pace decision.
- Kept the single `self._defer_no_stub_repair` call (for `user_repair_signal`) inline in `writer_agent.py`.
- Preserved every literal response text verbatim, including intentional duplication across outcomes that historically shared the same return string (`low_resource_no_practice`/`give_short_support_primary`/`give_short_support_markers` share one literal; `thanks_close`/`close_gently` share another) - the classifier still distinguishes them as separate outcomes for testability, only the caller's dispatch groups them onto a shared `return`.
- `clarify_one_point_multi_questions` computes `return_text` inside the helper (first question-terminated segment of `text`), matching the original inline computation exactly.
- Boundaries matched the PRD's stated `756-821` exactly against live HEAD, with `822` (Block B's opening comment) confirmed untouched immediately below.
- Added direct tests covering all fifteen outcomes, the `return_text` computation for `clarify_one_point_multi_questions` across multiple inputs, and the order-of-resolution guarantee for formally-overlapping conditions (`give_short_support_primary` wins over `give_short_support_len_or_flags` when both would match).
- Added a historical-before/live-after snapshot runner reusing the APPLY-20 17-case harness by import.

## Honest Boundary

- This PRD closes Block A only. Block B (`822-1033`, 212 lines: the known-concept answer-first path, the question-policy cascade, and the practice/active-line tail, including the method's only remaining `last_debug` write) is unreconnoitered and is the next boundary; its PRD size (one slice or several) is deferred until reconnaissance is done, per the project's standing principle of not planning ahead what has not been read.

## Verification Summary

- Direct helper tests: `20 passed`
- APPLY-26 contract tests: `3 passed`
- Historical clean-tree rerun `APPLY-6..26`: `134 passed, 1 warning` - fully green (the APPLY-20 `rule_count` self-test stays green because APPLY-25 already retired its hard equality assertion)
- Canonical isolated writer baseline: `19 failed, 260 passed, 2027 deselected, 190 warnings`
- Owner workspace canonical writer run: `14 failed, 265 passed, 2027 deselected, 346 warnings`

## Honest Note (not a regression, documented per PRD requirement)

- `give_short_support_len_or_flags` and `give_short_support_markers` share the exact gating predicate (`planner_next_move == "give_short_support"`) as `give_short_support_primary`, whose condition (`planner_next_move == "give_short_support" or planner_answer_shape == "short_support"`) is a strict OR-superset of theirs. This means these two outcomes are structurally unreachable through the classifier cascade - `give_short_support_primary` always wins first whenever `planner_next_move == "give_short_support"` holds, which is the only way to reach the other two branches' guard at all.
- This is not a defect introduced by decomposition - it is the same dead branch the original `if`/`return` cascade already had, preserved verbatim per the PRD's explicit "no dedup, copy literally" instruction (§2, "Не делаем").
- Proven and documented via `test_give_short_support_primary_wins_order_over_len_or_flags_and_markers_even_when_both_formally_true`, which constructs inputs satisfying all three predicates simultaneously and asserts `give_short_support_primary` wins - exactly the order-of-resolution test the PRD's Step 6 required.
- The owner workspace also still reports the separate environment-specific `14`-failure writer baseline (same known set as prior PRDs) - a second, unrelated, already-documented warning.
