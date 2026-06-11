# PRD-047.15-HF2-R1 Source Gate Retrieval Map

## Active Runtime Path

- Active user path is the unified multiagent runtime in `bot_psychologist/bot_agent/multiagent/orchestrator.py`.
- Chat API enters through `bot_psychologist/api/routes/chat.py` and uses the existing runtime adapter.
- No separate retrieval runtime branch exists today; retrieval decisions are assembled inside the orchestrator.

## Current Retrieval Flow

1. `ThreadManager` updates thread state.
2. Orchestrator builds `pre_retrieval_composer` via `build_contextual_retrieval_query_composer_v1(...)`.
3. Orchestrator rewrites `retrieval_user_message` ad hoc:
   - `suppress_rag` or `use_current_context_only` -> blank query.
   - `query_kb` / `query_memory` / `query_kb_and_memory` with `composed_query` -> replace user message with that query.
   - otherwise -> original user message.
4. `MemoryRetrievalAgent.assemble(...)` receives only `user_message`, `thread_state`, `user_id`.
5. Inside `MemoryRetrievalAgent`, `_build_rag_query(...)` constructs the final RAG query from:
   - incoming `user_message`
   - `thread_state.core_direction`
   - first `thread_state.open_loop`
6. `_load_rag(...)` executes retrieval and returns raw hits plus retrieval debug.
7. `apply_knowledge_policy_v1(...)` filters hits for writer-safe usage.
8. Orchestrator later builds a second composer payload and merges it into `retrieval_decision`.

## Current Gaps Against PRD

- Query-before-RAG is implicit, not represented as a first-class planner contract.
- Retrieval execution trace does not preserve a stable distinction between:
  - original user message
  - planned composed query
  - legacy fallback query
  - final executed RAG query
- Composer currently contains domain-specific hardcoded concept expansions, which violates anti-overengineering scope.
- `MemoryRetrievalAgent` cannot accept a structured `retrieval_plan`; only a rewritten string query.

## Reusable Existing Pieces

- `writer_context_package.py` already exposes retrieval metadata to Writer.
- `api/models.py` and debug payloads are permissive enough to carry extra dict fields without a large schema rewrite.
- Existing tests already cover:
  - composer contracts
  - retrieval gating
  - `MemoryRetrievalAgent`
  - multiagent trace payloads

## Intended HF2-R1 Refactor

- Add a formal `retrieval_plan` contract before RAG execution.
- Keep one runtime path and pass planner output into `MemoryRetrievalAgent.assemble(...)`.
- Preserve legacy fallback behavior when planner is disabled, shadow-only, invalid, or empty.
- Store planner metadata in trace/debug and writer context without creating user-facing text.
