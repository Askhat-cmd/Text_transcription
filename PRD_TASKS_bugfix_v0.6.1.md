# PRD Tasks — Bugfix + Quality Restoration (v0.6.1)

Источник: `PRD Bugfix + Quality Restoration — bot_psychologist v0.6.1.md`

## 0. Подготовка
- [x] Создать файл задач в корне проекта
- [x] Проверить текущее состояние зон фикса (`data_loader`, `retriever`, `runtime_config`, `api`)

## 1. Баг #1 — двойной вызов DataLoader при warmup
- [x] Добавить singleton-guard в `bot_psychologist/bot_agent/data_loader.py`
- [x] Обеспечить thread-safe инициализацию через `threading.Lock`
- [x] Добавить лог cache-hit: `[DATA_LOADER] cache_hit blocks={len}`
- [x] Реализовать корректный `reload()` с полным сбросом состояния
- [x] Проверить warmup-инициализацию на отсутствие двойной загрузки

## 2. Баг #2 — fallback при недоступном Bot_data_base
- [x] Реализовать цепочку: `api -> json_fallback -> degraded`
- [x] Провести через конфиг поля `DEGRADED_MODE`, `DATA_SOURCE`, `ALL_BLOCKS_MERGED_PATH`
- [x] Добавить корректную деградированную ветку в retriever
- [x] Обновить `/api/v1/health` метаданными источника и статуса

## 3. Баг #3 — агрессивный confidence_cap
- [x] Перенести cap-значения в конфиг (`high=7`, `medium=5`, `low=3`, `zero=0`)
- [x] Убрать хардкод cap, читать из runtime-конфига
- [x] Добавить лог применения cap (`level/cap/before/after`)

## 4. Тесты
- [x] Добавить `bot_psychologist/tests/test_data_loader_singleton.py`
- [x] Добавить `bot_psychologist/tests/test_data_loader_fallback.py`
- [x] Добавить `bot_psychologist/tests/test_confidence_cap.py`
- [x] Прогнать целевые тесты bugfix-набора
- [x] Прогнать регрессионный набор (релевантный)
- [x] Прогнать `pytest tests -v --tb=short` и устранить падения

## 5. Документация
- [x] Добавить запись о bugfix в `bot_psychologist/CHANGELOG.md`

## 6. Итог
- [x] Все пункты PRD v0.6.1 закрыты
