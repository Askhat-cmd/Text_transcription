# PRD-047.23 Writer Payload Consistency Audit

## C23-001
- rag_for_writer_vs_payload_mismatch: `False`
- rag_included_vs_payload_mismatch: `False`
- ui_chunks_vs_prompt_payload_mismatch: `False`
- trace_needs_schema_fix: `False`
- explanation: counts aligned

## C23-002
- rag_for_writer_vs_payload_mismatch: `True`
- rag_included_vs_payload_mismatch: `True`
- ui_chunks_vs_prompt_payload_mismatch: `False`
- trace_needs_schema_fix: `True`
- explanation: payload can still be built from semantic_hits fallback while rag_for_writer_count remains zero

## C23-003
- rag_for_writer_vs_payload_mismatch: `True`
- rag_included_vs_payload_mismatch: `True`
- ui_chunks_vs_prompt_payload_mismatch: `True`
- trace_needs_schema_fix: `True`
- explanation: web trace 'Чанки в Writer' count is sourced from semantic_hits, not guaranteed payload chunk_count
