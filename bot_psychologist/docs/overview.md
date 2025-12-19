# Обзор проекта Bot Psychologist

## Навигация

- [Назад к README](../README.md)
- [Архитектура](./architecture.md)
- [Поток данных](./data_flow.md)
- [Конфигурация](./configuration.md)

---

## Описание и назначение

**Bot Psychologist** — AI-ассистент-психолог, работающий поверх структурированных данных из `voice_bot_pipeline`. Проект использует SAG v2.0 данные, Knowledge Graph и семантический поиск для предоставления персонализированных ответов с отсылками к конкретным видео и таймкодам.

**Назначение документа**: Дать общее понимание проекта, его целей и места в монорепозитории.

**Для кого**: Новые разработчики, архитекторы, менеджеры проектов.

**Что содержит**:
- Общее описание проекта
- Связь с `voice_bot_pipeline`
- Основные возможности (Phase 1-6)
- Технологический стек
- Структура проекта

---

## Связь с voice_bot_pipeline

`bot_psychologist` является потребителем данных, сгенерированных `voice_bot_pipeline`:

```
voice_bot_pipeline/
└── data/
    ├── sag_final/          # Структурированные JSON блоки
    │   └── {year}/{month}/
    │       └── *.for_vector.json
    └── chromadb/           # Векторная БД (опционально)
        └── ...

bot_psychologist/
└── bot_agent/
    ├── data_loader.py      # Загружает sag_final/*.for_vector.json
    ├── graph_client.py     # Работает с Knowledge Graph из блоков
    └── retriever.py        # Поиск по блокам (TF-IDF или ChromaDB)
```

**Важно**: `bot_psychologist` не изменяет данные `voice_bot_pipeline`, только читает их.

---

## Основные возможности

### Phase 1: Базовый QA
- TF-IDF поиск по блокам
- Генерация ответов через OpenAI GPT
- Отсылки к видео с таймкодами

### Phase 2: SAG-aware QA
- Адаптация ответов по уровню пользователя (beginner/intermediate/advanced)
- Семантический анализ запросов
- Учёт сложности блоков (complexity_score)

### Phase 3: Knowledge Graph Powered
- Работа с графом знаний (95 узлов, 2182 связи)
- Рекомендация практик через граф
- Поиск по концептам и связям

### Phase 4: Adaptive QA
- Классификация состояния пользователя (10 состояний)
- Долгосрочная память диалога
- Персональные пути трансформации
- Адаптивные рекомендации

### Phase 5: REST API
- FastAPI сервер
- Endpoints для всех Phase 1-4
- Аутентификация через API ключи
- История пользователей и статистика

### Phase 6: Web UI
- React SPA интерфейс
- Чат с ботом
- Визуализация путей трансформации
- Профиль пользователя и статистика

---

## Технологический стек

### Backend (Python)
- **OpenAI API** — генерация ответов (GPT-4o-mini)
- **scikit-learn** — TF-IDF поиск
- **numpy** — численные вычисления
- **FastAPI** — REST API сервер
- **Pydantic** — валидация данных
- **python-dotenv** — управление переменными окружения

### Frontend (TypeScript/React)
- **React 19** — UI библиотека
- **TypeScript** — типизация
- **Vite** — сборщик
- **Tailwind CSS** — стилизация
- **React Router** — маршрутизация
- **Axios** — HTTP клиент
- **Zustand** — управление состоянием

### Данные
- **SAG v2.0 JSON** — структурированные блоки лекций
- **Knowledge Graph** — граф концептов и практик (встроен в JSON)
- **ChromaDB** (опционально) — векторная БД для семантического поиска

---

## Структура проекта

```
bot_psychologist/
├── bot_agent/              # Основной код бота
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
│   ├── package.json        # npm зависимости
│   └── vite.config.ts      # Конфигурация Vite
│
├── docs/                   # Документация проекта
│   ├── overview.md         # Этот файл
│   ├── architecture.md     # Архитектура
│   ├── data_flow.md        # Поток данных
│   ├── sag_v2.md           # SAG v2.0
│   ├── knowledge_graph.md  # Knowledge Graph
│   ├── bot_agent.md        # Bot Agent
│   ├── api.md              # REST API
│   ├── web_ui.md           # Web UI
│   ├── configuration.md    # Конфигурация
│   ├── testing.md          # Тестирование
│   ├── deployment.md       # Развёртывание
│   └── roadmap.md         # Дорожная карта
│
├── .cache_bot_agent/       # Кэш и данные бота
│   └── conversations/       # История диалогов пользователей
│
├── test_phase1.py          # Тесты Phase 1
├── test_phase2.py          # Тесты Phase 2
├── test_phase3.py          # Тесты Phase 3
├── test_phase4.py          # Тесты Phase 4
├── test_api.py             # Тесты API
│
├── requirements_bot.txt    # Python зависимости
├── .env.example            # Пример переменных окружения
└── README.md               # Главный README проекта
```

---

## Быстрый старт

### 1. Установка зависимостей

```bash
cd bot_psychologist
pip install -r requirements_bot.txt
pip install -r api/requirements.txt
```

### 2. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните:

```bash
OPENAI_API_KEY=sk-proj-...
PRIMARY_MODEL=gpt-4o-mini
DATA_ROOT=../voice_bot_pipeline/data
DEBUG=False
```

### 3. Проверка данных

Убедитесь, что данные из `voice_bot_pipeline` доступны:

```bash
# Проверить наличие sag_final данных
ls ../voice_bot_pipeline/data/sag_final/
```

### 4. Запуск тестов

```bash
# Phase 1
python test_phase1.py

# Phase 2
python test_phase2.py

# Phase 3
python test_phase3.py

# Phase 4
python test_phase4.py
```

### 5. Запуск API сервера

```bash
cd api
uvicorn main:app --reload --port 8000
```

### 6. Запуск Web UI

```bash
cd web_ui
npm install
npm run dev
```

---

## Принципы работы

1. **Только чтение данных**: Бот не изменяет данные `voice_bot_pipeline`
2. **Персонализация**: Адаптация ответов по уровню и состоянию пользователя
3. **Прозрачность**: Все ответы содержат ссылки на источники с таймкодами
4. **Память диалога**: Долгосрочное хранение истории для контекста
5. **Персональные пути**: Рекомендации практик на основе состояния пользователя

---

## Навигация

- [Архитектура](./architecture.md) — детальная архитектура Phase 1-6
- [Поток данных](./data_flow.md) — как данные поступают от voice_bot_pipeline
- [Конфигурация](./configuration.md) — настройка проекта
- [Развёртывание](./deployment.md) — локальный запуск и production
