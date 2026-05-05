# TASKLIST PRD-040 — Config & Env Multiagent-First Cleanup

## Контекст
- PRD: `TO_DO_LIST/PRD-040_Config_Env_Multiagent_First_Cleanup.md`
- Цель: убрать legacy-first defaults/формулировки из config/env/docs и зафиксировать multiagent-first контракт.

## План работ
- [x] Обновить `bot_agent/feature_flags.py`
- [x] Обновить `api/admin_routes.py` (deprecated runtime flags + warning)
- [x] Обновить `.env.example`
- [x] Обновить docs (`README`, `local_dev_runbook`, `testing_matrix`, `migration_legacy_to_multiagent`, `multiagent_architecture`)
- [x] Обновить/добавить тесты (`test_feature_flags`, admin runtime contract, inventory env/docs)
- [x] Прогнать целевые тесты PRD-040

## Тесты
- [x] `.venv\Scripts\python -m pytest tests/test_feature_flags.py -q`
- [x] `.venv\Scripts\python -m pytest tests/test_admin_runtime_contract.py -q`
- [x] `.venv\Scripts\python -m pytest tests/inventory/test_env_example_multiagent_first.py -q`
- [x] `.venv\Scripts\python -m pytest tests/inventory/test_docs_multiagent_first_contract.py -q`
- [x] `.venv\Scripts\python -m pytest tests/inventory -q`
- [x] `.venv\Scripts\python -m pytest tests/test_admin_multiagent.py tests/test_admin_agent_llm_config.py tests/test_admin_runtime_contract.py -q`
- [x] `.venv\Scripts\python -m pytest tests/api -q`
- [x] `.venv\Scripts\python -m pytest tests/multiagent -q`
- [x] `.venv\Scripts\python -m pytest tests/test_llm_streaming.py -q`
- [x] `.venv\Scripts\python -m pytest tests/telegram_adapter -q`
- [x] `npm run build` (`bot_psychologist/web_ui`)

## Smoke/Checks
- [x] Runtime effective payload содержит `deprecated_runtime_flags`
- [x] При `LEGACY_PIPELINE_ENABLED=true` runtime остается `multiagent`
- [x] `.env.example` содержит `MULTIAGENT_ENABLED=true` и не содержит legacy-first комментарий

## Прогресс
- [x] PRD-040 изучен
- [x] Зоны кода/runtime/docs/tests проанализированы
- [x] Реализация
- [x] Тесты
- [x] Финальная сверка
