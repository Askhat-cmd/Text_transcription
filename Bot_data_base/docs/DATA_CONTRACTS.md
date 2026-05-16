# Data Contracts

## Authority Fields
- `text`
- `source_id`
- `block_id`
- `chunk_type`
- `allowed_use`
- `safety_flags`
- `metadata.llm_enrichment` (advisory overlay)

## Storage Layers
- `all_blocks_merged.json` - canonical merged blocks snapshot.
- `registry.json` - source registry and summary stats.
- Chroma collection - retrieval index.

## Legacy Metadata
- `sd_level`
- `sd_distribution`

Эти поля могут сохраняться в historical artifacts, но не являются active authority для текущего retrieval/runtime/Diagnostic Center readiness.
