# PRD-047.42-APPLY-29 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-30 - _enforce_mvp_free_dialogue_compliance Part 2 (groups K-P + final fallback)`
- rationale:
  - Part 1 is now fully extracted with full 17-case coverage and zero side effects in the helper layer;
  - groups K-P plus the method's unconditional final fallback remain inline and are the last remaining unextracted surface of `_enforce_mvp_free_dialogue_compliance`;
  - line numbers for Part 2 must be re-verified against live HEAD after this PRD merges (they will shift), per the project's standing 'no map trust without fresh reconnaissance' principle.
