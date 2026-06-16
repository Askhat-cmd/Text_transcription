# PRD-047.17 Enrichment Quality Report

- status: `passed`
- source_id: `123__кузница_духа`
- source_doc: `Кузница Духа`
- total_source_blocks: `247`
- selected_blocks: `20`
- candidate_count: `20`
- by_chunk_type: `{"diagnostic_lens": 6, "mechanism": 2, "practice": 6, "source_fragment": 6}`
- by_risk_level: `{"high": 3, "low": 2, "medium": 15}`
- validation_warning_counts: `{"practice_current_metadata_missing_contraindications": 6}`
- validation_blocked_counts: `{}`

## Notes
- Deterministic candidates are manual-review inputs only.
- Candidates are not applied to live metadata, Writer, runtime, DB, or Chroma.
- LLM candidate mode is deferred/skipped unless explicitly confirmed and safely configured.
