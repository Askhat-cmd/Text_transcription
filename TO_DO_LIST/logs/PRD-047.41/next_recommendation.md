# PRD-047.41 Next Recommendation

- Keep `LEGACY_PIPELINE_ENABLED` diagnostic-only behavior until the dedicated admin dedup / compatibility cleanup PRD.
- After that, the next safe consolidation target is the non-env `EDITABLE_CONFIG` subset (`LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `TOP_K_BLOCKS`, `ENABLE_CACHING`).
- Master-plan follow-up: proceed with god-file decomposition only after this registry becomes the documented source of truth in project docs.
