# PRD-047.36 Next Recommendation

## Recommended Next Step
- `PRD-047.36-HF1 - No-Practice Boundary and Benign-Turn Acceptance Alignment`

## Why This Is The Right HF
- The final readiness gate found one clear product blocker:
  - `S8` still violates explicit `no_practice`
- The same gate also found a bounded but real delivery-integrity risk:
  - benign turns like `S1`, `S2`, `S7`, and `S12` can be quarantined by `final_answer_acceptance_gate_v1`
  - because of that, `saved memory assistant message` parity is not consistently provable

## Narrow HF Scope
- Repair explicit latest-turn `no_practice` compliance for free Writer answers.
- Calibrate `final_answer_acceptance_gate_v1` only for benign accepted turn classes that are currently being over-quarantined:
  - greeting / self-intro style openings
  - ordinary short support
  - explicit practice answers that are already user-requested
  - gratitude / close acknowledgements
- Keep all source-proof, hidden-competence, safety, DB/Chroma, and runtime-path boundaries unchanged.

## Explicit Non-Goals
- No new retrieval dictionary.
- No alias-map.
- No reindex.
- No new agent.
- No new route.
- No broad answer-style rewrite.
