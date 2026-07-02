# PRD-047.39 Consolidation Roadmap PRD-047.40+

## PRD-047.40 - Dead Pipeline Removal
- Remove only inventory-proven `dead_confirmed` retired pipelines/prompts.
- Gate: full regression plus live smoke; no behavior drift.

## PRD-047.41 - Flag Consolidation
- Move env sprawl into one effective-config registry.
- Gate: admin runtime effective values before/after match.

## PRD-047.42 - God-File Decomposition
- Split writer/admin/contract/retrieval/config god-files by responsibility.
- Gate: contract tests and behavior diff proof.

## PRD-047.43 - Admin UI Dedup
- Remove compatibility-only duplicate admin controls.
- Gate: browser proof that remaining UI covers real use cases.

## Safety Polish Backlog
- S7 `panic_medical_escalation_boundary_soft` from PRD-047.38 stays backlog.
- Do not repair it inside architecture consolidation inventory.
