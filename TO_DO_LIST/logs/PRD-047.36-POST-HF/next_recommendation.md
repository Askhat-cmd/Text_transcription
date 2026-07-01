# PRD-047.36-POST-HF Next Recommendation

Next PRD: `PRD-047.36-HF6 - No-Internal-DB / No-Practice Boundary Trace Integrity`.

- blocker_reasons: `G5=no_internal_db_trace_flag_missing`, `G6=no_practice_trace_flag_missing`
- Scope must stay narrow: restore explicit boundary-flag truth for `no_internal_db` / `no_practice` in runtime trace and prove it on the same owner gate scenarios.
- Do not bundle cleanup, wording polish, retrieval expansion, or new product logic into that HF.
