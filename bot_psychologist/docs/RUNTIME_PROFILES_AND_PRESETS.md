# Runtime Profiles And Presets (Runtime profiles и presets)

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now (Активно сейчас)
- `safe_guided` остаётся conservative preset unified runtime.
- `mvp_free_dialogue` по-прежнему поддерживается как developer-local alias.
- `free_dialogue_default` — разрешённый freer preset для MVP testing.

## Not Production Ready (Не готово к production)
- Ни один profile не включает broad production rollout.
- Ни один profile не обходит minimal safety.

## How To Test (Как тестировать)
- Используйте Admin Runtime effective payload.
- Убедитесь, что нет дублирующего orchestrator, Writer, Planner или API path для этих profiles.

## PRD-047.13-HF1 cleanup closure note (Заметка о закрытии cleanup PRD-047.13-HF1)
- Документ повторно проверен при закрытии cleanup; runtime behavior не менялся.

## PRD-047.13-HF1 Preset/Alias Closure (Закрытие preset/alias PRD-047.13-HF1)
- `safe_guided`: compatibility preset для conservative guided behavior.
- `mvp_free_dialogue`: developer-local compatibility alias, разрешающийся в freer preset.
- `free_dialogue_default`: значение preset внутри unified policy surface.
- Эти имена не должны представляться как отдельные bots, отдельные orchestrators или отдельные API paths.
