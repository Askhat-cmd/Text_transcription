# PRD-047.42-APPLY-24 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-25 - mvp_free_branch_handoff decision, then rule families 4-6`
- rationale:
  - family 2 is now fully extracted (`R04` plus `R07-R16`) with full 17-case coverage and zero side effects in the helper layer;
  - `mvp_free_branch_handoff` (line 746) is a single delegating self-call with no internal logic - a strong candidate to stay inline, but the architect should confirm before treating it as settled;
  - rule families 4-6 from the APPLY-20 map each need fresh reconnaissance before sizing the next PRD, per the owner's pace decision: batch whole families only when reconnaissance confirms no hidden last_debug competition or nested self-dependency risk.
