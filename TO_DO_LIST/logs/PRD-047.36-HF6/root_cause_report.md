# HF6 Root Cause Report

- verdict: `PASS`
- classification: `boundary_detected_but_not_exported_to_trace` + `boundary_exported_but_runner_not_extracting`

## Summary

Before HF6, both blocker turns were already correctly recognized inside the current runtime:
- `G5`: `latest_turn_constraints_v1.no_internal_db=true`, `grounding_reason=latest_turn_no_internal_db`, `Writer Payload = 0`
- `G6`: `latest_turn_constraints_v1.no_practice=true`, `grounding_reason=support_or_pushback_turn_trace_only`, `Writer Payload = 0`

The failure was not detection, not retrieval ranking, and not public answer behavior first. The failure was proof integrity:
- no stable owner/debug `boundary_trace_v1` existed across directive -> writer context -> runtime summary -> debug endpoint
- the post-HF readiness runner extracted `boundary_flags` only from top-level `latest_turn_constraints_v1`
- live debug payload exposed the constraints only under nested runtime summary, so `boundary_flags` collapsed to empty even when the boundary had already been honored

## G5

- scenario_id: `G5`
- latest_user_message: `Ответь без internal DB и без Нейросталкинга...`
- constraint_detected: `true`
- constraint_source: `latest_user_turn_explicit_text`
- final_answer_directive_flag: `true`
- writer_context_package_flag: `true`
- runtime_truth_trace_flag: `true`
- web_trace_boundary_flag before HF6: `false`
- gate_runner_boundary_flag before HF6: `false`
- writer_payload_count: `0`
- practice_blocked: `false`
- public_answer_violation: `false`
- loss_stage: `debug_trace_projection`
- root_cause: `boundary detected and applied, but no stable exported boundary object for owner/debug consumers`

## G6

- scenario_id: `G6`
- latest_user_message: `Объясни, почему я злюсь на себя, но без практик и упражнений.`
- constraint_detected: `true`
- constraint_source: `latest_user_turn_explicit_text`
- final_answer_directive_flag: `true`
- writer_context_package_flag: `true`
- runtime_truth_trace_flag: `true`
- web_trace_boundary_flag before HF6: `false`
- gate_runner_boundary_flag before HF6: `false`
- writer_payload_count: `0`
- practice_blocked: `true`
- public_answer_violation: `false`
- loss_stage: `debug_trace_projection`
- root_cause: `boundary detected and applied, but no stable exported boundary object for owner/debug consumers`

## Fix Scope

HF6 repaired the observability chain only:
- added `boundary_trace_v1`
- propagated it through final directive, writer context package, runtime truth trace, runtime summary, orchestrator debug, and debug API response
- updated gate extraction to read the stable boundary contract first

No retrieval ranking, DB, Chroma, source docs, Writer model, safety policy, or new runtime path was introduced.
