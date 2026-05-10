# KB Review Layer (v1)

This directory contains a minimal CLI-oriented human review workflow for KB enrichment metadata.

Scope of v1:
- Build a sanitized review queue from processed blocks.
- Generate a decision template.
- Validate decision overlays.

Non-goals of v1:
- No mutation of `all_blocks_merged.json`.
- No Chroma reset/reindex.
- No runtime bot behavior changes outside API retrieval policy PRDs.
- No direct apply of review decisions to production KB.

