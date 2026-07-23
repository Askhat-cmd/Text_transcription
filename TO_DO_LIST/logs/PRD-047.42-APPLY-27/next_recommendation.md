# PRD-047.42-APPLY-27 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-28 - Block B Part 2 (groups 7-12, lines ~898-1015)`
- rationale:
  - Block B Part 1 is now fully extracted with full 17-case coverage, zero side effects in the helper layer, and the method's only remaining direct `last_debug` write closed;
  - groups 7-12 contain the most structurally complex cluster in the whole method (group 9: 4 internal locals, 4 return points, one computed-text outcome from a regex match) plus a call into the module-level (non-self) `starts_with_mechanical_revoicing` function;
  - groups 7-12 contain zero direct `last_debug` writes, so APPLY-28 is technically simpler than APPLY-27 on that specific risk axis, but larger in local-variable surface (group 9);
  - after Block B closes in full, `_enforce_mvp_free_dialogue_compliance` (225 lines, a separate method starting at line 1017) needs its own from-scratch boundary mapping - it has not been mapped at all yet.
