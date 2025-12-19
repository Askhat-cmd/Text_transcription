# Архитектура Bot Psychologist

## Навигация

- [Назад к README](../README.md)
- [Обзор проекта](./overview.md)
- [Поток данных](./data_flow.md)
- [Bot Agent](./bot_agent.md)

---

## Описание и назначение

**Назначение документа**: Полное описание архитектуры проекта Bot Psychologist, включая все Phase 1-6, компоненты, их взаимодействие и потоки данных.

**Для кого**: Разработчики, изучающие код, архитекторы, планирующие изменения.

**Что содержит**:
- Архитектура Phase 1-6
- Компоненты системы
- Взаимодействие компонентов
- Потоки данных
- Технологический стек

---

## Общая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Web UI (Phase 6)                         │
│              React SPA + Tailwind CSS                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Chat   │  │ Profile  │  │  Path    │  │ Feedback │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│              REST API (Phase 5)                              │
│              FastAPI + Uvicorn                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  /api/v1/questions/basic                              │   │
│  │  /api/v1/questions/sag-aware                          │   │
│  │  /api/v1/questions/graph-powered                      │   │
│  │  /api/v1/questions/adaptive                           │   │
│  │  /api/v1/users/{user_id}/history                      │   │
│  │  /api/v1/feedback                                      │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              Bot Agent (Phase 1-4)                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Phase 1: Basic QA                                    │   │
│  │  ├─ Retriever (TF-IDF)                               │   │
│  │  └─ LLM Answerer                                     │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  Phase 2: SAG-aware QA                                │   │
│  │  ├─ User Level Adapter                               │   │
│  │  ├─ Semantic Analyzer                                │   │
│  │  └─ Complexity-aware retrieval                       │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  Phase 3: Graph-powered QA                           │   │
│  │  ├─ Graph Client (Knowledge Graph)                   │   │
│  │  ├─ Practices Recommender                            │   │
│  │  └─ Concept hierarchy search                         │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │  Phase 4: Adaptive QA                                │   │
│  │  ├─ State Classifier (10 состояний)                  │   │
│  │  ├─ Conversation Memory                              │   │
│  │  └─ Path Builder (персональные пути)                 │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              Data Layer                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Data Loader                                          │   │
│  │  ├─ Загрузка sag_final/*.for_vector.json             │   │
│  │  ├─ Парсинг блоков, метаданных                       │   │
│  │  └─ Кэширование в памяти                            │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│         voice_bot_pipeline/data/                             │
│  ├─ sag_final/          # SAG v2.0 JSON блоки              │
│  └─ chromadb/           # Векторная БД (опционально)       │
└──────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Базовый QA

### Компоненты

1. **DataLoader** (`data_loader.py`)
   - Загружает все `*.for_vector.json` из `sag_final/`
   - Парсит блоки, метаданные, граф-сущности
   - Кэширует в памяти

2. **SimpleRetriever** (`retriever.py`)
   - TF-IDF векторное представление блоков
   - Косинусное сходство для поиска
   - Фильтрация по минимальному порогу релевантности

3. **LLMAnswerer** (`llm_answerer.py`)
   - Формирует системный промпт бота-психолога
   - Собирает контекст из найденных блоков
   - Генерирует ответ через OpenAI API

### Поток данных

```
Пользовательский вопрос
    ↓
[SimpleRetriever] → TF-IDF поиск → Top-K релевантных блоков
    ↓
[LLMAnswerer] → Формирование промпта → OpenAI API → Ответ
    ↓
Ответ с источниками (таймкоды, ссылки)
```

### Используемые данные

- **Блоки**: `title`, `summary`, `content`, `keywords`
- **Метаданные**: `video_id`, `start`, `end`, `youtube_link`
- **Граф-сущности**: не используются в Phase 1

---

## Phase 2: SAG-aware QA

### Компоненты

1. **UserLevelAdapter** (`user_level_adapter.py`)
   - Определяет уровень пользователя (beginner/intermediate/advanced)
   - Фильтрует блоки по `complexity_score`
   - Адаптирует ответы под уровень

2. **SemanticAnalyzer** (`semantic_analyzer.py`)
   - Извлекает ключевые концепты из запроса
   - Анализирует семантические связи между концептами
   - Определяет тематическую область

### Поток данных

```
Пользовательский вопрос + уровень пользователя
    ↓
[SemanticAnalyzer] → Извлечение концептов
    ↓
[SimpleRetriever] → Поиск блоков
    ↓
[UserLevelAdapter] → Фильтрация по complexity_score
    ↓
[LLMAnswerer] → Адаптированный промпт → Ответ
    ↓
Ответ с учётом уровня пользователя
```

### Используемые данные

- **Блоки**: все поля Phase 1 + `complexity_score`, `block_type`
- **Граф-сущности**: концепты из `graph_entities` для семантического анализа

---

## Phase 3: Knowledge Graph Powered QA

### Компоненты

1. **GraphClient** (`graph_client.py`)
   - Загружает Knowledge Graph из блоков
   - Построение графа: узлы (95) + связи (2182)
   - Поиск по графу: BFS, DFS, shortest path
   - Типы узлов: CONCEPT, PRACTICE, TECHNIQUE, EXERCISE, PATTERN, PROCESS_STAGE

2. **PracticesRecommender** (`practices_recommender.py`)
   - Рекомендация практик через граф
   - Поиск практик для концептов
   - Фильтрация по релевантности

### Поток данных

```
Пользовательский вопрос
    ↓
[SemanticAnalyzer] → Извлечение концептов
    ↓
[GraphClient] → Поиск узлов в графе → Связанные концепты/практики
    ↓
[PracticesRecommender] → Рекомендация практик
    ↓
[SimpleRetriever] → Поиск блоков по концептам
    ↓
[LLMAnswerer] → Ответ с практиками из графа
    ↓
Ответ с практиками и концептами из Knowledge Graph
```

### Используемые данные

- **Knowledge Graph**: `graph_entities`, `graph_relations` из блоков
- **Граф-сущности**: полная структура графа (узлы + связи)
- **Блоки**: для контекста практик

---

## Phase 4: Adaptive QA

### Компоненты

1. **StateClassifier** (`state_classifier.py`)
   - Классификация состояния пользователя (10 состояний)
   - Keyword-based + LLM анализ
   - Определение эмоционального тона, глубины

2. **ConversationMemory** (`conversation_memory.py`)
   - Хранение истории диалога
   - Отслеживание интересов, вызовов, прорывов
   - Персистентное хранилище (JSON файлы)

3. **PathBuilder** (`path_builder.py`)
   - Построение персональных путей трансформации
   - Интеграция с Knowledge Graph
   - Рекомендация шагов на основе состояния

### Поток данных

```
Пользовательский вопрос + user_id
    ↓
[ConversationMemory] → Загрузка истории диалога
    ↓
[StateClassifier] → Анализ состояния (10 состояний)
    ↓
[SemanticAnalyzer] → Извлечение концептов
    ↓
[GraphClient] → Поиск в Knowledge Graph
    ↓
[PathBuilder] → Построение персонального пути
    ↓
[SimpleRetriever] → Поиск релевантных блоков
    ↓
[LLMAnswerer] → Адаптированный ответ с учётом состояния
    ↓
Ответ + анализ состояния + путь трансформации
    ↓
[ConversationMemory] → Сохранение оборота диалога
```

### Используемые данные

- **История диалога**: из `.cache_bot_agent/conversations/{user_id}.json`
- **Состояния**: 10 состояний от UNAWARE до INTEGRATED
- **Knowledge Graph**: для построения путей
- **Блоки**: для контекста ответов

---

## Phase 5: REST API

### Компоненты

1. **FastAPI Application** (`api/main.py`)
   - ASGI сервер (Uvicorn)
   - Middleware: CORS, TrustedHost, логирование
   - OpenAPI документация

2. **API Routes** (`api/routes.py`)
   - Endpoints для всех Phase 1-4
   - Аутентификация через API ключи
   - Валидация запросов (Pydantic)

3. **Auth Module** (`api/auth.py`)
   - Управление API ключами
   - Rate limiting (по типу ключа)
   - Верификация запросов

### Endpoints

```
POST /api/v1/questions/basic          # Phase 1
POST /api/v1/questions/sag-aware      # Phase 2
POST /api/v1/questions/graph-powered  # Phase 3
POST /api/v1/questions/adaptive       # Phase 4
POST /api/v1/users/{user_id}/history  # История пользователя
POST /api/v1/feedback                 # Обратная связь
GET  /api/v1/stats                    # Статистика
GET  /api/v1/health                   # Health check
```

### Поток данных

```
HTTP Request → [Auth] → [Routes] → [Bot Agent] → Response
```

---

## Phase 6: Web UI

### Компоненты

1. **React Application** (`web_ui/src/`)
   - SPA на React 19 + TypeScript
   - Роутинг: React Router
   - State: Zustand

2. **Pages**
   - `HomePage` — главная страница
   - `ChatPage` — основной интерфейс чата
   - `ProfilePage` — профиль пользователя
   - `SettingsPage` — настройки

3. **Components**
   - `ChatWindow` — диалоговое окно
   - `MessageList` — список сообщений
   - `StateCard` — индикатор состояния
   - `PathBuilder` — визуализация пути
   - `FeedbackWidget` — оценка ответов

4. **Services**
   - `api.service.ts` — HTTP клиент (Axios)
   - `websocket.service.ts` — WebSocket для real-time
   - `storage.service.ts` — localStorage

### Поток данных

```
User Interaction → React Component → API Service → REST API → Bot Agent
                                                              ↓
Response ← API Service ← React Component ← HTTP Response
```

---

## Взаимодействие компонентов

### Загрузка данных

```
[DataLoader] → Загружает sag_final/*.for_vector.json
    ↓
Парсинг блоков → [Block] объекты
    ↓
Извлечение граф-сущностей → [GraphClient] → Knowledge Graph
```

### Обработка вопроса

```
[Retriever] → Поиск блоков
    ↓
[SemanticAnalyzer] → Извлечение концептов
    ↓
[GraphClient] → Поиск в графе
    ↓
[StateClassifier] → Анализ состояния (Phase 4)
    ↓
[PathBuilder] → Построение пути (Phase 4)
    ↓
[LLMAnswerer] → Генерация ответа
```

### Сохранение истории

```
[ConversationMemory] → Добавление оборота
    ↓
Сохранение в .cache_bot_agent/conversations/{user_id}.json
```

---

## Технологический стек

### Backend
- **Python 3.10+**
- **OpenAI API** — GPT-4o-mini для генерации ответов
- **scikit-learn** — TF-IDF векторное представление
- **numpy** — численные вычисления
- **FastAPI** — REST API фреймворк
- **Pydantic** — валидация данных
- **Uvicorn** — ASGI сервер

### Frontend
- **React 19** — UI библиотека
- **TypeScript** — типизация
- **Vite** — сборщик
- **Tailwind CSS** — стилизация
- **React Router** — маршрутизация
- **Axios** — HTTP клиент
- **Zustand** — управление состоянием

### Данные
- **JSON** — структурированные блоки (SAG v2.0)
- **Knowledge Graph** — встроен в JSON блоки
- **ChromaDB** (опционально) — векторная БД

---

## Навигация

- [Обзор проекта](./overview.md)
- [Поток данных](./data_flow.md)
- [Bot Agent](./bot_agent.md)
- [REST API](./api.md)
- [Web UI](./web_ui.md)
