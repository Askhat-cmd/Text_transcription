# PRD-047.36-HF5 Knowledge Admission Contract Report

Date: 2026-07-01
Status: `PASS`

## New contract
When all of the following are true:
- current turn is a direct conceptual follow-up or a continuation of a just-discussed concept
- selected relevant knowledge already exists
- no hard blocker applies

the existing pipeline must admit a minimal hidden Writer package instead of leaving the knowledge trace-only.

## Contract details
- admission trigger is generic:
  - contextual follow-up or inherited topic
  - selected knowledge available
  - concept-followup wording such as `как влияет`, `что об этом`, `объясни`, `смоделируй`
- admitted package stays minimal:
  - up to `2` items in the repaired path
  - one selected semantic card can lead the package
  - Writer may ignore grounding
  - semantic cards stay advisory-only
  - no authority transfer to cards or retrieval layer

## Hard boundaries preserved
- greeting/contact still suppresses Writer-visible KB
- `no_internal_db` still wins over any selected knowledge
- public answer must not mention DB/chunks/cards/trace
- no direct source dump
- no new route or model behavior override

## Live proof
- `S-HF5-1`
  - retrieval suppressed
  - Writer payload `0`
- `S-HF5-3`
  - retrieval action `query_kb`
  - composer reason `direct_concept_followup_selected_knowledge`
  - grounding reason `direct_concept_followup`
  - Writer payload `2`
- `S-HF5-4`
  - follow-up about Neurostalking keeps hidden knowledge visible
  - Writer payload `2`
- `S-HF5-6`
  - `latest_turn_no_internal_db`
  - Writer payload `0`

## What was deliberately not done
- no dictionary of psychological terms
- no alias map
- no `if concept == imperfect_self`
- no new agent
- no new runtime path
- no retrieval-ranking rewrite
- no DB/Chroma/source mutation

