# PRD-047.42-APPLY-27 Implementation Report

- PRD: `PRD-047.42-APPLY-27`
- Status: `accepted`
- Delivery: `main_commit=52f071a`, `push_status=pushed_to_origin_main`

## Scope Delivered

- Added `writer_agent_enforce_slice6.py` with `EnforceBlockBPart1Result` and `_classify_enforce_block_b_part1(...)` - a pure classifier helper (no `self` access) returning one of nineteen tags (18 significant outcomes plus `not_matched`).
- Moved Block B Part 1 (`804-896`, groups 1-6 of Block B: known-concept prefirst path, the three-stage question-policy cascade, the `repair_misalignment` check, and the practice-forbidden template-leakage repair) from `_enforce_answer_compliance` into the helper.
- `not_matched` is not dispatched at all in `writer_agent.py` - there is no corresponding `if`, so control falls through naturally into group 7 (line 898), which remains byte-for-byte untouched.
- Kept all four `self`-methods (`_defer_no_stub_repair`, `_resolve_one_step_or_no_practice_fallback`, `_set_final_answer_shape_debug`, `_strip_optional_followup_invitation`) exclusively on the call site in `writer_agent.py`; the helper never calls or receives any of them.
- The method's only remaining direct `self.last_debug` write (`template_leakage_repair_deferred_to_gate`) is returned as an ordered `last_debug_patch` and applied by the caller strictly before `_set_final_answer_shape_debug`, preserving the original three-line sequence byte-for-byte.
- Preserved `known_concept_prefirst_correlation`/`no_question_known_concept_correlation` and the neurostalking pair as four distinct classifier tags (two physically different conditions in the original each), merged only at the call site's dispatch, not inside the classifier.
- Kept the group 3/5 marker tuples as inline literals inside the helper, matching the original (not module-level constants).
- `no_question_default_strip` computes `return_text` inside the helper via `re.sub(r"\s*\?+\s*", ". ", text).strip()`, matching the original inline computation exactly.
- Added direct tests covering all 18 significant outcomes, `not_matched`, `return_text` computation, the `last_debug` key-order guard for `practice_forbidden_unsolicited_repair`, and a priority-resolution case inside group 2.
- Added a historical-before/live-after snapshot runner reusing the APPLY-20 17-case harness by import.

## Honest Boundary

- This PRD closes only Part 1 of Block B (groups 1-6, `804-896`). Groups 7-12 (`898-1015`, 118 lines - including the most structurally complex cluster of the whole method, group 9) remain untouched in `writer_agent.py` and are the next boundary (APPLY-28), per the architect's split decision recorded in the PRD (Block B is ~3.2x longer than Block A and mixes two extraction mechanics, so it was not taken in one PRD).

## Verification Summary

- Direct helper tests: `26 passed`
- APPLY-27 contract tests: `3 passed`
- Historical clean-tree rerun `APPLY-6..27`: `137 passed, 1 warning` - fully green (the APPLY-20 `rule_count` self-test has stayed green since APPLY-25's fix)
- Canonical isolated writer baseline: `19 failed, 286 passed, 2030 deselected, 190 warnings`
- Owner workspace canonical writer run: `14 failed, 291 passed, 2030 deselected, 346 warnings`
- Groups 7-12 (`898-1015`) confirmed physically untouched: direct read of `writer_agent.py` immediately after the extracted block shows line 898 begins group 7 exactly as before, and the runner's `grep_proof.md` confirms the untouched marker against the historical source at the same relative position.
