# Unified Dialogue Policy V2 (Единая политика диалога V2)

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now (Активно сейчас)
- `safe_guided`, `mvp_free_dialogue` и `free_dialogue_default` разрешаются через одну unified policy surface.
- `mvp_free_dialogue` — compatibility alias/preset, а не отдельный orchestrator или API path.
- Порядок authority сохраняется: minimal safety, explicit user request, knowledge/concept need, writer freedom, planner/diagnostic advisory.

## Not Production Ready (Не готово к production)
- Developer-local profiles — не broad rollout profiles.
- Planner и diagnostic blocks не являются hard authority над содержимым final answer.

## How To Test (Как тестировать)
- Проверьте `/api/admin/runtime/effective` на `dialogue_policy.version`, `active_profile_alias` и `profile_preset`.
- Запустите architecture audit artifacts в `TO_DO_LIST/logs/PRD-047.12-HF1/`.

## PRD-047.13-HF1 cleanup closure note (Заметка о закрытии cleanup PRD-047.13-HF1)
- Документ повторно проверен при закрытии cleanup; runtime behavior не менялся.

## PRD-047.13-HF1 Split Closure (Закрытие split PRD-047.13-HF1)
- `unified_dialogue_policy_v2` — единственная текущая policy surface.
- `safe_guided`, `mvp_free_dialogue` и `free_dialogue_default` — значения preset/alias, разрешаемые unified policy, а не отдельные системы.
- Profile-specific depth/token/planner settings трактуются как configuration внутри того же runtime path.
