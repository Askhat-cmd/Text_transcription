# PRD-047.42-APPLY-28 Implementation Report

- PRD: `PRD-047.42-APPLY-28`
- Status: `accepted`
- Delivery: `main_commit=2ee0c71`, `push_status=pushed_to_origin_main`

## Scope Delivered

- Added `writer_agent_enforce_slice7.py` with `EnforceBlockBPart2Result` and `_classify_enforce_block_b_part2(...)` - a pure classifier helper (no `self` access) returning one of seventeen tags (16 significant outcomes plus `not_matched`).
- Moved Block B Part 2 (`883-999`, groups 7-12: `mechanism_explanation_repair`, the one-step cascade including first-list-item extraction, active-line practice-suppression repairs, mechanical-revoicing repairs, and the third known-concept signal cluster) from `_enforce_answer_compliance` into the helper.
- Group 9's nested 'maybe-return inside maybe-return' pattern is preserved exactly: `if list_like:` wraps `if first_item:` with no `else` at either level, so `list_like=True` with `first_item=None` (e.g. a bare list marker with no content) falls through to the `sentence_parts` check instead of exiting the group - verified by a dedicated edge-case test.
- `not_matched` is not dispatched at all in `writer_agent.py` - there is no corresponding `if`, so control falls through directly to the pre-existing `return text` at line 1000 (unchanged, the physical end of the method).
- Called the module-level (non-`self`) `starts_with_mechanical_revoicing` function directly inside the helper via `from ..active_line import starts_with_mechanical_revoicing` - no circular import, matching `writer_agent.py`'s own import path.
- Kept all `self`-methods (`_defer_no_stub_repair`, `_resolve_one_step_or_no_practice_fallback`) exclusively on the call site; the helper never calls or receives them.
- Preserved four distinct 'one-step-like' classifier tags (`one_step_g8`, `sentence_parts_one_step_g9`, `question_marker_one_step_g9`, `no_step_marker_one_step_g9`) that dispatch to the same `self`-call with identical arguments, merged only at the call site.
- `first_item_extraction_g9` and `revoicing_strip_g11` compute `return_text` inside the helper, matching the original inline computations exactly.
- Added direct tests covering all 16 significant outcomes, `not_matched` with correct final dispatch to `return text`, the group 9 edge case, `return_text` computation for both computed outcomes, and a group 8 vs. group 9 priority-resolution case.
- Added a historical-before/live-after snapshot runner reusing the APPLY-20 17-case harness by import.

## Honest Boundary

- This PRD closes Block B in full. The entire `_enforce_answer_compliance` method (`576-1000` at this HEAD) is now fully decomposed. The next boundary is a different method entirely: `_enforce_mvp_free_dialogue_compliance`, which has not been mapped at all and needs its own from-scratch reconnaissance.

## Verification Summary

- Direct helper tests: `24 passed`
- APPLY-28 contract tests: `2 passed`
- Historical clean-tree rerun `APPLY-6..28`: `139 passed, 1 warning` - fully green
- Canonical isolated writer baseline: `19 failed, 310 passed, 2032 deselected, 190 warnings`
- Owner workspace canonical writer run: `14 failed, 315 passed, 2032 deselected, 346 warnings`
- Group 9 edge case (`list_like=True`, `first_item=None`) confirmed to fall through to the `sentence_parts` check rather than exiting the group or raising, matching Особенность 1 exactly.
- Historical line 1000 confirmed to be exactly `return text` (the method's unconditional end), untouched, via `grep_proof.md`.
