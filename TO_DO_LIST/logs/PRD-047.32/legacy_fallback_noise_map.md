# PRD-047.32 Legacy / Fallback Noise Map

Status: complete
Date: 2026-06-24

## A. Still Active And Needed
- `current_turn_focus_v1` retrieval query build
  - Scope: production.
  - Why kept: canonical query source for current live pilot; avoids stale previous-question concatenation.
- `writer_kb_payload_v1`
  - Scope: production Writer input.
  - Why kept: canonical structured payload when grounding is allowed.
- `final_answer_directive_v1`
  - Scope: production Writer control block.
  - Why kept: single existing answer-obligation authority.
- `writer_grounding_visibility_v1`
  - Scope: production Writer input gate plus trace.
  - Why kept: PRD-047.30/047.31 boundary that prevents broad KB default.
- `legacy_advisory_sanitizer`
  - Scope: production prompt sanitization.
  - Why kept: strips legacy control pressure and keeps only a short Writer-visible summary.

## B. Trace-Only Compatibility
- `memory.semantic_hits`
  - Scope: trace/debug candidates unless selected into `rag_for_writer`.
  - Noise risk: currently rendered in UI as if it were Writer payload.
- `semantic_cards_pilot` with `status=trace_only`
  - Scope: trace/debug only.
  - Noise risk: selected card count can look like Writer authority unless paired with payload count.
- `overlay_shadow`
  - Scope: trace_only.
  - Noise risk: matched candidates can look actionable unless `WRITER VISIBLE=false` and scope are shown.
- Hybrid Retrieval Planner when `mode=shadow`
  - Scope: shadow/trace only.
  - Noise risk: invalid JSON currently looks like a runtime failure despite not controlling production answer.

## C. Misleading Owner-Visible Noise To Collapse In This PRD
- `Чанки в Writer (...)`
  - Current meaning: memory/RAG candidate hits from `memory.semantic_hits`.
  - Problem: label claims Writer payload even when actual Writer KB Payload is empty or contains a different semantic-card payload.
  - PRD-047.32 action: rename as retrieval/memory candidates and add an explanatory note plus Writer-visible payload section/count.
- `hybrid_retrieval_plan_error=JSONDecodeError:...`
  - Current meaning: shadow planner invalid JSON.
  - Problem: owner trace does not say this is shadow-only and production answer was unaffected.
  - PRD-047.32 action: expose owner-safe `planner_status`, `fallback_scope=shadow_only`, `production_answer_affected=false`, and do not expose raw invalid provider output.
- Unscoped `fallback_used`
  - Current meaning: can refer to shadow planner fallback, Writer KB payload fallback, or legacy compatibility path.
  - Problem: ambiguous owner-level summary.
  - PRD-047.32 action: add scope fields and distinguish `production`, `shadow`, `trace_only`, and `compatibility`.

## D. Retirement Candidates For Later PRD
- `legacy_rag_query`
  - Why not removed now: still useful for proving current-turn focus repair and comparing old query builder behavior.
  - Future action: keep only in deep debug once current-turn focus stability is proven over more live owner sessions.
- `legacy_semantic_hits_fallback_v1`
  - Why not removed now: Writer KB payload has fallback reporting and older tests still rely on compatibility semantics.
  - Future action: retire after no eligible payload path is covered by tests and live smoke.
- Compatibility `legacy_fallback_used` fields on legacy API surfaces.
  - Why not removed now: API contract compatibility tests still expect safe defaults.
  - Future action: deprecate in schema after owner trace uses scoped fallback taxonomy consistently.

## PRD-047.32 Applied Cleanup
- Owner-visible candidate list renamed to `Retrieval candidates / trace-only`.
- `writer_kb_payload_trace` now carries `fallback_scope` and `payload_scope` so compatibility fallback does not look like the primary production path.
- Hybrid Retrieval shadow planner now exposes `planner_status`, `fallback_scope`, `owner_severity`, `production_query_source`, and `production_answer_affected`.
- Runtime truth trace surfaces `legacy_fallback_scope` as `none` or `compatibility`; risky legacy paths were not deleted in this PRD.
