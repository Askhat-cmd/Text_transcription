# PRD-047.42-APPLY-23 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-24 - family 2 continuation (R07-R16)`
- rationale:
  - `R04` is now fully extracted as a pure classifier with full 17-case coverage and zero side effects;
  - `R07-R16` boundaries must be re-verified against live HEAD before cutting, per the same re-verification discipline used in this PRD and in APPLY-21/APPLY-22;
  - if any `R07-R16` rule shares `last_debug` writes with a neighboring rule, the full mechanic (d) from APPLY-22 should be used instead of the simplified classifier mechanic from this PRD.
