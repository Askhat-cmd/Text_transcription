# PRD-047.16 Source Audit

## Git Gate

- `git status --short` before changes showed one untracked source PRD file:
  - `TO_DO_LIST/PRD-047.16_Mechanism_Aware_KB_Preparation_Chunk_Metadata_v1_RU.md`
- Recent history confirms the previous accepted cycle is present:
  - `cb7762e PRD-047.15-HF2-R2 ignore local admin screenshots`
  - `09bc32e PRD-047.15-HF2-R2 post-push metadata sync`
  - `3480666 PRD-047.15-HF2-R2 hybrid retrieval visibility sync`
- No existing `PRD-047.16` implementation layer was found before this work.

## Current KB / BotDB Inventory

- Real governed export exists:
  - `Bot_data_base/data/processed/all_blocks_merged.json`
  - `Bot_data_base/data/processed/books/123__кузница_духа_blocks.json`
- Real registry exists:
  - `Bot_data_base/data/registry.json`
- Real Chroma store exists:
  - `Bot_data_base/data/chroma_db`
- Raw focus-source markdown exists:
  - `Bot_data_base/data/uploads/books/КУЗНИЦА ДУХА v.2.md`

## Existing Schema / Governance Contour

- Bot runtime governance contracts currently live in:
  - `bot_psychologist/bot_agent/knowledge_governance/contracts.py`
  - `bot_psychologist/bot_agent/knowledge_governance/validators.py`
  - `bot_psychologist/bot_agent/knowledge_governance/chunker.py`
  - `bot_psychologist/bot_agent/knowledge_governance/export.py`
- BotDB ingestion/governance contracts currently live in:
  - `Bot_data_base/governance/governance_adapter.py`
  - `Bot_data_base/governance/chunking_quality.py`
  - `Bot_data_base/models/universal_block.py`
  - `Bot_data_base/storage/json_export.py`
  - `Bot_data_base/knowledge_governance/enrichment_contracts.py`
  - `Bot_data_base/knowledge_governance/enrichment_validators.py`
- Retrieval/runtime touchpoints that already read governed metadata:
  - `Bot_data_base/api/retrieval_policy.py`
  - `bot_psychologist/bot_agent/multiagent/hybrid_retrieval_planner.py`
  - `bot_psychologist/bot_agent/multiagent/contextual_retrieval_query_composer.py`
  - `bot_psychologist/bot_agent/chroma_loader.py`

## Stable Legacy Metadata Detected

- Current processed blocks already carry:
  - `metadata.governance.schema_version`
  - `metadata.governance.chunk_type`
  - `metadata.governance.allowed_use`
  - `metadata.governance.safety_flags`
  - `metadata.governance.lens_family`
  - `metadata.governance.practice_metadata`
  - `metadata.governance.governance_notes`
  - `metadata.governance.source_trace`
  - `metadata.chunking_quality.*`
- These fields cannot be broken in this PRD because they remain part of the live retrieval/export shape.

## Gap Against PRD-047.16

- No dedicated `mechanism_aware_v1` schema exists.
- No backward-compatible adapter exists for normalizing legacy blocks into the target contract.
- No read-only audit runner exists that produces mechanism-aware artifacts over fixture and real local blocks.
- No explicit `visibility`, `quote_policy`, `depth_level`, or `writer_can_ignore` contract exists in BotDB metadata.
- No artifact pack currently answers:
  - which chunks are ready for mechanism-aware retrieval;
  - which chunks need manual review;
  - which practice chunks are unsafe without richer metadata;
  - which lens chunks must remain internal-only.

## Selected Implementation Path

- New schema home: `Bot_data_base/knowledge_governance/mechanism_metadata.py`
- Reason:
  - this is the existing offline knowledge/governance layer closest to `UniversalBlock`, export JSON, and audit tooling;
  - it avoids creating a parallel runtime architecture;
  - it keeps `PRD-047.16` read-only and outside the live Writer path.
