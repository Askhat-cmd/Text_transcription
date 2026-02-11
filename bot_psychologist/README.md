# Bot Psychologist

**Супер-Умный Бот-Психолог** — AI-ассистент на базе данных `voice_bot_pipeline`.

## Описание

Специализированный AI-бот-психолог, который:
- Работает поверх готовых данных SAG v2.0 JSON + Knowledge Graph из `voice_bot_pipeline`
- Использует все слои структуры: блоки, граф-сущности, семантические связи
- Отвечает на вопросы, опираясь на материалы из `voice_bot_pipeline` (таймкоды в ответе не требуются)
- Адаптирует ответы по уровню пользователя (beginner/intermediate/advanced)
- Классифицирует состояние пользователя (10 состояний)
- Строит персональные пути трансформации через Knowledge Graph
- Поддерживает semantic memory: поиск релевантных прошлых обменов по смыслу
- Генерирует краткое summary диалога и добавляет в контекст
- Адаптивно формирует контекст (short-term + semantic + summary по длине диалога)

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

Быстрая проверка:
```bash
cd bot_psychologist
python -m uvicorn api.main:app --reload --port 8000
```

После запуска проверяйте:
```bash
tail -f logs/app/bot.log
tail -f logs/retrieval/retrieval.log
tail -f logs/error/error.log
```

Для защищенных endpoints нужен заголовок `X-API-Key` (например: `dev-key-001`).

## Runtime Update (11.02.2026)

Ключевые изменения в боевой логике адаптивного ответа:

- `answer_adaptive` добавляет fast-path для приветствий, представления имени и очень коротких реплик в режимах `PRESENCE`/`CLARIFICATION`.
- В fast-path retrieval по лекционным блокам пропускается осознанно; в логах это видно как `[FAST_PATH] enabled ...`.
- `ResponseFormatter` больше не добавляет шаблонную префиксную фразу низкой уверенности в начале каждого ответа; тон uncertainty управляется роутингом и системной инструкцией.
- `ConversationMemory` стабильно синхронизирует `working_state` в JSON и SQLite, поэтому состояние пользователя восстанавливается между сессиями.
- Для Voyage Rerank рабочий признак в логах: `[VOYAGE] rerank enabled ...` и `[RETRIEVAL] reranked top_k=... (voyage_active=True)`.
- Даже при активном Voyage итоговый `Final blocks to LLM` может быть `1` из-за `stage_filter` и `confidence_cap` (это ожидаемое поведение).
- Практическая рекомендация: для более содержательных ответов обычно лучше `VOYAGE_TOP_K=3`; значение `1` часто делает контекст слишком узким.

После изменения `.env` обязательно перезапустите API/бота, чтобы новые параметры вступили в силу.
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

Важно: бот должен опираться на материалы, переданные в контексте (блоки/фрагменты). Если в материалах нет ответа, он должен честно сказать об этом и попросить уточнение.

## Память Диалога (Conversation Memory)

Бот поддерживает персистентную память диалога по `user_id`:

Новые уровни памяти:
- Semantic memory — поиск релевантных прошлых обменов по смыслу, а не по хронологии.
- Conversation summary — краткое резюме диалога, обновляемое каждые N ходов.
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
- Поле `metadata` сохранено для обратной совместимости и содержит расширенные детали retrieval/decision.

## Response Layer (PRD v2.0)

Единый слой генерации/форматирования ответов используется во всех `answer_*`:

- `bot_agent/response/response_generator.py` — mode-aware генерация (директива режима + confidence behavior).
- `bot_agent/response/response_formatter.py` — mode-aware ограничения длины/формата ответа.

## Retrieval Policy (PRD v2.0)

При retrieval используется дополнительная политика:

- Stage filter: ограничивает complexity блоков на ранних стадиях пользователя.
- Confidence cap: при низкой уверенности уменьшает число блоков, чтобы не «синтезировать лишнее».

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

Заполните обязательные переменные:

```env
OPENAI_API_KEY=sk-proj-...
DATA_ROOT=../voice_bot_pipeline/data
PRIMARY_MODEL=gpt-4o-mini

# Conversation Memory
CONVERSATION_HISTORY_DEPTH=3
MAX_CONTEXT_SIZE=2000
MAX_CONVERSATION_TURNS=1000

# Semantic Memory
ENABLE_SEMANTIC_MEMORY=true
SEMANTIC_SEARCH_TOP_K=3
SEMANTIC_MIN_SIMILARITY=0.7
SEMANTIC_MAX_CHARS=1000
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# Voyage Rerank (optional)
VOYAGE_API_KEY=pa-...
VOYAGE_MODEL=rerank-2
VOYAGE_TOP_K=3
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
```

Быстрое переключение модели:

- Для классического режима: `PRIMARY_MODEL=gpt-4o-mini`
- Для GPT-5: `PRIMARY_MODEL=gpt-5-mini`
- После изменения `.env` перезапускайте API/бота.
- Проверка активной модели:
  - `python -c "from bot_agent.config import config; print(config.LLM_MODEL)"`

### 3. Проверка данных

Убедитесь, что данные из `voice_bot_pipeline` доступны:

```bash
ls ../voice_bot_pipeline/data/sag_final/
```

### 4. Тестирование

```bash
# Phase 1: Базовый QA
python test_phase1.py

# Phase 2: SAG-aware QA
python test_phase2.py

# Phase 3: Knowledge Graph Powered QA
python test_phase3.py

# Phase 4: Adaptive QA
python test_phase4.py

# Semantic Memory
python test_semantic_memory.py

# SessionManager (SQLite persistence bootstrap)
python test_session_manager.py
python test_conversation_memory_persistence.py
python test_working_state.py
python test_decision_table.py
python test_decision_gate.py
python test_hybrid_query.py
python test_confidence_scorer.py
python test_stage_filter.py
python test_signal_detector.py
python test_voyage_reranker.py
python test_prompt_templates.py
python test_mode_handlers.py
python test_response_generator.py
python test_response_formatter.py
python test_full_dialogue_pipeline.py

# API тесты
python test_api.py
```

Очистка старых сессий (ретеншн):

```bash
python scripts/cleanup_old_sessions.py --active-days 90 --archive-days 365
```

### 5. Запуск API сервера

```bash
cd api
uvicorn main:app --reload --port 8000
```

API будет доступен по адресу `http://localhost:8000/api/docs`

### 6. Запуск Web UI (опционально)

```bash
cd web_ui
npm run dev
```

Web UI будет доступен по адресу `http://localhost:5173`

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
├── test_phase1.py          # Тесты Phase 1
├── test_phase2.py          # Тесты Phase 2
├── test_phase3.py          # Тесты Phase 3
├── test_phase4.py          # Тесты Phase 4
├── test_semantic_memory.py # Тесты Semantic Memory
├── test_api.py             # Тесты API
│
├── requirements_bot.txt    # Python зависимости
├── .env.example            # Пример переменных окружения
└── README.md               # Этот файл
```

## Связь с voice_bot_pipeline

`bot_psychologist` является потребителем данных, сгенерированных `voice_bot_pipeline`:

- **Данные**: `voice_bot_pipeline/data/sag_final/*.for_vector.json`
- **Векторная БД** (опционально): `voice_bot_pipeline/data/chromadb/`

**Важно**: `bot_psychologist` только читает данные, не изменяет их.

Подробнее о потоке данных см. [docs/data_flow.md](docs/data_flow.md)

## Документация

Полная документация проекта находится в папке [`docs/`](docs/):

- [Обзор проекта](docs/overview.md) — общее описание проекта
- [Архитектура](docs/architecture.md) — архитектура Phase 1-6
- [Поток данных](docs/data_flow.md) — как данные поступают от voice_bot_pipeline
- [SAG v2.0](docs/sag_v2.md) — использование SAG v2.0 данных
- [Knowledge Graph](docs/knowledge_graph.md) — работа с графом знаний
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
- **OpenAI API Key** (обязательно)
- **Данные из voice_bot_pipeline** (SAG v2.0 JSON файлы)
- **sentence-transformers + torch** (для semantic memory)

## Проект является частью монорепозитория

Этот проект является частью монорепозитория `Text_transcription`, который содержит:

1. **voice_bot_pipeline** — пайплайн подготовки данных из YouTube-лекций
2. **bot_psychologist** — AI-бот, использующий эти данные

См. корневой [README.md](../README.md) для общей информации о монорепозитории.

## Лицензия

Private — для внутреннего использования

## Автор

Askhat-cmd

## Retrieval Diagnostics (Adaptive QA)

Начиная с текущей версии, adaptive-pipeline поддерживает расширенную диагностику retrieval:

- Логи по этапам: initial retrieval, stage filter, confidence cap, final blocks to LLM, sources.
- Логи retriever: query hash/timestamp, top TF-IDF кандидаты со score и block_id.
- Логи confidence: contribution по сигналам и итоговый cap.
- Логи stage-filter: вход/выход, fallback-поведение при пустом фильтре.
- При `debug=true` в ответе API доступно `metadata.retrieval_details` с наборами блоков по каждому этапу.

Также исправлено схлопывание источников в fallback-сценариях:

- `VoyageReranker` fallback больше не режет кандидатов до `top_k=1`, если Voyage недоступен.
- `StageFilter` fallback при пустом фильтре возвращает stage-aware `top-N` (с backfill для разнообразия), а не только `top-1`.

## Session Data Storage

Данные пользовательских сессий и памяти сохраняются в проекте:

- JSON-история диалогов: `.cache_bot_agent/conversations/<user_id>.json`
- Semantic memory (эмбеддинги и метаданные): `.cache_bot_agent/semantic_memory/`
- SQLite-сессии (если включено): `data/bot_sessions.db` (путь задается `BOT_DB_PATH`)

Важно:

- Runtime-логи приложения пишутся через `logging_config.py` в `logs/app`, `logs/retrieval`, `logs/error`.
- Для HTTP API (кроме health-check) требуется заголовок `X-API-Key`; для `/api/v1/questions/adaptive` поле запроса — `query`.

