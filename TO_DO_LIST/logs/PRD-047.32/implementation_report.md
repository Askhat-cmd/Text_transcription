# PRD-047.32 Implementation Report

Status: passed_with_warning
Date: 2026-06-24
Main implementation commit: `aed27db63120709c32106eeeb46c716e8c61c405`

## What Changed
- Added `runtime_truth_trace_v1` to the existing Writer context package, Writer debug, runtime trace summary, orchestrator debug payload, API trace response, and Web Chat trace UI.
- Separated retrieved candidates, filtered/trace-only candidates, and actual Writer-visible payload with explicit counts and item evidence.
- Added Writer payload proof fields: `item_id`, `origin`, `sent_to_writer`, `writer_can_ignore`, `applied_as_authority`, and `inclusion_reason`.
- Renamed owner UI candidate list from misleading `Чанки в Writer` to `Retrieval candidates / trace-only` and added an explanatory note.
- Scoped Hybrid Retrieval shadow failures with `planner_status`, `fallback_scope`, `owner_severity`, `production_query_source`, and `production_answer_affected`.
- Added compact support/no-practice answer-shape hints through the existing dialogue policy and Writer prompt.
- Repaired direct-source phrasing `Что во внутренней базе...` so it does not fall through to stale contextual follow-up.

## What Was Intentionally Not Changed
- No new runtime path, agent, route, DB mutation, Chroma reindex, registry/source update, semantic-card content expansion, or thin-spine production apply.
- Hybrid Planner remains shadow/advisory where configured.
- Risky legacy/fallback paths were not deleted; they were scoped or moved behind clearer labels.
- Writer prompt was not rewritten from scratch.

## Files Changed
- Backend runtime/API: `writer_context_package.py`, `writer_kb_payload.py`, `writer_contract.py`, `writer_agent.py`, `writer_agent_prompts.py`, `dialogue_policy.py`, `dialogue_act_resolver.py`, `hybrid_retrieval_planner.py`, `runtime_trace_summary.py`, `orchestrator.py`, `api/models.py`, `api/debug_routes.py`.
- Web UI: `web_ui/src/components/chat/MultiAgentTraceWidget.tsx`, `MultiAgentTraceWidget.test.ts`, `web_ui/src/types/chat.types.ts`.
- Tests/tools: `tests/test_prd_047_32_runtime_truth_trace.py`, `tests/test_prd_047_32_hybrid_shadow_noise.py`, `tests/test_prd_047_32_answer_verbosity.py`, `tools/run_prd_047_32_live_owner_smoke.py`.
- Docs/artifacts: `TO_DO_LIST/PRD-047.32_TASK_LIST.md`, `TO_DO_LIST/logs/PRD-047.32/*`, `docs/PROJECT_STATE.md`, `docs/ROADMAP.md`, `docs/PRD_INDEX.md`, `docs/DECISIONS.md`.

## Trace Taxonomy Before/After
- Before: owner trace mixed memory semantic hits, RAG candidates, semantic cards, Writer payload, and fallback fields under ambiguous labels.
- After: `runtime_truth_trace_v1` exposes retrieved candidate count, trace-only count, filtered-out count, actual Writer-visible payload count/ids/types, grounding reason, payload decision reason, fallback scope, and planner production-impact status.

## `Чанки в Writer` Ambiguity Resolution
- The old label rendered `memory.semantic_hits`.
- The new label is `Retrieval candidates / trace-only`.
- Actual payload proof is now shown in `Runtime Truth Trace` and `Writer KB Payload`.

## Actual Writer-Visible Payload Proof
- Payload items are marked `sent_to_writer=true`.
- Semantic-card payload remains `applied_as_authority=false`.
- Filtered candidates are marked `sent_to_writer=false` with `filter_reason`.
- Live smoke practice and direct KB/source turns proved Writer payload count `1`.

## Hybrid Planner JSONDecodeError
- Raw invalid provider text is not exposed in owner trace.
- Shadow invalid JSON reports compactly as `shadow_invalid_json`, `fallback_scope=shadow_only`, `owner_severity=info`, and `production_answer_affected=false`.

## Legacy/Fallback Fields
- Active production fields remain: `current_turn_focus_v1`, `writer_kb_payload_v1`, `final_answer_directive_v1`, `writer_grounding_visibility_v1`.
- Compatibility fields remain for deep/debug proof: `legacy_rag_query`, payload fallback trace, legacy API fallback defaults.
- Owner summary now carries scope fields so compatibility/shadow labels do not look production-authoritative.

## Test Results
- Targeted PRD-047.32 tests: `8 passed`.
- PRD-047.30/047.31 preservation tests: `11 passed`.
- Regression subset: `15 passed`.
- UI lint/test/build: passed.
- Full `pytest tests -q`: blocked by unrelated known `_build_llm_prompts` import error.

## Live Smoke Results
- Backend/frontend restarted; health passed with Bot_data_base available.
- Mandatory owner scenario passed trace truth checks.
- Explicit practice path produced Writer payload `1`.
- Direct KB/source question produced Writer payload `1`.
- Ordinary support and no-internal-db turns produced Writer payload `0`.
- Warning: no-practice explanation remains above the soft compact target, though support/no-internal-db answers improved and the compact policy is now stricter.

## No-Mutation Summary
- No DB/Chroma/registry/source/governance mutation.
- No reindex.
- No new agent or production runtime path.
- No broad KB default re-enabled.

## Known Warnings
- Full suite collection still blocked by unrelated `_build_llm_prompts` import error.
- Some support/explanation answers can still be longer than target.
- Existing Vite chunk-size warnings remain.

## Next Recommendation
- `PRD-047.33 - Owner Pilot Stabilization / Answer Shape Calibration v1`.
