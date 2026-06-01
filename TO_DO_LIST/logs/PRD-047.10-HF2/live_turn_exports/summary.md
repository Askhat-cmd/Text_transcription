# Live Turn Exports Summary (PRD-047.10-HF2)

- Exported case folders: `HF2-001 .. HF2-008`
- Exported turn files: see `turn_*.json` in each case folder
- Reproduce/fix cycle:
  - Initial live run against stale backend showed short-input `422` and stale regulate-stub occurrences.
  - Fresh backend rerun on `:8020` passed all global checks.
- Evidence focus fields per turn:
  - `dialogue_pragmatics`
  - `retrieval_decision`
  - `live_turn_evidence`
