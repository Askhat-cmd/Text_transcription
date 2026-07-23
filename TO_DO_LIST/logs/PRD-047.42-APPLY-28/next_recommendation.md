# PRD-047.42-APPLY-28 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-29 (or a boundary-mapping PRD) - _enforce_mvp_free_dialogue_compliance boundary mapping`
- rationale:
  - `_enforce_answer_compliance` decomposition is now complete across all APPLY-21..28 slices; there is no more content to extract from that method;
  - `_enforce_mvp_free_dialogue_compliance` (a separate method, ~225 lines at last estimate before this PRD) has never been mapped - assumptions about its structure should not be carried over from `_enforce_answer_compliance`'s decomposition, per the project's standing 'no map trust without fresh reconnaissance' principle (the APPLY-20 map itself underestimated family widths twice);
  - once that method closes, the lightweight Epoch 2 gate (owner decision #4) opens on Scenario A completion, pending confirmation that no hidden complexity surfaces during that method's reconnaissance.
