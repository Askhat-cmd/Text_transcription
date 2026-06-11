# Architecture Current (Текущая архитектура)

- status: current
- last_verified_prd: PRD-047.13-HF1
- source_of_truth: docs/PROJECT_STATE.md; docs/PRD_INDEX.md; /api/admin/runtime/effective
- active_now: true
- not_production_ready: true
- related_artifacts: TO_DO_LIST/logs/PRD-047.13-HF1; TO_DO_LIST/reports/PRD-047.13-HF1_IMPLEMENTATION_REPORT.md

## Active Now (Активно сейчас)
- Активный пользовательский путь — единый multiagent runtime в `bot_agent.multiagent.orchestrator`.
- `unified_dialogue_policy_v2` разрешает profile presets и передаёт Writer через один `WriterContract`.
- После Writer и Validator выполняется `final_answer_acceptance_gate_v1`, и только затем — dialogue state, last offer и memory acceptance.
- Diagnostic Center, Planner, Active Line и Diagnostic Card остаются advisory/context sources.

## Not Production Ready (Не готово к production)
- Широкий rollout не включён.
- Activation для обычных пользователей не одобрен.
- Free dialogue profile — developer-local.

## How To Test (Как тестировать)
- Запустите targeted backend tests для final answer gate и orchestrator quarantine.
- Запустите `scripts/run_prd_047_12_hf1_acceptance.py --live --browser` против локального backend и Web UI.

## PRD-047.13-HF1 cleanup closure note (Заметка о закрытии cleanup PRD-047.13-HF1)
- Документ повторно проверен при закрытии cleanup; runtime behavior не менялся.
