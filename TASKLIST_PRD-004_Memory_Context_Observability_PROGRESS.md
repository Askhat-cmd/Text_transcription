# TASKLIST PRD-004 Memory Context Integrity & LLM Observability (PROGRESS)

Status: DONE  
PRD: `bot_psychologist/docs/PRD-004-Memory-Context-Observability.md`  
Started: 2026-04-09  
Completed: 2026-04-09

## Wave 0 — Intake
- [x] Pull PRD-004 from commit `e37ebf7`.
- [x] Read PRD and extract FIX-4/5/6/7 requirements.
- [x] Map real code paths for context build, llm-payload endpoint, and memory save flow.

## Wave 1 — FIX-4 + FIX-6 (critical)
- [x] Ensure summary-aware context build path is deterministic (`summary` + `recent window`).
- [x] Ensure hybrid query includes summary excerpt + latest user turns and does not shrink aggressively.
- [x] Add `CONTEXT_BUILD mode=... summary_len=... recent_turns=... total_prompt_chars=...` log.
- [x] Remove/avoid duplicate memory persistence calls in request flow.
- [x] Add `MEMORY save ... reason=` logging contract.
- [x] Add/update unit tests for context composition and single-save behavior.

## Wave 2 — FIX-5 (observability)
- [x] Introduce structured prompt payload object with named sections.
- [x] Return structured JSON in `/api/debug/session/{id}/llm-payload`.
- [x] Add section-level `chars` and `tokens_est=len//4`.
- [x] Add diagnostics fields (`summary_present`, `summary_lag`, `recent_dialog_turns`, `hybridquery_len`, `hybridquery_text`).
- [x] Keep backward compatibility for `?format=flat`.
- [x] Add/update debug route tests.

## Wave 3 — FIX-7 (performance)
- [x] Move summary generation to background task (`asyncio.create_task`) outside critical response path.
- [x] Ensure task starts after response stream completion point in runtime flow.
- [x] Add `SUMMARY_TASK scheduled/done` logs.
- [x] Ensure task failure is warning-only (no pipeline crash).
- [x] Add/update async/background summary behavior tests.

## Validation
- [x] Run targeted unit tests (memory/debug/telegram unaffected).
- [x] Run related integration subset.
- [x] Update this tasklist with evidence.

## Validation Evidence
- `cd bot_psychologist && .venv\Scripts\python -m pytest tests/test_llm_payload_endpoint.py tests/test_hybrid_query.py tests/unit/test_memory_snapshot_v12.py tests/unit/test_memory_save_contract_prd004.py tests/unit/test_memory_fallback_chain.py tests/integration/test_context_continuity_between_sessions.py tests/unit/test_summary_v12.py tests/regression/test_streaming_sd_runtime_disabled_contract.py tests/test_retrieval_pipeline_simplified.py tests/test_phase4.py tests/unit/test_trace_payload_schema.py -q`
- Result: `29 passed` (warnings: existing numpy deprecation in `session_manager.py`)


## Notes
- UI debug panel switched to `?format=flat` for backward-compatible rendering while backend default is structured payload.
