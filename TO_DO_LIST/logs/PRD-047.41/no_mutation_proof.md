# PRD-047.41 No-Mutation Proof

This PRD stayed within config-truth consolidation and bounded hygiene.

## Not changed

- Writer prompt logic and model-selection behavior.
- Retrieval ranking, candidate selection policy, and source documents.
- Safety policy and panic/medical escalation behavior.
- Bot_data_base, Chroma, registry data, processed blocks, and reindex flow.
- Runtime-path topology: no new agent, no new route, no new fallback path, no new parallel config system.

## Changed within scope

- Added one authoritative effective-config registry module and integrated it into the existing admin runtime effective payload.
- Converted only the proven-frozen bucket-A env reads into constants with the same defaults.
- Reclassified bucket-B metadata labels without removing existing admin edit capability.
- Masked secret-like env flags to `is_set`-only export.
- Moved helper runner location from root `tools/` into `TO_DO_LIST/tools`.
- Updated docs and reports to reflect the new consolidation state.

## Evidence

- Focused contract/admin/config tests passed on the changed surfaces.
- Before/after admin runtime payload diff is documented and normalized for restart-only volatile fields.
- Full regression logs were captured both before and after the implementation; both timed out at the same global-suite debt boundary rather than exposing a new PRD-local failure class.
