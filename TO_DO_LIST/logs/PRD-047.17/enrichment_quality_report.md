# PRD-047.17 Enrichment Quality Report

- status: `passed`
- source_id: `123__кузница_духа`
- source_doc: `Кузница Духа`
- total_source_blocks: `247`
- selected_blocks: `80`
- candidate_count: `80`
- by_chunk_type: `{"case_example": 4, "concept": 10, "diagnostic_lens": 16, "mechanism": 10, "practice": 21, "safety": 2, "source_fragment": 16, "style_voice": 1}`
- by_risk_level: `{"high": 11, "low": 19, "medium": 50}`
- validation_warning_counts: `{"practice_current_metadata_missing_contraindications": 21}`
- validation_blocked_counts: `{}`

## Notes
- Deterministic candidates are manual-review inputs only.
- Candidates are not applied to live metadata, Writer, runtime, DB, or Chroma.
- LLM candidate mode is deferred/skipped unless explicitly confirmed and safely configured.
