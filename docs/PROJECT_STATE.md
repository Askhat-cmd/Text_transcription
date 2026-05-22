# Project State - Bot Psychologist / Neo MindBot

## Current Stage
PRD-046.1.37 completed Diagnostic Center v1 as governed creator-live / developer-pilot layer. Creator-only / allowlist runtime remains allowed for pilot, normal users remain unaffected, broad rollout stays prohibited, and production_ready remains false.
## Current Runtime Architecture
User path remains unchanged: State Analyzer -> Thread Manager -> Context Assembly -> Diagnostic Card -> Diagnostic Center shadow/limited governance layers -> Writer.

## Diagnostic Center Acceptance State
`PRD-046.1.28` accepted provider-backed phase as governed limited-runtime candidate.
Boundary flags remain strict: `broad_rollout_allowed=false`, `production_ready=false`, `normal_user_activation_allowed=false`.

## Current Knowledge Base State
Focus source remains `123__кузница_духа`; governed blocks/chroma integrity is preserved by no-mutation policy and explicit gates.

## Current Context / Memory State
Context assembly + additive summaries remain active; deterministic fallback stays mandatory when async summaries are unavailable or invalid.

## Stable Modules
- Multiagent orchestrator and writer compliance chain.
- Diagnostic Center shadow and constrained prompt-constraint stack.
- BotDB registry/query/admin stability gates.
- Artifact encoding hygiene and no-mutation proof flows.

## Permanent Gates
- Final runtime governance acceptance gates.
- Provider-backed evidence and normal-user no-effect gates.
- Rollback/hard-stop, safety/KB boundary, trace sanitization gates.
- BotDB stability, response quality eval/calibration, contract and no-mutation gates.

## Known Risks
- Broad rollout without separate PRD would violate governance boundaries.
- Cleanup/deletion without manifest approval can break reproducibility.
- Historical artifact encoding noise may be misread as current runtime corruption without normalization report.

## Next Planned PRD
`Multiagent Quality & Tuning Track`
## Do Not Do Yet
- Do not activate broad Diagnostic Center runtime authority.
- Do not enable normal-user activation.
- Do not mutate KB governance authority fields (`chunk_type`, `allowed_use`, `safety_flags`).
- Do not perform Chroma reindex as part of this cleanup PRD.

## Documentation Update Rule
1. Update this file for every stage/runtime boundary PRD.
2. Update roadmap for sequencing changes.
3. Update decisions for architecture boundary changes.
4. Update PRD index after each merged PRD cycle.
5. Keep full historical details in `TO_DO_LIST`, keep docs operational and compact.

## Last Updated
- Date: 2026-05-22
- Source cycle: PRD-046.1.37

## PRD-046.1.35-HF4
Current Stage:
PRD-046.1.35-HF4 calibrated creator-live response behavior: example/explanation requests no longer trigger regulate_first by default, practice rejection suppresses body-action suggestions, and Web Trace displays non-empty safe Writer chunk previews.
Next:
PRD-046.1.36 Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1.

## HF4 Delivery Metadata
- prd_id: PRD-046.1.35-HF4
- commit_hash: 3a3c6a32a0c29551440432c0a266ab7cbab25b20
- push_status: pushed_to_origin_main

## PRD-046.1.36 Delivery Metadata
- prd_id: PRD-046.1.36
- commit_hash: 14a04164059dfff8b9b8e625cb1f3f1578e0d57b
- push_status: pushed_to_origin_main

## PRD-046.1.37 Delivery Metadata
- prd_id: PRD-046.1.37
- commit_hash: ff77155
- push_status: pushed_to_origin_main

## Diagnostic Center Track Status
Diagnostic Center Track Status: CLOSED FOR CURRENT PHASE
