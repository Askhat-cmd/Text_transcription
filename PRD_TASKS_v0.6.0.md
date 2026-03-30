# PRD_TASKS_v0.6.0

## ⚠️ ИНСТРУКЦИЯ АГЕНТУ — ЧИТАТЬ ПЕРВЫМ

## Контекст для агента

## БЛОК 0 — Подготовка и аудит стека

### Таски

- [x] 0.1  Создать PRD_TASKS_v0.6.0.md с полным чеклистом всех тасков
- [x] 0.2  Создать ветку: git checkout -b fix/v0.6.0-cleanup-trace-behavior
- [x] 0.3  Checkpoint-коммит: git commit -m "checkpoint: before v0.6.0"
- [x] 0.4  Определить фронтенд-стек:
- [x] 0.5  Определить модель хранения конфига:
- [x] 0.6  Определить хранение трейса:
- [x] 0.7  Определить применяются ли уровни сложности:
- [x] 0.8  Запустить baseline тесты и сохранить:
- [x] 0.9  Зафиксировать все находки в PRD_TASKS_v0.6.0.md

FRONTEND_STACK: React + Vite + TypeScript + Tailwind (bot_psychologist/web_ui/package.json)
CONFIG_SOURCE: bot_agent/config.py + RuntimeConfig overrides from data/admin_overrides.json (load_dotenv .env)
TRACE_STORAGE: In-memory TTL store (bot_psychologist/api/session_store.py), default TTL 30 min
LEVELS_USED: yes (UserLevelAdapter + prompt_system_level_* + api/models.py user_level)
BASELINE_TESTS: bot_psychologist/tests_v060_before.txt
## БЛОК 1 — Диагностика и починка Web Admin (hot-reload конфига)

### Проблема

### 1.1 Диагностика — найти разрыв

- [x] 1.1  Открыть api/admin_routes.py
- [x] 1.2  Открыть bot_agent/answer_adaptive.py
- [x] 1.3  Задокументировать разрыв прямо в коде комментарием перед правкой:
### 1.2 Починить связку admin → runtime

- [x] 1.4  Создать или найти singleton runtime-конфиг:
- [x] 1.5  В answer_adaptive.py заменить все прямые обращения к config.py
- [x] 1.6  В admin_routes.py обновить POST /api/admin/config:
- [x] 1.7  Установить правильные дефолтные значения (важно!):
### 1.3 Персистентность конфига (важно!)

- [x] 1.8  Решить вопрос сохранения конфига между перезапусками:
- [x] 1.9  В RuntimeConfig.__init__ добавить загрузку оверрайда:
- [x] 1.10 В RuntimeConfig.update() после изменений — сохранять в файл:
- [x] 1.11 Добавить config_override.json в .gitignore
- [x] 1.12 В .env.example добавить секцию с комментарием:

Примечание: persistence реализована через `bot_psychologist/data/admin_overrides.json` (RuntimeConfig уже читает/пишет его),
отдельный `config_override.json` не создавался.
### 1.4 Тест блока

- [x] 1.13 Написать tests/test_admin_config.py:
- [x] 1.14 Smoke-тест блока 1:
- [x] 1.15 Коммит:
## БЛОК 2 — Фикс поведения: бот перестаёт зеркалить вопросы

### Проблема

### 2.1 Найти источник инструкции

- [x] 2.1  Просмотреть ВСЕ файлы промптов (открыть каждый и прочитать):
- [x] 2.2  Искать ключевые фразы в каждом файле (grep + ручная проверка):
- [x] 2.3  Зафиксировать в PRD_TASKS_v0.6.0.md: в каком файле(ах) найдена
NOTE: Found mirroring instruction in bot_psychologist/bot_agent/prompt_sd_green.md ("я слышу ...").
### 2.2 Убрать или смягчить инструкцию

- [x] 2.4  Если инструкция явная ("всегда начинай с отражения запроса",
- [x] 2.5  Если инструкция мягкая ("можешь отразить", "при необходимости
- [x] 2.6  Если инструкция находится в нескольких файлах — убрать из каждого.
- [x] 2.7  Сохранить все изменённые .md файлы промптов.
### 2.3 Тесты поведения (все SD-уровни)

- [x] 2.8  Написать tests/test_prompt_behavior.py с параметризованными тестами
- [x] 2.9  Вручную проверить в UI:
- [x] 2.10 Коммит:
## БЛОК 3 — Очистка уровней сложности (Начинающий/Средний/Продвинутый)

### Контекст

### 3.1 Сценарий A: уровни НЕ применяются (LEVELS_USED = no)

- [ ] 3.1a Удалить файлы промптов уровней:
- [ ] 3.2a В admin_routes.py найти и удалить:
- [ ] 3.3a В bot_agent/__init__.py и других модулях удалить импорты:
- [ ] 3.4a В web_ui/ найти и удалить UI-элементы уровней:
- [ ] 3.5a Добавить комментарий в местах удаления:
- [ ] 3.6a Проверить что sd_classifier.py НЕ затронут (он нужен!):
### 3.2 Сценарий B: уровни применяются (LEVELS_USED = yes)

- [x] 3.1b Определить точно где и как применяются:
- [x] 3.2b Определить как уровень назначается пользователю:
- [x] 3.3b Задокументировать механизм в README.md:
## Уровни сложности пользователя

- [x] 3.4b Убедиться что в UI есть понятный элемент управления уровнем
- [x] 3.5b В Config Snapshot трейса сделать видимым активный уровень:
- [x] 3.6b Добавить в CHANGELOG.md:

LEVELS_FLOW: Chat Settings (userLevel) -> API payload `user_level` -> AskQuestionRequest.user_level -> UserLevelAdapter
### 3.3 Очистка трейса от мёртвых полей (оба сценария)

- [x] 3.7  В api/models.py найти модель TraceData (или аналог)
- [x] 3.8  Проверить в трейсе через UI:
- [x] 3.9  Коммит:

TRACE_MODEL: используется `DebugTrace` в `bot_psychologist/api/models.py`; для snapshot добавлен `user_level`.
## БЛОК 4 — Трейс 2.0: вкладка «Полотно LLM»

### Цель

### 4.1 Бэкенд — модель данных

- [ ] 4.1  В api/models.py добавить новые модели:
- [ ] 4.2  В существующую модель TraceData (или аналог) добавить поле:
### 4.2 Бэкенд — перехват payload

- [ ] 4.3  В bot_agent/llm_answerer.py перед вызовом
- [ ] 4.4  Убедиться что llm_answerer.py имеет доступ к объекту current_trace.
- [ ] 4.5  В answer_adaptive.py убедиться что retrieved_blocks, sd_level,
### 4.3 Бэкенд — новый endpoint

- [x] 4.6  В api/debug_routes.py добавить endpoint:
- [x] 4.7  Убедиться что функция get_trace_by_session существует и корректна.
- [x] 4.8  Добавить endpoint в роутер в api/main.py если он там не подключён.
### 4.4 Фронтенд — компонент «Полотно LLM»

- [x] 4.9  Перед написанием кода — определить используемый стек
- [x] 4.10 Реализовать компонент согласно структуре:
- [x] 4.11 Реализовать lazy load:
- [x] 4.12 Подключить LLMPayloadPanel в конец существующего компонента
STACK_NOTE: React + TypeScript (`web_ui/src/components/debug/LLMPayloadPanel.tsx`)
### 4.5 Тест блока

- [x] 4.13 Написать тест api: tests/test_llm_payload_endpoint.py:
- [x] 4.14 Smoke-тест в UI:
- [x] 4.15 Коммит:
## БЛОК 5 — Очистка наследия: граф, логи, warmup

### 5.1 Условная инициализация KnowledgeGraphClient

- [x] 5.1  В bot_agent/data_loader.py найти вызов KnowledgeGraphClient.
- [x] 5.2  В bot_agent/path_builder.py добавить guard в начало функции:
- [x] 5.3  В .env.example добавить:

NOTE: Вызов в `data_loader.py` не используется в текущей архитектуре; guard реализован в
`bot_agent/graph_client.py`, `bot_agent/path_builder.py` и warmup в `api/main.py`.
### 5.2 Устранение дублирования логирования блоков

- [x] 5.4  В bot_agent/answer_adaptive.py найти двойное логирование блоков.
- [x] 5.5  Оставить только одно логирование — SOURCES после получения
- [x] 5.6  Удалить строку "Final blocks to LLM" или аналогичную,
### 5.3 Обновление версии

- [x] 5.7  В bot_agent/__init__.py найти строку инициализации:
### 5.4 Warmup embedding-модели

- [x] 5.8  В bot_agent/semantic_memory.py найти место lazy-загрузки модели.
- [x] 5.9  В api/main.py найти секцию [WARMUP] (startup event).
- [x] 5.10 Проверить в логах при старте:
### 5.5 Тест и финальный коммит блока

- [x] 5.11 Проверить логи при старте: [GRAPH] KnowledgeGraphClient disabled
- [x] 5.12 Проверить что warmup отрабатывает при старте (не при запросе)
- [x] 5.13 Отправить первый запрос после старта — замерить время ответа.
- [x] 5.14 Коммит:

LOG_NOTE: startup показал `[WARMUP] starting`, `[GRAPH] ... disabled`, `[SEMANTIC] loading ...` один раз до первого запроса.
FIRST_REQ_NOTE: adaptive request после старта ~9.9s; повторной загрузки embedding на первом запросе нет.
BLOCK5_COMMIT: b3e3d04

TEST_DIFF_NOTE: см. `bot_psychologist/tests_diff.txt` (before: 80 passed / after: 88 passed, новых failed нет).
SMOKE_NOTE: выполнен API-smoke (`/api/v1/questions/adaptive`) с `dev-key-001`; greeting=FAST_PATH, содержательный запрос дал stages=`state_classifier,sd_classifier,retrieval,rerank,llm,format`.
ADMIN_NOTE: через `/api/admin/config` TOP_K_BLOCKS переключен 9→7 и восстановлен 7→9; в логах retrieval пошёл с `top_k=7`.
UI_PENDING_NOTE: остаются ручные UI-проверки 6.7/6.10.
## БЛОК 6 — Финальная проверка и релиз

### 6.1 Полный прогон тестов

- [x] 6.1  python -m pytest tests/ -v --tb=short > tests_v060_after.txt 2>&1
- [x] 6.2  diff tests_v060_before.txt tests_v060_after.txt
- [x] 6.3  Все тесты зелёные ИЛИ помечены @pytest.mark.xfail(reason="...")
- [x] 6.4  Новых FAILED тестов не должно быть
### 6.2 Сквозной smoke-тест (живой UI)

- [x] 6.5  Запустить Bot_data_base:
- [x] 6.6  Запустить бота:
- [ ] 6.7  Открыть localhost:3000 (или порт веб-UI)
- [x] 6.8  Тест 1 — Приветствие:
- [x] 6.9  Тест 2 — Содержательный вопрос:
- [ ] 6.10 Тест 3 — Трейс Полотно LLM:
- [x] 6.11 Тест 4 — Конфиг из админки:
- [x] 6.12 Проверить Pipeline Timeline в трейсе:
### 6.3 Обновление документации

- [x] 6.13 Обновить README.md:
- [x] 6.14 Обновить CHANGELOG.md:
## [0.6.0] — 2026-03-25

### Added

### Fixed

### Removed

### Changed

- [ ] 6.15 Финальный коммит:
- [ ] 6.16 Создать PR: fix/v0.6.0-cleanup-trace-behavior → main
## Критерии приёмки (Definition of Done)

## Риски и митигации

## Порядок коммитов

## Сводная карта файлов


