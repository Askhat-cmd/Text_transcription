# PRD-047.36-HF2 Chat 8 Replay Report

## Method
- Replayed the PRD A1-A8 probes against live backend `:8001` and BotDB `:8003`.
- Used debug trace plus `source_chunk_match_trace_v1` to classify where grounding was found or lost.
- Raw private chat file stayed local and uncommitted; only derived probe outputs are recorded here.

## Probe Results
- `A1` `Что такое анестетическая депрессия?`
  - classification: `FAIL_raw_source_missing`
  - loss: `raw_source / no_raw_source_match_in_runtime_top_k`
- `A2` follow-up on `анестетическая депрессия`
  - classification: `FAIL_raw_source_missing`
  - loss: `raw_source / no_raw_source_match_in_runtime_top_k`
- `A3` `...в Нейросталкинге?`
  - classification: `FAIL_raw_source_missing`
  - loss: `raw_source / no_raw_source_match_in_runtime_top_k`
- `A4` `Что такое программа несовершенное Я?`
  - classification: `PASS_source_found_and_payload_visible`
  - repaired branch: empty explicit gate recovered from policy-allowed near-exact hit
- `A5` `Назови пять драйверов выживания.`
  - classification: `INCONCLUSIVE_missing_trace_or_insufficient_fields`
  - expected control: not treated as explicit source-proof knowledge question by this PRD
- `A6` `Что значит страдание как безопасность?`
  - classification: `PASS_source_found_and_payload_visible`
  - repaired branch: empty explicit gate recovered from policy-allowed near-exact hit
- `A7` `Что такое контролёр в панике?`
  - classification: `FAIL_raw_source_missing`
  - loss: `raw_source / no_raw_source_match_in_runtime_top_k`
- `A8` `Что такое духовная кома?`
  - classification: `FAIL_raw_source_missing`
  - loss: `raw_source / no_raw_source_match_in_runtime_top_k`

## Replay Conclusion
- Chat 8 now has explicit proof for where source grounding is found or lost.
- The silent-loss class is removed for the actionable direct-match cases.
- Remaining misses require a separate source/DB preparation decision, not a runtime dictionary patch.
