# PRD-047.36-HF4 Frontend Browser Trace Report

Date: 2026-07-01

## Browser proof verdict
- `browser_evidence_present=true`
- `NO_TRACE_UNAVAILABLE_IN_FRESH_CHAT=true`

## Evidence summary
- Fresh 5-turn chat before reload:
  - `pipeline_count=5`
  - `trace_unavailable_count=0`
- Same chat after reload:
  - `pipeline_count=5`
  - `trace_unavailable_count=0`
- Old session after backend restart:
  - `pipeline_count=0`
  - `trace_unavailable_count=5`
  - `has_trace_expired_reason=true`
- Fresh new chat after restart:
  - `pipeline_count=2`
  - `trace_unavailable_count=0`
- Same new chat after reload:
  - `pipeline_count=2`
  - `trace_unavailable_count=0`
