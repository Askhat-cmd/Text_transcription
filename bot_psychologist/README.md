# Bot Psychologist

**Bot Psychologist** — AI-бот для честного самоисследования и поддерживающего диалога.
Основная база знаний: `Bot_data_base` (через HTTP API) с контролируемыми fallback-путями.

## Neo MindBot v10.1 (актуальная архитектура)

- Архив PRD: `../АРХИВ_отработано/PRD_10.1_Neo_MindBot.md`.
- Архив tasklist: `../АРХИВ_отработано/TASKLIST_10.1_Neo_MindBot.md`.
- Архив прогресса: `../АРХИВ_отработано/TASKLIST_10.1_Neo_MindBot_PROGRESS.md`.
- Runtime architecture note: `docs/neo_runtime_v101.md`.
- Release checklist: `docs/release_checklist_v101.md`.
- E2E smoke pack: `tests/e2e/`.

## Neo MindBot v10.2 (Legacy Runtime Purge)

Итерация `PRD_10.2_Legacy_Runtime_Purge` завершила зачистку legacy-влияния в live runtime.

Что зафиксировано:
- В live `metadata` больше нет `user_level` и `user_level_adapter_applied`.
- SD-runtime поля не попадают в healthy trace/metadata при `DISABLE_SD_RUNTIME=true`.
- Streaming и non-stream используют один runtime truth и одинаковые контракты trace.
- Path-builder не запускается автоматически в дефолтном adaptive-flow.
- Degraded fallback сохранен (покрыт отдельным E2E тестом).

Ключевые post-purge тесты:
- `tests/contract/test_live_metadata_contract_after_purge.py`
- `tests/contract/test_trace_contract_after_purge.py`
- `tests/regression/test_no_user_level_runtime_metadata.py`
- `tests/regression/test_no_sd_runtime_metadata_fields.py`
- `tests/regression/test_trace_reflects_real_execution_only.py`
- `tests/e2e/test_degraded_retrieval_case.py`

## Neo MindBot v10.3 (Response Richness Recalibration)

Итерация `PRD_10.3_Response_Richness_Recalibration` фокусируется на поведенческой калибровке ответов:
- убрана жёсткая связка `curious -> informational override`;
- informational route стал уже для действительно concept-first запросов;
- mixed/personal запросы больше не скатываются в сухой glossary-style по умолчанию;
- prompt policy для `inform`, `mixed_query` и `first_turn` стала богаче (смысл, различия, примеры, практический ракурс);
- в `output_validator` добавлена anti-sparse проверка (`underfilled_inform_answer`) и richer regeneration hint.

Новые тестовые слои v10.3:
- inventory baseline: `tests/inventory/test_sparse_output_fixture_inventory.py`, `tests/inventory/test_informational_routing_baseline_map.py`, `tests/inventory/test_prompt_richness_bottlenecks_map.py`;
- routing recalibration: `tests/unit/test_curious_not_auto_informational.py`, `tests/unit/test_informational_mode_narrowing.py`, `tests/integration/test_routing_recalibration_for_exploratory_queries.py`;
- prompt richness + anti-sparse: `tests/unit/test_prompt_style_policy_inform_rich.py`, `tests/unit/test_output_validator_anti_sparse_rules.py`, `tests/integration/test_sparse_output_triggers_regeneration_hint.py`;
- runtime richness E2E: `tests/e2e/test_informational_richness_runtime.py`, `tests/e2e/test_mixed_query_richness_runtime.py`, `tests/e2e/test_first_turn_richness_runtime.py`, `tests/e2e/test_practice_start_richness_runtime.py`, `tests/e2e/test_richness_does_not_break_safety_runtime.py`.

## Быстрая проверка Neo runtime

Чтобы бот работал по Neo MindBot v10.1, в `bot_psychologist/.env` должны быть включены флаги:
- `NEO_MINDBOT_ENABLED=true`
- `LEGACY_PIPELINE_ENABLED=false`
- `DISABLE_SD_RUNTIME=true`
- `DISABLE_USER_LEVEL_ADAPTER=true`
- `USE_NEW_DIAGNOSTICS_V1=true`
- `USE_DETERMINISTIC_ROUTE_RESOLVER=true`
- `USE_PROMPT_STACK_V2=true`
- `USE_OUTPUT_VALIDATION=true`
- `INFORMATIONAL_BRANCH_ENABLED=true`

Признаки Neo в debug trace (UI dev-key / `debug=true`):
- `resolved_route` присутствует
- `route_resolution_count=1`
- `prompt_stack_v2_enabled=true`
- `output_validation_enabled=true`

## Описание

В текущем runtime (Neo MindBot v10.1) бот:
- Делает лёгкую диагностику (Diagnostics v1) и выбирает один детерминированный маршрут на ход (RouteResolver).
- Достаёт контекст из `Bot_data_base` без SD/level-гейтинга; при сбоях работает в degraded mode.
- Собирает единый системный промпт через Prompt Stack v2 и применяет Output Validation (валидация отделена от генерации).
- Подбирает практику детерминированно (Practice Engine v1) только для релевантных маршрутов.
- Поддерживает Memory v1.1: short-term + semantic + summary с fallback chain и schema validation.
- Пишет расширенный debug trace (включая schema validation) и поддерживает rollback при ошибочных admin overrides.

## Legacy: SD Integration (не используется в Neo runtime)

Секция ниже описывает legacy-слой SD, который был добавлен ранее.
В Neo MindBot v10.1 этот слой не должен участвовать в live runtime (см. feature flags в `bot_psychologist/.env.example`).

Что реализовано:
- SD-классификатор пользователя: `bot_agent/sd_classifier.py`
- SD-конфиг: `config/sd_classification.yaml`
- SD-оверлей промты:
  - `bot_agent/prompt_sd_purple.md`
  - `bot_agent/prompt_sd_red.md`
  - `bot_agent/prompt_sd_blue.md`
  - `bot_agent/prompt_sd_orange.md`
  - `bot_agent/prompt_sd_green.md`
  - `bot_agent/prompt_sd_yellow.md`
- Интеграция в adaptive orchestrator:
  - SD-классификация пользователя
  - проброс `sd_level` в `ResponseGenerator.generate(...)`
  - SD-поля в `metadata` ответа
  - SD-уровень виден в debug trace
- Расширение памяти:
  - `ConversationMemory.get_user_sd_profile()`
  - `ConversationMemory.update_sd_profile(...)`

Безопасность:
- При любой SD-ошибке используется fallback `GREEN`, ответ продолжает генерироваться.
- `prompt_system_base.md` не изменяется; SD-адаптация накладывается через отдельные SD-файлы.

Тесты SD:
- `tests/test_sd_classifier.py`
- `tests/test_sd_integration.py`

## Speed Layer (PRD v3.0.2)

Оптимизация скорости ответов без снижения качества:

- **Warm preload**: DataLoader, SemanticMemory, Retriever загружаются параллельно при старте API;
  GraphClient прогревается только при `ENABLE_KNOWLEDGE_GRAPH=true`.
  Используется FastAPI DI через `Depends()`; при сбое остаётся lazy-init fallback.
- **Параллельные классификаторы**: StateClassifier и SDClassifier запускаются через `asyncio.gather`.
  При ошибке одного — второй продолжает работу, сохранены fallback-значения.
- **Streaming**: `POST /api/v1/questions/adaptive-stream` (SSE) отдаёт токены сразу, уменьшает perceived latency.
- **TF-IDF cache**: матрица сохраняется через `joblib` с hash-валидацией.
- **Latency header**: `X-Response-Time-Ms` в каждом ответе API.

## Web UI (PRD 09.02.2026)

Ключевые изменения по PRD редизайна Web UI (стиль ChatGPT) и миграции на серверные сессии.

- Серверные chat sessions: `session_id` поддерживается в adaptive-flow; добавлены эндпоинты `GET/POST/DELETE /users/{user_id}/sessions`.
- Sidebar с историей чатов: создание, переключение, удаление; группировка по датам (Сегодня/Вчера/Последние 7 дней/Старые).
- Settings modal (внутри ChatPage): секции "Информация о системе", "Данные доступа", "Настройки интерфейса", "Настройки бота", "Тема", "Управление данными".
- Настройки UI/бота: `showSources`, `showPath`, `autoScroll`, `compactMode`, `includeFeedbackPrompt`; хранение в localStorage; применение без перезагрузки.
- Управление данными: экспорт истории/сессий в JSON, удаление всех чатов с двойным подтверждением.
- Навигация: открытие настроек через `/chat?open_settings=1`, закрытие по `Escape` и клику вне модалки.

Связанные файлы:
- Backend: `bot_agent/storage/session_manager.py`, `api/models.py`, `api/routes.py`
- Frontend: `web_ui/src/pages/ChatPage.tsx`, `web_ui/src/hooks/useChat.ts`, `web_ui/src/services/api.service.ts`

## Inline Debug Trace (PRD v4.2, dev-key-001)

Для разработки добавлена встроенная трассировка прямо под каждым сообщением бота (collapsible панель).

Как включить:
- В Web UI укажите `X-API-Key = dev-key-001` (в настройках).
- Для dev-key debug включается автоматически на бэкенде (не нужно вручную ставить `debug=true`).
- Панель появляется под каждым ответом, когда бэкенд вернул `trace` (работает и для non-stream, и для SSE-stream).

Что показывает панель:
- Роутинг: `recommended_mode`, `decision_rule_id`, `confidence_level/confidence_score`, состояние пользователя.
- Retrieval: список выбранных и отсеянных блоков (с `block_id`, `score`, `source`, `stage`, полным текстом чанка).
- Память: `memory_turns`, `semantic_hits`, `summary_used`, `summary_length`, `summary_last_turn`.
- SD: `sd_level` (и SD prompt overlay, если он был применён).

Дополнительно (PRD v2.0.3):
- ⚡ LLM вызовы: шаг, модель, токены, длительность, preview промпта и ответа.
- 🤖 Модели пайплайна: primary/classifier/embedding/reranker и статус Voyage.
- 🪙 Токены и стоимость: prompt/completion/total за сообщение + накопительный итог по сессии.
  Стоимость приблизительная и показывается только если модель есть в таблице цен.

## Developer Command Center (PRD v2.0.6)

В dev-режиме (API key: `dev-key-001`) доступен расширенный набор debug-инструментов для сессии:

- Backend хранит **in-memory** отладочные трейсы и большие куски текста (blobs) с TTL (сбрасывается при перезапуске API).
- В ответах `/api/v1/questions/adaptive` и `/api/v1/questions/adaptive-stream` возвращается структурированный `trace`.
- Для больших данных используются blob id, которые можно подгружать отдельным запросом (PII в blob-ответе санитизируется).

Debug endpoints:
- `GET /api/debug/blob/{blob_id}`
- `GET /api/debug/session/{session_id}/metrics`
- `GET /api/debug/session/{session_id}/traces`
- `GET /api/debug/session/{session_id}/llm-payload`

## LLM Payload + Curious Mode (PRD v5.2)

Что добавлено:
- `llm_calls` стабильно заполняется в обоих путях ответа: adaptive и graph-powered.
- Для каждого вызова LLM пишутся:
  - `system_prompt_blob_id`, `user_prompt_blob_id`
  - `system_prompt_preview`, `user_prompt_preview`
  - `blob_error` (если blob сохранить не удалось).
- Эндпоинт `GET /api/debug/session/{session_id}/llm-payload` теперь отдает полезные данные даже при проблемах с blob-хранилищем (через preview + `blob_error`).

Curious-mode override:
- Добавлен отдельный промт `bot_agent/prompt_mode_informational.md`.
- Для `user_state=curious` применяется mode-переопределение (информационный ответ), которое перекрывает SD-слой.
- В debug trace пишутся поля:
  - `informational_mode`
  - `applied_mode_prompt`
  - `user_state`

## Production Logging (PRD 10.02.2026)

Минимальный PRD по production logging реализован.

Что добавлено:
- Централизованная конфигурация: `logging_config.py` (`setup_logging`, `get_logger`).
- Раздельные лог-файлы:
  - `logs/app/bot.log` — общий поток INFO+.
  - `logs/retrieval/retrieval.log` — диагностические retrieval-события (`[RETRIEVAL]`).
  - `logs/error/error.log` — ошибки ERROR+.
- Ротация через `TimedRotatingFileHandler`:
  - `app`/`retrieval`: ежедневно, хранение 30 дней.
  - `error`: ежедневно, хранение 90 дней.
- Интеграция в ключевые модули:
  - `api/main.py`
  - `bot_agent/retriever.py`
  - `bot_agent/answer_adaptive.py`
  - `bot_agent/conversation_memory.py`
  - `bot_agent/semantic_memory.py`
- Добавлена структура директорий логов с `.gitkeep`:
  - `logs/`, `logs/app/`, `logs/retrieval/`, `logs/error/`
- Для Windows-консоли добавлен безопасный handler (`SafeStreamHandler`): при проблемах кодировки (эмодзи и т.п.) строка логов не ломает процесс, а выводится с экранированием.

Быстрая проверка:
```bash
cd bot_psychologist
python -m uvicorn api.main:app --reload --port 8001
```

После запуска проверяйте:
```bash
tail -f logs/app/bot.log
tail -f logs/retrieval/retrieval.log
tail -f logs/error/error.log
```

Для защищенных endpoints нужен заголовок `X-API-Key` (например: `dev-key-001`).

## Admin Config Panel (PRD v2.2)

Веб-интерфейс для горячего управления параметрами бота без рестарта сервера.

### Возможности

- **28 редактируемых параметров** в реальном времени:
  - 🤖 **LLM:** модель, температура, токены, reasoning effort, streaming
  - 🔍 **Retrieval:** TOP-K, Voyage rerank, порог релевантности
  - 🧠 **Memory:** глубина истории, semantic search, summary
  - 🗄️ **Storage:** ретеншн сессий, авто-очистка
  - ⚙️ **Runtime:** warmup, кэширование

- **11 промтов для редактирования:**
  - Системный базовый промт
  - SD-адаптации (6 уровней: Purple/Red/Blue/Orange/Green/Yellow)
  - Уровни пользователя (Beginner/Intermediate/Advanced)
  - Режимный промт для `curious`: `prompt_mode_informational`

- **История изменений:** последние 50 записей с экспортом/импортом JSON

- **Цветовая схема по группам:**
  - LLM — фиолетовая
  - Поиск — синяя
  - Память — зелёная
  - Хранилище — янтарная
  - Runtime — серая
  - Промты — розовая
  - История — индиго

### Доступ

- **URL:** `http://localhost:3000/admin`
- **API ключ:** `dev-key-001` (вводится в UI)

### Backend реализация

- `bot_agent/runtime_config.py` — `RuntimeConfig` с override-слоем
- `bot_agent/config.py` — `config = RuntimeConfig()`
- `api/admin_routes.py` — 11 API endpoints (`/api/admin/*`)
- `api/main.py` — регистрация `admin_router`

### Frontend реализация

- `web_ui/src/constants/adminColors.ts` — цветовые константы
- `web_ui/src/components/admin/AdminPanel.tsx` — главный компонент
- `web_ui/src/components/admin/ConfigGroupPanel.tsx` — карточки параметров
- `web_ui/src/components/admin/PromptEditorPanel.tsx` — редактор промтов
- `web_ui/src/components/admin/HistoryPanel.tsx` — история изменений

### Тесты

```bash
cd bot_psychologist
python -m pytest tests/test_runtime_config_reset.py -v
# test_is_reasoning_model — проверка блокировки температуры для gpt-5*, o1, o3, o4
```

### Важные исправления

**Bug Fix B2:** `reset_prompt_override` теперь удаляет ключ из JSON, а не записывает `null`

**Bug Fix B1:** Температура реагирует на смену модели мгновенно (из черновика UI), без необходимости сохранять

---

## Промпт (System Prompt) и уровни сложности

Системный промпт вынесен в отдельные файлы, чтобы его было проще редактировать без правок кода:

- Базовый системный промпт: `bot_agent/prompt_system_base.md`

Добавки по сложности:
- `bot_agent/prompt_system_level_beginner.md`
- `bot_agent/prompt_system_level_intermediate.md`
- `bot_agent/prompt_system_level_advanced.md`

Интеграция в коде:

- `bot_agent/llm_answerer.py`: `LLMAnswerer.build_system_prompt()` читает `prompt_system_base.md`
- `bot_agent/user_level_adapter.py`: `UserLevelAdapter.adapt_system_prompt()` добавляет к базовому промпту текст из `prompt_system_level_{beginner|intermediate|advanced}.md`
- `api/models.py`: `AskQuestionRequest.user_level` задает уровень пользователя для каждого запроса
- `api/routes.py`: `request.user_level` передается в `answer_question_adaptive(...)`
- `web_ui/src/pages/ChatPage.tsx`: уровень выбирается в Настройки -> Настройки бота -> Уровень пользователя
- `web_ui/src/services/api.service.ts`: `user_level` пробрасывается в `/questions/adaptive-stream`
- `web_ui/src/components/debug/ConfigSnapshot.tsx`: активный уровень отображается как `USER_LEVEL` в трейсе

Важно: бот должен опираться на материалы, переданные в контексте (блоки/фрагменты). Если в материалах нет ответа, он должен честно сказать об этом и попросить уточнение.

## Память Диалога (Conversation Memory)

Бот поддерживает персистентную память диалога по `user_id`:

Новые уровни памяти:
- Semantic memory — поиск релевантных прошлых обменов по смыслу, а не по хронологии.
- Conversation summary — краткое резюме диалога, обновляемое каждые N ходов.
- Cross-session context — краткий контекст из предыдущих сессий пользователя (SQLite `session_summaries`).
- Adaptive context — динамическая загрузка контекста в зависимости от длины диалога.

- История хранится на диске в `bot_psychologist/.cache_bot_agent/conversations/{user_id}.json` (папка в git игнорируется).
- Контекст последних сообщений автоматически добавляется в промпт перед материалами из базы знаний.
- Память используется во всех режимах ответов: Phase 1-4 (basic, sag-aware, graph-powered, adaptive).

Оптимизация контекста (чтобы не раздувать токены):

- Адаптивная стратегия: 1-5 ходов — только short-term, 6-20 — short-term + semantic, 21+ — short-term + semantic + summary.
- В LLM передаются только последние N обменов.
- Контекст обрезается по лимиту символов.
- История автоматически ротируется, если превысила максимальное число сохранённых ходов.

Настройки через `.env` (см. `bot_psychologist/.env.example`):

- `PRIMARY_MODEL` (default: `gpt-4o-mini`) — основная модель для генерации ответа.
- `CLASSIFIER_MODEL` (default: `gpt-4o-mini`) — быстрая модель для классификаторов (state + SD), чтобы не тормозить основной ответ.
- `REASONING_EFFORT` (default: `low`) — только для reasoning-моделей (семейство `gpt-5`, `o1/o3/o4`): `low` / `medium` / `high`.
- `CONVERSATION_HISTORY_DEPTH` (default: `3`) — сколько последних обменов добавлять в контекст.
- `MAX_CONTEXT_SIZE` (default: `2000`) — максимальный размер контекста в символах.
- `MAX_CONVERSATION_TURNS` (default: `1000`) — максимальное число ходов, хранимых для одного пользователя (старые удаляются).
- `ENABLE_SEMANTIC_MEMORY` (default: `true`) — включить semantic memory.
- `SEMANTIC_SEARCH_TOP_K` (default: `3`) — количество релевантных прошлых обменов.
- `SEMANTIC_MIN_SIMILARITY` (default: `0.7`) — порог косинусного сходства.
- `SEMANTIC_MAX_CHARS` (default: `1000`) — лимит символов для semantic контекста.
- `EMBEDDING_MODEL` (default: `paraphrase-multilingual-MiniLM-L12-v2`) — модель эмбеддингов.
- `ENABLE_CONVERSATION_SUMMARY` (default: `true`) — включить summary диалога.
- `SUMMARY_UPDATE_INTERVAL` (default: `5`) — обновление summary каждые N ходов.
- `SUMMARY_MAX_CHARS` (default: `500`) — лимит длины summary.
- `WARMUP_ON_START` (default: `true`) — прогрев компонентов на старте API.
- `ENABLE_STREAMING` (default: `true`) — включить SSE endpoint `/api/v1/questions/adaptive-stream`.
- `ENABLE_FAST_STATE_DETECTOR` (default: `true`) — быстрый L0 слой для StateClassifier.
- `ENABLE_FAST_SD_DETECTOR` (default: `true`) — быстрый L0 слой для SDClassifier.
- `ENABLE_CONDITIONAL_RERANKER` (default: `true`) — условный запуск reranker вместо always-on.
- `ENABLE_EMBEDDING_PROVIDER` (default: `true`) — семантический fallback через EmbeddingProvider.

Ключевые файлы:

- `bot_agent/conversation_memory.py` — хранение, загрузка/сохранение, сбор контекста, очистка.
- `bot_agent/semantic_memory.py` — semantic memory, эмбеддинги, поиск, кэширование.
- `bot_agent/llm_answerer.py` — принимает `conversation_history` и добавляет в `build_context_prompt(...)`.
- `bot_agent/answer_basic.py`, `bot_agent/answer_sag_aware.py`, `bot_agent/answer_graph_powered.py`, `bot_agent/answer_adaptive.py` — подключают память, добавляют историю в LLM и сохраняют ход после ответа.
- `api/routes.py` — пробрасывает `user_id` во все режимы и даёт endpoints управления историей.

API для истории:

- `GET /api/v1/users/{user_id}/history?last_n_turns=10`
- `GET /api/v1/users/{user_id}/summary`
- `DELETE /api/v1/users/{user_id}/history`
- `POST /api/v1/questions/basic-with-semantic`
- `GET /api/v1/users/{user_id}/semantic-stats`
- `POST /api/v1/users/{user_id}/rebuild-semantic-memory`
- `POST /api/v1/users/{user_id}/update-summary`

Режимные поля в ответах API (новое):

- `recommended_mode` — выбранный режим ответа (`PRESENCE`, `CLARIFICATION`, `VALIDATION`, `THINKING`, `INTERVENTION`, `INTEGRATION`).
- `decision_rule_id` — сработавшее правило decision table.
- `confidence_level` и `confidence_score` — уровень/число уверенности роутинга.
- `sd_level` — определённый SD-уровень пользователя (fallback: `GREEN`).
- Память (в `metadata`): `memory_turns`, `semantic_hits`, `summary_used`, `summary_length`, `summary_last_turn`.
- Дополнительно в `metadata`: `contradiction_detected`, `cross_session_context_used`.
- Поле `metadata` сохранено для обратной совместимости и содержит расширенные детали retrieval/decision.

## Response Layer (PRD v2.0)

Единый слой генерации/форматирования ответов используется во всех `answer_*`:

- `bot_agent/response/response_generator.py` — mode-aware генерация (директива режима + confidence behavior).
- `bot_agent/response/response_formatter.py` — mode-aware ограничения длины/формата ответа (char_limit).

Token budget (PRD v2.0.2):
- Лимит токенов для LLM согласован с `ResponseFormatter` по режимам и задаётся в `bot_agent/config.py` через `MODE_MAX_TOKENS` + `get_mode_max_tokens(mode)`.
- Это снижает риск обрыва ответа на уровне API (когда генерация обрывается без `...`), а финальная обрезка (если нужна) происходит уже в formatter с `...`.

## Retrieval Policy (PRD v2.0)

При retrieval используется дополнительная политика:

- Confidence cap: при низкой уверенности уменьшает число блоков, чтобы не «синтезировать лишнее».

## Архитектура ретривала

Упрощённый пайплайн ретривала (без Stage/SD фильтров):

1. Построение hybrid‑query (контекст + вопрос).
2. Retrieval:
    - `KNOWLEDGE_SOURCE=api|chromadb` → Bot_data_base API
    - fallback → TF‑IDF
3. Progressive RAG:
   - взвешивание блоков по `block_weights` (SQLite), применяется до rerank.
4. Rerank:
   - Voyage (top‑k = `VOYAGE_TOP_K`) в условном режиме (confidence/mode/block-count).
   - fallback: сортировка по score без урезания списка
5. Confidence cap:
   - итоговый лимит = `TOP_K_BLOCKS` (из runtime/admin config)
6. LLM получает финальные блоки + диагностический контекст (Diagnostics v1) + сигналы противоречий/кросс-сессий.

## Архитектурный обзор

Проект состоит из 6 фаз разработки:

| Фаза | Название | Описание |
|------|----------|----------|
| **Phase 1** | Базовый QA | TF-IDF поиск + LLM ответы с таймкодами |
| **Phase 2** | SAG-aware QA | Адаптация по уровню пользователя, семантический анализ |
| **Phase 3** | Knowledge Graph Powered | Рекомендация практик через граф знаний (95 узлов, 2182 связи) |
| **Phase 4** | Adaptive QA | Классификация состояний, память диалога, персональные пути |
| **Phase 5** | REST API | FastAPI сервер с endpoints для всех Phase 1-4 |
| **Phase 6** | Web UI | React SPA интерфейс для взаимодействия с ботом |

## Быстрый старт

### 1. Установка зависимостей

```bash
cd bot_psychologist

# Рекомендуется отдельная venv внутри подпроекта
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1

# Python зависимости
pip install -r requirements_bot.txt
pip install -r api/requirements.txt

# Node.js зависимости (для Web UI, опционально)
cd web_ui
npm install
cd ..
```

### 2. Настройка переменных окружения

Создайте `.env` файл:

```bash
cp .env.example .env
```

Заполните обязательные переменные (Neo runtime по умолчанию):

```env
OPENAI_API_KEY=sk-proj-...

# Основной источник базы знаний (рекомендуется)
KNOWLEDGE_SOURCE=api
BOT_DB_URL=http://localhost:8003

# Models
# PRIMARY_MODEL — основная модель ответа. Для GPT-5 (reasoning) используется Responses API
# и параметр max_output_tokens; system-prompt объединяется с user (system role не используется).
PRIMARY_MODEL=gpt-5-mini
# CLASSIFIER_MODEL — быстрая модель для state + SD классификаторов (рекомендуется gpt-4o-mini).
CLASSIFIER_MODEL=gpt-4o-mini
# Только для reasoning моделей (gpt-5, o1/o3/o4): ускорение за счет effort=low/medium/high.
REASONING_EFFORT=low

# Conversation Memory
CONVERSATION_HISTORY_DEPTH=3
MAX_CONTEXT_SIZE=2000
MAX_CONVERSATION_TURNS=1000

# Semantic Memory
ENABLE_SEMANTIC_MEMORY=true
SEMANTIC_SEARCH_TOP_K=3
SEMANTIC_MIN_SIMILARITY=0.7
SEMANTIC_MAX_CHARS=1000
EMBEDDING_MODEL=intfloat/multilingual-e5-base

# Voyage Rerank (optional)
# Чтобы включить rerank: установите `VOYAGE_ENABLED=true` и задайте `VOYAGE_API_KEY`
VOYAGE_API_KEY=pa-...
VOYAGE_MODEL=rerank-2
VOYAGE_TOP_K=5
VOYAGE_ENABLED=false

# Conversation Summary
ENABLE_CONVERSATION_SUMMARY=true
SUMMARY_UPDATE_INTERVAL=5
SUMMARY_MAX_CHARS=500

# Session Storage (SQLite)
ENABLE_SESSION_STORAGE=true
BOT_DB_PATH=data/bot_sessions.db
SESSION_RETENTION_DAYS=90
ARCHIVE_RETENTION_DAYS=365
AUTO_CLEANUP_ENABLED=true

# Speed Layer
WARMUP_ON_START=true
ENABLE_KNOWLEDGE_GRAPH=false
ENABLE_STREAMING=true

# Neo MindBot v10.1 feature flags (должны быть включены)
NEO_MINDBOT_ENABLED=true
LEGACY_PIPELINE_ENABLED=false
DISABLE_SD_RUNTIME=true
DISABLE_USER_LEVEL_ADAPTER=true
USE_NEW_DIAGNOSTICS_V1=true
USE_DETERMINISTIC_ROUTE_RESOLVER=true
USE_PROMPT_STACK_V2=true
USE_OUTPUT_VALIDATION=true
INFORMATIONAL_BRANCH_ENABLED=true
```

### 3. Проверка базы знаний

В режиме `KNOWLEDGE_SOURCE=api` бот читает знания из `Bot_data_base` по HTTP.
Убедитесь, что сервис `Bot_data_base` запущен на `BOT_DB_URL` и отвечает:

```bash
curl http://127.0.0.1:8003/api/registry/
```

### 4. Тестирование

```bash
# Unit/Integration (рекомендуется)
pytest -q

# Минимальная проверка интеграции с Bot_data_base API
pytest -q tests/test_db_api_client.py

# E2E smoke pack (опционально)
pytest -q tests/e2e
```

Очистка старых сессий (ретеншн):

```bash
python scripts/cleanup_old_sessions.py --active-days 90 --archive-days 365
```

### 5. Запуск API сервера

```bash
cd bot_psychologist
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8001
```

API будет доступен по адресу `http://localhost:8001/api/docs`

### 6. Запуск Web UI (опционально)

```bash
cd web_ui
npm run dev
```

Web UI будет доступен по адресу `http://localhost:3000`

## Legacy режим (совместимость)

Если `Bot_data_base` недоступен, можно использовать legacy-источники:

- `KNOWLEDGE_SOURCE=db_json` — заранее экспортированный JSON из `Bot_data_base` (без сервера).
- `KNOWLEDGE_SOURCE=json` — SAG v2.0 JSON из `voice_bot_pipeline` (исторический режим).

Для legacy-режимов могут понадобиться дополнительные переменные (например `DATA_ROOT`) — см. `bot_psychologist/.env.example`.

## Структура проекта

```
bot_psychologist/
├── bot_agent/              # Основной код бота (Phase 1-4)
│   ├── config.py           # Конфигурация
│   ├── data_loader.py      # Загрузка данных из voice_bot_pipeline
│   ├── retriever.py        # TF-IDF поиск
│   ├── llm_answerer.py     # Генерация ответов через OpenAI
│   ├── answer_basic.py     # Phase 1: Базовый QA
│   ├── answer_sag_aware.py # Phase 2: SAG-aware QA
│   ├── answer_graph_powered.py # Phase 3: Graph-powered QA
│   ├── answer_adaptive.py  # Phase 4: Adaptive QA
│   ├── user_level_adapter.py # Адаптация по уровню
│   ├── semantic_analyzer.py # Семантический анализ
│   ├── graph_client.py     # Работа с Knowledge Graph
│   ├── practices_recommender.py # Рекомендация практик
│   ├── state_classifier.py # Классификация состояний
│   ├── conversation_memory.py # Память диалога
│   ├── semantic_memory.py     # Semantic memory (эмбеддинги + поиск)
│   └── path_builder.py     # Построение путей трансформации
│
├── api/                    # FastAPI сервер (Phase 5)
│   ├── main.py             # Приложение FastAPI
│   ├── routes.py            # API endpoints
│   ├── models.py            # Pydantic модели
│   ├── auth.py              # Аутентификация
│   └── requirements.txt     # Зависимости API
│
├── web_ui/                 # React приложение (Phase 6)
│   ├── src/
│   │   ├── components/     # React компоненты
│   │   ├── pages/          # Страницы приложения
│   │   ├── hooks/          # React hooks
│   │   ├── services/       # API сервисы
│   │   └── types/          # TypeScript типы
│   └── package.json        # npm зависимости
│
├── docs/                   # Документация проекта
│   ├── overview.md         # Общее описание
│   ├── architecture.md     # Архитектура Phase 1-6
│   ├── data_flow.md        # Поток данных от voice_bot_pipeline
│   ├── sag_v2.md           # SAG v2.0 + семантика
│   ├── knowledge_graph.md  # Knowledge Graph
│   ├── bot_agent.md        # Bot Agent, состояния, логика
│   ├── api.md              # REST API
│   ├── web_ui.md           # Web UI
│   ├── configuration.md    # Конфигурация
│   ├── testing.md          # Тестирование
│   ├── deployment.md       # Развёртывание
│   └── roadmap.md          # Дорожная карта
│
├── .cache_bot_agent/       # Кэш и данные бота
│   └── conversations/      # История диалогов пользователей
│   └── semantic_memory/    # Эмбеддинги semantic memory
│
├── tests/                 # Все тесты проекта
│   ├── test_phase1.py     # Тесты Phase 1
│   ├── test_phase2.py     # Тесты Phase 2
│   ├── test_phase3.py     # Тесты Phase 3
│   ├── test_phase4.py     # Тесты Phase 4
│   ├── test_semantic_memory.py # Тесты Semantic Memory
│   └── test_api.py        # Тесты API
│
├── requirements_bot.txt    # Python зависимости
├── .env.example            # Пример переменных окружения
└── README.md               # Этот файл
```

## Связь с voice_bot_pipeline и Bot_data_base

`bot_psychologist` поддерживает несколько источников базы знаний (через `KNOWLEDGE_SOURCE`):

### 🆕 **Режим API (рекомендуемый)**
- **Источник данных**: `Bot_data_base` через HTTP API
- **Конфигурация**: `KNOWLEDGE_SOURCE=api` в `.env`
- **Преимущества**: 
  - Универсальная база знаний с множеством авторов
  - SD-метаданные могут присутствовать в блоках, но в Neo runtime не используются для гейтинга
  - Масштабируемость и независимость от `voice_bot_pipeline`
- **Требования**: Запущенный `Bot_data_base` на `BOT_DB_URL` (по умолчанию `http://localhost:8003`)

### 🧾 **Режим Offline (без сервера)**
- **Источник данных**: экспортированный JSON из `Bot_data_base`
- **Конфигурация**: `KNOWLEDGE_SOURCE=db_json`
- **Когда нужно**: если вы не хотите/не можете запускать `Bot_data_base` как сервис, но хотите сохранить доступ к базе знаний

### 📁 **Режим Legacy (совместимость)**
- **Источник данных**: `voice_bot_pipeline/data/sag_final/*.for_vector.json`
- **Конфигурация**: `KNOWLEDGE_SOURCE=json` в `.env`
- **Ограничения**: Только данные Сарсекенова Саламата

### ⚙️ **Настройка режима**

```bash
# Для работы с Bot_data_base (универсальная БД)
KNOWLEDGE_SOURCE=api
BOT_DB_URL=http://localhost:8003

# Для работы с Bot_data_base без сервера (offline export)
KNOWLEDGE_SOURCE=db_json

# Для работы с voice_bot_pipeline (legacy SAG JSON)
KNOWLEDGE_SOURCE=json
```

**Важно**: `bot_psychologist` только читает данные, не изменяет их.

Подробнее о потоке данных см. [docs/data_flow.md](docs/data_flow.md)

## Документация

Полная документация проекта находится в папке [`docs/`](docs/):

- [Neo runtime v10.1](docs/neo_runtime_v101.md) — актуальная карта runtime Neo MindBot
- [Release checklist v10.1](docs/release_checklist_v101.md) — чек-лист релиза/проверок
- [Обзор проекта](docs/overview.md) — общее описание проекта
- [Архитектура](docs/architecture.md) — архитектура Phase 1-6
- [Поток данных](docs/data_flow.md) — как знания поступают в бот (Bot_data_base + legacy)
- [SAG v2.0](docs/sag_v2.md) — использование SAG v2.0 данных
- [Legacy runtime map](docs/legacy_runtime_map.md) — карта legacy-слоёв/фичей (исторически)
- [Knowledge Graph](docs/knowledge_graph.md) — legacy: работа с графом знаний (в Neo по умолчанию выключен)
- [Bot Agent](docs/bot_agent.md) — компоненты бота, состояния, логика
- [REST API](docs/api.md) — описание API endpoints
- [Web UI](docs/web_ui.md) — описание Web UI
- [Конфигурация](docs/configuration.md) — настройка проекта
- [Тестирование](docs/testing.md) — тестирование Phase 1-6
- [Развёртывание](docs/deployment.md) — локальный запуск и production
- [Дорожная карта](docs/roadmap.md) — возможное развитие проекта

## Требования

- **Python 3.10+**
- **Node.js 18+** (для Web UI, опционально)
- **LLM API Key** (минимум: `OPENAI_API_KEY` для дефолтного провайдера)
- **Bot_data_base** (рекомендуется): запущенный HTTP API на `BOT_DB_URL` или экспорт `db_json` (offline)
- **sentence-transformers + torch** (для semantic memory / embeddings)

## Проект является частью монорепозитория

Этот проект является частью монорепозитория `Text_transcription`, который содержит:

1. **Bot_data_base** — универсальная база знаний (книги/YouTube) + ChromaDB + UI загрузки
2. **bot_psychologist** — AI-бот (Neo MindBot runtime) с Admin UI и расширенным trace
3. **voice_bot_pipeline** — legacy-пайплайн подготовки данных (исторически)

См. корневой [README.md](../README.md) для общей информации о монорепозитории.

## Лицензия

Private — для внутреннего использования

## Автор

Askhat-cmd

## Retrieval Diagnostics (Adaptive QA)

Начиная с текущей версии, adaptive-pipeline поддерживает расширенную диагностику retrieval:

- Логи по этапам: initial retrieval, rerank, confidence cap, final blocks to LLM, sources.
- Логи retriever: query hash/timestamp, top TF-IDF кандидаты со score и block_id.
- Логи confidence: contribution по сигналам и итоговый cap.
- При debug-режиме в ответе API доступен `trace` (и часть деталей также сохраняется в `metadata.retrieval_details` для обратной совместимости).
- Web UI (dev-key-001) использует `trace` + `/api/debug/blob/{blob_id}` для Inline Debug Trace и Developer Command Center.

Также исправлено схлопывание источников в fallback-сценариях:

- `VoyageReranker` fallback больше не режет кандидатов до `top_k=1`, если Voyage недоступен.

## Session Data Storage

Данные пользовательских сессий и памяти сохраняются в проекте:

- JSON-история диалогов: `.cache_bot_agent/conversations/<user_id>.json`
- Semantic memory (эмбеддинги и метаданные): `.cache_bot_agent/semantic_memory/`
- SQLite-сессии (если включено): `data/bot_sessions.db` (путь задается `BOT_DB_PATH`)

Важно:

- Runtime-логи приложения пишутся через `logging_config.py` в `logs/app`, `logs/retrieval`, `logs/error`.
- Для HTTP API (кроме health-check) требуется заголовок `X-API-Key`; для `/api/v1/questions/adaptive` поле запроса — `query`.


