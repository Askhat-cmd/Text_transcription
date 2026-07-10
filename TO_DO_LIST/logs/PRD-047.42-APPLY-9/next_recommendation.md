# PRD-047.42-APPLY-9 Next Recommendation

- recommended_next_prd: `PRD-047.42-APPLY-10 - writer_agent.py _call_llm writer_kb_payload_and_trace_capture`
- rationale:
  - this PRD removes the second pre-provider helper-friendly cluster cleanly, proving the local-only detector intermediates do not need to leak back into `_call_llm`;
  - the next natural edge is `writer_kb_payload_and_trace_capture`, but it writes into `self.last_debug`, so the move should use an explicit debug-patch boundary instead of another pure-only helper assumption;
  - provider dispatch, response parsing, and the giant `WRITER_USER_TEMPLATE.format(...)` render remain intentionally deferred until more preparation logic is extracted first.
