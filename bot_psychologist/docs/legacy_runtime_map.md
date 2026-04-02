# Legacy Runtime Map (Phase 0 Baseline)

Этот файл фиксирует baseline-карту legacy runtime перед миграцией на Neo MindBot (PRD_10.1, PHASE 0).

Источник для автопроверок:
- `bot_psychologist/tests/fixtures/legacy_runtime_map.json`
- `bot_psychologist/tests/inventory/test_legacy_runtime_map.py`

## Pipeline entrypoints
- `api/routes.py::ask_adaptive_question` (`/api/v1/questions/adaptive`)
- `api/routes.py::ask_adaptive_question_stream` (`/api/v1/questions/adaptive-stream`)
- `bot_agent.__init__::answer_question_adaptive`
- `bot_agent/answer_adaptive.py::answer_question_adaptive`

## Legacy runtime dependencies (зафиксированы для поэтапного удаления)
- `sd_classifier`
- `sd_level`
- `user_level_adapter`
- `decision_gate`
- `prompt_overlays`

## Feature flags (Phase 0 safety net)
- `NEO_MINDBOT_ENABLED`
- `LEGACY_PIPELINE_ENABLED`
- `DISABLE_SD_RUNTIME`
- `DISABLE_USER_LEVEL_ADAPTER`
- `USE_NEW_DIAGNOSTICS_V1`
- `USE_DETERMINISTIC_ROUTE_RESOLVER`

Правило: флагами управляем постепенной миграцией, без «слепого» rewrite.
