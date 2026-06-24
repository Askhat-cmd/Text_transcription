# PRD-047.32 Runtime Truth Audit

Status: complete
Date: 2026-06-24

## Source Gate
- Read PRD: `TO_DO_LIST/PRD-047.32_Owner_Web_Chat_Runtime_Truth_Trace_Legacy_Fallback_Noise_Collapse_RU.md`.
- Read owner Web Chat evidence: `TO_DO_LIST/context/ЧАТ_С_БОТОМ_3.txt`.
- Read PRD-047.31-HF1 reports: implementation, live smoke, tests, no-mutation proof, next recommendation.
- Read PRD-047.30 implementation report.
- Read root docs: `docs/PROJECT_STATE.md`, `docs/ROADMAP.md`, `docs/PRD_INDEX.md`, `docs/DECISIONS.md`.

## Audit Answers

1. Where is the UI/trace block `Чанки в Writer` formed?
- Frontend owner trace: `bot_psychologist/web_ui/src/components/chat/MultiAgentTraceWidget.tsx`, memory section lines around the accordion titled `Чанки в Writer (${(memory.semantic_hits || []).length})`.

2. What does it show now?
- It renders `memory.semantic_hits`, passed through `MemoryContextTrace`.
- These are memory/RAG semantic hits for trace/debug visibility, not a proof that a chunk reached Writer.
- This is a mixed/debug candidate view and can include trace-only candidates.

3. Where is Writer KB Payload formed?
- Backend payload builder: `bot_psychologist/bot_agent/multiagent/writer_kb_payload.py`.
- Writer context assembly: `bot_psychologist/bot_agent/multiagent/writer_context_package.py`.
- Prompt insertion: `bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py` under `WRITER KB PAYLOAD`.

4. Where is the exact payload list sent to Writer recorded?
- `writer_context_package.py` builds `writer_kb_payload` and `writer_kb_payload_trace`.
- `writer_kb_payload.py::build_writer_kb_payload_trace` records `payload_chunk_count`, `chunk_summaries`, `payload_sent_to_writer_char_count`, `payload_full_text_sent_to_writer`, `writer_can_ignore`, and `applied_as_authority`.
- `writer_agent_prompts.py` includes the formatted payload in the Writer prompt. The LLM canvas remains the manual proof surface.

5. Where can `rag_for_writer_count` diverge from visible trace labels?
- `writer_context_package.py` computes `rag_for_writer` after visibility filtering, but Web UI still labels all `memory.semantic_hits` as `Чанки в Writer`.
- Semantic cards may add actual Writer payload items while `rag_for_writer_count=0`. This is valid, but the current UI label makes it look contradictory.

6. Where does Hybrid Planner shadow write JSONDecodeError?
- `bot_psychologist/bot_agent/multiagent/hybrid_retrieval_planner.py`.
- `_parse_json_object` raises `json.JSONDecodeError`; `build_hybrid_retrieval_plan_v1` catches generic exceptions and returns `error=f"{exc.__class__.__name__}:{exc}"`, `valid=false`, `fallback_used=true`.
- Orchestrator copies this to `hybrid_retrieval_plan_error`, and UI renders it as `plan_error`, without clear shadow-only scope.

7. Where does `legacy_fallback_used` appear?
- Legacy adaptive entrypoint defaults are in `bot_psychologist/bot_agent/answer_adaptive.py` and API route normalization in `bot_psychologist/api/routes/common.py`.
- Current multiagent trace uses related fallback fields instead: `hybrid_retrieval_fallback_used`, `writer_kb_payload_trace.fallback_is_primary`, `writer_kb_payload_trace.fallback_reason`, `legacy_rag_query`, and retrieval query build fallback metadata.

8. Which legacy/fallback fields affect the answer and which are trace-only/compatibility noise?
- Active production inputs: executed retrieval query, `rag_included_for_writer`, `writer_kb_payload`, `final_answer_directive`, and Writer prompt assembly.
- Shadow/trace-only: Hybrid planner in `mode=shadow`, semantic cards when `status=trace_only`, overlay shadow, `memory.semantic_hits` when not selected for Writer.
- Compatibility/noise: owner-level `Чанки в Writer` label over `memory.semantic_hits`, unscoped `plan_error`, unscoped `fallback_used`, and `legacy_rag_query` shown without production/source context.

9. Where do advisory instructions duplicate in prompt assembly?
- `writer_agent_prompts.py` contains `FINAL ANSWER DIRECTIVE`, `ADVISORY CONTEXT SUMMARY`, `GROUNDING AUTHORITY`, `PRACTICE NOTE`, `WRITER FREEDOM CONTRACT`, `DIALOGUE POLICY`, `HUMAN-LIKE ANSWER POLICY`, and `mvp_free_dialogue_overrides`.
- PRD-047.30 already shortened some advisory prose, but `human_like_answer_policy.default_depth=medium_to_long` and broad free-dialogue affordances still encourage longer support/explanation answers.

10. Which support/explanation paths lead to verbose/mechanism-heavy answers?
- Free dialogue policy in `dialogue_policy.py` sets `default_depth=medium_to_long`, allows multiple options, and relaxes max-sentence constraints for ordinary non-safety turns.
- `writer_agent_prompts.py` exposes these fields directly to Writer.
- The PRD-safe fix is a small compact answer-shape hint for ordinary support/no-practice explanations, not a new agent or global hard cap.

## Implementation Direction Chosen
- Add `runtime_truth_trace_v1` inside existing Writer context / runtime summary / API trace surfaces.
- Rename owner UI label from `Чанки в Writer` to a candidate/trace-only label and separately display actual `Writer-visible payload`.
- Keep Hybrid Planner non-authoritative; add `planner_status`, `fallback_scope=shadow_only`, `production_answer_affected=false`, and `production_query_source=current_turn_focus_v1` where invalid shadow JSON occurs.
- Add scoped legacy/fallback labels rather than deleting risky legacy paths.
- Add bounded compactness guidance for ordinary support/no-practice explanation turns only.

## Post-Implementation Check
- `runtime_truth_trace_v1` now separates retrieved candidates, trace-only/filtered candidates, and actual Writer-visible payload.
- Owner Web Chat no longer labels `memory.semantic_hits` as `Чанки в Writer`; the UI label is now `Retrieval candidates / trace-only`.
- Actual Writer-visible payload proof is shown via `Runtime Truth Trace` and `Writer KB Payload`.
- Shadow planner invalid JSON is scoped as `shadow_only` and `production_answer_affected=false`.
