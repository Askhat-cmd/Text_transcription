# PRD-043 Repository Hygiene Audit

## Deleted temp artifacts
| Path | Reason |
|---|---|
| `bot_psychologist/.pytest_cache/` | Local pytest cache |
| `bot_psychologist/.tmp_pytest_*` | Local pytest temp basetemp directories |
| `bot_psychologist/**/__pycache__/` | Generated Python bytecode cache |
| `bot_psychologist/tests/test_sqlite.db*` | Temporary local test DB artifacts |
| `bot_psychologist/.tmp_uvicorn_*.log` | Temporary uvicorn output logs |
| `bot_psychologist/tests_before.txt` and related snapshots | Local run snapshots, not source artifacts |
| `bot_psychologist/live_test_report.*` | Local live test outputs |
| `bot_psychologist/prd025_verify_report.json` | Local verification report |

## Runtime local state removed
| Path | Reason |
|---|---|
| `bot_psychologist/data/threads/*_active.json` | Runtime-generated thread state |
| `bot_psychologist/data/threads/*_archive.json` | Runtime-generated archived thread state |
| `bot_psychologist/data/threads/live_test_*.json` | Runtime-generated live test state |
| `bot_psychologist/data/threads/sha256` | Empty local artifact, not required by contract |

## Archived documents
| Old path | New path | Reason |
|---|---|---|
| `AUDIT_MULTIAGENT_MIGRATION_READINESS_2026-05-01.md` | `bot_psychologist/docs/archive/legacy_migration/AUDIT_MULTIAGENT_MIGRATION_READINESS_2026-05-01.md` | Historical migration audit |
| `bot_psychologist/docs/legacy_physical_purge_audit_prd041.md` | `bot_psychologist/docs/archive/legacy_migration/legacy_physical_purge_audit_prd041.md` | Historical migration audit |
| `bot_psychologist/docs/post_purge_remaining_review_modules_prd042.md` | `bot_psychologist/docs/archive/legacy_migration/post_purge_remaining_review_modules_prd042.md` | Historical migration audit |
| `bot_psychologist/docs/post_purge_stabilization_audit_prd042.md` | `bot_psychologist/docs/archive/legacy_migration/post_purge_stabilization_audit_prd042.md` | Historical migration audit |
| `bot_psychologist/docs/MULTIAGENT_LAUNCH_CHECKLIST.md` | `bot_psychologist/docs/archive/legacy_migration/MULTIAGENT_LAUNCH_CHECKLIST.md` | Historical launch checklist |
| `bot_psychologist/docs/migration_legacy_to_multiagent.md` | `bot_psychologist/docs/archive/legacy_migration/migration_legacy_to_multiagent.md` | Historical migration details retained in archive |

## Kept active
| Path | Reason |
|---|---|
| `bot_psychologist/data/.gitkeep` | Keep data directory in repo |
| `bot_psychologist/data/threads/.gitkeep` | Keep empty runtime state directory |
| `bot_psychologist/logs/app/.gitkeep` | Keep logs structure without committing logs |
| `bot_psychologist/logs/retrieval/.gitkeep` | Keep logs structure without committing logs |
| `bot_psychologist/logs/error/.gitkeep` | Keep logs structure without committing logs |
| `bot_psychologist/tests/inventory/*` | Active inventory contract tests |

## Review later
| Path | Reason | Suggested future PRD |
|---|---|---|
| `bot_psychologist/tests/test_decision_gate.py` and related legacy-looking tests | May still protect reused diagnostics/support code paths | PRD-044 REVIEW modules audit |
| `bot_psychologist/tests/phase8_runtime_support.py` | REVIEW cluster from post-purge stabilization | PRD-044 REVIEW modules audit |
