# PRD-047.36-HF5 Root Cause Report

Date: 2026-07-01
Status: `PASS`

## Root cause summary
The failing Chat 12 class was a coordination defect between retrieval/query composition, Writer grounding visibility, and payload assembly. The runtime could already find and select relevant knowledge, but contextual concept follow-ups could still be classified as trace-only and end with `grounding_reason=no_clear_retrieval_need`, leaving Writer with zero hidden knowledge payload.

## Suppression path before HF5
1. Dialogue / Fresh Gate
   - not a greeting/contact close
   - no hard blocker at this stage
2. Dialogue Pragmatics
   - contextual follow-up to the previous self-realization explanation
   - inherited concept context exists
3. Retrieval Query Build / current_turn_focus_v1
   - direct concept follow-up was not promoted to a knowledge-admission path
   - contextual follow-up could stay on trace-only / no-clear-retrieval-need semantics
4. Semantic Cards selection
   - relevant cards were still selected correctly
   - this proved selection was not the failing layer
5. Runtime Truth Trace classification
   - trace showed selected cards and filtered candidates
   - but no Writer-visible payload
6. Grounding Visibility / Chunk Inclusion Gate
   - `build_writer_grounding_visibility_v1` treated the turn like generic trace-only grounding
   - reason collapsed to `no_clear_retrieval_need`
7. Writer KB Payload builder
   - no base RAG admitted for Writer
   - semantic cards stayed `trace_only`
8. Final Writer prompt package
   - Writer answered without the selected hidden knowledge package

## Exact repair points
- [bot_psychologist/bot_agent/multiagent/contextual_retrieval_query_composer.py](C:/My_practice/Text_transcription/bot_psychologist/bot_agent/multiagent/contextual_retrieval_query_composer.py)
  - lines `388-414`
  - added a generic contextual concept-follow-up branch:
    - contextual follow-up or inherited topic
    - selected knowledge available
    - concept-followup wording
    - result: `query_kb`, `knowledge_context`, `include_for_writer_if_found=true`, `reason=direct_concept_followup_selected_knowledge`
- [bot_psychologist/bot_agent/multiagent/writer_context_package.py](C:/My_practice/Text_transcription/bot_psychologist/bot_agent/multiagent/writer_context_package.py)
  - lines `358-410`
  - added `concept_followup` visibility classification and `reason=direct_concept_followup`
  - lines `1033-1044`
  - added bounded selected-knowledge recovery from existing `memory_bundle.knowledge_rag_hits` when selected knowledge should flow and no hard blocker exists
  - lines `1170-1178`
  - changed payload ordering so one selected semantic card leads the minimal package on concept follow-up instead of being re-suppressed by payload ordering

## Why this stays inside scope
- no new runtime path
- no new agent
- no dictionary or alias map
- no term-specific route for one concept
- no DB/Chroma/source mutation
- semantic cards remain advisory-only and Writer-can-ignore

## Verified result after HF5
- `S-HF5-3` live:
  - retrieval action: `query_kb`
  - composer reason: `direct_concept_followup_selected_knowledge`
  - grounding reason: `direct_concept_followup`
  - selected cards:
    - `program_imperfect_self_v1`
    - `control_as_safety_v1`
    - `fact_vs_interpretation_v1`
  - Writer payload count: `2`
- `S-HF5-6` preservation:
  - `no_internal_db=true`
  - grounding reason: `latest_turn_no_internal_db`
  - Writer payload count: `0`

## Final diagnosis
HF5 repairs the admission contract itself:

`selected relevant knowledge -> no hard blocker -> minimal hidden Writer package`

The fix is coordination, not a dictionary.

