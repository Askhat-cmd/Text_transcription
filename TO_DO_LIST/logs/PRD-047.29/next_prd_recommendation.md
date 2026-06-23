# Next PRD Recommendation After PRD-047.29

Recommended next PRD:
`PRD-047.30 - Writer Grounding Visibility Throttle / Non-KB Turn Noise Reduction v1`

## Why

PRD-047.29 fixed explicit latest-turn constraint respect and added compact trace readability. The next visible noise class is narrower:

- on ordinary non-KB turns, Writer-visible KB payload and semantic-card grounding can still remain present even when the user did not ask a knowledge question
- this is still advisory-only, but it is now the clearest remaining pilot-noise layer

## Suggested Goal

- suppress or throttle Writer-visible KB/semantic-card grounding on non-knowledge emotional/support turns
- keep direct KB questions fully grounded
- keep `no_internal_db` hard suppression behavior from PRD-047.29 intact
