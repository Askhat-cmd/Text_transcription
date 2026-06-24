# PRD-047.30 Prompt Before/After Summary

Date: 2026-06-24
Status: completed

## Before

- Writer could receive KB payload plus semantic-card enrichment even on ordinary support/repair turns
- legacy advisory summary repeated `final_answer_directive_v1` signals in longer prose
- prompt had weaker explicit wording about which layers are mandatory vs optional
- runtime trace could not state clearly whether grounding was intentionally hidden or simply absent

## After

- Writer gets `writer_grounding_authority_note`
- Writer gets `writer_grounding_visibility_json`
- KB/semantic cards are explicitly framed as optional grounding
- support/repair/simplify/pushback turns suppress Writer-visible grounding by default
- trace/debug still expose hidden grounding evidence and the suppression reason

## Net Prompt Effect

- less duplicate advisory prose
- clearer ordering of authority
- smaller chance that Writer sounds like internal KB recitation
- better explanation of why grounding is present or absent on a turn

## Important Non-Change

- this PRD did not create a new prompt system or new route
- `final_answer_directive_v1` remains the main behavioral control
- `knowledge_policy.py` still governs chunk safety/eligibility before packaging
