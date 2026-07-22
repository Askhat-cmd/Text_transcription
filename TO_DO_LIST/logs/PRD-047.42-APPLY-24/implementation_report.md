# PRD-047.42-APPLY-24 Implementation Report

- PRD: `PRD-047.42-APPLY-24`
- Status: `accepted_with_warning`
- Delivery: `main_commit=fa935d5`, `push_status=pushed_to_origin_main`

## Scope Delivered

- Added `writer_agent_enforce_slice4.py` with `EnforceSlice4Result` and `_classify_enforce_slice4_obligation_repairs_and_echo(...)` - a pure classifier helper (no `self` access) returning one of six outcomes: `not_matched`, `literal_markdown_echo_mismatch`, `acknowledge_style_preference_repair`, `repair_and_answer_last_question_repair`, `answer_last_offer_repair`, `answer_knowledge_or_direct_repair`.
- Moved rules `R07-R16` (the literal markdown echo repair plus four obligation-specific repair rules) from `_enforce_answer_compliance` into the helper in one batched slice, per the owner's pace decision recorded in the v4.27 master plan update: families without reconnaissance-confirmed hidden complexity are cut whole, not rule-by-rule.
- Kept the single `self._defer_no_stub_repair` call inline in `writer_agent.py`, dispatched once with `signal`/`must_answer` taken from the classifier result.
- For `literal_markdown_echo_mismatch`, the helper returns the ordered 2-key `last_debug_patch` (`format_request_repair_applied` first, `final_answer_shape` second) plus `return_text`; the caller applies `self.last_debug.update(...)` then returns the text, preserving the only `last_debug` write in the whole family exactly as ordered in the original.
- Boundaries matched the PRD's stated `690-745` exactly against live HEAD, with `746` (the MVP-free handoff) confirmed untouched immediately below - no boundary re-verification discrepancy this time, unlike APPLY-23.
- Added direct tests covering all six classifier outcomes, exact patch key order for the echo-mismatch outcome, correct `target` computation for the repair-and-answer-last-question outcome, and a purity/idempotency check.
- Added a historical-before/live-after snapshot runner reusing the APPLY-20 17-case harness by import.

## Honest Boundary

- This PRD closes family 2 (`obligation_specific_repairs_before_profile_split`) in full: `R04` (APPLY-23) plus `R07-R16` (this PRD). Family 3 (`mvp_free_branch_handoff`, a single delegating `self`-call at line 746) is the next boundary; the architect is expected to decide it likely stays inline, by analogy with owner decision #3 on `provider_dispatch`.

## Verification Summary

- Direct helper tests: `12 passed`
- APPLY-24 contract tests: `3 passed`
- Historical clean-tree rerun `APPLY-6..24`: `130 passed, 1 failed` (see Honest Warning below for the single failure)
- Canonical isolated writer baseline: `19 failed, 240 passed, 2024 deselected, 190 warnings`
- Owner workspace canonical writer run: `14 failed, 245 passed, 2024 deselected, 346 warnings`

## Honest Warning

- `bot_psychologist/tests/contract/test_prd_047_42_apply_20_enforce_compliance_mapping.py::test_rule_count_matches_boundary_map_inventory` now fails: `67 == 75` (was `75`, now `67`). This APPLY-20 self-test does not compare against a frozen snapshot - it live-walks the AST of `_enforce_answer_compliance` and counts physical `if` nodes. Before this PRD, rules `R07-R16` were 5 independent rule-pairs, each a nested pair of `if` statements (10 `if` nodes total). This PRD's Step 3 - executed verbatim from the PRD text - collapses all 10 into exactly 2 dispatch `if` statements in `writer_agent.py`. `75 - 8 = 67` matches the observed drop exactly.
- This is a structural consequence of the PRD's own specified batched-classifier design (the owner's pace decision recorded in the v4.27 master plan update: cut whole families in one PRD when reconnaissance finds no hidden complexity), not an implementation defect. It is proven non-regressive by (a) before/after snapshot byte-identity across all 17 harness cases and (b) the canonical isolated writer baseline reproducing the exact same known `19` failures with none new.
- Per the project's red line against modifying a prior PRD's test file, `test_prd_047_42_apply_20_enforce_compliance_mapping.py` was left untouched. This finding is recorded honestly here, in `TO_DO_LIST/PRD-047.42-APPLY-24_EXECUTION_TASKS_v1.md`, and in the project docs, rather than silently patched or hidden.
- The owner workspace also still reports the separate environment-specific `14`-failure writer baseline (same known set as APPLY-21/22/23) - a second, unrelated, already-documented warning.
