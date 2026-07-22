# PRD-047.42-APPLY-22 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-23 - family 2 (obligation_specific_repairs_before_profile_split, originally R04-R16) boundary re-verification and first slice`
- rationale:
  - family 1 (`R01-R03`) is now fully extracted with a first branching (mechanic d) helper and full 17-case coverage;
  - the APPLY-20 map underestimated family 1's true width once already (a hidden second wave of locals plus a nested rule); the next family's boundaries must be re-scouted against live HEAD, not trusted literally from the map;
  - the architect should decide whether to widen harness coverage before cutting family 2, given the same underestimation risk noted in the v4.25 master plan update.
