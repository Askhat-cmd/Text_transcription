# Retirement Candidates After Experiment

## 1. Candidate to retire soon
- `legacy_query_builder_fallback` once current-turn-focused retrieval remains stable across future PRDs.
- Trace-only surfaces that duplicate the same runtime truth and add noise without changing answers.
- Stale `must_answer` sources that survive only as compatibility residue.

## 2. Candidate to keep as advisory
- Safety floor and minimal answer-boundary checks.
- `overlay_shadow_trace` as non-authoritative observability only.
- `semantic_cards_pilot_v1` only as optional advisory grounding, not as a route.

## 3. Candidate to keep temporarily until more evidence
- Diagnostic Center advisory visibility.
- Heavy dialogue-act / answer-obligation path until simplification can prove no regression.
- `legacy_semantic_hits_fallback` until no-fallback evidence is sustained by later cleanup PRD.

## 4. Candidate to leave untouched
- Canonical `multiagent_adapter` production-like path until owner review decides otherwise.
- `writer_kb_payload_v1` as canonical knowledge-to-Writer path.
- `current_turn_focus_v1` as canonical retrieval query builder.

## 5. Candidate requiring separate risk PRD
- Any live replacement of the current runtime with thin spine.
- Any deletion of heavy layers from production code.
- Any removal of the old compatibility graph/surface without dedicated reproducibility review.

- evaluated_rows: `30`
