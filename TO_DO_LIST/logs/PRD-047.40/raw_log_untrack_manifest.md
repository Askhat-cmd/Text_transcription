# PRD-047.40 Raw Log Untrack Manifest

Date: 2026-07-08
Stage: A
Status: completed

## Scope
- Source manifest: `TO_DO_LIST/logs/PRD-047.39/logs_tracking_manifest.md`
- Requested action: untrack raw-artifact files only with `git rm --cached`
- Runtime/data mutation: none

## Proof
- `raw_manifest_count`: `532`
- `raw_now_count` from current `build_logs_tracking_manifest(...)`: `532`
- `raw_manifest_equals_current`: `true`
- `raw_keep_intersection`: `0`
- `raw_exists_on_disk_before_untrack`: `532`
- `staged_untrack_count`: `532`
- `raw_exists_on_disk_after_untrack`: `532`
- `missing_after_untrack`: `0`

## Notes
- The raw candidate list from PRD-047.39 still matches the current repo exactly for the `raw_artifact` tier.
- The broader summary counts in `logs_tracking_manifest.md` are stale relative to the current repo state, but the raw path block itself is still valid and was used as the source of truth.
- The action removed paths from Git tracking only. Files remain on disk for local inspection.
- No markdown evidence files were included in the staged Stage A untrack set.

## Execution
- Parsed the raw path block from `TO_DO_LIST/logs/PRD-047.39/logs_tracking_manifest.md`.
- Recomputed tiering via `tools/run_prd_047_39_architecture_inventory.py`.
- Executed `git rm -r --cached --pathspec-from-file=<temp_manifest>`.

## Commit Boundary
- Stage A commit must contain only:
- the `532` raw-log untrack index removals
- this Stage A manifest
