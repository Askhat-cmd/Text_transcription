# TASKLIST_PRD-014_NEO_Final_SD_Purge_and_Runtime_Contract_PROGRESS.md

## Статус
- [x] Создан PRD-014
- [x] Выполнен code purge (API/WebUI/runtime)
- [x] Обновлена документация NEO-only
- [x] Пройдены тесты и smoke
- [x] Подготовлен финальный отчет

## Этап 1. API контракт
- [x] Удалить `/questions/sag-aware` из backend routes
- [x] Удалить объявления этого endpoint из `api/main.py`
- [x] Удалить `user_level` из request модели для web-потока
- [x] Адаптировать runtime вызовы без `user_level`

## Этап 2. Runtime engine и memory
- [x] Удалить SD trace/runtime ветки из `answer_adaptive`
- [x] Удалить SD profile методы/запись из `conversation_memory`
- [x] Сохранить tolerant-read старых snapshot полей без их активного использования
- [x] Упростить flags/config от SD-переключателей

## Этап 3. Web UI
- [x] Удалить `QUESTIONS_SAG_AWARE`
- [x] Удалить передачу `user_level` в API запросах
- [x] Обновить типы API под NEO-only контракт
- [x] Сохранить только безопасную cleanup миграцию localStorage legacy ключей

## Этап 4. Документация
- [x] Обновить `docs/api.md` (NEO-only endpoint contract)
- [x] Обновить `docs/testing.md` (без SAG Phase 2 как активного runtime)
- [x] Обновить релевантные ссылки `docs/data_flow.md`, `docs/knowledge_graph.md`
- [x] Убрать `user_level` из активного примера в `docs/web_ui.md`

## Этап 5. Проверки
- [x] Запустить таргетные backend tests
- [x] Запустить таргетные frontend tests
- [x] Выполнить smoke через API/TestClient + SSE trace

## Лог выполнения
- 2026-04-13: Инициирован PRD-014 и старт реализации.
- 2026-04-13: Удален legacy API endpoint `/questions/sag-aware`, очищены request/response модели от `user_level`.
- 2026-04-13: В `api/routes.py` и `api/debug_routes.py` внедрен единый purge sanitizer (`user_level*`, `sd_*`, `sd_confidence_threshold` в config snapshot).
- 2026-04-13: Web UI очищен от `userLevel` контракта (`constants`, `types`, `api.service`, `useChat`, `ChatPage`, `storage cleanup`).
- 2026-04-13: Runtime memory/config очищены от активного `sd_profile` и SD-флагов; сохранен tolerant-read старых снапшотов.
- 2026-04-13: Прогоны:
  - backend: `.\\bot_psychologist\\.venv\\Scripts\\python.exe -m pytest -q bot_psychologist/tests/test_api.py bot_psychologist/tests/test_llm_streaming.py bot_psychologist/tests/test_concurrent_streams.py bot_psychologist/tests/regression/test_no_user_level_runtime_metadata.py bot_psychologist/tests/contract/test_trace_contract_after_purge.py bot_psychologist/tests/contract/test_live_metadata_contract_after_purge.py bot_psychologist/tests/integration/test_pipeline_without_level_adapter.py` → `11 passed, 10 skipped`.
  - frontend lint: `npm run lint` → OK.
  - frontend tests: `npm test` → `18 passed`.
- 2026-04-13: Дополнительный purge по запросу:
  - удалены `bot_agent/legacy/prompts`, `bot_agent/legacy/python`, `migrations`, `tests/test_sd_classifier.py`, `tests/test_sd_integration.py`.
  - обновлены `tests/contract/test_no_legacy.py`, `scripts/bootstrap_eval_sets.py`, `pytest.ini`, `README.md`.
  - проверка: `pytest -q bot_psychologist/tests/contract/test_no_legacy.py bot_psychologist/tests/regression/test_no_user_level_runtime_metadata.py bot_psychologist/tests/contract/test_trace_contract_after_purge.py` → `5 passed`.
