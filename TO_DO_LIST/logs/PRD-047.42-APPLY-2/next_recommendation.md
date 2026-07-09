# PRD-047.42-APPLY-2 Next Recommendation

Recommended next slice: a second bounded `writer_agent.py` helper/static-method extraction PRD, not a broad class split.

Suggested target order:
1. Static tail helpers that do not depend on mutable agent state, starting with:
   - `_build_gentle_close_reply`
   - `_build_no_practice_fallback_text`
   - `_detect_language`
   - `_format_hits`
   - `_format_diagnostic_summary`
   - `_normalize_name`
2. Only after those static/pure pieces are out, move to small `self`-bound methods.
3. Leave `_call_llm` and `_enforce_answer_compliance` for the end of the decomposition chain.

Reasoning:
- this PRD proved the slice-first pattern on a truly pure helper block;
- the next safest work is more pure/static code, not lifecycle methods with mutable state;
- the highest-risk nodes remain `WriterAgent._call_llm` and `WriterAgent._enforce_answer_compliance`, so they should stay last.
