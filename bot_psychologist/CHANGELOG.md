# Changelog

## v0.6.0 - 2026-03-25

### Changed
- Simplified retrieval pipeline: removed Stage/SD filters, flow is retrieval -> rerank -> cap -> LLM.
- Confidence scoring simplified (no voyage_confidence in formula).
- Fixed retrieval caps: `RETRIEVAL_TOP_K=5`, `VOYAGE_TOP_K=5`.
- Voyage rerank fallback keeps full candidate set (sorted by score).
- Increased adaptive request `query` limit to 2000 chars.
- Removed mirror-style opening from GREEN prompt to reduce reflective repeats in first sentence.
- Restored user level flow end-to-end: UI setting -> API payload `user_level` -> adaptive pipeline.
- Added active `USER_LEVEL` to trace `Config Snapshot`.

### Tests
- Updated tests to match simplified retrieval pipeline.
- Added integration-style tests for simplified retrieval and confidence scorer.
