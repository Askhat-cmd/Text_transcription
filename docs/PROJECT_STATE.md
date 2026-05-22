# Project State - Bot Psychologist / Neo MindBot

## Current Stage
PRD-046.1.35-HF3 verified creator live RAG-to-Writer delivery. KB snippets are present and safe, while Writer KB Context Payload v2 remains backlog.
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
`PRD-046.1.36 - Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1`
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
- Source cycle: PRD-046.1.35-HF3
