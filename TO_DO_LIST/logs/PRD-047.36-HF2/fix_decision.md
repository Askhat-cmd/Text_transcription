# PRD-047.36-HF2 Fix Decision

## Decision
- Primary implemented branch: `B`
- Residual classified branch: `D`
- Final status target: `accepted_with_warning`

## Why Branch B Was Implemented
- Live audit proved that `A4` and `A6` already had a direct or near-exact source match in runtime candidates.
- The loss was not at raw source or retrieval ranking for those cases.
- The actual break was candidate-selection visibility:
  - `retrieval_decision.rag_included_count=0`
  - `writer_grounding_visibility_v1.reason=direct_knowledge_question`
  - policy-allowed knowledge hits already existed in `memory_bundle.knowledge_rag_hits`

## Minimal Generic Repair
- Added `source_chunk_match_trace_v1` and raw-hit summaries so the loss stage is explicit.
- Added a bounded recovery path in `writer_context_package.py`:
  - only when an explicit retrieval gate is empty;
  - only when KB is already allowed for the current direct knowledge turn;
  - only when a policy-allowed fallback hit has a near-exact current-turn match;
  - no new route, no new flag, no new agent, no dictionary term map.

## Why Branch D Remains Reported
- `A1`, `A2`, `A3`, `A7`, and `A8` still fail at `raw_source` in the current runtime proof.
- The relevant phrase or concept may exist in workspace source materials, but the current BotDB/runtime top-k does not prove a near-exact source chunk for those turns.
- PRD explicitly forbids masking this with runtime dictionaries or alias routes.

## Rejected Options
- No DB/source/chroma mutation.
- No hardcoded term dictionary.
- No marker-route workaround.
- No second retrieval system or new runtime path.

## Outcome
- `A4` and `A6` now pass with raw/runtime/payload proof.
- Missing-source cases remain honestly classified as missing.
