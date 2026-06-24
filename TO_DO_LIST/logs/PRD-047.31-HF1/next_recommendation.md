# PRD-047.31-HF1 Next Recommendation

## Recommended Next PRD
- `PRD-047.32 - Owner Web Chat Runtime Truth / Legacy Fallback Noise Collapse v1`

## Why This Is Next
- The urgent stale-latest-turn bug is now repaired.
- The remaining visible quality debt is no longer “practice request ignored”; it is residual verbosity/fallback noise around support/explanation turns.
- Live smoke still shows:
  - verbose explanation drift on `не давай практику` turns
  - support answers that can over-explain instead of simply staying present
  - legacy runtime noise such as `datetime.utcnow()` deprecation and hybrid fallback residue

## Recommended Scope Boundary
- Do not add a new runtime path or new agent.
- Focus on retiring legacy fallback noise and reducing prompt/advisory verbosity in the current canonical pipeline.
- Keep broad KB hidden by default on ordinary support turns.
