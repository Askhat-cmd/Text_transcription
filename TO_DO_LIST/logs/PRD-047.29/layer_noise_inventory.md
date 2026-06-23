# PRD-047.29 Layer Noise Inventory

Date: 2026-06-23
Status: completed

## What Was Repaired In This PRD

- Added compact `latest_turn_constraints_v1` on the canonical current pipeline.
- Made explicit latest-turn constraints visible inside `final_answer_directive_v1`, Writer contract prompt assembly, and compact runtime trace summary.
- Added `no_internal_db` suppression at the Writer-visible payload boundary in `writer_context_package_v1`.
- Added compact `runtime_trace_summary_v1` for pilot/debug surfaces without deleting the full trace.

## Noise Still Present But Allowed In Scope

- Writer-visible KB payload and semantic cards are still present on ordinary non-KB-forbidden turns.
  - This is still advisory-only, not answer authority.
  - It is now explicitly suppressible when the user says `no_internal_db=true`.
- `final_answer_directive`, `dialogue_policy`, `retrieval_decision`, and `live_turn_evidence` remain large debug blocks.
  - They stay because this PRD adds a compact top layer instead of removing deep observability.
- Legacy advisory sanitization still exists alongside raw final directive.
  - This remains acceptable because the writer-visible layer is now constrained by latest-turn booleans.

## Biggest Remaining Pilot Noise Candidate

- Non-KB turns can still carry Writer-visible KB/semantic-card grounding even when the user did not ask a knowledge question.
- This did not violate PRD-047.29 acceptance, but it is the clearest next retirement/throttling target.

## Safe Retire-Next Candidates

- Conditional suppression of Writer-visible KB payload on non-knowledge emotional/support turns.
- Conditional suppression of semantic-card enrichment on simplify/repair/support turns unless grounding is truly needed.
- Compacting or collapsing duplicate advisory summaries when `final_answer_directive_v1` already carries the same signal.

## Not Retired Here On Purpose

- Full multiagent trace
- Semantic cards subsystem itself
- Writer KB payload subsystem itself
- Overlay trace
- Diagnostic Center shadow/advisory chain

Reason: this PRD targeted latest-turn constraint respect and top-level pilot readability, not subsystem deletion.
