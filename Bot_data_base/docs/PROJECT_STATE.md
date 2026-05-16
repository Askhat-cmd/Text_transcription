# Bot_data_base Project State

## Runtime
- admin/api base: `http://127.0.0.1:8003`
- focus source: `123__кузница_духа`
- expected counts: `1/247/247`

## Governance
- authority: `chunk_type`, `allowed_use`, `safety_flags`, deterministic retrieval policy
- enrichment: advisory metadata layer

## Legacy SD
- legacy SD decommissioned from active ingestion/runtime path by default
- explicit legacy mode required for SD labeling invocation
- `sd_level` query input remains compatibility-only and ignored for filtering

## Chroma
- strict reconciliation gate required for runtime readiness
- recovery path documented in `CHROMA_RECOVERY.md`
