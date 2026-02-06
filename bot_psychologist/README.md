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

- История хранится на диске в `bot_psychologist/.cache_bot_agent/conversations/{user_id}.json` (папка в git игнорируется).
- Контекст последних сообщений автоматически добавляется в промпт перед материалами из базы знаний.
- Память используется во всех режимах ответов: Phase 1-4 (basic, sag-aware, graph-powered, adaptive).

Оптимизация контекста (чтобы не раздувать токены):

- В LLM передаются только последние N обменов.
- Контекст обрезается по лимиту символов.
- История автоматически ротируется, если превысила максимальное число сохранённых ходов.

Настройки через `.env` (см. `bot_psychologist/.env.example`):

- `CONVERSATION_HISTORY_DEPTH` (default: `3`) — сколько последних обменов добавлять в контекст.
- `MAX_CONTEXT_SIZE` (default: `2000`) — максимальный размер контекста в символах.
- `MAX_CONVERSATION_TURNS` (default: `1000`) — максимальное число ходов, хранимых для одного пользователя (старые удаляются).

Ключевые файлы:

- `bot_agent/conversation_memory.py` — хранение, загрузка/сохранение, сбор контекста, очистка.
- `bot_agent/llm_answerer.py` — принимает `conversation_history` и добавляет в `build_context_prompt(...)`.
- `bot_agent/answer_basic.py`, `bot_agent/answer_sag_aware.py`, `bot_agent/answer_graph_powered.py`, `bot_agent/answer_adaptive.py` — подключают память, добавляют историю в LLM и сохраняют ход после ответа.
- `api/routes.py` — пробрасывает `user_id` во все режимы и даёт endpoints управления историей.

API для истории:

- `GET /api/v1/users/{user_id}/history?last_n_turns=10`
- `GET /api/v1/users/{user_id}/summary`
- `DELETE /api/v1/users/{user_id}/history`

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

# Conversation Memory
CONVERSATION_HISTORY_DEPTH=3
MAX_CONTEXT_SIZE=2000
MAX_CONVERSATION_TURNS=1000
```

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

# API тесты
python test_api.py
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
│
├── test_phase1.py          # Тесты Phase 1
├── test_phase2.py          # Тесты Phase 2
├── test_phase3.py          # Тесты Phase 3
├── test_phase4.py          # Тесты Phase 4
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

## Проект является частью монорепозитория

Этот проект является частью монорепозитория `Text_transcription`, который содержит:

1. **voice_bot_pipeline** — пайплайн подготовки данных из YouTube-лекций
2. **bot_psychologist** — AI-бот, использующий эти данные

См. корневой [README.md](../README.md) для общей информации о монорепозитории.

## Лицензия

Private — для внутреннего использования

## Автор

Askhat-cmd
