# Diagnostic Center Eval Harness

## Permanent Harness Families
- Final runtime governance acceptance gates.
- Provider-backed evidence and budget gates.
- Normal-user no-effect gates.
- Rollback and hard-stop gates.
- Safety/KB boundary and trace/provider sanitization gates.
- BotDB stability gates.
- Response quality eval/calibration packs.
- Contract and no-mutation proofs.
- Artifact encoding hygiene validation.

## Harness Principles
- Deterministic checks first.
- No destructive cleanup in harness execution.
- Historical evidence remains reproducible.
- Cleanup candidates are manifest-only until explicit approval PRD.

## Operational Rule
Any future rollout/authority-expansion PRD must reuse these harness families and keep conservative baseline checks as blockers.
