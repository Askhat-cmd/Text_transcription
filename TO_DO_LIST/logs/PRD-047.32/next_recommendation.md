# PRD-047.32 Next Recommendation

Recommended next PRD: `PRD-047.33 - Owner Pilot Stabilization / Answer Shape Calibration v1`.

## Why
- Runtime truth is now visible enough to distinguish retrieval candidates, trace-only evidence, filtered candidates, and actual Writer payload.
- Remaining quality debt is no longer hidden trace ambiguity; it is answer-shape calibration.
- No-practice/simple explanation answers still sometimes exceed the soft compact target even when compact policy is active.

## Suggested Scope
- Calibrate answer shape in a small owner-pilot loop.
- Keep Writer as final author.
- Avoid new agents, new runtime paths, DB mutation, Chroma reindex, and broad prompt rewrite.
- Preserve explicit practice, direct KB/source, no-internal-db, and broad-KB-hidden support behavior.
