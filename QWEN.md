# QWEN.md — Контекст проекта Text Transcription

## 📋 Обзор проекта

**Text Transcription** — монорепозиторий, содержащий два связанных проекта для работы с транскрипцией YouTube-лекций и созданием AI-бота-психолога на базе учения Саламата Сарсекенова (нейро-сталкинг/нео-сталкинг).

### Проекты

| Проект | Назначение | Ключевые технологии |
|--------|------------|---------------------|
| **voice_bot_pipeline** | Пайплайн подготовки данных из YouTube-лекций | Python, OpenAI API, ChromaDB, yt-dlp, SAG v2.0 |
| **bot_psychologist** | AI-бот-психолог поверх данных pipeline | Python, FastAPI, React, TF-IDF, Knowledge Graph |

### Связь между проектами

```
voice_bot_pipeline (офлайн-подготовка)
    ↓
SAG v2.0 JSON + ChromaDB + Knowledge Graph
    ↓
bot_psychologist (онлайн-ответы пользователю)
```

---

## 🎬 voice_bot_pipeline

### Назначение
Офлайн-пайплайн для извлечения субтитров из YouTube, структурирования в SAG v2.0 формат, построения Knowledge Graph и индексации в векторную БД.

### Ключевые компоненты

```
voice_bot_pipeline/
├── pipeline_orchestrator.py      # Главный оркестратор пайплайна
├── subtitle_extractor/           # Извлечение субтитров с YouTube
│   └── get_subtitles.py          # YouTubeSubtitlesExtractor
├── text_processor/               # Обработка текста
│   ├── sarsekenov_processor.py   # Главный процессор SAG v2.0
│   ├── subtitles_to_blocks.py    # Разбиение на семантические блоки
│   ├── sd_labeler.py             # SD-лейблинг блоков
│   └── extractors/               # 5 экстракторов знаний
│       ├── safety_extractor.py
│       ├── causal_chain_extractor.py
│       ├── concept_hierarchy_extractor.py
│       ├── case_study_extractor.py
│       └── prerequisite_extractor.py
├── vector_db/                    # ChromaDB интеграция
│   └── VectorDBManager.py
├── utils/                        # Утилиты
│   ├── video_registry.py         # Реестр видео
│   ├── youtube_metadata_fetcher.py
│   ├── file_utils.py
│   └── channel_list_parser.py
├── config.yaml                   # Конфигурация пайплайна
└── requirements.txt              # Зависимости
```

### SAG v2.0 — Структурированная генерация

**SAG (Structured Augmented Generation) v2.0** — продвинутая система подготовки структурированных данных:

- **Автоматическая классификация блоков**: `monologue`/`dialogue`/`practice`/`theory`
- **Граф-сущности**: 442 узла + 259 отношений (нейросталкинг термины)
- **Семантический анализ**: Автоматическое выявление связей между концептами
- **Knowledge Graph**: Максимально полная база знаний со всеми взаимосвязями
- **Умная маршрутизация**: `collection_target` + `routing_confidence`

### Система экстракторов знаний (5 этапов)

| Этап | Экстрактор | Назначение |
|------|------------|------------|
| 1 | TerminologyValidator | Валидация плотности терминов Сарсекенова (≥15%) |
| 2 | NeurostalkingPatternExtractor | Распознавание паттернов учения (4 категории) |
| 3 | CausalChainExtractor | Извлечение пошаговых процессов трансформации |
| 4 | ConceptHierarchyExtractor | Построение иерархии концептов (5 уровней) |
| 5 | SarsekenovProcessor (Оркестратор) | Слияние результатов, построение Knowledge Graph |

### Запуск пайплайна

```bash
cd voice_bot_pipeline
pip install -r requirements.txt
# Настроить .env с API ключами
python pipeline_orchestrator.py --help
```

### Конфигурация (config.yaml)

```yaml
pipeline:
  text_processing:
    output_dir: "data/sag_final"
  sag_v2:
    use_safety_extractor: true
    use_causal_chain_extractor: true
    # ...

vector_db:
  db_path: "data/chromadb"
  collection_prefix: "sag_v2"
  auto_index: true
  embedding:
    provider: "sentence-transformers"
    model: "intfloat/multilingual-e5-large"
```

### Структура данных

```
voice_bot_pipeline/data/
├── raw_subtitles/          # Сырые субтитры с YouTube
├── sag_final/              # Финальные SAG v2.0 JSON файлы
│   └── *.for_vector.json   # Готовые блоки для векторного поиска
├── chromadb/               # Векторная база данных ChromaDB
├── graphs/                 # Графы знаний (JSON)
└── channel_video_list/     # Список видео канала
```

---

## 🤖 bot_psychologist

### Назначение
AI-бот-психолог, работающий поверх данных `voice_bot_pipeline`. Отвечает на вопросы пользователей с опорой на материалы лекций Сарсекенова.

### Архитектура (6 фаз)

| Фаза | Название | Файл | Описание |
|------|----------|------|----------|
| Phase 1 | Базовый QA | `answer_basic.py` | TF-IDF поиск + LLM ответы |
| Phase 2 | SAG-aware QA | `answer_sag_aware.py` | Адаптация по уровню пользователя |
| Phase 3 | Knowledge Graph | `answer_graph_powered.py` | Рекомендации через граф знаний |
| Phase 4 | Adaptive QA | `answer_adaptive.py` | Классификация состояний, память диалога |
| Phase 5 | REST API | `api/routes.py` | FastAPI сервер |
| Phase 6 | Web UI | `web_ui/src/` | React SPA интерфейс |

### Ключевые компоненты

```
bot_psychologist/
├── bot_agent/                    # Ядро бота
│   ├── config.py                 # Конфигурация
│   ├── data_loader.py            # Загрузка данных из pipeline
│   ├── retriever.py              # TF-IDF поиск
│   ├── llm_answerer.py           # Генерация ответов (OpenAI)
│   ├── answer_adaptive.py        # Adaptive QA (основной режим)
│   ├── conversation_memory.py    # Память диалога (JSON)
│   ├── semantic_memory.py        # Semantic search (эмбеддинги)
│   ├── graph_client.py           # Knowledge Graph клиент
│   ├── sd_classifier.py          # SD-классификатор пользователя
│   ├── state_classifier.py       # Классификация состояния
│   ├── user_level_adapter.py     # Адаптация по уровню
│   ├── practices_recommender.py  # Рекомендация практик
│   ├── path_builder.py           # Построение путей трансформации
│   ├── decision/                 # Decision table + gate
│   │   ├── decision_table.py
│   │   └── decision_gate.py
│   ├── retrieval/                # Retrieval политика
│   │   ├── confidence_scorer.py
│   │   ├── stage_filter.py
│   │   ├── sd_filter.py
│   │   └── voyage_reranker.py
│   └── response/                 # Генерация ответов
│       ├── response_generator.py
│       └── response_formatter.py
│
├── api/                          # FastAPI сервер
│   ├── main.py                   # Приложение
│   ├── routes.py                 # Endpoints
│   ├── auth.py                   # Аутентификация (X-API-Key)
│   ├── models.py                 # Pydantic модели
│   ├── dependencies.py           # DI зависимости
│   ├── session_store.py          # In-memory хранилище
│   └── debug_routes.py           # Debug endpoints (dev)
│
├── web_ui/                       # React интерфейс
│   └── src/
│       ├── pages/
│       │   ├── ChatPage.tsx      # Главная страница чата
│       │   └── SettingsPage.tsx
│       ├── components/
│       │   ├── Message.tsx
│       │   ├── MessageList.tsx
│       │   ├── InlineDebugTrace.tsx  # Debug панель
│       │   └── ...
│       ├── hooks/
│       │   ├── useChat.ts
│       │   └── useTraceCache.ts  # Кэш трейсов
│       └── services/
│           └── api.service.ts
│
├── tests/                        # Тесты
│   ├── test_phase1.py
│   ├── test_phase4.py
│   ├── test_semantic_memory.py
│   ├── test_sd_integration.py
│   └── ...
│
├── .cache_bot_agent/             # Кэш бота
│   ├── conversations/            # История диалогов (JSON)
│   └── semantic_memory/          # Эмбеддинги
│
├── logs/                         # Логи
│   ├── app/bot.log               # Общий лог (INFO+)
│   ├── retrieval/retrieval.log   # Retrieval события
│   └── error/error.log           # Ошибки (ERROR+)
│
└── config/
    └── sd_classification.yaml    # SD-конфигурация
```

### SD-интеграция (Спиральная Динамика)

**SD-классификатор** определяет уровень сознания пользователя:

| Уровень | Цвет | Описание |
|---------|------|----------|
| 1 | PURPLE | Архаичный, мистический |
| 2 | RED | Импульсивный, эгоцентричный |
| 3 | BLUE | Авторитарный, абсолютистский |
| 4 | ORANGE | Достиженческий, научный |
| 5 | GREEN | Плюралистический, релятивистский |
| 6 | YELLOW | Интегральный, системный |

**Файлы промптов:**
- `prompt_sd_purple.md`, `prompt_sd_red.md`, `prompt_sd_blue.md`
- `prompt_sd_orange.md`, `prompt_sd_green.md`, `prompt_sd_yellow.md`

### Память диалога

**Уровни памяти:**
1. **Short-term** — последние N обменов (`CONVERSATION_HISTORY_DEPTH=3`)
2. **Semantic memory** — релевантные прошлые обмены по смыслу (эмбеддинги)
3. **Conversation summary** — краткое резюме диалога (обновляется каждые 5 ходов)

**Адаптивная стратегия:**
- 1-5 ходов: только short-term
- 6-20 ходов: short-term + semantic
- 21+ ходов: short-term + semantic + summary

### API Endpoints

```bash
# Health check
GET /health

# Вопросы боту (требует X-API-Key)
POST /api/v1/questions/basic
POST /api/v1/questions/sag-aware
POST /api/v1/questions/graph-powered
POST /api/v1/questions/adaptive          # Основной режим
POST /api/v1/questions/adaptive-stream   # SSE streaming

# Управление сессиями
GET  /api/v1/users/{user_id}/sessions
POST /api/v1/users/{user_id}/sessions
DELETE /api/v1/users/{user_id}/sessions/{session_id}

# История диалогов
GET /api/v1/users/{user_id}/history
DELETE /api/v1/users/{user_id}/history

# Semantic memory
GET /api/v1/users/{user_id}/semantic-stats
POST /api/v1/users/{user_id}/rebuild-semantic-memory

# Debug (dev-key-001)
GET /api/debug/blob/{blob_id}
GET /api/debug/session/{session_id}/metrics
GET /api/debug/session/{session_id}/traces
```

### Переменные окружения (.env)

```bash
# API ключи
OPENAI_API_KEY=sk-proj-...
VOYAGE_API_KEY=pa-...         # Опционально для rerank

# Модели
PRIMARY_MODEL=gpt-5-mini      # Основная модель ответа
CLASSIFIER_MODEL=gpt-4o-mini  # Модель для классификаторов
REASONING_EFFORT=low          # Для reasoning-моделей (gpt-5, o1/o3/o4)

# Память диалога
CONVERSATION_HISTORY_DEPTH=3
MAX_CONTEXT_SIZE=2000
MAX_CONVERSATION_TURNS=1000

# Semantic memory
ENABLE_SEMANTIC_MEMORY=true
SEMANTIC_SEARCH_TOP_K=3
SEMANTIC_MIN_SIMARITY=0.7
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# Voyage Rerank
VOYAGE_ENABLED=false
VOYAGE_MODEL=rerank-2
VOYAGE_TOP_K=1

# Summary
ENABLE_CONVERSATION_SUMMARY=true
SUMMARY_UPDATE_INTERVAL=5

# Session storage
ENABLE_SESSION_STORAGE=true
BOT_DB_PATH=data/bot_sessions.db

# Speed Layer
WARMUP_ON_START=true
ENABLE_STREAMING=true
```

### Запуск API сервера

```bash
cd bot_psychologist
pip install -r requirements_bot.txt
pip install -r api/requirements.txt

# Проверка тестами
python -m pytest tests/ -v

# Запуск сервера
python -m uvicorn api.main:app --reload --port 8001

# Проверка логов
tail -f logs/app/bot.log
tail -f logs/retrieval/retrieval.log
tail -f logs/error/error.log
```

### Запуск Web UI

```bash
cd web_ui
npm install
npm run dev
# http://localhost:3000
```

---

## 🔧 Интеграция и workflow

### Полный workflow разработки

```
1. Обработка видео (voice_bot_pipeline)
   ↓
   youtube-dl → субтитры → sarsekenov_processor → SAG v2.0 JSON
   ↓
   Knowledge Graph → ChromaDB индексация

2. Использование ботом (bot_psychologist)
   ↓
   Пользователь задаёт вопрос → retriever (TF-IDF) → retrieval policy
   ↓
   SD-классификация → SD-фильтр блоков → decision table
   ↓
   LLM (с учётом SD-уровня) → ответ с памятью диалога
```

### Интеграция данных

**voice_bot_pipeline → bot_psychologist:**

```python
# bot_psychologist/bot_agent/data_loader.py
DATA_ROOT = "../voice_bot_pipeline/data"
SAG_FINAL_DIR = f"{DATA_ROOT}/sag_final"
CHROMADB_PATH = f"{DATA_ROOT}/chromadb"

# Загрузка блоков
for json_file in Path(SAG_FINAL_DIR).glob("*.for_vector.json"):
    blocks = json.load(json_file)["blocks"]
```

---

## 🧪 Тестирование

### voice_bot_pipeline

```bash
cd voice_bot_pipeline
pytest tests/ -v
```

### bot_psychologist

```bash
cd bot_psychologist

# Модульные тесты
python tests/test_phase1.py
python tests/test_phase2.py
python tests/test_phase3.py
python tests/test_phase4.py

# SD-интеграция
python tests/test_sd_classifier.py
python tests/test_sd_filter.py
python tests/test_sd_integration.py

# Память
python tests/test_semantic_memory.py
python tests/test_conversation_memory_persistence.py

# Retrieval
python tests/test_hybrid_query.py
python tests/test_confidence_scorer.py
python tests/test_stage_filter.py
python tests/test_voyage_reranker.py

# Response layer
python tests/test_response_generator.py
python tests/test_response_formatter.py

# API
python tests/test_api.py

# Полный прогон
pytest tests/ -v
```

---

## 🐛 Известные проблемы (PRD v3.0.2)

### Debug Panel — 5 критических багов

| # | Проблема | Файл | Статус |
|---|----------|------|--------|
| 1 | Трейс исчезает при смене чата | `ChatPage.tsx`, `useTraceCache.ts` | Требуется sessionStorage кэш |
| 2 | Панель всегда развёрнута | `InlineDebugTrace.tsx` | Нет `<details>` с toggle |
| 3 | Чанк не раскрывается полностью | `InlineDebugTrace.tsx` | `ChunkRow` без useState expand |
| 4 | Нет стоимости и токенов | `InlineDebugTrace.tsx` | `<details>` без `open` |
| 5 | Порядок секций неверный | `InlineDebugTrace.tsx` | Timeline должен быть первым |

### Стратегия фикса

1. **useTraceCache.ts** — новый хук для sessionStorage кэширования трейсов
2. **InlineDebugTrace.tsx** — конвертировать в `<details>`, добавить `useState` для чанков
3. **Порядок секций**: Timeline → Retrieval → Memory → SD → Anomalies → Config → Cost

---

## 📝 Конвенции разработки

### Код-стайл

- **Python**: PEP 8, type hints обязательны
- **TypeScript**: Strict mode, интерфейсы для типов
- **Именование**: snake_case (Python), camelCase (TypeScript)

### Логирование

```python
from logging_config import get_logger

logger = get_logger(__name__)

logger.info("[RETRIEVAL] Query processed")
logger.error("[ERROR] Unexpected error", exc_info=True)
```

### Коммиты

```bash
git status && git diff HEAD && git log -n 3

# Формат коммита:
feat(bot): добавить semantic memory кэш
fix(pipeline): исправить дедупликацию блоков
docs: обновить README для SAG v2.0
```

### Ветвление

- `main` — основная ветка
- `feat/*` — новые функции
- `fix/*` — исправления багов
- `docs/*` — документация

---

## 🔍 Debug-инструменты

### Inline Debug Trace (dev-key-001)

Для включения debug-режима:
1. В Web UI указать `X-API-Key = dev-key-001`
2. Под каждым ответом бота появляется collapsible панель

**Что показывает:**
- Роутинг: `recommended_mode`, `decision_rule_id`, `confidence`
- Retrieval: выбранные/отсеянные блоки с `block_id`, `score`, `source`
- Память: `memory_turns`, `semantic_hits`, `summary_used`
- SD: `sd_level`, SD prompt overlay
- LLM вызовы: модель, токены, длительность, стоимость

### Developer Command Center

```bash
# Получить blob (большие данные)
GET /api/debug/blob/{blob_id}

# Метрики сессии
GET /api/debug/session/{session_id}/metrics

# Трейсы сессии
GET /api/debug/session/{session_id}/traces
```

### Логи

```bash
# Приложение
tail -f logs/app/bot.log

# Retrieval события
tail -f logs/retrieval/retrieval.log

# Ошибки
tail -f logs/error/error.log
```

---

## 📚 Полезные ссылки

### Документация

- [voice_bot_pipeline README](voice_bot_pipeline/README.md) — SAG v2.0, экстракторы
- [bot_psychologist README](bot_psychologist/README.md) — 6 фаз, API, Web UI
- [PRD v3.0.2](PRD%20v3.0.2%20—%20Hotfix%20Debug%20Panel%205%20Critical%20Bugs.md) — Debug Panel фиксы

### Ключевые файлы

| Файл | Описание |
|------|----------|
| `voice_bot_pipeline/pipeline_orchestrator.py` | Главный оркестратор пайплайна |
| `voice_bot_pipeline/text_processor/sarsekenov_processor.py` | SAG v2.0 процессор |
| `bot_psychologist/bot_agent/answer_adaptive.py` | Основной режим ответов |
| `bot_psychologist/api/routes.py` | API endpoints |
| `bot_psychologist/web_ui/src/pages/ChatPage.tsx` | Главная страница чата |
| `bot_psychologist/bot_agent/conversation_memory.py` | Память диалога |
| `bot_psychologist/bot_agent/semantic_memory.py` | Semantic search |

---

## 🚀 Быстрый старт (полный)

```bash
# 1. voice_bot_pipeline — подготовка данных
cd voice_bot_pipeline
pip install -r requirements.txt
# Настроить .env (OPENAI_API_KEY, YOUTUBE_API_KEY)
python pipeline_orchestrator.py --help

# 2. bot_psychologist — запуск бота
cd ../bot_psychologist
pip install -r requirements_bot.txt
pip install -r api/requirements.txt
# Настроить .env (OPENAI_API_KEY, DATA_ROOT)
python -m uvicorn api.main:app --reload --port 8001

# 3. Web UI (опционально)
cd web_ui
npm install
npm run dev
# http://localhost:3000
```

---

## 👤 Автор

Askhat-cmd

---

**Последнее обновление:** 6 марта 2026 г.
