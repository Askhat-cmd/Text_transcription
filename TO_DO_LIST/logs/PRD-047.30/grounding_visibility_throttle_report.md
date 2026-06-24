# PRD-047.30 Grounding Visibility Throttle Report

Date: 2026-06-24
Status: completed

## Goal

Reduce Writer-visible grounding noise on non-KB turns without removing governance, retrieval, semantic cards, or full trace visibility.

## Main Mechanism

`writer_context_package.py` now builds `writer_grounding_visibility_v1` before packaging Writer-visible grounding.

The decision controls:

- `kb_visible_to_writer`
- `semantic_cards_visible_to_writer`
- `reason`
- direct/source/safety indicators
- trace-only availability

## Allowed Writer-Visible Grounding

- direct KB question
- direct source request
- explicit concept/mechanism explanation need
- safety-grounding boundary

## Forced Trace-Only Grounding

- ordinary emotional/support turns
- repair / simplify turns
- practice pushback
- greeting / close
- explicit `no_internal_db`
- follow-up turns where context matters but KB does not need to drive the answer

## Packaging Effects

- `rag_for_writer` becomes empty when visibility is hidden
- semantic cards move to `status=trace_only` instead of enriching Writer payload
- `writer_kb_payload` receives no fallback raw semantic hits when grounding is hidden
- `rag_candidates_for_trace` still records candidates and why they were excluded

## Prompt/Contract Effects

- Writer receives compact authority wording
- Writer receives grounding visibility JSON
- legacy advisory stays short and no longer re-expands the same constraints into long prose

## Verified Outcomes

- targeted PRD tests: `8 passed`
- relevant regression subset: `24 passed`
- live smoke after backend restart: `10 passed`, `0 blocked`

## Live Cases That Prove the Throttle

- `P30-001`: support turn -> hidden, reason `non_kb_emotional_support_turn`
- `P30-002`: anger/support turn -> hidden
- `P30-005`: `no_internal_db` -> hard suppression
- `P30-006`: simplify/repair -> hidden, semantic cards trace-only
- `P30-009`: contextual follow-up -> hidden, reason `contextual_followup_without_knowledge_need`

## Live Cases That Prove Grounding Still Works

- `P30-003`: direct KB question -> visible
- `P30-004`: concept explanation -> visible
- `P30-008`: safety boundary -> visible
- `P30-010`: direct source request -> visible
