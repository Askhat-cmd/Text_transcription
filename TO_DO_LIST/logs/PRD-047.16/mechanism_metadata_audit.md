# PRD-047.16 Mechanism Metadata Audit

- schema_version: `mechanism_metadata_audit_v1`
- metadata_schema_version: `mechanism_aware_v1`
- mode: `dry-run`
- status: `passed`
- fixture_chunks_checked: `4`
- real_chunks_checked: `50`
- total_chunks_checked: `54`
- real_sample_status: `real_blocks_loaded`

## Distribution
- by_chunk_type: `{"case_example": 2, "concept": 5, "diagnostic_lens": 10, "mechanism": 5, "practice": 8, "safety": 2, "source_fragment": 22}`
- by_allowed_use: `{"diagnostic_hint": 18, "direct_to_writer": 22, "internal_lens": 17, "not_for_direct_quote": 54, "practice_suggestion": 8, "retrieval_seed": 42}`

## Validation
- error_count: `0`
- warning_count: `34`
- top_errors: `[]`
- top_warnings: `['missing_mechanism_hints', 'practice_direct_to_writer_without_preconditions', 'practice_missing_avoid_when', 'practice_missing_steps_short']`

## Boundary Confirmation
- dry-run only: yes
- Chroma reindexed: no
- DB mutated: no
- Writer/runtime path changed: no
- raw full chunk text in artifacts: no

## Notes
- Mechanism-aware metadata is semantic guidance, not deterministic routing.
- Legacy governance metadata was normalized without mutating source files, DB, or Chroma.
- Sample artifacts are sanitized previews only.
