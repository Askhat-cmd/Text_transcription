# PRD-047.42-APPLY-21 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-22 - enforce_answer_compliance coverage-extension or first rule-family slice`
- rationale:
  - the prelude is now isolated with full 17-case coverage and stable before/after snapshots;
  - rule-family cuts should happen only after an explicit architect decision on whether to widen the harness beyond the current `22/75` covered rules;
  - the first future family slice should respect the APPLY-20 nesting warning (`R04 ⊃ R05 ⊃ R06`) rather than flatten the cascade.
