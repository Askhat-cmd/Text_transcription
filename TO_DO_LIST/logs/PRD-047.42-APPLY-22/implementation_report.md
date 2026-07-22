# PRD-047.42-APPLY-22 Implementation Report

- PRD: `PRD-047.42-APPLY-22`
- Status: `accepted_pending_delivery_metadata`
- Delivery: `main_commit_pending`

## Scope Delivered

- Added `writer_agent_enforce_slice2.py` with `EnforceSlice2SecondPreludeResult` and `_extract_enforce_slice2_second_prelude_and_close_gently(...)` (mechanic d: extract-and-maybe-return).
- Moved the second prelude + inlined R03 window `628-700` from `_enforce_answer_compliance` into the helper with literal line-for-line semantics, an ordered `last_debug_patch` (5 keys on the `close_gently` early-return branch, 6 keys otherwise), and a boolean `close_gently_triggered` flag.
- Kept `self._set_final_answer_shape_debug` and `self._build_gentle_close_reply` calls inline in `writer_agent.py`, executed strictly after `self.last_debug.update(slice2_result.last_debug_patch)`, to preserve the historical `self.last_debug` key order (`final_answer_shape` sixth, not first).
- Passed the three module-level marker tuples (`_PRACTICE_MARKERS`, `_KNOWN_CONCEPT_CLARIFICATION_MARKERS`, `_EXTERNAL_SURVEILLANCE_MARKERS`) into the helper as parameters instead of importing them, avoiding a circular import (law Z-3: no new structure for one PRD).
- Kept `R02` (`623-627`) and `R04` (`702+`) untouched, immediately above and below the helper call.
- Removed the now-unused `evaluate_concrete_answer_fit` import from `writer_agent.py` (its only call site moved into the helper).
- Added direct tests covering both branches of the patch (5 vs 6 keys, exact order), an integration test proving `final_answer_shape` lands sixth (not first) in the true branch, and a marker-parameter substitution test.
- Added a historical-before/live-after snapshot runner reusing the APPLY-20 17-case harness by import.

## Honest Boundary

- This PRD closes family 1 (`intake_and_obligation_prelude`, `R01-R03`) of `_enforce_answer_compliance`: `text`/`R01` inline, slice1 (first prelude), `R02` inline, slice2 (second prelude + `R03`).
- Rule families `R04+` remain untouched; boundaries for the next family must be re-verified against the live HEAD rather than trusted from the APPLY-20 map, per the boundary-underestimation finding recorded in the v4.25 master plan update.
