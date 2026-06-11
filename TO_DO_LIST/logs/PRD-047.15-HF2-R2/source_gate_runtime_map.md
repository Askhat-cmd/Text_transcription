# PRD-047.15-HF2-R2 Source Gate Runtime Map

## Runtime truth sources

- `bot_psychologist/api/admin_routes.py`
  - `/api/admin/runtime/effective`
  - already exposes `hybrid_retrieval_planner` effective payload
  - currently missing explicit `model` / `max_tokens` in admin response
- `bot_psychologist/api/debug_routes.py`
  - `/api/debug/session/{session_id}/multiagent-trace`
  - `/api/debug/session/{session_id}/traces?format=compact`
  - already exposes HF2-R1 hybrid retrieval fields in full trace
  - compact mode currently strips heavy fields but does not add `hybrid_retrieval_summary`
- `bot_psychologist/api/models.py`
  - `MemoryContextTrace.hybrid_retrieval` exists as generic dict
  - `MultiAgentTraceResponse` contains base HF2-R1 hybrid retrieval fields
- `bot_psychologist/bot_agent/multiagent/orchestrator.py`
  - runtime source of hybrid retrieval trace/debug values
  - already writes:
    - `hybrid_retrieval_plan`
    - `hybrid_retrieval_planner_version`
    - `hybrid_retrieval_planner_mode`
    - `hybrid_retrieval_plan_valid`
    - `hybrid_retrieval_plan_error`
    - `hybrid_retrieval_universal_gate`
    - `hybrid_retrieval_llm_called`
    - `hybrid_retrieval_llm_reason`
    - `hybrid_retrieval_fallback_used`
    - `planned_composed_query`
    - `executed_rag_query`
    - `legacy_rag_query`
    - `query_before_rag_proof`
    - `needed_chunk_types`
    - `mechanism_hints`
    - `retrieval_gap_reason`
    - `writer_can_ignore_rag`
- `bot_psychologist/bot_agent/multiagent/hybrid_retrieval_planner.py`
  - source of effective planner settings
  - `get_hybrid_retrieval_planner_settings()` already resolves:
    - `mode`
    - `version`
    - `model`
    - `max_tokens`

## Web surfaces before HF2-R2

- `bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx`
  - Runtime tab shows both:
    - editable raw `runtime` config group
    - read-only effective runtime cards
  - this exposes stale visual controls:
    - raw dialogue profile selector
    - raw `Knowledge Graph` checkbox
  - `Advanced Controls` shows duplicate sub-tabs:
    - `LLM`
    - `Retrieval`
    - `Diagnostics`
    - `Routing`
    - `Prompts`
    - `Compatibility`
  - no visible Hybrid Retrieval Planner runtime block
- `bot_psychologist/web_ui/src/components/chat/MultiAgentTraceWidget.tsx`
  - shows `rag_query`
  - does not render a dedicated Hybrid Retrieval visibility block
- `bot_psychologist/web_ui/src/types/admin.types.ts`
  - no typed `hybrid_retrieval_planner` contract yet
- `bot_psychologist/web_ui/src/types/chat.types.ts`
  - no typed hybrid retrieval summary / root-level trace fields yet

## HF2-R2 implementation boundary

- allowed:
  - add read-only metadata fields
  - add admin/web trace visibility
  - hide stale primary UI surfaces
  - move legacy status into Compatibility read-only surface
- forbidden:
  - mutate planner decision semantics
  - change writer authority
  - change retrieval execution semantics
  - change KB / DB / storage contracts
