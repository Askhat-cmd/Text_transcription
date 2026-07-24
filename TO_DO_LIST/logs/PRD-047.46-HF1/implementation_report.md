# PRD-047.46-HF1 Implementation Report

Date: 2026-07-24
Status: `accepted`

## Scope Delivered

- Applied the exact diff from PRD §1 to
  `bot_psychologist/bot_agent/multiagent/dialogue_pragmatics.py`
  (`_detect_short_utterance_type`): `close_ack` recognition now also
  matches short utterances that *start with* a close-acknowledgement
  marker (e.g. "спасибо, этого достаточно"), not only utterances made
  entirely of marker words, provided the message contains no
  followup-imperative marker ("объясни", "покажи", "дальше", ...).
- Added 3 new tests to
  `bot_psychologist/tests/test_dialogue_pragmatics_followup_v2.py`:
  - `test_thanks_with_extra_words_is_close_ack` — reproduces the exact
    S9/S10 pair from the PRD-047.46 gate report; confirms `close_ack` /
    `is_contextual_followup=False` / `followup_relation=
    "close_acknowledgement"`.
  - `test_thanks_with_intent_word_is_close_ack_not_followup` — a second
    natural close phrase ("понял, спасибо, буду разбираться").
  - `test_thanks_but_explain_more_is_still_imperative_followup` — guard
    case: gratitude combined with a followup imperative ("спасибо, но
    объясни подробнее ещё раз") must still resolve to
    `imperative_followup`, not `close_ack`.

## Diff verification

`git diff` on the changed file matches PRD §1's diff byte-for-byte
(verified before committing).

## Test Results

- Targeted run (4 files: `test_dialogue_pragmatics_v1.py`,
  `test_dialogue_pragmatics_followup_v2.py`,
  `test_multiagent_prd_047_10_hf1_dialogue_pragmatics.py`,
  `test_prd_047_10_hf1_dialogue_pragmatics_runner.py`): 14 passed, 1
  failed. The 1 failure
  (`test_writer_compliance_rewrites_regulate_stub_on_contextual_followup`)
  is the pre-existing, unrelated failure documented in PRD §2 — it
  fails identically before and after this fix (confirmed below), and
  does not exercise `_detect_short_utterance_type` (it builds
  `dialogue_pragmatics` as a hand-written dict, bypassing the function
  this PRD changes).
- Canonical `pytest tests/ -k writer -q`, run twice in the owner
  workspace (not an isolated worktree) — once with the fix stashed
  (pre-fix baseline) and once with the fix applied (post-fix):
  - Pre-fix: `14 failed, 356 passed, 2036 deselected`.
  - Post-fix: `14 failed, 356 passed, 2039 deselected` (the +3 selected
    count is exactly the 3 new tests added in this PRD).
  - The named failure list is **byte-for-byte identical** in both runs
    (see `test_results.md`). No new failure, no unexpected fix of an
    old failure.

## Runtime Scope

Only `bot_agent/multiagent/dialogue_pragmatics.py` was changed
(deterministic, non-LLM utterance classification helper). No
protected file of the .42-APPLY writer_agent.py decomposition series
was touched. No DB/Chroma/source/registry/processed-block/route/agent
mutation was introduced.

## Sanitization

No raw private chat logs or screenshots are part of this PRD's
deliverable; all evidence is deterministic function output.
