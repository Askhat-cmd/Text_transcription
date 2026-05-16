# Architecture

## Runtime Flow
1. Upload/Source ingest (`book`/`youtube`).
2. Chunking (`BookChunker`/`SemanticChunker`).
3. Deterministic governance assignment (`chunk_type`, `allowed_use`, `safety_flags`).
4. Embeddings + Chroma indexing.
5. Registry + dashboard summary.
6. Review/enrichment artifacts as advisory metadata.
7. Retrieval API with governance-aware policy.

## Authority Layer
Текущая authority модель retrieval/runtime:
- `text`
- `source_id`
- `block_id`
- `chunk_type`
- `allowed_use`
- `safety_flags`
- `metadata.llm_enrichment` (advisory, non-authority for core governance)

## Legacy SD
`sd_level` / `sd_distribution` - legacy metadata для обратной совместимости.
SD не является architecture authority слоем.
