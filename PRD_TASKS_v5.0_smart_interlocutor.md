# PRD Tasks — v5.0 Умный Полноценный Собеседник

Источник: `PRD v5.0 — Умный Полноценный Собеседник.md`

## 0. Подготовка
- [x] Прочитать PRD v5.0 и зафиксировать scope/инварианты
- [x] Создать task-файл в корне проекта

## 1. Fix C + Test — токены и FREE_CONVERSATION_MODE
- [x] Добавить runtime-параметры `FREE_CONVERSATION_MODE`, `MAX_TOKENS`, `MAX_TOKENS_SOFT_CAP`
- [x] Убрать хардкод token-limit в `bot_agent/llm_answerer.py`
- [x] Реализовать единый билдер API-параметров для chat/responses API
- [x] Добавить тесты `bot_psychologist/tests/test_llm_answerer.py`
- [x] Прогнать `pytest tests/test_llm_answerer.py -v`

## 2. Fix D + Test — приоритет промптов и FREE-ветка
- [x] Реализовать иерархию приоритетов промптов (base -> sd -> mode) с флагами
- [x] Добавить FREE-ветку системного промпта (без ограничивающих директив)
- [x] Добавить/обновить тесты `bot_psychologist/tests/test_path_builder.py`
- [x] Прогнать `pytest tests/test_path_builder.py -v`

## 3. Fix B1 + Test — routing параметры runtime
- [x] Добавить routing-параметры в `runtime_config.py` и schema/metadata
- [x] Добавить тесты `bot_psychologist/tests/test_routing_config.py`
- [x] Прогнать `pytest tests/test_routing_config.py -v`

## 4. Fix B2 — fast detector toggle
- [x] Внедрить флаг `FAST_DETECTOR_ENABLED` и threshold-логику в `fast_detector.py`
- [x] Проверить существующие тесты `test_fast_detector.py`

## 5. Fix A1/A2/A3 + Test — admin API
- [x] Добавить `/api/v1/admin/config`, `/schema`, `/status`
- [x] Добавить CRUD для `/api/v1/admin/prompts`
- [x] Добавить `/api/v1/admin/reload-data`
- [x] Добавить startup-создание `.default.md` снимков промптов
- [x] Добавить/обновить `bot_psychologist/tests/test_admin_api.py`
- [x] Прогнать `pytest tests/test_admin_api.py -v`

## 6. UI A/B — Admin Panel и RoutingTab
- [x] Починить вкладку «Промпты» (без `Failed to fetch`)
- [x] Добавить в UI: `MAX_TOKENS=null`, `MAX_TOKENS_SOFT_CAP`, `CONFIDENCE_CAP_*`
- [x] Обновить Runtime вкладку (status + reload-data)
- [x] Создать `RoutingTab.tsx` с предупреждением для слоёв 2–3

## 7. Регрессия и документация
- [x] Прогнать `pytest tests --tb=short`
- [x] Обновить `bot_psychologist/CHANGELOG.md` (v0.7.0)
- [ ] Подготовить commit/push
