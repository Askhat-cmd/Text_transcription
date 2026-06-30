# PRD-047.36-HF2 Next Recommendation

## Immediate Recommendation
- Do not add runtime dictionaries or alias routes for the remaining misses.
- Keep the PRD-047.36-HF2 repair as the final runtime-side fix for the direct-match silent-loss class.

## If Delivery/UI Truncation Is Still Reproducible
- Run `PRD-047.36-HF1 - Final Answer Delivery Integrity / Chat Bubble Truncation Repair`

## If Owner Priority Is Retrieval Coverage
- Prepare a separate source/DB preparation PRD for the branch-`D` cases:
  - `A1`
  - `A2`
  - `A3`
  - `A7`
  - `A8`
- Scope of that future PRD should stay outside runtime dictionaries and focus on source presence, chunking, or ingestion coverage.

## If Owner Priority Is Pilot Readiness
- Move next to `PRD-047.36 - Owner Pilot Readiness Gate / 12 Scenario Freeze v1`
- Use the current PRD reports as the truth baseline for which questions are already runtime-fixed and which are still source-missing.
