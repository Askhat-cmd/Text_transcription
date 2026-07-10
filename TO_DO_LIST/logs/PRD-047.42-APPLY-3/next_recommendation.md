# PRD-047.42-APPLY-3 Next Recommendation

Recommended next slice: move the remaining small non-static fallback/name-continuity methods before touching any giant lifecycle/compliance body.

Suggested target order:
1. Small `self`-bound fallback methods next:
   - `_repair_greeting_without_mechanism_lecture`
   - `_resolve_one_step_or_no_practice_fallback`
   - `_set_final_answer_shape_debug`
   - `_defer_no_stub_repair`
   - `_apply_name_continuity`
   - `_extract_user_name`
2. After those, isolate client/cost helpers:
   - `_get_client`
   - `_estimate_cost`
3. Keep `_call_llm` and `_enforce_answer_compliance` for the end of the decomposition chain.

Reasoning:
- slice 2 proved that class-surface-preserving delegates keep risk low when static helpers still have `self.` callers;
- the next safest work is still inside the fallback tail, but now in the smallest `self`-bound methods;
- the highest-risk nodes remain `_call_llm` and `_enforce_answer_compliance`, so they should stay last.
