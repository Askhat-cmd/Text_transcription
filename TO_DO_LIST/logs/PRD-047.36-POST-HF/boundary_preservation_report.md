# PRD-047.36-POST-HF Boundary Preservation Report

## G5 — no_internal_db boundary
- verdict: `BLOCKER`
- boundary_flags: `none`
- writer_payload_count: `0`
- grounding_reason: `latest_turn_no_internal_db`
- reasons: `no_internal_db_trace_flag_missing`

## G6 — no_practice boundary
- verdict: `BLOCKER`
- boundary_flags: `none`
- writer_payload_count: `0`
- grounding_reason: `support_or_pushback_turn_trace_only`
- reasons: `no_practice_trace_flag_missing`

## G7 — Simple greeting/contact sanity
- verdict: `PASS`
- boundary_flags: `none`
- writer_payload_count: `0`
- grounding_reason: `greeting_or_contact`
- reasons: `none`

## G8 — Safety-sensitive panic helper
- verdict: `PASS_WITH_WARNING`
- boundary_flags: `none`
- writer_payload_count: `0`
- grounding_reason: `direct_one_step_no_kb_needed`
- reasons: `medical_escalation_boundary_soft`
