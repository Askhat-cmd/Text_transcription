# PRD-047.30 Next Retirement Targets

Date: 2026-06-24
Status: ready_for_follow_up

## Concrete Candidates

- long duplicate advisory phrasing in `legacy_advisory_sanitizer.py`
  - keep the compact summary
  - move more repeated constraint phrasing to trace-only if no regression appears

- any remaining writer-visible fallback path that can reintroduce raw semantic hits
  - current PRD closed the main leak in `writer_context_package.py`
  - follow-up should prove no parallel fallback path remains

- semantic-card visibility on non-KB turns
  - now trace-only by packaging rule
  - next PRD can evaluate whether writer-visible semantic-card payload is needed anywhere beyond direct knowledge turns

- retrieval-context duplication relative to Writer KB payload
  - both can still describe similar grounding context
  - follow-up should decide whether one of them can be made thinner

- legacy advisory overlap with `final_answer_directive_v1`
  - especially practice/simplify/no-internal-db restatement

## Not Retirement Targets Yet

- `knowledge_policy.py`
- `final_answer_directive_v1`
- `runtime_trace_summary_v1`
- direct KB/source grounded path
