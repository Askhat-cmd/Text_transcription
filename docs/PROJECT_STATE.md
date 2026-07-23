# Project State - Bot Psychologist / Neo MindBot

Главный источник курса проекта: `docs/MASTER_STRATEGIC_PLAN_NEO_MindBot_v4_RU.md`.

## PRD-047.42-APPLY-29 _enforce_mvp_free_dialogue_compliance slice 1 Part 1
PRD-047.42-APPLY-29 opens decomposition of the second (and last) large method in `writer_agent.py`: `_enforce_mvp_free_dialogue_compliance`, a ~225-line method with a completely different signature (explicit keyword parameters, not `(self, response_text, contract)`) that was mapped from scratch in this session - no assumptions carried over from `_enforce_answer_compliance`'s decomposition. Reconnaissance found two things not seen in the prior method: dead code (`offer_repair_context`, computed and never read) and a group that mutates `text`/`lowered_text` in place and lets the mutation survive past the group if it doesn't return.

Current result:
- main implementation commit: `27861f4`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `bot_psychologist/bot_agent/multiagent/agents/writer_agent_mvp_slice1.py`;
- extracted surface is one frozen dataclass `MvpPart1Result` with a `Literal` outcome field (17 tags: 16 significant outcomes plus `not_matched`), always-populated `updated_text`/`updated_lowered_text`, and optional `return_text`/`computed_target`/`last_debug_patch` - a pure classifier with zero `self` access;
- group B's in-place mutation of `text`/`lowered_text` is carried through as `updated_text`/`updated_lowered_text`, unconditionally returned regardless of outcome; the caller reassigns both immediately after the classifier call, before checking `outcome` - the first occurrence of this pattern in either method's decomposition;
- group A's computed `target` (last direct question or user message) is returned as `computed_target` and used for `must_answer` on the call site;
- group J's two physically distinct branches that write an identical `last_debug` pair under different conditions (`practice_forbidden_repair_needed`, `practice_forbidden_repair_default`) stay as two distinct classifier tags, merged only at the call site's shared dispatch branch;
- `offer_repair_context` (line 1018) is confirmed dead code (zero reads anywhere in the method) and is deliberately not carried into the helper, documented rather than fixed;
- all `self`-methods (`_defer_no_stub_repair`, `_resolve_one_step_or_no_practice_fallback`, `_set_final_answer_shape_debug`, `_strip_optional_followup_invitation`) stay exclusively on the call site; `detect_stale_stub` (module-level, non-`self`) is called directly inside the helper;
- boundaries matched the PRD's stated `1019-1126` exactly against live HEAD;
- direct helper tests cover all 16 significant outcomes, `not_matched`, the group B mutation-carry behavior, and `computed_target` for both group A branches;
- dedicated APPLY-29 runner reuses the APPLY-20 `17`-case harness by import, builds a historical-before snapshot from commit `05c9de9`, and proves byte-identical before/after output plus identical `last_debug` key ordering;
- `no_mutation_proof.md` reports `0` changed protected paths across the `25` canonical protected files (the accepted `24` plus `writer_agent_enforce_slice7.py`) and `0` changed paths under the accepted APPLY-20..28 log folders;
- clean-tree historical contract rerun across APPLY-6..APPLY-29 is fully green at `141/141`;
- the PRD-required isolated clean-worktree `pytest tests/ -k writer -q` baseline reports `19 failed, 334 passed, 2034 deselected, 190 warnings` - the same known failure set as prior PRDs;
- the owner workspace canonical writer run shows the known environment-specific `14 failed, 339 passed, 2034 deselected, 346 warnings` - an already-documented, unrelated warning.
- Honest boundary: this PRD closes only Part 1 (groups A-J). Groups K-P plus the method's final unconditional fallback remain inline and are the next boundary (APPLY-30), whose line numbers must be re-verified against live HEAD after this PRD merged.

## PRD-047.42-APPLY-28 _enforce_answer_compliance slice 7 Block B Part 2 - method fully decomposed
PRD-047.42-APPLY-28 closes Block B in full, completing the entire `_enforce_answer_compliance` decomposition that began at PRD-047.42-APPLY-21. Groups 7-12 (the second and last part of Block B) contain the single most structurally complex cluster in the whole method (group 9: 4 internal locals, 4 return points, a novel nested "maybe-return inside maybe-return" sub-pattern) but, unlike Part 1, contain zero direct `last_debug` writes.

Current result:
- main implementation commit: `2ee0c71`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice7.py`;
- extracted surface is one frozen dataclass `EnforceBlockBPart2Result` with a `Literal` outcome field (17 tags: 16 significant outcomes plus `not_matched`) and an optional computed `return_text` - a pure classifier with zero `self` access;
- group 9's novel sub-pattern is preserved exactly: `if list_like:` wraps `if first_item:` with no `else` at either level, so `list_like=True` with `first_item=None` (a bare list marker with no content after it) falls through to the `sentence_parts` check instead of exiting the group - verified with a dedicated edge-case test (`text="-\n"`);
- `not_matched` has no dispatch branch at all on the call site - control falls through directly into the pre-existing unconditional `return text` (the literal end of the method), confirmed untouched;
- the module-level (non-`self`) `starts_with_mechanical_revoicing` function is called directly inside the helper via the same import path as `writer_agent.py` (`from ..active_line import starts_with_mechanical_revoicing`) - no circular import;
- all `self`-methods (`_defer_no_stub_repair`, `_resolve_one_step_or_no_practice_fallback`) stay exclusively on the call site; four distinct "one-step-like" classifier tags that dispatch to the same `self`-call with identical arguments are merged only at the call site, not inside the classifier;
- `first_item_extraction_g9` and `revoicing_strip_g11` compute `return_text` inside the helper, matching the original inline computations exactly;
- boundaries matched the PRD's stated `883-999` exactly against live HEAD, with line 1000 (`return text`, the method's physical end) confirmed untouched;
- direct helper tests cover all 16 significant outcomes, `not_matched` with correct final dispatch, the group 9 edge case, `return_text` computation for both computed outcomes, and a group 8 vs. group 9 priority-resolution case;
- dedicated APPLY-28 runner reuses the APPLY-20 `17`-case harness by import, builds a historical-before snapshot from commit `c4a447a7`, and proves byte-identical before/after output plus identical `last_debug` key ordering;
- `no_mutation_proof.md` reports `0` changed protected paths across the `24` canonical protected files (the accepted `23` plus `writer_agent_enforce_slice6.py`) and `0` changed paths under the accepted APPLY-20..27 log folders;
- clean-tree historical contract rerun across APPLY-6..APPLY-28 is fully green at `139/139`;
- the PRD-required isolated clean-worktree `pytest tests/ -k writer -q` baseline reports `19 failed, 310 passed, 2032 deselected, 190 warnings` - the same known failure set as prior PRDs;
- the owner workspace canonical writer run shows the known environment-specific `14 failed, 315 passed, 2032 deselected, 346 warnings` - an already-documented, unrelated warning.
- **Milestone: `_enforce_answer_compliance` (the largest method in `writer_agent.py`) is now fully decomposed across slices 1-7 (APPLY-21, 22, 23, 24, 26, 27, 28) plus one technical decision (`mvp_free_branch_handoff` stays inline) and one hygiene micro-PRD (APPLY-25).** The next boundary is a different method entirely, `_enforce_mvp_free_dialogue_compliance`, which has never been mapped.

## PRD-047.42-APPLY-27 _enforce_answer_compliance slice 6 Block B Part 1 classifier
PRD-047.42-APPLY-27 extracts the first half of Block B (the last unreconnoitered stretch of `_enforce_answer_compliance`), following the architect's split decision: Block B (212 lines) is ~3.2x longer than Block A and mixes two extraction mechanics (some groups always return - classifier; some groups may fall through - mechanic (d) from APPLY-22) plus the method's only remaining direct `last_debug` write, so it was cut into two PRDs at the natural structural boundary after group 6.

Current result:
- main implementation commit: `52f071a`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice6.py`;
- extracted surface is one frozen dataclass `EnforceBlockBPart1Result` with a `Literal` outcome field (19 tags: 18 significant outcomes plus `not_matched`), an optional computed `return_text`, and an optional `last_debug_patch` - a pure classifier with zero `self` access;
- `not_matched` is a fall-through signal, not a normal outcome: `writer_agent.py` has no `if` branch for it at all, so control drops naturally into group 7 (line 898), which stays untouched - the same pattern already used for slice3/4/5 when no outcome matches;
- `_enforce_answer_compliance(...)` keeps all four `self`-methods (`_defer_no_stub_repair`, `_resolve_one_step_or_no_practice_fallback`, `_set_final_answer_shape_debug`, `_strip_optional_followup_invitation`) exclusively on the call site; the helper never calls or receives any of them;
- the method's only remaining direct `self.last_debug` write (`template_leakage_repair_deferred_to_gate`) is returned as an ordered `last_debug_patch` and applied by the caller strictly before `_set_final_answer_shape_debug`, preserving the original three-line sequence byte-for-byte - the same ordering discipline established in APPLY-22;
- `known_concept_prefirst_correlation`/`no_question_known_concept_correlation` and the neurostalking pair are preserved as four distinct classifier tags (two physically different conditions in the original each), merged only at the call site's dispatch, not inside the classifier - direct precedent from APPLY-26;
- `no_question_default_strip` computes `return_text` inside the helper via `re.sub(r"\s*\?+\s*", ". ", text).strip()`, matching the original inline computation exactly;
- boundaries matched the PRD's stated `804-896` exactly against live HEAD, with group 7 (line 898) confirmed physically untouched immediately below - no re-verification discrepancy;
- direct helper tests cover all 18 significant outcomes, `not_matched`, `return_text` computation across multiple inputs, the `last_debug` key-order guard for `practice_forbidden_unsolicited_repair`, and a group-2 priority-resolution case;
- dedicated APPLY-27 runner reuses the APPLY-20 `17`-case harness by import, builds a historical-before snapshot from commit `2dfc9dfb`, and proves byte-identical before/after output plus identical `last_debug` key ordering;
- `no_mutation_proof.md` reports `0` changed protected paths across the `23` canonical protected files (the accepted `22` plus `writer_agent_enforce_slice5.py`) and `0` changed paths under the accepted APPLY-20..26 log folders;
- clean-tree historical contract rerun across APPLY-6..APPLY-27 is fully green at `137/137`;
- the PRD-required isolated clean-worktree `pytest tests/ -k writer -q` baseline reports `19 failed, 286 passed, 2030 deselected, 190 warnings` - the same known failure set as prior PRDs;
- the owner workspace canonical writer run shows the known environment-specific `14 failed, 291 passed, 2030 deselected, 346 warnings` - an already-documented, unrelated warning.

## PRD-047.42-APPLY-26 _enforce_answer_compliance slice 5 Block A classifier
PRD-047.42-APPLY-26 follows the architect's direct technical decision that `mvp_free_branch_handoff` (a single delegating `self._enforce_mvp_free_dialogue_compliance(...)` call with no internal logic or `last_debug` writes) stays inline, by analogy with owner decision #3 on `provider_dispatch` - closing family 3 of the APPLY-20 map without a PRD. Reconnaissance of the remaining 278-line method tail found a natural split at the "known concept answer-first path" comment: Block A (66 lines, clean, zero `last_debug` writes, one terminal self-call) and Block B (212 lines, unreconnoitered, contains the method's only remaining `last_debug` write). This PRD extracts Block A whole.

Current result:
- main implementation commit: `ad12bf8`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice5.py`;
- extracted surface is one frozen dataclass `EnforceSlice5Result` with a `Literal` outcome field (fifteen values) plus an optional computed `return_text` - a pure classifier with zero `self` access;
- `_enforce_answer_compliance(...)` keeps the single `self._defer_no_stub_repair` call (for `user_repair_signal`) inline, dispatching on `slice5_result.outcome`; every literal response text is preserved verbatim, including intentional duplication across outcomes that historically shared one return string;
- `clarify_one_point_multi_questions` computes `return_text` inside the helper (first question-terminated segment of `text`), matching the original inline computation exactly;
- boundaries matched the PRD's stated `756-821` exactly against live HEAD, with `822` (Block B's opening comment) confirmed untouched immediately below - no re-verification discrepancy;
- direct helper tests cover all fifteen outcomes, `return_text` computation across multiple inputs, and an explicit proof that `give_short_support_primary` always wins over `give_short_support_len_or_flags`/`give_short_support_markers` - two outcomes that share the exact same gating predicate as `primary` (a strict OR-superset), making them structurally unreachable through the cascade; this is a preserved dead-code quirk from the original, not a defect introduced by decomposition;
- dedicated APPLY-26 runner reuses the APPLY-20 `17`-case harness by import, builds a historical-before snapshot from commit `787b7f0d`, and proves byte-identical before/after output plus identical `last_debug` key ordering;
- `no_mutation_proof.md` reports `0` changed protected paths across the `22` canonical protected files (the accepted `21` plus `writer_agent_enforce_slice4.py`) and `0` changed paths under the accepted APPLY-20..25 log folders;
- clean-tree historical contract rerun across APPLY-6..APPLY-26 is fully green at `134/134` (the APPLY-20 `rule_count` self-test stays green because APPLY-25 already retired its hard equality assertion);
- the PRD-required isolated clean-worktree `pytest tests/ -k writer -q` baseline reports `19 failed, 260 passed, 2027 deselected, 190 warnings` - the same known failure set as prior PRDs;
- the owner workspace canonical writer run shows the known environment-specific `14 failed, 265 passed, 2027 deselected, 346 warnings` - an already-documented, unrelated warning.

## PRD-047.42-APPLY-25 hygiene micro-PRD - retire live rule-count invariant
PRD-047.42-APPLY-25 resolves the honest finding recorded in APPLY-24: `test_prd_047_42_apply_20_enforce_compliance_mapping.py::test_rule_count_matches_boundary_map_inventory` live-walks the AST of `_enforce_answer_compliance` and asserted a hard `== 75`, an assumption that classifier-style decomposition (APPLY-23/24) permanently and legitimately breaks with every batched slice that collapses nested `if` cascades into flat dispatch checks.

Current result:
- main implementation commit: `b2c4c48`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- retired exactly one assertion (`assert len(rules) == 75`) and added a docstring explaining the expected drift, referencing this doc's v4.28 update and the APPLY-24 implementation report;
- kept the self-consistency assertion (`payload["metadata"]["rule_count"] == len(rules)`) and the `>= 40` sanity floor - both retain diagnostic value;
- left the other two test functions in the file, all production code, and every `TO_DO_LIST/logs/PRD-047.42-APPLY-20/` artifact completely untouched (`0`-diff proof in `no_mutation_proof.md`);
- the entire PRD diff is scoped to exactly one file;
- clean-tree historical contract rerun across APPLY-6..APPLY-25 is now `131/131` green (up from `130 passed, 1 failed` before this PRD);
- the canonical isolated writer baseline is unchanged at `19 failed, 240 passed, 2024 deselected, 190 warnings`, and the owner workspace baseline is unchanged at `14 failed, 245 passed, 2024 deselected, 346 warnings` - both identical to APPLY-24's numbers, confirming zero side effects beyond the one retired assertion.

## PRD-047.42-APPLY-24 _enforce_answer_compliance slice 4 R07-R16 batched obligation-repair classifier
PRD-047.42-APPLY-24 closes family 2 (`obligation_specific_repairs_before_profile_split`) of `_enforce_answer_compliance` in full, batching `R07-R16` (five independent rules) into one PRD per the owner's pace decision recorded in the v4.27 master plan update: families without reconnaissance-confirmed hidden complexity are cut whole, not rule-by-rule; the small-step law (Z-4) applies only where reconnaissance confirms real risk, as it did for `R03`/`R04`.

Current result:
- main implementation commit: `fa935d5`;
- push status: `pushed_to_origin_main`;
- status is `accepted_with_warning`;
- new helper module is `bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice4.py`;
- extracted surface is one frozen dataclass `EnforceSlice4Result` with a `Literal` outcome field (six values: `not_matched`, `literal_markdown_echo_mismatch`, `acknowledge_style_preference_repair`, `repair_and_answer_last_question_repair`, `answer_last_offer_repair`, `answer_knowledge_or_direct_repair`) plus optional `last_debug_patch`/`return_text`/`defer_signal`/`defer_must_answer` fields - a pure classifier with zero `self` access;
- `_enforce_answer_compliance(...)` keeps the single `self._defer_no_stub_repair` call inline in `writer_agent.py`, dispatched once with `signal`/`must_answer` from the classifier result; for `literal_markdown_echo_mismatch` the caller applies the ordered 2-key `last_debug_patch` (`format_request_repair_applied` first, `final_answer_shape` second) before returning `return_text` - the only `last_debug` write in the whole family, preserved in original order;
- boundaries matched the PRD's stated `690-745` exactly against live HEAD, with `746` (the MVP-free handoff) confirmed untouched immediately below - no re-verification discrepancy this time, unlike APPLY-23;
- direct helper tests cover all six outcomes individually, exact patch key order for the echo-mismatch outcome, correct `target` computation (and its fallback to `user_message`) for the repair-and-answer-last-question outcome, and a purity/idempotency check plus a source-scan confirming zero `self.` references in the helper module;
- dedicated APPLY-24 runner reuses the APPLY-20 `17`-case harness by import, builds a historical-before snapshot from commit `b39ed432`, and proves byte-identical before/after output plus identical `last_debug` key ordering;
- `no_mutation_proof.md` reports `0` changed protected paths across the `21` canonical protected files (the accepted `20` plus `writer_agent_enforce_slice3.py`) and `0` changed paths under the accepted APPLY-20/21/22/23 log folders;
- clean-tree historical contract rerun across APPLY-6..APPLY-24 reports `130 passed, 1 failed`; the single failure is an honestly-documented non-regression (see warning below);
- the PRD-required isolated clean-worktree `pytest tests/ -k writer -q` baseline reports `19 failed, 240 passed, 2024 deselected, 190 warnings` - the same known failure set as APPLY-20/21/22/23;
- honest warning #1: `test_prd_047_42_apply_20_enforce_compliance_mapping.py::test_rule_count_matches_boundary_map_inventory` now reports `67` instead of `75` `if`-nodes, because this APPLY-20 self-test live-walks the AST of `_enforce_answer_compliance` (not a frozen snapshot) and this PRD's batched classifier collapsed `10` physical `if` nodes (5 independent rule-pairs) into `2` dispatch `if` statements - `75 - 8 = 67` matches exactly. Proven non-regressive by 17/17 byte-identical before/after snapshots and an unchanged canonical failure list; the APPLY-20 test file itself was left untouched per the project's red line against modifying prior PRD tests;
- honest warning #2: the owner workspace canonical writer run still shows the known environment-specific `14 failed, 245 passed, 2024 deselected, 346 warnings` - a separate, already-documented warning unrelated to this PRD's surface.

## PRD-047.42-APPLY-23 _enforce_answer_compliance slice 3 R04 bounded practice classifier
PRD-047.42-APPLY-23 starts family 2 (`obligation_specific_repairs_before_profile_split`) of `_enforce_answer_compliance` after architect reconnaissance found it cleaner than family 1: six self-contained `if`/`return` rules with no shared local-variable preparation between them. Per law Z-4 (small steps where risk grows with size), family 2 is cut rule-by-rule rather than in one PRD; this PRD extracts only `R04` (`provide_one_bounded_practice`).

Current result:
- main implementation commit: `d7ef669`;
- push status: `pushed_to_origin_main`;
- status is `accepted_with_warning`;
- new helper module is `bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice3.py`;
- extracted surface is one frozen dataclass `EnforceSlice3BoundedPracticeResult` with a single `outcome` field (`Literal["not_matched", "be_strong", "defer_repair", "strip_followup"]`) - a pure classifier with zero `self` access and zero `last_debug` writes, since `R04` has no competing writes from neighboring rules (unlike APPLY-22's `close_gently`);
- `_enforce_answer_compliance(...)` keeps all three `self`-calls (`_set_final_answer_shape_debug`, `_defer_no_stub_repair`, `_strip_optional_followup_invitation`) and the literal `be_strong` response text inline in `writer_agent.py`, dispatching on `slice3_result.outcome`;
- boundary re-verification: the PRD's approximate line reference (`666-692`) was stale by 4 lines against live HEAD because the `be_strong` literal response is split across 3 string literals in current formatting; the actual span is `666-696`, confirmed to match the PRD's Step 2/3 code verbatim, so this was recorded as an honest correction rather than a STOP;
- grep confirms `practice_anchor_present`, `practice_step_present`, and `practice_multistep` are never read outside the extracted window;
- `R07` (`if literal_markdown_echo:`, historically line 698) stays untouched immediately below the helper call;
- direct helper tests cover all four classifier outcomes plus a purity/idempotency check and a source-scan confirming zero `self.`/`last_debug` references in the helper module;
- dedicated APPLY-23 runner reuses the APPLY-20 `17`-case harness by import, builds a historical-before snapshot from commit `ff9489c2`, and proves byte-identical before/after output plus identical `last_debug` key ordering;
- `no_mutation_proof.md` reports `0` changed protected paths across the `20` canonical protected files (the accepted `19` plus `writer_agent_enforce_slice2.py`) and `0` changed paths under the accepted APPLY-20/21/22 log folders;
- clean-tree historical contract rerun across APPLY-6..APPLY-23 passed `128/128`;
- the PRD-required isolated clean-worktree `pytest tests/ -k writer -q` baseline reports `19 failed, 228 passed, 2021 deselected, 190 warnings` - the same known failure set as APPLY-20/21/22;
- honest warning remains because the owner workspace canonical writer run still shows the known environment-specific `14 failed, 233 passed, 2021 deselected, 346 warnings`.

## PRD-047.42-APPLY-22 _enforce_answer_compliance slice 2 second prelude + close_gently
PRD-047.42-APPLY-22 closes family 1 (`intake_and_obligation_prelude`, `R01-R03`) of `_enforce_answer_compliance` after APPLY-21's verification found that the APPLY-20 map had underestimated the family's true width: a hidden second wave of `~16` locals sits between `R02` and `R03`, with `R03` (`close_gently`) physically nested inside it rather than after it. This is the project's first extracted window containing an early return with code after it that must not run when the return fires, so it introduces a new mechanic (d: extract-and-maybe-return) instead of the simple dataclass mechanic (c) used everywhere else.

Current result:
- main implementation commit: `c01b96c`;
- push status: `pushed_to_origin_main`;
- status is `accepted_with_warning`;
- new helper module is `bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice2.py`;
- extracted surface is one frozen dataclass `EnforceSlice2SecondPreludeResult` with a `close_gently_triggered: bool` flag, an ordered `last_debug_patch`, and locals that are `Optional` and valid only when the flag is `False`;
- `_enforce_answer_compliance(...)` keeps `R02` (`623-627`) and `R04` (`702+`) untouched immediately above/below the helper call, calls `self.last_debug.update(slice2_result.last_debug_patch)` first, and only afterward - strictly in that order - calls `self._set_final_answer_shape_debug("gentle_close")` and `return self._build_gentle_close_reply()` when `close_gently_triggered` is `True`, preserving the historical `self.last_debug` key order (`final_answer_shape` sixth, not first);
- the helper never receives `self._set_final_answer_shape_debug` or `self._build_gentle_close_reply` in any form, by design, to avoid corrupting that key order;
- the three module-level marker tuples (`_PRACTICE_MARKERS`, `_KNOWN_CONCEPT_CLARIFICATION_MARKERS`, `_EXTERNAL_SURVEILLANCE_MARKERS`) are passed into the helper as parameters instead of being relocated, avoiding a circular import (law Z-3);
- the now-unused `evaluate_concrete_answer_fit` import was removed from `writer_agent.py` because its only call site moved into the helper;
- direct helper tests cover both patch branches (`5` keys on the `close_gently` branch, `6` otherwise, exact order), an integration test proving `final_answer_shape` lands sixth (not first) in the true branch, and a marker-parameter substitution test;
- dedicated APPLY-22 runner reuses the APPLY-20 `17`-case harness by import, builds a historical-before snapshot from commit `f730754e`, and proves byte-identical before/after output plus identical `last_debug` key ordering;
- `grep_proof.md` confirms the historical `628-700` window is assignment-only for `self.last_debug` and confirms zero remaining direct uses of the removed `evaluate_concrete_answer_fit` import in `writer_agent.py`;
- `no_mutation_proof.md` reports `0` changed protected paths across the `19` canonical protected files (the accepted `18` plus `writer_agent_enforce_slice1.py`) and `0` changed paths under the accepted APPLY-20/APPLY-21 log folders;
- clean-tree historical contract rerun across APPLY-6..APPLY-22 passed `125/125`;
- the PRD-required isolated clean-worktree `pytest tests/ -k writer -q` baseline reports `19 failed, 220 passed, 2018 deselected, 190 warnings` - the same known failure set as APPLY-20/APPLY-21;
- honest warning remains because the owner workspace canonical writer run still shows the known environment-specific `14 failed, 225 passed, 2018 deselected, 346 warnings`, so final delivery records both numbers explicitly rather than flattening them into one false certainty.

## PRD-047.42-APPLY-21 _enforce_answer_compliance slice 1 prelude
PRD-047.42-APPLY-21 starts the first real code transfer inside `WriterAgent._enforce_answer_compliance(...)` after the accepted APPLY-20 map. The extracted surface is intentionally the full always-executed prelude window before `R02`: one continuous `120`-line block that builds `44` locals from the contract/context and writes the first `10` ordered `last_debug` fields, but does not yet enter any rule family with early returns. This keeps the first apply slice behaviorally total over the existing `17`-case harness instead of pretending that the uncovered `53/75` rule gap is already solved.

Current result:
- main implementation commit: `37a2c2f`;
- push status: `pushed_to_origin_main`;
- status is `accepted_with_warning`;
- new helper module is `bot_psychologist/bot_agent/multiagent/agents/writer_agent_enforce_slice1.py`;
- extracted surface is one frozen dataclass `EnforceSlice1PreludeResult` with exactly `44` locals in assignment order plus one ordered `last_debug_patch`;
- `_enforce_answer_compliance(...)` keeps `text` + `R01` inline above the helper call, keeps `R02` and everything below untouched, replaces the prelude with one helper call, explicit unpack of all `44` locals, and one `self.last_debug.update(...)`;
- direct helper tests pass on field order, representative field values, ordered debug-patch insertion, and contract immutability;
- dedicated APPLY-21 runner reuses the APPLY-20 `17`-case harness by import, builds a historical-before snapshot from commit `ab7ec52`, and proves byte-identical before/after output plus identical `last_debug` key ordering;
- `grep_proof.md` confirms that historical lines `587-706` contain `10` `self.last_debug[...] = ...` writes and no in-range reads, and confirms zero remaining direct uses in `writer_agent.py` for the removed local detector imports;
- `no_mutation_proof.md` reports `0` changed protected paths across the accepted writer helper/mixin/call-llm surface and `0` changed paths under the accepted APPLY-20 log folder;
- clean-tree historical contract rerun across APPLY-6 + APPLY-7 + APPLY-8 + APPLY-9 + APPLY-10 + APPLY-11 + APPLY-12 + APPLY-13 + APPLY-14 + APPLY-15 + APPLY-16 + APPLY-17 + APPLY-18 + APPLY-19 + APPLY-20 + APPLY-21 passed `122/122`;
- the PRD-required isolated clean-worktree `pytest tests/ -k writer -q` baseline reports `19 failed, 215 passed, 2015 deselected, 190 warnings`;
- honest warning remains because the owner workspace canonical writer run still shows the known environment-specific `14 failed, 220 passed, 2015 deselected, 346 warnings`, so final delivery records both numbers explicitly rather than flattening them into one false certainty.

## PRD-047.42-APPLY-20 _enforce_answer_compliance boundary mapping
PRD-047.42-APPLY-20 turns the next giant writer method into an evidence-backed decomposition target without moving any production code. The work maps `WriterAgent._enforce_answer_compliance(...)` as a `610`-line ordered rule cascade, proves deterministic behavior on named `(response_text, contract)` cases, and records honest coverage gaps before any future apply slice touches the method.

Current result:
- main implementation commit: `ce37f03`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new runner is `TO_DO_LIST/tools/run_prd_047_42_apply_20_enforce_compliance_mapping.py`;
- boundary map records `75` ordered rules with exact line spans, early-return markers, and locals-read lists;
- snapshot harness covers `17` deterministic cases and reproduces identical output on double build with `generated_at_utc == NORMALIZED_TIMESTAMP`;
- coverage log records `22` covered rules and `53` uncovered rules explicitly, with reasons instead of papering them over;
- clean-tree historical contract rerun across APPLY-6 + APPLY-7 + APPLY-9 + APPLY-10 + APPLY-11 + APPLY-12 + APPLY-13 + APPLY-14 + APPLY-15 + APPLY-16 + APPLY-17 + APPLY-18 + APPLY-19 + APPLY-20 passed `40/40`;
- the PRD-required isolated clean-worktree `pytest tests/ -k writer -q` baseline reports `19 failed, 213 passed, 2010 deselected, 190 warnings`;
- `no_mutation_proof.md` reports `0` changed protected paths across the canonical `17` protected files plus `writer_agent_call_llm_slice12.py` and whole `writer_agent.py`;
- `git diff --name-only -- bot_psychologist/bot_agent` is empty, so the mapping PRD kept the runtime surface untouched exactly as required;
- default next step is `PRD-047.42-APPLY-21`: first decomposition slice for one continuous non-MVP `_enforce_answer_compliance` rule family.

## PRD-047.42-APPLY-19 _call_llm slice 12
PRD-047.42-APPLY-19 closes the last movable `_call_llm` cluster after the accepted APPLY-18 owner decision that `provider_dispatch` must stay inline. The work moves only the `response_unpack_cost_and_return` tail out of the inline method body, preserving the exact `result.text` identity, the tuple-unpack of `tokens_*`, the single keyword call into the protected `_estimate_cost` method, the module-level `time.perf_counter()` timing seam that the snapshot harness monkeypatches, and the ordered `13`-key `last_debug` patch.

Current result:
- main implementation commit: `4d92228`;
- push status: `pushed_to_origin_main`;
- status is `accepted_with_warning`;
- new helper module is `writer_agent_call_llm_slice12.py`;
- extracted surface is one frozen dataclass carrying the original `llm_response` object plus one ordered `13`-key `last_debug_patch`;
- direct slice-12 helper tests passed `3/3`, including exact tuple unpacking, one keyword-only `_estimate_cost` call, deterministic `duration_ms=123` through module-level `time.perf_counter`, exact `13`-key patch order, and object-identity preservation for `result.text`;
- new runner contract tests passed `3/3`;
- accepted before/after `_call_llm` snapshot is byte-identical against the accepted APPLY-18 baseline across all `3` scenarios, and `user_prompt_equivalence.md` proves line-by-line and SHA1-level identity of the exact prompt text sent to the LLM;
- `no_mutation_proof.md` reports `0` changed protected paths across the `17` protected files, explicitly including unchanged `writer_agent_fallback_state_mixin.py`;
- `_call_llm` now keeps only helper calls, the single `WRITER_USER_TEMPLATE.format(...)` render, the inline `await create_agent_completion(...)` preserved by owner decision #3, and the final `return llm_response`;
- the clean-tree historical contract rerun across APPLY-6..19 passed `37/37` after the main implementation commit landed on `main`;
- the PRD-required isolated clean-worktree `pytest tests/ -k writer -q` baseline reports `19 failed, 213 passed, 2010 deselected, 190 warnings`;
- the owner workspace itself currently reports `14 failed, 218 passed, 2010 deselected, 346 warnings` for the same canonical command, so this PRD is recorded with an honest environment warning rather than as a response-tail regression.

## PRD-047.42-APPLY-18 _call_llm slice 11
PRD-047.42-APPLY-18 continues the post-render `_call_llm` decomposition phase after APPLY-17 by moving the `runtime_settings_and_system_prompt_selection` cluster out of the inline method body. The work preserves the third `dialogue_profile` namesake rule in the series: the helper receives the old local profile as the default input, normalizes the ctx override if present, returns the new value, and `_call_llm` rebinds the local variable explicitly before provider dispatch. It also preserves the first bound-method dependency in the decomposition track by passing `self._resolve_runtime_settings` into the helper as a callable rather than copying or mutating the lifecycle mixin.

Current result:
- main implementation commit: `076d916`;
- push status: `pushed_to_origin_main`;
- status is `accepted_with_warning`;
- new helper module is `writer_agent_call_llm_slice11.py`;
- extracted surface is one frozen dataclass carrying reassigned `dialogue_profile`, resolved `runtime_settings`, selected `system_prompt`, and one ordered `2`-key `last_debug_patch`;
- direct slice-11 helper tests passed `3/3`, including default-vs-ctx profile precedence, both `system_prompt` branches, exact keyword-call semantics into `resolve_runtime_settings`, and exact `["system_prompt", "dialogue_profile"]` patch order;
- new runner contract tests passed `3/3`;
- accepted before/after `_call_llm` snapshot is byte-identical across all `3` scenarios, and `user_prompt_equivalence.md` proves line-by-line and SHA1-level identity of the exact prompt text sent to the LLM;
- `no_mutation_proof.md` reports `0` changed protected paths across the `16` protected files, explicitly including unchanged `writer_agent_lifecycle_mixin.py` and `writer_agent_prompts.py`;
- zero-match grep confirmed that `WRITER_SYSTEM` and `WRITER_SYSTEM_MVP_FREE_DIALOGUE` no longer have direct usage in `writer_agent.py`, so only those names were removed from its imports while `WRITER_USER_TEMPLATE` stayed;
- clean-tree historical contract rerun passed `34/34` across APPLY-6 + APPLY-7 + APPLY-9 + APPLY-10 + APPLY-11 + APPLY-12 + APPLY-13 + APPLY-14 + APPLY-15 + APPLY-16 + APPLY-17 + APPLY-18;
- the PRD-required broad writer baseline is reproduced on a clean isolated worktree with the APPLY-18 files copied in (`19 failed, 210 passed, 2007 deselected, 190 warnings`);
- the owner workspace itself currently reports `14 failed, 215 passed, 2007 deselected, 346 warnings` for the same canonical command because `5` environment-sensitive writer tests pass under the full local sibling-workspace context, so this PRD is recorded with an honest environment warning rather than as a prompt/decomposition regression.

## PRD-047.42-APPLY-17 _call_llm slice 10
PRD-047.42-APPLY-17 starts the post-`WRITER_USER_TEMPLATE.format(...)` decomposition phase inside `_call_llm` by moving the `prompt_constraint_append_and_debug_bookkeeping` cluster out of the inline method body. The work preserves the only remaining prompt-mutating branch after render, keeps the exact ordered `18`-key `last_debug` patch, preserves the deliberate asymmetry between `prompt_constraint_decision is not None` and `isinstance(prompt_constraint_decision, dict)`, and proves byte-identical behavior on the accepted 3-scenario `_call_llm` snapshot plus explicit direct coverage of the append branch that the snapshot harness never hits.

Current result:
- main implementation commit: `364aff9`;
- push status: `pushed_to_origin_main`;
- status is `accepted_with_warning`;
- new helper module is `writer_agent_call_llm_slice10.py`;
- extracted surface is one frozen dataclass carrying the final `user_prompt` and one ordered `last_debug_patch`;
- direct slice-10 helper tests passed `3/3`, including both prompt-section branches and the exact `18`-key insertion order assertion;
- new runner contract tests passed `3/3`;
- accepted before/after `_call_llm` snapshot is byte-identical across all `3` scenarios, and `user_prompt_equivalence.md` proves line-by-line and SHA1-level identity of the exact prompt text sent to the LLM;
- `no_mutation_proof.md` reports `0` changed protected paths, and the old direct `format_prompt_constraint_section_v1` import was removed only after a zero-match grep confirmed that `writer_agent.py` no longer uses it directly;
- clean-tree historical contract rerun passed `31/31` across APPLY-6 + APPLY-7 + APPLY-9 + APPLY-10 + APPLY-11 + APPLY-12 + APPLY-13 + APPLY-14 + APPLY-15 + APPLY-16 + APPLY-17;
- the PRD-required broad writer baseline is reproduced on a clean isolated worktree with the APPLY-17 files copied in (`19 failed, 207 passed, 2004 deselected, 190 warnings`);
- the owner workspace itself currently reports `14 failed, 212 passed, 2004 deselected, 346 warnings` for the same canonical command because `5` environment-sensitive writer tests pass under the full local sibling-workspace context, so this PRD is recorded with an honest environment warning rather than as a prompt/decomposition regression.

## PRD-047.42-APPLY-16 _call_llm slice 9
PRD-047.42-APPLY-16 closes the `WRITER_USER_TEMPLATE.format(...)` decomposition roadmap inside `_call_llm` by moving the final mapped render families out of inline prompt assembly: `retrieval_decision`, `human_like_answer_policy`, and `final_answer_shape_and_constraint_resolution`. The work keeps the same single render call, preserves the mirrored semantic trap where `constraint_resolution_profile` must default from the already-normalized local `dialogue_profile` instead of a fresh `ctx.get(...)`, leaves `mvp_free_dialogue_overrides=mvp_override_block` inline as the final pure passthrough, and proves byte-identical behavior on the accepted 3-scenario `_call_llm` snapshot including exact `user_prompt` text and full `last_debug`.

Current result:
- main implementation commit: `c57807e`;
- push status: `pushed_to_origin_main`;
- status is `accepted_with_warnings`;
- new helper module is `writer_agent_call_llm_slice9.py`;
- extracted surface is one typed dataclass carrying the final `33` computed prompt-argument values from the remaining mapped render families;
- the accepted before/after snapshot is byte-identical across all `3` scenarios, and `user_prompt_equivalence.md` proves line-by-line and SHA1-level identity of the exact prompt text sent to the LLM;
- direct slice-9 helper tests passed `3/3`;
- new runner contract tests passed `3/3`;
- clean-tree historical contract rerun passed `28/28` across APPLY-6 + APPLY-7 + APPLY-9 + APPLY-10 + APPLY-11 + APPLY-12 + APPLY-13 + APPLY-14 + APPLY-15 + APPLY-16;
- the broad writer subset currently reports `12 failed, 211 passed, 346 warnings` with `PYTHONPATH=bot_psychologist`; this wider suite background is recorded as an honest warning and not as slice-9 prompt-render regression evidence;
- protected previously accepted files remained unchanged under diff/hash proof, including slice-1 through slice-8 helpers, writer mixins, `writer_contract.py`, and the `admin_routes` split modules.

## PRD-047.42-APPLY-15 _call_llm slice 8
PRD-047.42-APPLY-15 continues the `WRITER_USER_TEMPLATE.format(...)` decomposition track by moving the next two fully ctx-driven argument families out of inline prompt assembly: `response_planner` plus `dialogue_profile_and_pragmatics`. The work keeps the same single render call, preserves the intentionally separate `dialogue_profile` `ctx.get(...)` expression instead of collapsing it into the earlier local variable, and proves byte-identical behavior on the accepted 3-scenario `_call_llm` snapshot including exact `user_prompt` text and full `last_debug`.

Current result:
- main implementation commit: `04bac53`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `writer_agent_call_llm_slice8.py`;
- extracted surface is one typed dataclass carrying the `30` computed prompt-argument values from the two accepted families;
- every moved field remains a direct copy of the original `ctx.get(..., literal_default)` family, including list-to-csv normalization, float coercion, and the intentionally fresh `dialogue_profile` `ctx.get(...)` expression inside this slice;
- the accepted before/after snapshot is byte-identical across all `3` scenarios, and `user_prompt_equivalence.md` proves line-by-line and SHA1-level identity of the exact prompt text sent to the LLM;
- direct slice-8 helper tests passed `3/3`;
- new runner contract tests passed `3/3`;
- clean-tree historical contract rerun passed `25/25` across APPLY-6 + APPLY-7 + APPLY-9 + APPLY-10 + APPLY-11 + APPLY-12 + APPLY-13 + APPLY-14 + APPLY-15;
- the known focused baseline failure `test_semantic_hits_limit_to_two` remains pre-existing and unchanged;
- protected previously accepted files remained unchanged under diff/hash proof, including slice-1/slice-2/slice-3/slice-4/slice-5/slice-6/slice-7 helpers, writer mixins, `writer_contract.py`, and the `admin_routes` split modules.

## PRD-047.42-APPLY-14 _call_llm slice 7
PRD-047.42-APPLY-14 continues the `WRITER_USER_TEMPLATE.format(...)` decomposition track by moving the next two fully ctx-driven argument families out of inline prompt assembly: `fresh_chat_and_context_package` plus `active_line`. The work keeps the same single render call, has no passthrough exceptions in this slice, and proves byte-identical behavior on the accepted 3-scenario `_call_llm` snapshot including exact `user_prompt` text and full `last_debug`.

Current result:
- main implementation commit: `d0c2a93`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `writer_agent_call_llm_slice7.py`;
- extracted surface is one typed dataclass carrying the `25` computed prompt-argument values from the two accepted families;
- every moved field remains a direct copy of the original `ctx.get(..., literal_default)` family, including integer coercion, bool normalization, and empty-string fallback behavior;
- the accepted before/after snapshot is byte-identical across all `3` scenarios, and `user_prompt_equivalence.md` proves line-by-line and SHA1-level identity of the exact prompt text sent to the LLM;
- direct slice-7 helper tests passed `3/3`;
- new runner contract tests passed `3/3`;
- clean-tree historical contract rerun passed `22/22` across APPLY-6 + APPLY-7 + APPLY-9 + APPLY-10 + APPLY-11 + APPLY-12 + APPLY-13 + APPLY-14;
- protected previously accepted files remained unchanged under diff/hash proof, including slice-1/slice-2/slice-3/slice-4/slice-5/slice-6 helpers, writer mixins, `writer_contract.py`, and the `admin_routes` split modules.

## PRD-047.42-APPLY-13 _call_llm slice 6
PRD-047.42-APPLY-13 continues the `WRITER_USER_TEMPLATE.format(...)` decomposition track by moving the next two fully ctx-driven argument families out of inline prompt assembly: `final_answer_directive` plus `legacy_and_grounding_visibility`. The work keeps the same single render call, has no passthrough exceptions in this slice, and proves byte-identical behavior on the accepted 3-scenario `_call_llm` snapshot including exact `user_prompt` text and full `last_debug`.

Current result:
- main implementation commit: `3291a40`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `writer_agent_call_llm_slice6.py`;
- extracted surface is one typed dataclass carrying the `22` computed prompt-argument values from the two accepted families;
- every moved field remains a direct copy of the original `ctx.get(..., literal_default)` family, including bool normalization and literal fallback behavior;
- the accepted before/after snapshot is byte-identical across all `3` scenarios, and `user_prompt_equivalence.md` proves line-by-line and SHA1-level identity of the exact prompt text sent to the LLM;
- direct slice-6 helper tests passed `3/3`;
- clean-tree historical contract rerun passed `19/19` across APPLY-6 + APPLY-7 + APPLY-9 + APPLY-10 + APPLY-11 + APPLY-12 + APPLY-13;
- protected previously accepted files remained unchanged under diff/hash proof, including slice-1/slice-2/slice-3/slice-4/slice-5 helpers, writer mixins, `writer_contract.py`, and the `admin_routes` split modules.

## PRD-047.42-APPLY-12 _call_llm slice 5
PRD-047.42-APPLY-12 continues the `WRITER_USER_TEMPLATE.format(...)` decomposition track by moving the next two already-computed argument families out of inline prompt assembly: `writer_kb_payload_and_knowledge_answer` plus `philosophy_kernel_and_writer_freedom`. The work keeps the same single render call, preserves the four mandated inline passthrough kwargs, and proves byte-identical behavior on the accepted 3-scenario `_call_llm` snapshot including exact `user_prompt` text and full `last_debug`.

Current result:
- main implementation commit: `3d3abe8`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `writer_agent_call_llm_slice5.py`;
- extracted surface is one typed dataclass carrying the `23` computed prompt-argument values from the two accepted families;
- the four inline passthrough kwargs intentionally remain in `writer_agent.py`: `writer_kb_payload_text`, `practice_ban_instruction`, `known_concept_clarification_ban`, and `external_surveillance_frame_ban`;
- the accepted before/after snapshot is byte-identical across all `3` scenarios, and `user_prompt_equivalence.md` proves line-by-line and SHA1-level identity of the exact prompt text sent to the LLM;
- direct slice-5 helper tests passed `3/3`;
- clean-tree historical contract rerun passed `16/16` across APPLY-6 + APPLY-7 + APPLY-9 + APPLY-10 + APPLY-11 + APPLY-12;
- protected previously accepted files remained unchanged under diff/hash proof, including slice-1/slice-2/slice-3/slice-4 helpers, writer mixins, `writer_contract.py`, and the `admin_routes` split modules.

## PRD-047.42-APPLY-11 _call_llm slice 4
PRD-047.42-APPLY-11 starts the `WRITER_USER_TEMPLATE.format(...)` decomposition track without splitting the render call itself. The work moves the first `39` argument expressions out of inline prompt assembly into `writer_agent_call_llm_slice4.py`, keeps the same single `WRITER_USER_TEMPLATE.format(...)` call, preserves `conversation_context=formatted_context` inline, and proves byte-identical behavior on the accepted 3-scenario `_call_llm` snapshot including exact `user_prompt` text and full `last_debug`.

Current result:
- main implementation commit: `0c35d2f`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `writer_agent_call_llm_slice4.py`;
- extracted surface is one typed dataclass carrying the first `39` prompt-argument fields from the five accepted families: unified dialogue policy, dialogue act/offer state, dialogue style/answer obligation, diagnostic card/writer move, and context budget/profile;
- `writer_move_instruction_summary` intentionally remains raw `ctx.get(...) or "нет"` without a new `str()` wrapper;
- the accepted before/after snapshot is byte-identical across all `3` scenarios, and the dedicated `user_prompt_equivalence.md` report proves line-by-line and hash-level identity of the exact prompt text sent to the LLM;
- direct slice-4 helper tests passed `3/3`;
- new runner contract tests passed `3/3`;
- clean-tree historical contract rerun passed `13/13` across APPLY-6 + APPLY-7 + APPLY-9 + APPLY-10 + APPLY-11;
- protected previously accepted files remained unchanged under diff/hash proof, including slice-1/slice-2/slice-3 helpers, writer mixins, `writer_contract.py`, and the `admin_routes` split modules.

## PRD-047.42-APPLY-10 _call_llm slice 3
PRD-047.42-APPLY-10 completes the first state-coupled extraction inside `WriterAgent._call_llm` after the pure ctx-only slices and the APPLY-8 stale-test repair. The work moves only the mapped `writer_kb_payload_and_trace_capture` cluster into `writer_agent_call_llm_slice3.py`, returns exactly two cross-boundary outputs (`writer_kb_payload_text` and `last_debug_patch`), preserves the same downstream prompt input, and proves that one `self.last_debug.update(...)` call yields a byte-identical full debug surface compared to the previous seven inline assignments.

Current result:
- main implementation commit: `f726aa1`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `writer_agent_call_llm_slice3.py`;
- the accepted 3-scenario `_call_llm` snapshot is byte-identical before vs after, including full `last_debug` for every scenario rather than only `llm_response`;
- direct slice-3 helper tests passed `3/3`;
- new runner contract tests passed `2/2`;
- clean-tree historical rerun over APPLY-6 + APPLY-7 + APPLY-9 contracts passed `8/8`;
- targeted writer KB payload integration tests passed `3/3`;
- protected previously accepted files remained unchanged under diff/hash proof, including slice-1/slice-2 helpers, writer mixins, `writer_contract.py`, and the `admin_routes` split modules;
- the known focused baseline failure `test_semantic_hits_limit_to_two` remains pre-existing and out of scope.

## PRD-047.42-APPLY-9 _call_llm slice 2
PRD-047.42-APPLY-9 resumes the real `_call_llm` decomposition track after the APPLY-8 test-debt repair and stays strictly inside one mapped pre-provider cluster: `request_detectors_and_mvp_override_block`. The work moves only the current live lines `275-348` out of `WriterAgent._call_llm`, keeps the same downstream local variable names through explicit unpacking, preserves the same byte-identical three-scenario `_call_llm` snapshot, and leaves provider dispatch, response parsing, `writer_kb_payload_and_trace_capture`, `writer_contract.py`, and all admin decomposition files untouched.

Current result:
- main implementation commit: `0d9e6bb`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `writer_agent_call_llm_slice2.py`;
- exported slice-2 surface is intentionally limited to `5` cross-cluster values: `explicit_answer_need`, `sarcasm_or_negative_feedback`, `repair_user_dissatisfaction`, `overruled_constraints`, and `mvp_override_block`;
- the `9` detector/intermediate names confirmed as `local_only` by the accepted APPLY-6 dependency map stay internal to the helper and do not widen `_call_llm` namespace;
- required before/after `_call_llm` snapshot is byte-identical across `safe_guided_direct`, `mvp_free_overview`, and `mvp_free_rich_request`;
- protected previously accepted files remain unchanged under diff/hash proof, including slice-1 helper, all writer mixins/helpers from earlier PRDs, `writer_contract.py`, and the `admin_routes` split modules;
- the focused writer subset still carries the same single pre-existing failure `test_semantic_hits_limit_to_two`, which remains out of scope and unchanged;
- the clean-tree historical contract rerun now passes `8/8` across APPLY-6 + APPLY-7 + APPLY-9 once the main implementation commit removed the working diff seen by the old `no_mutation` assertion.

## PRD-047.42-APPLY-8 frozen variable-inventory baseline
PRD-047.42-APPLY-8 closes a narrow structural-test debt exposed right after the first real `_call_llm` slice. The broken contract was not signaling behavior drift in `WriterAgent`; it was re-parsing the live `_call_llm` structure and comparing it to expectations frozen before the first slice. The fix freezes the accepted APPLY-6 variable inventory from commit `e5f5f32` into a dedicated JSON fixture, rewrites only `test_variable_inventory_contains_expected_spine_variables` to read that baseline, and extends the APPLY-6 runner with an optional `source_text` path for historical analysis without changing the default live analysis path.

Current result:
- main implementation commit: `e615581`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new frozen fixture is `bot_psychologist/tests/contract/fixtures/prd_047_42_apply_6_variable_inventory_baseline.json`;
- fixture provenance explicitly records `source_commit=e5f5f32`;
- `test_prd_047_42_apply_6_call_llm_boundary_mapping.py` is green again at `4/4`;
- the APPLY-7 contract runner remains green at `2/2`;
- live `build_variable_inventory()` output on the current `writer_agent.py` is byte-identical before vs after this PRD when called without `source_text`;
- protected production files remain untouched under diff proof, including `writer_agent.py`, all extracted writer helper/mixin files, `writer_contract.py`, and the `admin_routes` split modules;
- the focused writer subset still carries the same single pre-existing failure `test_semantic_hits_limit_to_two`, which remains out of scope and unchanged.

## PRD-047.42-APPLY-7 _call_llm slice 1
PRD-047.42-APPLY-7 completed the first real extraction inside `WriterAgent._call_llm` and stayed strictly inside the two pure, no-`self.last_debug` clusters mapped by PRD-047.42-APPLY-6. The work moved the adjacent `knowledge_practice_kernel_inputs` and `dialogue_policy_and_context_budget` clusters out of the inline method body, preserved the same downstream local variable names through explicit unpacking, and left provider dispatch, response parsing, prompt rendering, and all state-coupled debug-writing clusters untouched.

Current result:
- main implementation commit: `9249f04`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- new helper module is `writer_agent_call_llm_slice1.py`;
- the extracted helper surface is one explicit function returning one typed dataclass, not two separate helpers and not a `locals().update()` trick;
- `practice_gate` deliberately stays local inside the helper because the accepted dependency map marked it `local_only`;
- the focused baseline remained behavior-equivalent before vs after: the same single pre-existing failure stayed (`test_semantic_hits_limit_to_two`), while the after-set ended at `1 failed, 58 passed, 58 warnings`;
- the required three-scenario `_call_llm` snapshot is byte-identical before vs after, including `safe_guided_direct`, `mvp_free_overview`, and `mvp_free_rich_request`;
- previously accepted helper/mixin/admin/contract files remained byte-identical under diff/hash proof.

## PRD-047.42-APPLY-6 _call_llm boundary mapping
PRD-047.42-APPLY-6 completed a read-only boundary-mapping pass over `WriterAgent._call_llm` and stayed strictly inside the Stage-2 decomposition track for `writer_agent.py`. It did not move any production code. Instead, it produced an exact internal map for the remaining `804`-line giant method, classified stateful vs helper-friendly clusters, captured a 3-scenario `_call_llm` snapshot baseline with mocked provider dispatch, and proved zero diffs across the protected production files.

Current result:
- main implementation commit: `e5f5f32`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- `_call_llm` is now mapped into `11` contiguous clusters from client/bootstrap through provider dispatch and response parse;
- the true provider boundary is confirmed at lines `902-912`, while the heaviest remaining pre-provider responsibility is still `WRITER_USER_TEMPLATE.format(...)` at `454-842`;
- the earliest clearly state-coupled preparation cluster begins at `407-453`, where prompt preparation starts writing into `self.last_debug`;
- a full local-variable dependency inventory was generated for `_call_llm`, including scope classification (`writer_prompt_input`, `provider_dispatch_input`, `local_only`);
- snapshot baseline now covers `safe_guided_direct`, `mvp_free_overview`, and `mvp_free_rich_request` with mocked `create_agent_completion` and full `self.last_debug` export;
- protected files stayed byte-identical under diff/blob-hash proof, including `writer_agent.py`, all four extracted writer helper/mixin files, `writer_contract.py`, `admin_routes.py`, and the `10` admin decomposition modules;
- the next recommended real cut is not provider dispatch first, but the smallest pre-provider extraction edge around runtime/system-prompt selection plus selected pure/default-formatting helpers.

## PRD-047.42-APPLY-5 writer_agent slice 4
PRD-047.42-APPLY-5 completed the fourth bounded `writer_agent.py` apply slice and stayed strictly inside the mapped lifecycle spine from PRD-047.42. The work moved `_resolve_runtime_settings()` and the public `write()` entrypoint into a dedicated `WriterAgentLifecycleMixin`, preserved `__init__` / `_resolve_model` in the main class, kept `write()` behavior byte-for-byte stable on the required four-path snapshot gate, and left the remaining giant writer methods untouched.

Current result:
- main implementation commit: `a419ead`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- extracted lifecycle methods are `_resolve_runtime_settings` and `write`;
- `WriterAgent` now inherits as `WriterAgent(WriterAgentLifecycleMixin, WriterAgentFallbackStateMixin)`;
- explicit MRO order is deliberate: lifecycle comes first because `write()` is the public entrypoint and depends on slice-3 fallback helpers through `self`;
- added thin `_get_temperature_for_agent()` compat wrapper so existing monkeypatch-based contract tests against `bot_agent.multiagent.agents.writer_agent` keep working after the move;
- required write-path before/after snapshot is identical across `safety_success`, `safety_exception`, `normal_empty`, and `normal_exception`;
- `writer_agent_constants.py`, `writer_agent_fallback_helpers.py`, `writer_agent_fallback_state_mixin.py`, `writer_contract.py`, `admin_routes.py`, and all `10` admin decomposition modules remained byte-identical under diff/blob-hash proof;
- the focused baseline stayed behavior-equivalent before vs after: the same single pre-existing failure remained (`test_semantic_hits_limit_to_two`), while new direct lifecycle coverage passed and the after-set ended at `1 failed, 53 passed, 58 warnings`;
- additional external/contract verification over orchestrator/trace/knowledge-answer/boundary-map callers passed `24/24`.

## PRD-047.42-APPLY-4 writer_agent slice 3
PRD-047.42-APPLY-4 completed the third bounded `writer_agent.py` apply slice and stayed strictly inside the mapped self-bound fallback/state surface from PRD-047.42. The work moved eight `self`-bound methods plus three local constants into a dedicated `WriterAgentFallbackStateMixin`, preserved existing call sites through normal inheritance, and kept the remaining giant writer methods untouched.

Current result:
- main implementation commit: `fadd43f`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- extracted stateful helpers are `_repair_greeting_without_mechanism_lecture`, `_resolve_one_step_or_no_practice_fallback`, `_set_final_answer_shape_debug`, `_defer_no_stub_repair`, `_get_client`, `_estimate_cost`, `_apply_name_continuity`, and `_extract_user_name`;
- the moved constants are `_COST_PER_1K_TOKENS`, `_RU_NAME_PATTERNS`, and `_EN_NAME_PATTERNS`;
- the mixin approach was chosen deliberately because these methods mutate `self.last_debug`, `self._client`, and call each other through `self`, so free functions would have increased risk;
- `_PRACTICE_MARKERS` intentionally stayed owned by `writer_agent.py` and is exposed to the mixin through a class attribute bridge;
- `writer_agent_constants.py`, `writer_agent_fallback_helpers.py`, `writer_contract.py`, `admin_routes.py`, and all `10` admin decomposition modules remained byte-identical under git diff/blob-hash proof;
- the focused baseline stayed behavior-equivalent before vs after: the same single pre-existing failure remained (`test_semantic_hits_limit_to_two`), while new direct mixin coverage passed and the after-set ended at `1 failed, 48 passed, 58 warnings`.

## PRD-047.42-APPLY-3 writer_agent slice 2
PRD-047.42-APPLY-3 completed the second bounded `writer_agent.py` apply slice and stayed strictly inside the mapped fallback/static surface from PRD-047.42. The work moved eight existing `@staticmethod` helper bodies into a dedicated fallback-helper module, preserved the class-level surface with thin delegates, and kept all non-static `WriterAgent` methods untouched.

Current result:
- main implementation commit: `b918b44`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- extracted helpers are `_build_gentle_close_reply`, `_build_no_practice_fallback_text`, `_strip_optional_followup_invitation`, `_detect_language`, `_format_hits`, `_format_diagnostic_summary`, `_static_fallback`, and `_normalize_name`;
- delegate strategy was chosen deliberately so existing `self._...` call sites and current `WriterAgent._detect_language(...)` tests stayed stable without broader rewrites;
- `writer_agent_constants.py`, `writer_contract.py`, `admin_routes.py`, and all `10` admin decomposition modules remained byte-identical under SHA-256 proof;
- the focused baseline stayed behavior-equivalent before vs after: the same single pre-existing failure remained (`test_semantic_hits_limit_to_two`), while new direct fallback-helper coverage passed `8/8`.

## PRD-047.42-APPLY-2 writer_agent slice 1
PRD-047.42-APPLY-2 completed the first bounded `writer_agent.py` apply slice and stayed strictly inside the Stage-1 map accepted in PRD-047.42. The work moved only four already-pure module-level helpers into a dedicated helper module, preserved all in-file call names, left every `WriterAgent` method body untouched, and added direct tests for the extracted helpers.

Current result:
- main implementation commit: `1051e68`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- extracted helpers are `_extract_literal_markdown_echo_request`, `_to_int`, `_to_float`, and `_contains_any`;
- the supporting `_LITERAL_MARKDOWN_ECHO_PATTERNS` constant moved unchanged with the markdown-echo helper to avoid circular import pressure;
- `writer_contract.py`, `admin_routes.py`, and all `10` admin decomposition modules remained byte-identical under SHA-256 proof;
- the focused baseline stayed behavior-equivalent before vs after: the same single pre-existing failure remained (`test_semantic_hits_limit_to_two`), while new direct helper coverage passed `5/5`.

## PRD-047.42-APPLY admin_routes decomposition
PRD-047.42-APPLY completed the first real Stage-2 god-file decomposition slice and stayed strictly bounded to `bot_psychologist/api/admin_routes.py`. The work moved the mapped admin surface into `10` focused modules plus a thin aggregator, while preserving the external `main.py` import contract, route registration order, and backend behavior.

Current result:
- main implementation commit: `9822277`;
- push status: `pushed_to_origin_main`;
- status is `accepted_with_warning`;
- `bot_psychologist/api/admin_routes.py` is now a thin aggregator that still exports `admin_router` and `admin_router_v1`;
- the accepted map was realized as `10` extracted modules: runtime compat, bootstrap, helpers, runtime effective payload, diagnostics payload, config schema, config routes, prompt routes, agent ops routes, and misc routes;
- full before/after route evidence now covers `77/77` registered admin route cases (`48` legacy + `29` v1);
- the exhaustive snapshot gate stayed clean with `0` response differences before vs after;
- `api/main.py`, `writer_agent.py`, and `writer_contract.py` remained untouched;
- focused post-refactor backend/admin verification passed `101` tests with `3` warnings.

Accepted warning:
- a small UI string/assertion subset still fails, but it fails the same `5` assertions on the accepted pre-PRD baseline and after this PRD, so it is recorded as pre-existing suite noise rather than regression evidence against the admin-routes split.

## PRD-047.42 God File Boundary Mapping
PRD-047.42 completed the Stage-1 god-file boundary mapping pass for the three highest-priority non-diagnostic-center files: `writer_agent.py`, `admin_routes.py`, and `writer_contract.py`. The work stayed strictly read-only on production sources: no code moved, no signatures changed, no Writer prompt/model behavior changed, and no retrieval/safety/DB/Chroma/registry/runtime-path mutation was introduced.

Current result:
- main implementation commit: `d62fa43`;
- push status: `pushed_to_origin_main`;
- status is `accepted`;
- exact line-range boundary maps were produced for all three target files;
- `legacy_compat` fragments are now explicitly marked instead of being guessed from filename size alone;
- representative snapshot contracts passed `8/8` across `WriterContract.to_prompt_context`, `WriterAgent._resolve_runtime_settings`, `WriterAgent._enforce_answer_compliance`, and selected `admin_routes` HTTP handlers;
- external importer/dependency inventory is now recorded for all three files;
- no-mutation proof confirms zero diffs in the original target files;
- `19` production `diagnostic_center_*` files remain explicitly deferred to future `PRD-047.42b`;
- the output of this PRD is a decomposition map, not a decomposition commit.

## PRD-047.41 Flag Consolidation
PRD-047.41 completed the consolidation follow-up after PRD-047.40 and stayed bounded to effective-config truth, secret masking, bucket-A env freeze, and docs/tooling hygiene. It did not change Writer prompt/model behavior, retrieval ranking, safety logic, Bot_data_base, Chroma, registry data, processed blocks, or source documents.

Current result:
- main implementation commit: `3211322`;
- push status: `pushed_to_origin_main`;
- status is `accepted_with_warning`;
- built one authoritative `effective_config_registry_v1` over all `103` inventoried env flags;
- introduced explicit statuses `secret`, `active_tunable`, `frozen_constant`, and `retirement_candidate_deferred`;
- secret-proof now covers `10` credential-like flags and exports only `{"is_set": bool}` without raw values;
- bucket A converted `41` truly frozen env reads into literal constants with the same effective defaults;
- bucket B reclassified `19` already-editable env flags into `active_tunable` with no UI/runtime edit removal;
- the env-backed editable alignment is now explicit and tested as `35 == 35`;
- existing admin runtime payload stayed stable before/after once volatile restart-only fields were normalized, while the new `effective_config` block became the canonical explanatory surface;
- `LEGACY_PIPELINE_ENABLED` is intentionally deferred as `retirement_candidate_deferred` until a later admin-dedup / compatibility cleanup PRD;
- root-level helper `tools/` was removed and its remaining runner content moved into `TO_DO_LIST/tools`;
- `.gitignore` was corrected, `bot_psychologist/docs/testing.md` was updated to stop documenting deleted Phase 1/2/3 scripts, and the master plan Part 4 was advanced to the post-PRD-047.40 state.

Accepted warning:
- the full `pytest bot_psychologist/tests` capture before and after both hit the same 10-minute timeout budget, so regression evidence is honest but partial;
- one unrelated pre-existing UI string test (`tests/ui/test_runtime_tab_shows_effective_runtime_truth.py`) still fails outside the PRD-047.41 contract surface and remains candidate debt for a separate suite-health / docs/UI cleanup follow-up.

## PRD-047.40 Dead Pipeline Removal
PRD-047.40 is the first bounded removal pass after the PRD-047.39 inventory. It stays cleanup-only: no active runtime behavior, Writer prompt/model, retrieval ranking, safety logic, Bot_data_base, Chroma, registry, processed blocks, or source documents are changed.

Current result:
- status is `accepted_with_warning`;
- Stage A main commit: `417113b` untracked exactly `532` manifest-approved raw log artifacts from Git while keeping them on disk and preserving markdown evidence tracking;
- Stage B main commit: `b954a52` removed `5` dead legacy-bound test files and the matching `5` `pytest.ini` ignore lines;
- the positive replacement contract is now `bot_psychologist/tests/contract/test_dead_code_removed.py`;
- best-effort secondary cleanup removed stale `sd_classifier` debug/bootstrap leftovers without reopening legacy runtime paths;
- full regression moved from `309 failed / 1742 passed / 1006 warnings` to `308 failed / 1743 passed / 1006 warnings`, so no new PRD-local regression class was introduced;
- live smoke before/after stayed healthy with `200` post/trace results and `forbidden_trace_keys_present=false`;
- `user_level_adapter` verdict is `active`: active runtime/API compat surfaces still accept or expose the legacy name as a no-op/metadata compatibility shape, so removal is deferred to a separate PRD.

Architectural consequence: the project has now completed both the manifest-first raw-log untrack and the first dead-pipeline retirement slice without touching behavior. The next default work is separate and narrower: env-flag consolidation (`PRD-047.41`), global test-suite health (`PRD-047.45`), or a dedicated follow-up for remaining `user_level_adapter` compatibility shims.

## PRD-047.39 Architecture Consolidation Inventory
PRD-047.39 is the first architecture-consolidation stage after the accepted PRD-047.38 automated gate. It stays inventory-first and non-runtime: no active `bot_agent/`, `api/`, or `web_ui/src/` runtime behavior, Writer prompt, retrieval ranking, safety logic, Bot_data_base, Chroma, registry, processed blocks, or source documents are changed.

Current result:
- status is `accepted_with_warnings`;
- main implementation commit: `3c9cf15faac3f0f31b49af58bad63939cfdbf78c`;
- legacy inventory covers `14` retired/legacy candidates;
- env/flag inventory found `103` env/config flags;
- god-file inventory found `55` files over 500 lines under multiagent/API scope;
- fully merged remote branches deleted: `bot-psychologist`, `feature/sd-integration`, `refactor/simplify-retrieval-pipeline`;
- `TO_DO_LIST/backups` is removed from Git tracking only and ignored; local backup files remain on disk;
- logs tracking manifest classifies `424` markdown evidence files as keep, `532` raw artifact candidates as deferred, and does not untrack markdown evidence;
- dead `_build_llm_prompts` regression is quarantined under `_retired` and no longer collected by pytest;
- PRD-047.38 S7 warning remains backlog only, not repaired here.

The accepted warning is deliberate: raw-log untrack is deferred because the manifest contains `532` candidates and requires a separate owner-confirmed follow-up to avoid losing context continuity.

## PRD-047.38 Automated Owner Pilot Evidence Gate
PRD-047.38 replaces the manual owner pass over the 12 pilot scenarios with a read-only automated evidence gate. It does not tune answer intelligence/style and does not mutate runtime behavior, Writer prompts, retrieval ranking, Bot_data_base, Chroma, registry, processed blocks, source documents, routes, agents, or persistent trace storage. The gate runs S1-S11 through the current backend/session/trace path and S12 through the existing HF4 browser/restart/reload smoke automation, then emits sanitized PASS/WARNING/BLOCKER reports only.

Current evidence result:
- main implementation commit: `915be5b`;
- overall verdict is `ACCEPTED_WITH_WARNINGS`;
- `12/12` scenarios executed;
- blockers: `0`;
- warnings: `1`, limited to `S7 panic_medical_escalation_boundary_soft`;
- S1-S11 exact traces were available;
- S12 fresh post-restart reload trace passed with `2` exact trace turns and `0` unavailable cards after reload;
- raw private chat logs, raw traces, screenshots, provider payloads, DB/cache files, and helper browser artifacts are not committed.

Architectural consequence: the project can move to architecture consolidation / cleanup planning with the warning register visible. Remaining answer-style or bot-smartness tuning is explicitly deferred and should not be folded into cleanup unless a future PRD opens that scope.

## PRD-047.37 Freeze Baseline
PRD-047.37 moves the project out of the immediate hotfix loop and into a frozen owner-pilot baseline with documented warnings and cleanup backlog. The canonical runtime remains `multiagent_adapter / multiagent_v1`; Writer remains final answer author; `writer_kb_payload_v1` remains the knowledge-to-Writer path; owner/debug trace remains observability rather than public answer content; semantic cards remain advisory-only and Writer-can-ignore. No runtime behavior, Writer style, retrieval ranking, Bot_data_base, Chroma, registry, processed blocks, source documents, or new route/agent path is changed by this PRD.

Accepted current evidence:
- PRD-047.36-HF4 restored fresh Web Chat trace/reload truth, with old pre-restart debug trace expiry accepted only when labelled honestly.
- PRD-047.36-HF5 restored direct concept follow-up selected-knowledge admission into minimal hidden Writer payload.
- PRD-047.36-HF6 restored stable `boundary_trace_v1` proof for explicit `no_internal_db` and `no_practice`.
- PRD-047.37 documents accepted invariants, known warnings, pilot-start checklist, cleanup/retirement backlog, blocker register, and transfer brief.

Known accepted warnings:
- old debug traces may expire after backend restart if explicitly labelled;
- greeting/contact wording can be too therapeutic or mechanized;
- source exact-match coverage can be weak for concepts without strong DB chunks;
- shadow planner can be noisy/invalid while production path is correct;
- full pytest still has historical unrelated `_build_llm_prompts` import debt;
- UI trace labels / Session Trace Panel polish remain cleanup candidates.

## Current Stage
PRD-047.42-APPLY-7 has now proven the first explicit local-namespace extraction pattern inside `_call_llm`: two adjacent pure clusters are out, provider dispatch and prompt rendering are still in place, and the before/after snapshot stayed byte-identical. `admin_routes.py` remains decomposed and stable, `writer_contract.py` remains untouched, and the next mode stays narrow: continue `_call_llm` with the next mapped pre-provider helper edge in `PRD-047.42-APPLY-8`, switch to the deferred `PRD-047.42b` mapping pass for the `19` production `diagnostic_center_*` files, or pause decomposition and address unrelated suite-wide debt in `PRD-047.45`.

PRD-047.36-POST-HF completed the shortened post-HF owner readiness gate as an honest `BLOCKED` result on top of HF4 + HF5. The work stayed read-only: one new gate runner, one small contract test, reports, and docs only; no runtime behavior, Writer logic, retrieval ranking, DB/Chroma/source, or new route/agent mutation was introduced. Fresh trace/reload truth now passes again (`G1`), direct concept baseline/follow-up/Neurostalking continuity all pass (`G2/G3/G4`), greeting sanity passes (`G7`), and panic helper stays bounded with a warning on soft medical escalation wording (`G8`). The gate still blocks on boundary integrity: `G5` fails because explicit `no_internal_db` is honored in visible behavior but not surfaced as a durable trace boundary flag, and `G6` fails for the same reason on explicit `no_practice`. Delivery/memory sanity remains `pass_with_warning` because API-only sampling did not include visible chat bubble text and one quarantined panic-helper turn still diverges from saved memory without being a raw cross-turn contamination leak. Full `python -m pytest tests -q` still stops on the historical unrelated `_build_llm_prompts` import blocker. The next recommended step is one narrow repair only: `PRD-047.36-HF6 - No-Internal-DB / No-Practice Boundary Trace Integrity`.
PRD-047.36-HF5 completed the selected-knowledge admission repair on the canonical current pipeline with `accepted_with_warning` status. The runtime still stays on `multiagent_adapter`; no retrieval-ranking rewrite, no dictionary/alias map, no new route, no new agent, and no Bot_data_base/Chroma/source mutation were introduced. `contextual_retrieval_query_composer.py` now promotes generic contextual concept follow-ups with already selected knowledge into a bounded `query_kb` / `knowledge_context` admission path, while `writer_context_package.py` now exposes `direct_concept_followup`, bounded selected-knowledge recovery from existing `memory_bundle.knowledge_rag_hits`, and payload ordering that lets one selected semantic card lead the minimal hidden Writer package instead of being re-suppressed. Live HF5 smoke passed all required scenarios: greeting kept Writer payload `0`, the repaired Chat 12 concept follow-up now yields `grounding_reason=direct_concept_followup` and Writer payload `2`, Neurostalking follow-up also stays grounded, and `no_internal_db` still suppresses payload with `latest_turn_no_internal_db`. Honest residual note: full `python -m pytest tests -q` still stops on the historical unrelated `_build_llm_prompts` import blocker. The next recommended step is a shortened post-HF readiness gate over HF4 + HF5, not a dictionary-style runtime expansion.
PRD-047.36-HF4 completed the hard trace-restoration blocker repair on the canonical current pipeline with accepted_with_warning status. The runtime still stays on multiagent_adapter; no Writer behavior, retrieval ranking, DB/Chroma/source, semantic cards, model, or safety mutation was introduced. The repaired chain now persists streamed turns into session history under the exact chat session_id, reuses one resolved turn number across debug save/SSE/history, sends X-Device-Fingerprint from Web UI so backend session identity matches the intended browser scope, and preserves bot_active_chat_id through hydration/reload instead of clearing it before session restore. Live smoke passed the full owner-critical matrix: fresh 5-turn Web Chat shows real Pipeline NEO under every assistant turn, reload of the same fresh chat keeps exact trace, old sessions after backend restart now honestly show debug_trace_expired_after_backend_restart, and a new post-restart chat restores the same active session after reload with no fresh-turn Trace unavailable. Honest residual note: python -m pytest tests/test_final_answer_acceptance_gate_v1.py tests/multiagent/test_writer_agent.py -q still fails on the unrelated historical test_semantic_hits_limit_to_two. The accepted warning is bounded to legitimate old-session in-memory trace expiry after backend restart plus that unrelated historical test failure. The next recommended step is to rerun PRD-047.36 - Owner Pilot Readiness Gate / 12 Scenario Freeze v1 on top of HF1 + HF2 + HF3 + HF4 before any broader behavior change.
PRD-047.36-HF3 completed the narrow trace-availability / reload-hydration observability repair on the canonical current pipeline with `passed` status. The runtime still stays on `multiagent_adapter`; no Writer behavior, retrieval ranking, DB/Chroma/source, semantic cards, model, safety, or SSE protocol mutation was introduced. `SessionStore.find_multiagent_debug()` is now candidate-scoped by default for debug lookup, explicit `turn_index` requests no longer silently fall back to latest trace, `/api/debug/session/{session_id}/multiagent-trace` now returns structured `trace_availability`, and owner/dev Web Chat now renders an explicit unavailable notice under assistant turns when exact trace cannot be recovered after reload. Targeted backend/API/UI tests passed, frontend typecheck/build passed, and live smoke passed after backend restart with exact `turn_index=1 -> 200 available exact_turn_match=true` and missing `turn_index=999 -> 404 unavailable requested_turn_missing`. Honest bounded note: `memory_written.assistant=\"\"` can still appear when acceptance logic quarantines a visible answer; HF3 classified that as a separate delivery/acceptance-state phenomenon and did not mutate it here. The next recommended step is to rerun `PRD-047.36 - Owner Pilot Readiness Gate / 12 Scenario Freeze v1` on top of HF1 + HF2 + HF3 before any broader behavior change.
PRD-047.36-HF1 completed the narrow readiness repair on the canonical current pipeline with `passed_with_warning` status. The runtime still stays on `multiagent_adapter`; no new route, no new agent, no retrieval ranking mutation, and no DB/Chroma/source mutation were introduced. The fix closes the concrete `S8` no-practice collapse and the benign-turn delivery/history integrity gap by removing forced one-step fallback where latest-turn no-practice/contact constraints forbid it, allowing benign no-stub warnings to remain acceptable/savable when no real failed checks remain, threading stable `turn_number` through SSE/API/history/frontend state, and binding Web trace/canvas lookup to explicit turn identity instead of fragile message-index inference. Targeted backend/UI tests passed, frontend build passed, live backend health returned `healthy`, and live frontend probes returned `200`. Honest residual warning: full `python -m pytest tests -q` is still blocked by the historical unrelated `_build_llm_prompts` import error in `tests/regression/test_no_sd_required_by_response_flow.py`. The next recommended step is to rerun the owner readiness freeze (`PRD-047.36`) on top of this repaired pipeline before introducing any further behavioral change.
PRD-047.36 completed the owner-pilot readiness gate as an honest `BLOCKER` result on the canonical current pipeline. No new route, no new LLM agent, no DB/Chroma/registry/source mutation, and no behavior hotfix were introduced inside this PRD; the work stayed in read-only scenario-gate tooling, trace/report evidence, and one bounded trace-only consistency cleanup in `writer_context_package.py`. The authoritative live gate on `14` fixed scenarios finished with `S8` as the main blocker (`no_practice` still violated), `S6/S14` as honest `source_missing_expected` warnings, and an additional delivery-integrity risk: `S1/S2/S7/S8/S12` were quarantined by `final_answer_acceptance_gate_v1`, so saved-memory parity is not fully proven even when visible answers look acceptable. The next recommended step is `PRD-047.36-HF1 - No-Practice Boundary and Benign-Turn Acceptance Alignment`.
PRD-047.36-HF2 completed retrieval recall proof and direct-match candidate-selection repair on the canonical current pipeline with `accepted_with_warning` status. The runtime still stays on `multiagent_adapter`; no new route, no new LLM agent, and no Bot_data_base/Chroma/registry/source mutation were introduced. `memory_retrieval.py` now exposes `raw_hit_summaries`, `writer_context_package.py` now emits `source_chunk_match_trace_v1` plus a bounded `retrieval_gate_recovery_applied` flag, and owner/Web trace can now prove whether a knowledge answer was lost at raw source, runtime retrieval, or writer payload. Live A1-A8 audit fixed the silent-loss class for `A4` and `A6`, while `A1/A2/A3/A7/A8` remain honestly classified as `raw_source` missing in the current runtime top-k; the next step is either `PRD-047.36-HF1` delivery-integrity repair if UI truncation is still reproducible, or a separate source/DB preparation PRD before the owner readiness gate.
PRD-047.35 completed hidden-knowledge competence and Wake-depth calibration on the canonical current pipeline with `passed_with_warning` status. The runtime still stays on `multiagent_adapter`; no new route, no new LLM agent, no Bot_data_base/Chroma/registry/source mutation, and no semantic-card expansion were introduced. `writer_context_package.py` now emits `hidden_knowledge_competence_v1`, public user mode suppresses DB/chunk/semantic-card/internal-system wording, Writer prompt/runtime trace carry the same rule, and ordinary answers are biased toward one mechanism plus its protective function instead of theory dumps. Live smoke after backend/frontend restart kept `contains_internal_language=false` across all checked turns and preserved PRD-047.34 latest-turn authority, while honest warnings remain for one panic-helper opening, one overlong deep explanation, and one over-recap close turn. The next recommended step is `PRD-047.36 - Owner Pilot Readiness Gate / 12 Scenario Freeze v1`.
PRD-047.34 completed latest-turn authority repair and free Writer contact-mode calibration on the canonical current pipeline with `passed_with_warning` status. The runtime still stays on `multiagent_adapter`; no new route, no new LLM agent, no Bot_data_base/Chroma/registry/source mutation, and no semantic-card expansion were introduced. `final_answer_directive_v1` now makes the latest non-empty user turn the default answer target, keeps `previous_must_answer` as context-only unless explicit continuation is detected, exposes `must_answer_source` / `previous_must_answer_demoted` / `answer_target` / `writer_contact_mode`, and drives `latest_turn_authority_v1` through runtime trace and Writer prompt assembly. Live smoke after backend/frontend restart passed A-D, including the exact Chat5 stale-KB failure and the support-after-practice refusal case, while the only honest remaining warning is unrelated test-suite debt outside PRD-047.34. The next recommended step is `PRD-047.35 - Owner Pilot Consolidation / Minimal Public Demo Readiness v1`.
PRD-047.33 completed owner-pilot answer-shape calibration on the canonical current pipeline with `passed_with_warning` status. No new runtime path, no new LLM agent, no Bot_data_base/Chroma/registry/source mutation, and no broad KB re-enable were introduced. The runtime now carries soft `answer_shape_profile` hints through `final_answer_directive_v1`, Writer prompt assembly, and `runtime_trace_summary_v1`; compact support target length is tighter; direct KB/source turns now trace as `direct_kb_grounded_compact`; explicit practice, no-practice, and no-internal-db boundaries remain preserved. Live smoke after backend/frontend restart stayed honest and passed with warning: most A-H cases are shorter and more human-like, but one ordinary resistance case still reports `adaptive_current_pipeline` in trace even though the answer itself improved. The next recommended step remains `PRD-047.34 - Owner Pilot Consolidation / Minimal Public Demo Readiness v1`, with `PRD-047.34-HF1` reserved if owner review rejects that residual shape-conflict warning.
PRD-047.32 completed owner Web Chat runtime truth and fallback-noise collapse on the canonical current pipeline with `passed_with_warning` status. The runtime remains `multiagent_adapter`; no thin-spine apply, no new route, no new LLM agent, and no DB/Chroma mutation were introduced. Owner trace now separates retrieved candidates, trace-only/filtered candidates, and actual Writer-visible payload through `runtime_truth_trace_v1`; the misleading `Чанки в Writer` label is replaced by `Retrieval candidates / trace-only`; Hybrid Planner shadow JSON errors are scoped as `shadow_only` with `production_answer_affected=false`; direct KB/source and explicit practice paths remain preserved. Live smoke passed the required trace truth checks after backend/frontend restart, with a bounded warning that some no-practice explanation answers remain above the soft compact target. The next recommended step is `PRD-047.33 - Owner Pilot Stabilization / Answer Shape Calibration v1`.
PRD-047.31-HF1 completed the urgent explicit-practice-request repair on the canonical current pipeline. The runtime remains `multiagent_adapter`; no thin-spine apply, no new route, no new LLM agent, and no DB/Chroma mutation were introduced. The repaired path now lets the latest explicit practice request override stale `must_answer`, keeps the anger/boss/lying follow-up in the current thread, allows only narrow Writer-visible practice grounding (`practice`, `dialogue_move`, `anti_pattern`, `safety`) instead of broad KB reopening, and exposes a compact explicit-practice runtime note in trace surfaces. Full backend/frontend restart plus live smoke passed the `ЧАТ_С_БОТОМ2` scenario and removed the stale `открой задачу / 5 минут` fallback. The only honest remaining global blocker is still the unrelated full-suite import error around `_build_llm_prompts`. The next recommended step is `PRD-047.32 - Owner Web Chat Runtime Truth / Legacy Fallback Noise Collapse v1`.
PRD-047.30 completed Writer input authority recovery on the canonical current pipeline. The runtime still stays `multiagent_adapter`; no thin-spine live apply, no new agent, no new route, and no DB/Chroma mutation were introduced. `knowledge_policy.py` remains the chunk governance gate, while `writer_context_package.py` now exposes `writer_grounding_visibility_v1` so ordinary emotional/support/repair/simplify/pushback turns hide Writer-visible KB/semantic-card payload by default and keep that evidence in trace-only form. Writer prompt assembly now marks KB/semantic cards/retrieval notes as optional grounding, duplicate advisory prose is shorter, `runtime_trace_summary_v1` and `/api/debug/session/{session_id}/multiagent-trace` expose the visibility decision, and live smoke on the restarted `:8001` backend passed `10/10`. The only honest remaining global blocker is still the unrelated full-suite import error around `_build_llm_prompts`. The next recommended step is `PRD-047.31 - Legacy Advisory Retirement / Writer Prompt Noise Collapse v1`.
PRD-047.29 completed targeted current-pipeline simplification and latest-turn constraint repair on top of the PRD-047.28 thin-spine blocker evidence. The canonical runtime remains `multiagent_adapter`; no thin-spine live apply, no new agent, and no DB/Chroma mutation were introduced. The runtime now exposes `latest_turn_constraints_v1` for explicit user requests (`no_practice`, `no_breathing_only`, `simplify`, `long_term_perspective`, `no_internal_db`), suppresses Writer-visible KB/semantic-card payload when `no_internal_db=true`, and adds compact `runtime_trace_summary_v1` over the full debug payload. Live smoke on the real backend after restart passed `8/8`, while the only honest remaining global blocker is still the unrelated full-suite import error around `_build_llm_prompts`. The next recommended step is `PRD-047.30 - Writer Grounding Visibility Throttle / Non-KB Turn Noise Reduction v1`, not thin-spine replacement.
PRD-047.28 completed as an isolated thin-spine live experiment with honest `BLOCKED` status and no production-runtime mutation. The experiment added a separate A/B/C runner (`A_current`, `B_thin`, `C_thin_note`), fixture set, thin context collector, short natural-language live-turn-note path, safety/leak checks, comparative reporting, and no-mutation evidence outside the canonical runtime. Live evidence is explicit: `case_count=10`, `row_count=30`, `average_direct_answer_score_A=1.8`, `average_direct_answer_score_B=1.7`, `average_direct_answer_score_C=1.6`. The main blocker is answer-quality, not infrastructure: thin variants still forced practice in `TS-003`, and constraint-respect weaknesses remain visible (`TS-005`, `TS-008`). The next recommended step is `PRD-047.29 - Current Pipeline Simplification Targets / Layer Noise Reduction v1`, not thin-spine apply.
PRD-047.27 completed the minimal DB-track semantic chunk cards pilot as a bounded, advisory-only Writer grounding layer with `passed_with_warning` status. A local/dev/test-only `semantic_cards_pilot_v1` pack now feeds 1-3 compact semantic cards into the existing `writer_kb_payload_v1` path without changing retrieval authority, Chroma, registry, processed blocks, DB schema, or Writer authorship. Live pilot evidence is explicit: `semantic_card_selected_when_expected_count=5`, `semantic_card_suppressed_when_not_needed_count=2`, `direct_answer_success_rate=1.0`, `card_internal_leak_count=0`, `raw_source_dump_count=0`, `practice_overpush_count=0`. The only honest warning is one overly textbook answer (`SCP-005`), so the next recommended step is `PRD-047.28 - Live Interactive Pilot / Owner Dialogue Review v1`, not broader runtime authority or DB mutation.
PRD-047.26-HF1 completed the targeted route/obligation/evaluator repair on top of the PRD-047.26 live triage baseline and is now the current top-stage evidence layer with `passed_with_warning` status. The runtime/evidence path stayed trustworthy: `source_gate=passed`, `dry_run=passed`, `live_cases=12/12`, `overlay_apply_detected_count=0`, `internal_leak_count=0`, `raw_kb_dump_count=0`, `unsafe_practice_count=0`, `diagnostic_overclaim_count=0`, and `trace_missing_evidence_count=0`. The repaired counters are explicit: `direct_answer_success_rate=1.0`, `overlay_false_positive_count=8`, `dialogue_act_error_count=0`, `answer_obligation_error_count=0`, `writer_style_regression_count=0`, `evaluator_false_pass_count=0`, so DB-track moved from `not_ready` to `ready_with_warning`. The remaining blocker class is no longer answer routing; it is overlay shadow noise only. The next recommended step is `PRD-047.26-HF2 - Overlay Shadow Noise Reduction / Evidence Repair v1`, and DB metadata expansion stays deferred until that warning is reduced.
PRD-047.25 collected live evidence for the cleaned retrieval baseline plus `overlay_shadow_trace` and `writer_kb_payload_v1`, and it is the new top-stage baseline with `passed_with_warning` status. The active local runtime remains singular (`multiagent_adapter`), `current_turn_focus_v1` stays primary for retrieval query assembly, and `writer_kb_payload_v1` stays canonical for KB delivery with `kb_payload_primary_rate=1.0`, `current_turn_focus_clean_rate=1.0`, `legacy_query_builder_primary_count=0`, `overlay_apply_detected_count=0`, and no internal payload leakage or raw KB dump in final answers. The bounded warning is now explicit and evidence-backed: overlay remains trace-only and non-authoritative, but live evidence shows `overlay_false_positive_count=6`, so the next recommended step is `PRD-047.26 - Overlay Shadow Noise Reduction / Evidence Repair v1`, not overlay graduation or authority expansion.
PRD-047.24 closed the retrieval query assembly pollution/duplication class with accepted `passed_with_warning` status and is the current top-stage baseline. The runtime now uses `current_turn_focus_v1` query assembly by default for local/dev/pilot/test surfaces, blocks naive previous-question concatenation for standalone knowledge asks, permits compact inherited-topic context only for genuine elliptical follow-ups, collapses duplicate fragments, avoids mid-word truncation, and exposes `retrieval_query_build_trace_v1` in runtime/debug/API/Web Trace. Live repair evidence shows Q24-002 no longer carries the stale self-realization query, Q24-003 no longer duplicates/truncates mid-word, retrieval relevance is no longer `missing_expected_source`, Writer KB payload remains canonical with structured payload active, and no Bot_data_base/Chroma/source/chunk mutation was performed. The remaining warning is bounded: Q24-003 improved to `medium_related` top-k evidence rather than a stronger exact top-1 style match. Next recommended work is `PRD-047.25 - Overlay + Writer KB Payload Live Evidence / Evaluation v1`.
PRD-047.22-HF2 closed the manual Web Chat runtime parity gap for Writer KB Payload and is the current top-stage baseline. The backend now resolves `WRITER_KB_PAYLOAD_ENABLED` from a single effective-config source with `APP_ENV=local` leading to `default_local`, exposes that source in admin runtime and debug trace, and proves over the real Web Chat streaming path that `writer_kb_payload_v1` is primary (`fallback_is_primary=false`, `payload_chunk_count>=1`, `mid_sentence_cut_count=0`) while keeping retrieval ranking/query, Writer authority, Chroma, registry, processed blocks, and live metadata unchanged. Browser screenshot capture remains an explicit warning-only gap; API/Web Chat parity, prompt-canvas proof, no-mutation proof, and encoding hygiene passed. Next recommended work is `PRD-047.23 - Overlay + Writer KB Payload Live Evidence / Evaluation v1`, now gated on PRD-047.22-HF2 parity truth.
PRD-047.22-HF1 repaired the live API Writer KB payload evidence path and is the current top-stage baseline. The previous PRD-047.22 warning was traced to the smoke transport itself: ad-hoc PowerShell-piped inline Python corrupted Cyrillic query text before it reached the backend, and the smoke did not own/verify backend startup with `WRITER_KB_PAYLOAD_ENABLED=true`. HF1 adds a managed live runner and live-like API test that send ASCII-safe escaped JSON, verify/start backend locally with the payload flag enabled, and now produce live `writer_kb_payload_trace.enabled=true` with `payload_chunk_count=1` for `С‡С‚Рѕ С‚Р°РєРѕРµ РќРµР№СЂРѕСЃС‚Р°Р»РєРёРЅРі?`, while keeping retrieval ranking/query, Writer authority, Chroma, registry, processed blocks, and live metadata unchanged. Next recommended work returns to `PRD-047.23 - Overlay + Writer KB Payload Live Evidence / Evaluation v1`.

PRD-047.22 completed structured Writer KB delivery as a bounded runtime-input change with accepted `passed` status. The active retrieval path still selects chunks exactly as before, but default-off `WRITER_KB_PAYLOAD_*` config now allows selected Writer-visible knowledge to travel as `writer_kb_payload_v1` instead of relying on blind flat semantic-hit truncation. The new path adds sentence/paragraph-aware excerpting, `writer_kb_payload_trace`, `future_graduation_notes`, and read-only API/Web Trace visibility while preserving Writer as final author and keeping retrieval ranking, executed retrieval query, semantic-hit selection, BotDB registry, processed blocks, live metadata, and Chroma unchanged. Next recommended work is `PRD-047.23 - Overlay + Writer KB Payload Live Evidence / Evaluation v1`.

PRD-047.21 completed overlay-aware retrieval shadow integration as a strict trace-only runtime surface with accepted `passed` status. Added default-off `OVERLAY_SHADOW_TRACE_*` feature flags, isolated `overlay_shadow_trace.py`, orchestrator/debug/API wiring, Web Trace rendering, trace/sample/no-behavior/authority/no-mutation artifacts, targeted multiagent/API tests, PRD-047.20 regression coverage, and Web trace widget verification/build. Batch-1 accepted overlay remains explicitly non-live (`human_final_approval=false`, `live_apply_allowed=false`, `safe_to_apply_to_live_metadata=false`): overlay is visible only in trace/debug as sanitized shadow evidence, while WriterContract, Writer prompt, executed retrieval query, semantic hits, final answer logic, BotDB registry/processed blocks, and Chroma remain unchanged. API smoke is intentionally `warning`/skipped in the runner by default (`skipped_inprocess_app_smoke_default_off`) because contract coverage is already provided by dedicated API tests. Next recommended work is `PRD-047.22 - Overlay Shadow Allowlisted Live Evidence / Trace Review v1`.

PRD-047.20 completed the first real curated overlay batch and offline retrieval evaluation without changing runtime behavior. Added batch-1 selection over `16` real PRD-047.18 queue candidates, an evaluation-only decisions pack (`12` accepted overlay items, `139` accepted fields), accepted-overlay preview, PRD-047.19-based dry-run apply/preflight wrapper, and retrieval shadow evaluation over `18` curated cases. The overlay remains explicitly non-live: `human_final_approval=false`, `evaluation_only=true`, `live_apply_allowed=false`, `ready_for_live_apply=false`, while `ready_for_eval_over_real_overlay=true` is now supported for offline evidence. Read-only BotDB smoke passed on `:8003`; retrieval eval passed with `overlay_shadow_hit_rate=0.7778`, `combined_expected_help_rate=0.7778`, `unsafe_overlay_hit_count=0`, and `practice_without_safety_count=0`. No Writer/runtime/Admin/Web/registry/processed-block/Chroma mutation was performed. Next recommended work is `PRD-047.21 - Overlay-Aware Retrieval Shadow Integration / Trace-Only v1`.

PRD-047.19-HF1 repaired acceptance evidence integrity for PRD-047.19 without changing functionality. The hotfix reran the PRD-047.18, PRD-047.17, and PRD-047.19 regression subsets with repository-local `--basetemp` and local `TEMP/TMP`, eliminating the false `C:\Users\video\AppData\Local\Temp\pytest-of-video` `PermissionError` failures from the original command log. HF1 also regenerated `test_command_output.txt` as clean UTF-8, restored `replacement_char_warning_count=0`, added explicit source-gate / rerun-summary / no-mutation evidence, and left Writer, runtime, live metadata, Chroma, processed blocks, and registry untouched. Next recommended work remains `PRD-047.20 - Real Human Curated Overlay Batch 1 / Accepted Decisions Pack v1`.

PRD-047.19 completed curated candidate dry-run apply preflight with accepted `passed_with_expected_blockers` status. Added `mechanism_metadata_overlay_intake_report_v1`, `mechanism_metadata_dry_run_apply_plan_v1`, `mechanism_metadata_apply_preflight_v1`, future field-apply mapping, negative overlay fixtures, anti-runtime-activation proof, read-only BotDB smoke, and no-mutation/encoding artifacts over the PRD-047.18 fixture overlay. The project can now explain candidate/block consistency, future metadata targets, and diff previews under `overlay_only_no_write`, but it still honestly reports `ready_for_live_apply=false` and `ready_for_eval_over_real_overlay=false` because the current overlay is fixture-only and contains no real human-reviewed accepted decisions. No processed blocks, live metadata, Chroma, retrieval, Writer prompt, or runtime behavior were changed. Next recommended work is `PRD-047.20 - Real Human Curated Overlay Batch 1 / Accepted Decisions Pack v1`.

PRD-047.18 completed manual review / curated candidate acceptance workflow with accepted `passed` implementation status. Added `mechanism_metadata_review_decision_v1`, `mechanism_metadata_review_queue_v1`, `mechanism_metadata_curated_overlay_preview_v1`, offline decision validation, fixture-only curated overlay preview, and a dedicated review runner over the `80` real PRD-047.17 candidates. The workflow now produces a governed review queue, all-pending decision template, validation report, curated overlay preview, curation status report, anti-runtime-activation proof, read-only BotDB smoke, and no-mutation/encoding artifacts. Real candidates still remain preview-only: `live_apply_allowed=false`, `safe_to_apply_to_live_metadata=false`, no Writer/runtime behavior changed, Chroma was not reindexed, and DB/live metadata were not mutated. Next recommended work is `PRD-047.19 - Curated Candidate Dry-Run Apply Plan / Preflight over Accepted Overlay v1`.

PRD-047.17 completed offline enrichment candidate generation over the real Kuznica source with accepted `passed` status. Added `mechanism_metadata_enrichment_candidate_v1`, a deterministic offline enrichment runner over `123__???????_????`, source-profile and chapter-coverage reports, manual-review pack, anti-runtime-activation proof, and encoding/no-mutation artifacts. The run selected `80` real blocks out of `247` and produced `80` manual-review candidates across `practice`, `diagnostic_lens`, `source_fragment`, `mechanism`, `concept`, `case_example`, `safety`, and `style_voice`. Candidates are explicitly not applied to live metadata, Writer/runtime behavior is unchanged, Chroma was not reindexed, DB was not mutated, and LLM-candidate mode remains deferred/skipped behind explicit confirmation and safe configuration. Next recommended work is `PRD-047.18 - Manual Review / Curated Candidate Acceptance Workflow v1`.

PRD-047.16 completed mechanism-aware knowledge base preparation / chunk metadata foundation with accepted `passed` implementation status and read-only audit evidence. Added `MechanismAwareChunkMetadata v1` in the existing `Bot_data_base/knowledge_governance` layer, a backward-compatible adapter from legacy governed blocks, and a dry-run audit runner over fixture plus real local BotDB blocks. The new metadata is explicitly semantic guidance only: Writer remains the sole author of user-facing text, runtime answer behavior is unchanged, and no new metadata was activated in the live Writer path. Chroma was not reindexed, DB schema was not mutated, and no new runtime path or LLM enrichment agent was added. Real-sample audit checked `54` chunks (`50` real + `4` fixture) and passed structurally while surfacing quality warnings for incomplete mechanism/practice metadata. Next recommended work is `PRD-047.18 - Manual Review / Curated Candidate Acceptance Workflow v1`.

PRD-047.15-HF2-R1 completed Hybrid Retrieval Planner / Query-Before-RAG with accepted `passed` status. Added `hybrid_retrieval_planner_v1_r1` as a metadata-only planner in the existing multiagent runtime: deterministic universal gates cover simple greeting/thanks/summary/formatting/reject/support cases, optional strict-JSON LLM planning is reserved for complex low-confidence cases, and approved retrieval metadata now reaches `MemoryRetrievalAgent` before RAG execution. Trace/debug/API now expose planned vs executed query, query-before-RAG proof, planner validity/fallback, planner mode, needed chunk types, and mechanism hints while Writer remains the sole final answer author. Direct acceptance passed `16/16`; live acceptance passed `6/6` after restarting the live backend on `:8001` with `HYBRID_RETRIEVAL_PLANNER_MODE=apply`; anti-overengineering, encoding, and no-mutation gates passed; no DB/KB/frontend mutation or new runtime path was added. User-owned documentation updates under `bot_psychologist/docs/**` and `TO_DO_LIST/context/**` were included in the main push as requested. Next recommended work is `Backend в†” Web Admin в†” Web Trace Sync`, with `PRD-047.16` deferred behind that visibility follow-up.

PRD-047.15-HF1 completed Contextual Retrieval Composer Live Calibration / Owner Trace Review with warning status and no runtime mutation. HF1 generated a 40-case replay library, composer trace schema, replay trace review, owner review sheet, live trace inventory, LLM/hybrid decision brief, runtime-scope proof, encoding gate, acceptance artifact, and tests. Automated blocker gates passed (`literal_short_reply_query_count=0`, `summary_external_kb_leak_count=0`, `no_stub_violations_count=0`, tests passed), while mixed/low-confidence cases produced evidence for future hybrid assistance. Owner scores are intentionally pending; Writer remains final answer author, no LLM calls or new runtime path were added. Next recommended PRD is `PRD-047.15-HF1.1 - Owner Trace Review Completion / Calibration Decisions v1`, with `PRD-047.15-HF2 - Hybrid LLM-Assisted Query Composer Experiment v1` as the evidence-backed follow-up if owner review confirms the automated findings.

PRD-047.15 completed Contextual Retrieval Query Composer v1 with warning status. Added deterministic internal `contextual_retrieval_query_composer_v1` plus `retrieval_query_contract.py`: the composer builds retrieval need/action/query from dialogue context, last assistant offer, dialogue act, answer obligation, final directive, planner signals, and knowledge need instead of blindly relying on the current user utterance. Short confirmations can inherit the previous offer topic; summary requests default to `use_current_context_only`; greeting/close/support/one-step turns suppress RAG; knowledge and practice overview questions compose compact KB queries. The composer is visible in `retrieval_decision`, `writer_context_package_v1`, `WriterContract.to_prompt_context`, and debug trace. It is deterministic, does not create user-facing text, does not add an LLM agent, and does not mutate DB/KB/frontend. Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.15/`; validation/runtime-scope/encoding/no-stub composer scan passed. Warning remains for deterministic-v1 live calibration and HF1.2 out-of-scope static/advisory candidates. Next recommended PRD is `PRD-047.15-HF1 - Contextual Retrieval Composer Live Calibration / Owner Trace Review v1`.

PRD-047.14-HF2 completed summary request routing / answer obligation repair with warning status. Explicit current-conversation summary requests now route as `dialogue_act=summary_request`, outrank open last-offer confirmation, resolve to `answer_obligation=summarize_current_conversation`, and expose `summary_request`, `summary_scope=current_conversation`, `no_confirmation_needed`, and `no_practice_unless_requested` through `final_answer_directive_v1` / WriterContract. Writer no longer injects a canned summary; bad summary attempts are handled by `final_answer_acceptance_gate_v1` as retry/quarantine signals (`summary_request_reconfirmed_instead_of_answered`, `summary_answered_last_offer_instead`, `summary_answer_lacks_conversation_context`). Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.14-HF2/`; validation, runtime scope, encoding, and no-stub summary scan passed. Warning remains only because HF1.2 out-of-scope static/advisory candidates are intentionally not part of this HF2 scope. Next recommended PRD is `PRD-047.15 - Contextual Retrieval Query Composer Agent v1`.

PRD-047.14-HF1.2 completed targeted no-stub runtime repair with warning status: high-confidence Writer static repair/knowledge/direct-answer returns were converted to `no_stub_repair_signal_v1` and existing final-answer gate retry/quarantine semantics instead of canned replacement answers. Writer target blockers moved `31 -> 0`; total blocker inventory moved `55 -> 24`; no new user-facing stub was created; runtime mutation scope, encoding gate, and tests passed. Remaining candidates are out-of-scope/advisory/safety-minimal or summary-routing debt and are tracked for later PRDs. Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.14-HF1.2/`; the next repair path returns to `PRD-047.14-HF2 - Summary Request Routing / Answer Obligation Repair v1`.

PRD-047.14-HF1.1 completed as an audit-only no-stub boundary inventory with no runtime mutation. The audit tool inventoried hardcoded user-facing reply candidates across active runtime paths, classified all candidates, and produced an honest `blocker` result: 55 `blocker_stub_user_facing` candidates and 41 `warning_needs_targeted_refactor` candidates remain, with `unknown_active_candidates_count=0`, `runtime_mutation_status=passed`, `encoding_gate_status=passed`, and guard regression tests passed. Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.14-HF1.1/`; the next repair path is `PRD-047.14-HF2 - Summary Request Routing / Answer Obligation Repair v1`.

PRD-047.14-HF1 passed as a targeted hotfix after the PRD-047.14 blocker audit. Active hardcoded template-family fallback was removed from `concrete_answer_fit.py`; `template_family_guard_v1` now detects exact/fuzzy leakage in the existing final-answer acceptance gate, triggers retry/quarantine semantics, and prevents contaminated answers from becoming healthy memory, summary source, or last assistant offer. Writer call sites now defer problematic drafts to the existing gate instead of generating a canned replacement answer. No new runtime path, no new LLM agent, no prompt philosophy overhaul, no KB/Chroma/governance mutation, and no rollout flag changes were introduced. Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.14-HF1/`.

PRD-047.14 completed as an audit-only blocker cycle, not a runtime repair. The audit found active template-family leakage in `bot_psychologist/bot_agent/multiagent/concrete_answer_fit.py` and static summary/recap routing risk (`summary_request` has no dedicated answer-obligation route while `confirmation_to_last_offer` risk is present). No Writer, Orchestrator, prompts, policy, RAG/Chroma, Admin API, Web UI runtime, KB/governance, or database files were changed. Required artifacts are stored under `TO_DO_LIST/logs/PRD-047.14/`; the next repair path is `PRD-047.14-HF1 - Template Leakage Quarantine / Summary Contamination Guard v1`.

PRD-047.13-HF1 completed cleanup closure after PRD-047.13: active docs contradictions, misleading legacy labels, active empty artifacts, active duplicate docs, and unknown current docs are closed with no runtime mutation. PRD-047.13 completed as the cleanup-only inventory and docs truth-sync step. It inventoried docs, reports, logs, admin surfaces, legacy terms, empty artifacts, and encoding/corruption candidates after the accepted PRD-047.12-HF1 baseline, without changing Writer, Orchestrator, Final Answer Acceptance Gate, Stale Stub Detector, Dialogue Act Resolver, RAG/Chroma, Diagnostic Center authority, or prompt/runtime behavior.

PRD-047.12-HF1 is accepted as the current engineering baseline: `final_answer_acceptance_gate_v1` runs after Writer/Validator, failed/stale final answers are quarantined before unanswered-question closure, healthy context memory, and last-offer seeding, and Admin Runtime exposes gate capability. Web Chat markdown rendering uses the existing `ReactMarkdown` path with stronger real assistant bubble styling. Required live/browser/encoding/no-mutation artifacts passed under `TO_DO_LIST/logs/PRD-047.12-HF1/`.

Current rollout boundary remains unchanged: `production_ready=false`, `broad_rollout_allowed=false`, and `normal_user_activation_allowed=false`. Next planned quality work is `Backend в†” Web Admin в†” Web Trace Sync`.

PRD-047.12 completed as a passed unification cycle: `unified_dialogue_policy_v2` now owns preset resolution (`safe_guided`, `free_dialogue_default`, `mvp_free_dialogue` alias), dialogue-act / last-offer / unanswered-question / style-state / answer-obligation layers are wired through the single multiagent runtime, Writer-first prompt assembly exposes one effective control/context contract, Admin Runtime shows unified policy/resolver state, and the dedicated PRD-047.12 acceptance runner finished `dry=passed`, `direct=passed`, `live=passed`, `browser=passed`, `admin_surface=passed`. Artifacts live under `TO_DO_LIST/logs/PRD-047.12/`; no new runtime path, no new LLM agent, and no governance-authority mutation were introduced.
PRD-047.11-HF3 completed as a residual reality-repair cycle on top of HF2: concrete situation answers no longer fall back to the formula stub `РЎРµР№С‡Р°СЃ РїРѕР»РµР·РЅРµРµ РЅРµ СѓРїСЂР°Р¶РЅРµРЅРёРµ...` in MVP cases that need a contextual explanation, bare gratitude turns keep deterministic `intent=contact` and `nervous_state=window`, real localhost Web Chat/Admin proof moved back to `localhost:3000`, and HF3 artifacts now capture source inventory, HF2 audit, reset/memory proof, browser/admin snapshots, live cases, and encoding hygiene under `TO_DO_LIST/logs/PRD-047.11-HF3/`. HF3 remains a local stabilization hotfix, not a rollout PRD; Diagnostic Center/Planner/Active Line remain advisory-only, and production readiness is still not claimed.
PRD-047.11-HF2 completed as a passed runtime/frontend repair: fresh chats now start under `fresh_chat_context_policy_v1`, Writer receives RAG only through `writer_context_package_v1`, greeting/repair turns no longer inherit stale mechanism context, current-chat reset and dev-only user-memory clear controls are explicit, and real browser/Admin proof passed on isolated live runtime (`8002/3001`). Required HF2 artifacts are stored in `TO_DO_LIST/logs/PRD-047.11-HF2/`, with `live_cases_passed=true`, `memory_controls_passed=true`, `markdown_browser_passed=true`, and `admin_screenshots_passed=true`.
PRD-047.11-HF1 completed as a passed writer-prompt-diet repair: `mvp_free_dialogue` now keeps `FINAL ANSWER DIRECTIVE` writer-visible while collapsing legacy diagnostic/planner/active-line command pressure into a sanitized advisory summary, rewriting practice suppression to `no_exercise_but_answer_normally`, preserving raw observability in trace/admin, and removing stale runtime fallback phrases. Required HF1 artifacts are stored in `TO_DO_LIST/logs/PRD-047.11-HF1/`, with `writer_prompt_diet_eval=4/4 passed`.
PRD-047.11-AUDIT completed as a warning-grade evidence audit, not a pass: `TO_DO_LIST/logs/PRD-047.11-AUDIT/` now contains the dedicated runner output, source inventory, prompt/acceptance audits, live case matrix, raw traces, and no-mutation proof, but live evidence still shows `14/18` failed cases, `15` bad-phrase hits, missing browser screenshot proof, and incomplete admin configurability proof. The next recommended repair path is `PRD-047.11-HF1`, while Diagnostic Center remains advisory-only and production readiness is explicitly not claimed.
PRD-047.11 passed full Writer-first consolidation acceptance: `final_answer_directive_v1`, MVP prompt assembly cleanup, legacy-constraint suppression metadata, stale-stub detector, admin/runtime/UI exposure, live evidence enrichment, strict dry/direct/live runner, and real Web Chat markdown smoke are all green in final artifacts.
PRD-047.10-HF2 completed live turn evidence export + follow-up reliability repair + markdown smoke verification in unified runtime: added `live_turn_evidence_v1` payload in trace pipeline, upgraded short follow-up pragmatics/retrieval taxonomy, fixed short-input API validation (`min_length=1`), produced reproducible dry/direct/live artifacts with required case exports, and confirmed live pass on fresh backend `:8020` (`status=passed`).
PRD-047.10-HF1 completed direct follow-up repair + contextual retrieval noise reduction + chat markdown readability calibration in unified runtime: added deterministic `dialogue_pragmatics_v1`, contextual retrieval gating (`included` vs `candidates`, `writer_can_ignore_rag`), writer follow-up/repair compliance fixes, explicit trace/API visibility (`dialogue_pragmatics`, `retrieval_decision`), and safe markdown rendering (`react-markdown + remark-gfm + skipHtml`), with runner acceptance `dry/direct/live=passed` on fresh backend `:8019`.
PRD-047.10 completed human-like writer autonomy calibration in `mvp_free_dialogue`: `human_like_answer_policy` + `constraint_resolution` are now part of unified effective dialogue policy, Writer MVP compliance now handles sarcasm/dissatisfaction repair, structured summary requests, direct concrete answers, and explicit one-step preservation with trace/admin visibility; acceptance runner passed (`dry=passed`, `direct=passed`, `live=passed` on fresh backend `:8018`).
PRD-047.9 completed Unified Adaptive Dialogue Policy context-unclamp for `mvp_free_dialogue`: effective authority resolver (`minimal safety > explicit user request > knowledge/concept need > writer freedom > planner/diagnostic advisory`), recency-preserved writer context budget, practice-overview routing/planner shape, admin effective visibility, and live acceptance passed on fresh backend (`dry=passed`, `direct=passed`, `live=passed` on `:8016`).
PRD-047.7 added Guided Live User Testing Protocol v1: structured scenario set (18), sanitized feedback capture/storage, summary builder, smoke runner, and admin/web runtime visibility for feedback loop readiness (`dry smoke passed`, optional live smoke blocked on unavailable backend and recorded as such).
PRD-047.6 added `planner_drift_guard_v1` as observe-only runtime stability envelope: deterministic planner-vs-answer drift checks, rolling in-memory counters, trace/debug/admin visibility, and dry/direct/live replay artifacts (`dry=32/32`, `direct=32/32`, `live=12/12`, `repeat=3`, `warnings=0`, `criticals=0`, `missing_payload=0`, no runner fallback on fresh backend `:8015`).
PRD-047.5-HF1 repaired the answer-fit false-positive class (planner `stabilize_safety` / `safety_grounding` incorrectly passing mechanism-style answers), hardened final-answer compliance gates, and refreshed HF1 artifacts with strict green matrix (`dry=26/26`, `direct=26/26`, `live=26/26` on fresh temporary backend `:8014`).
PRD-047.5 completed planner quality calibration over live dialogue answer-fit groups and hardened Writer compliance for planner policies (`question/practice/revoicing/shape`), with refreshed artifacts (`dry=26/26`, `direct=26/26`, `live=26/26` on fresh temporary backend `:8013`).
PRD-047.4 added `Response Planner v1` as deterministic next-meaningful-move layer between Active Line and WriterContract, with trace/API/admin visibility and reproducible calibration artifacts (`dry=14/14`, `direct=14/14`, `live=14/14` on fresh temporary backend `:8012`).
PRD-047.0-HF1 closed evaluator false positives by enforcing final-answer compliance for known-concept routing and practice-gate behavior. Failure baseline artifacts are refreshed with honest answer-level validation (`direct=5/5`, `live=skipped` on stale backend). Diagnostic Center v1 remains in governed creator/developer-local boundary; broad rollout remains prohibited and `production_ready=false`.
PRD-047.1 introduced `NEO Philosophy Kernel` + `Writer Freedom Contract v1` as an always-on internal lens layer for Writer, with runtime/admin visibility and trace-safe metadata blocks (no raw source quote dumping).
PRD-047.2 calibrated kernel answer quality with reproducible `12`-case dataset/runner, added prompt compactness budget gates, and synced runtime/admin visibility for quality calibration status (`direct=12/12`, `live=skipped` honestly on stale backend).
PRD-047.3 added `Active Line / Dialogue Continuity v1` as deterministic continuity layer (intent, continuity mode, repair mode, revoicing/practice suppression) with trace + admin effective visibility and reproducible dry/direct/live runner artifacts (`dry=10/10`, `direct=10/10`, `live=10/10` on fresh temporary backend `:8011`).
## Current Runtime Architecture
User path remains unchanged: State Analyzer -> Thread Manager -> Context Assembly -> Diagnostic Card -> Diagnostic Center shadow/limited governance layers -> Writer.

## Diagnostic Center Acceptance State
`PRD-046.1.28` accepted provider-backed phase as governed limited-runtime candidate.
Boundary flags remain strict: `broad_rollout_allowed=false`, `production_ready=false`, `normal_user_activation_allowed=false`.
Admin control surface is available via `GET/POST /api/admin/diagnostic-center/*` and mirrored `v1` routes.
`developer_local_all_users` is available for single-developer local governance only and is not production rollout.

## Current Knowledge Base State
Focus source remains `123__РєСѓР·РЅРёС†Р°_РґСѓС…Р°`; governed blocks/chroma integrity is preserved by no-mutation policy and explicit gates.

## Current Context / Memory State
Context assembly + additive summaries remain active; deterministic fallback stays mandatory when async summaries are unavailable or invalid.

## Stable Modules
- Multiagent orchestrator and writer compliance chain.
- Diagnostic Center shadow and constrained prompt-constraint stack.
- BotDB registry/query/admin stability gates.
- Artifact encoding hygiene and no-mutation proof flows.

## Permanent Gates
- Final runtime governance acceptance gates.
- Provider-backed evidence and normal-user no-effect gates.
- Rollback/hard-stop, safety/KB boundary, trace sanitization gates.
- BotDB stability, response quality eval/calibration, contract and no-mutation gates.

## Known Risks
- Broad rollout without separate PRD would violate governance boundaries.
- Cleanup/deletion without manifest approval can break reproducibility.
- Historical artifact encoding noise may be misread as current runtime corruption without normalization report.

## Next Planned PRD
Default next step is Owner Pilot Start using `TO_DO_LIST/logs/PRD-047.37/pilot_start_brief.md`. If implementation work is needed before pilot, prefer Cleanup Pass 1 focused on docs/logs/trace labels/legacy report hygiene only. DB/chunk preparation and historical test debt remain separate later PRDs.

## PRD-047.23 Audit State
PRD-047.23 closed the evidence gap between Bot_data_base chunks, retrieval query assembly, Writer KB payload, and Web Trace preview.
Stored/source evidence does not support a primary Bot_data_base chunk-boundary defect for the observed Neurostalking case; the suspicious `...изнутри чего т` cut is downstream from stored content and aligns with preview/full-content ambiguity in the uploaded trace.
The dominant failure class is current-turn retrieval query pollution/duplication for the "Программа несовершенное Я" and "Пять драйверов" cases, with secondary trace-schema mismatch where Web Trace chunk counters can diverge from actual writer payload counters.

## HF2-R2 Runtime Visibility State
Hybrid Retrieval Planner visibility is now synchronized across backend admin runtime, Web Admin Runtime, multiagent trace, and compact trace summary.
Advanced Controls is compatibility-only; duplicate legacy sub-tabs are no longer presented as primary control centers.
Knowledge Graph runtime flag remains backend-legacy/optional but is shown as compatibility status instead of a modern primary Runtime toggle.
## Do Not Do Yet
- Do not activate broad Diagnostic Center runtime authority.
- Do not enable normal-user activation.
- Do not mutate KB governance authority fields (`chunk_type`, `allowed_use`, `safety_flags`).
- Do not perform Chroma reindex as part of this cleanup PRD.

## Documentation Update Rule
1. Update this file for every stage/runtime boundary PRD.
2. Update roadmap for sequencing changes.
3. Update decisions for architecture boundary changes.
4. Update PRD index after each merged PRD cycle.
5. Keep full historical details in `TO_DO_LIST`, keep docs operational and compact.

## Last Updated
2026-07-02
- Source cycle: PRD-047.37
- Date: 2026-06-05
- Source cycle: PRD-047.12
- Source cycle: PRD-047.11-HF3
- Source cycle: PRD-047.11-HF2
- Source cycle: PRD-047.11-HF1
- Source cycle: PRD-047.11-AUDIT
- Source cycle: PRD-047.10-HF2
- Source cycle: PRD-047.11

## PRD-046.1.35-HF4
Current Stage:
PRD-046.1.35-HF4 calibrated creator-live response behavior: example/explanation requests no longer trigger regulate_first by default, practice rejection suppresses body-action suggestions, and Web Trace displays non-empty safe Writer chunk previews.
Next:
PRD-046.1.36 Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1.

## HF4 Delivery Metadata
- prd_id: PRD-046.1.35-HF4
- commit_hash: 3a3c6a32a0c29551440432c0a266ab7cbab25b20
- push_status: pushed_to_origin_main

## PRD-046.1.36 Delivery Metadata
- prd_id: PRD-046.1.36
- commit_hash: 14a04164059dfff8b9b8e625cb1f3f1578e0d57b
- push_status: pushed_to_origin_main

## PRD-046.1.37 Delivery Metadata
- prd_id: PRD-046.1.37
- commit_hash: ff77155
- push_status: pushed_to_origin_main

## PRD-047.15-HF2-R2 Delivery Metadata
- prd_id: PRD-047.15-HF2-R2
- commit_hash: 3480666
- push_status: pushed_to_origin_main

## PRD-047.23 Delivery Metadata
- prd_id: PRD-047.23
- commit_hash: 4f70dc4
- push_status: pushed_to_origin_main

## PRD-047.24 Delivery Metadata
- prd_id: PRD-047.24
- commit_hash: 47693c2
- push_status: pushed_to_origin_main

## PRD-047.25 Delivery Metadata
- prd_id: PRD-047.25
- commit_hash: e1b0fb5
- push_status: pushed_to_origin_main

## PRD-047.26 Delivery Metadata
- prd_id: PRD-047.26
- commit_hash: da2e8f5
- push_status: pushed_to_origin_main

## Diagnostic Center Track Status
Diagnostic Center Track Status: CLOSED FOR CURRENT PHASE


## PRD-047.26-HF1 Delivery Metadata
- prd_id: PRD-047.26-HF1
- commit_hash: e131358
- push_status: pushed_to_origin_main

## PRD-047.27 Delivery Metadata
- prd_id: PRD-047.27
- commit_hash: 6ad266b
- push_status: pushed_to_origin_main

## PRD-047.27-HF1 Delivery Metadata
- prd_id: PRD-047.27-HF1
- commit_hash: 74cb113
- push_status: pushed_to_origin_main

## PRD-047.27-HF2 Delivery Metadata
- prd_id: PRD-047.27-HF2
- commit_hash: fa9072f
- push_status: pushed_to_origin_main

## PRD-047.32 Delivery Metadata
- prd_id: PRD-047.32
- commit_hash: aed27db
- push_status: pushed_to_origin_main
- status: passed_with_warning

## PRD-047.36-HF2 Delivery Metadata
- prd_id: PRD-047.36-HF2
- commit_hash: 51fbfbf
- push_status: pushed_to_origin_main
- status: accepted_with_warning

## PRD-047.36 Delivery Metadata
- prd_id: PRD-047.36
- commit_hash: a3d42d1
- push_status: pushed_to_origin_main
- status: blocker

## PRD-047.34 Delivery Metadata
- prd_id: PRD-047.34
- commit_hash: 39ff982
- push_status: pushed_to_origin_main
- status: passed_with_warning

## PRD-047.35 Delivery Metadata
- prd_id: PRD-047.35
- commit_hash: 897e73f
- push_status: pushed_to_origin_main
- status: passed_with_warning

## PRD-047.36-HF3 Delivery Metadata
- prd_id: PRD-047.36-HF3
- commit_hash: 59f0561
- push_status: pushed_to_origin_main
- status: passed


## PRD-047.36-HF4 Delivery Metadata
- prd_id: PRD-047.36-HF4
- commit_hash: cc5110e
- push_status: pushed_to_origin_main
- status: accepted_with_warning

## PRD-047.36-HF5 Delivery Metadata
- prd_id: PRD-047.36-HF5
- commit_hash: 4eb7b9a
- push_status: pushed_to_origin_main
- status: accepted_with_warning

## PRD-047.36-POST-HF Delivery Metadata
- prd_id: PRD-047.36-POST-HF
- commit_hash: faa34a1
- push_status: pushed_to_origin_main
- status: blocked

## PRD-047.36-HF6 Delivery Metadata
- prd_id: PRD-047.36-HF6
- commit_hash: c908d33
- push_status: pushed_to_origin_main
- status: accepted_with_warning

## PRD-047.37 Delivery Metadata
- prd_id: PRD-047.37
- commit_hash: 6ed92e1
- push_status: pushed_to_origin_main
- status: accepted_with_warning

Controlled rollout planning completed in `PRD-046.1.30` (plan-only): no provider execution, no normal-user activation, no production mutation; next execution gated by `PRD-046.1.31`.
