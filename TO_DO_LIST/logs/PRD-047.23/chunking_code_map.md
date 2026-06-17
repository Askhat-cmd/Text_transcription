# PRD-047.23 Chunking Code Map

## chunker
- path: `Bot_data_base/chunkers/book_chunker.py`
- functions: `_chunk_with_structure, _split_section_role_aware, _split_practice_section, _chunk_text_budget, _make_block`
- mutation_allowed_in_this_prd: `False`
- notes: Primary source-aware chunk splitter; assigns section role hints, chunk boundaries, split reasons and block payload text.

## storage_model
- path: `Bot_data_base/models/universal_block.py`
- functions: `to_bot_format`
- mutation_allowed_in_this_prd: `False`
- notes: Canonical stored block model; preserves block id, title, metadata and full block text before export/query.

## storage_export
- path: `Bot_data_base/storage/json_export.py`
- functions: `export_blocks_by_source, export_merged_blocks`
- mutation_allowed_in_this_prd: `False`
- notes: Writes processed source JSON and all_blocks_merged export used for read-only audit lookup.

## query_api
- path: `Bot_data_base/api/routes/query.py`
- functions: `query_knowledge_base, _build_chunk_result`
- mutation_allowed_in_this_prd: `False`
- notes: Returns retrieval hits to bot runtime and carries block content plus governance metadata.

## runtime_adapter
- path: `bot_psychologist/bot_agent/db_api_client.py`
- functions: `retrieve_relevant_context`
- mutation_allowed_in_this_prd: `False`
- notes: Bot-side HTTP adapter into Bot_data_base /api/query/.

## retrieval_runtime
- path: `bot_psychologist/bot_agent/multiagent/agents/memory_retrieval.py`
- functions: `run_memory_retrieval, _load_rag`
- mutation_allowed_in_this_prd: `False`
- notes: Builds composed query, executes retrieval and exposes planned/executed/legacy query trace.

## knowledge_policy
- path: `bot_psychologist/bot_agent/multiagent/knowledge_policy.py`
- functions: `apply_knowledge_policy_v1, build_safe_knowledge_debug_detail_v1`
- mutation_allowed_in_this_prd: `False`
- notes: Sanitizes hits for writer/debug and can expose preview-only detail in trace.

## writer_context_package
- path: `bot_psychologist/bot_agent/multiagent/writer_context_package.py`
- functions: `build_writer_context_package_v1`
- mutation_allowed_in_this_prd: `False`
- notes: Assembles rag_for_writer, rag_candidates_for_trace and can build payload from semantic hit fallback.

## writer_payload
- path: `bot_psychologist/bot_agent/multiagent/writer_kb_payload.py`
- functions: `build_writer_kb_payload, build_writer_kb_payload_trace, _truncate_excerpt`
- mutation_allowed_in_this_prd: `False`
- notes: Builds writer_kb_payload_v1 and truncation trace; key boundary between stored content and prompt canvas.

## trace_assembly
- path: `bot_psychologist/bot_agent/multiagent/orchestrator.py`
- functions: `run_multiagent_pipeline`
- mutation_allowed_in_this_prd: `False`
- notes: Assembles safe semantic hit detail, writer chunks detail and writer_kb_payload_trace into debug payload.

## api_trace_adapter
- path: `bot_psychologist/api/debug_routes.py`
- functions: `get_multiagent_trace, _build_semantic_hit_trace_list`
- mutation_allowed_in_this_prd: `False`
- notes: Normalizes debug trace lists and may surface preview-sized content as content_full fallback.

## trace_compat
- path: `bot_psychologist/api/routes/common.py`
- functions: `_normalize_semantic_hits_detail_for_debug_trace_compat`
- mutation_allowed_in_this_prd: `False`
- notes: Compatibility layer that limits semantic hit preview text before Web/API rendering.

## web_trace_preview
- path: `bot_psychologist/web_ui/src/components/chat/MultiAgentTraceWidget.tsx`
- functions: `render`
- mutation_allowed_in_this_prd: `False`
- notes: Displays 'Чанки в Writer' from memory.semantic_hits, which can diverge from writer_kb_payload chunk_count.
