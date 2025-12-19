# Поток данных от voice_bot_pipeline

## Навигация

- [Назад к README](../README.md)
- [Обзор проекта](./overview.md)
- [Архитектура](./architecture.md)
- [SAG v2.0](./sag_v2.md)

---

## Описание и назначение

**Назначение документа**: Описать поток данных от `voice_bot_pipeline` к `bot_psychologist`, структуру данных и способы их использования.

**Для кого**: Разработчики, работающие с данными, архитекторы данных.

**Что содержит**:
- Источник данных (voice_bot_pipeline)
- Структура данных SAG v2.0
- Процесс загрузки данных
- Использование данных в Bot Agent

---

## Источник данных

### voice_bot_pipeline/data/

```
voice_bot_pipeline/
└── data/
    ├── sag_final/              # Структурированные JSON блоки
    │   └── {year}/
    │       └── {month}/
    │           └── {video_id}.for_vector.json
    └── chromadb/               # Векторная БД (опционально)
        └── ...
```

**Важно**: `bot_psychologist` только читает данные, не изменяет их.

---

## Структура данных SAG v2.0

### Формат файла: `*.for_vector.json`

```json
{
  "document_metadata": {
    "video_id": "abc123",
    "source_url": "https://youtube.com/watch?v=abc123",
    "title": "Название лекции",
    "duration_seconds": 3600,
    "processed_at": "2024-01-01T00:00:00Z"
  },
  "blocks": [
    {
      "block_id": "block_001",
      "video_id": "abc123",
      "start": "00:05:30",
      "end": "00:08:15",
      "title": "Что такое осознавание",
      "summary": "Краткое описание блока",
      "content": "Полный текст блока...",
      "keywords": ["осознавание", "трансформация"],
      "youtube_link": "https://youtube.com/watch?v=abc123&t=330s",
      "block_type": "concept_explanation",
      "complexity_score": 0.6,
      "graph_entities": [
        {
          "entity_id": "concept_001",
          "name": "осознавание",
          "entity_type": "CONCEPT",
          "normalized_name": "осознавание"
        }
      ],
      "graph_relations": [
        {
          "from_id": "concept_001",
          "to_id": "practice_001",
          "relation_type": "IS_PRACTICE_FOR",
          "explanation": "Медитация является практикой для развития осознавания"
        }
      ]
    }
  ]
}
```

### Ключевые поля

#### document_metadata
- `video_id` — ID видео YouTube
- `source_url` — URL видео
- `title` — название лекции
- `duration_seconds` — длительность в секундах
- `processed_at` — дата обработки

#### blocks[]
- `block_id` — уникальный ID блока
- `video_id` — ID видео
- `start` / `end` — таймкоды начала/конца
- `title` — заголовок блока
- `summary` — краткое описание
- `content` — полный текст блока
- `keywords` — ключевые слова
- `youtube_link` — ссылка с таймкодом
- `block_type` — тип блока (concept_explanation, practice_description, etc.)
- `complexity_score` — оценка сложности (0.0-1.0)

#### graph_entities[]
- `entity_id` — ID сущности
- `name` — имя сущности
- `entity_type` — тип (CONCEPT, PRACTICE, TECHNIQUE, etc.)
- `normalized_name` — нормализованное имя

#### graph_relations[]
- `from_id` / `to_id` — ID узлов связи
- `relation_type` — тип связи (IS_PRACTICE_FOR, REQUIRES, etc.)
- `explanation` — пояснение связи

---

## Процесс загрузки данных

### DataLoader (`bot_agent/data_loader.py`)

```python
# Инициализация
data_loader = DataLoader()
data_loader.load_all_data()

# Структура данных в памяти
data_loader.documents        # List[Document]
data_loader.all_blocks       # List[Block]
data_loader._video_id_to_doc # Dict[str, Document]
data_loader._block_id_to_block # Dict[str, Block]
```

### Шаги загрузки

1. **Поиск файлов**
   ```python
   json_files = config.SAG_FINAL_DIR.glob("**/*.for_vector.json")
   ```

2. **Парсинг каждого файла**
   ```python
   with open(json_path, 'r', encoding='utf-8') as f:
       data = json.load(f)
   ```

3. **Создание объектов**
   ```python
   document = Document(
       video_id=data["document_metadata"]["video_id"],
       source_url=data["document_metadata"]["source_url"],
       title=data["document_metadata"]["title"],
       blocks=[Block(**block_data) for block_data in data["blocks"]]
   )
   ```

4. **Кэширование**
   - Все документы и блоки хранятся в памяти
   - Индексы для быстрого поиска по ID

---

## Использование данных в Bot Agent

### Phase 1: Базовый QA

**Используемые поля**:
- `blocks[].title`
- `blocks[].summary`
- `blocks[].content`
- `blocks[].keywords`
- `blocks[].youtube_link`
- `blocks[].start` / `end`

**Процесс**:
1. TF-IDF поиск по `title + keywords + summary`
2. Выбор Top-K релевантных блоков
3. Формирование контекста для LLM

### Phase 2: SAG-aware QA

**Дополнительные поля**:
- `blocks[].complexity_score`
- `blocks[].block_type`

**Процесс**:
1. Поиск блоков (как в Phase 1)
2. Фильтрация по `complexity_score` в зависимости от уровня пользователя
3. Адаптация ответа под уровень

### Phase 3: Knowledge Graph Powered

**Используемые поля**:
- `blocks[].graph_entities[]`
- `blocks[].graph_relations[]`

**Процесс**:
1. Извлечение концептов из запроса
2. Поиск узлов в Knowledge Graph
3. Поиск связанных практик через `graph_relations`
4. Рекомендация практик на основе графа

### Phase 4: Adaptive QA

**Используемые поля**:
- Все поля Phase 1-3
- История диалога из `.cache_bot_agent/conversations/`

**Процесс**:
1. Загрузка истории пользователя
2. Анализ состояния на основе истории + текущего запроса
3. Построение персонального пути через Knowledge Graph
4. Адаптация ответа под состояние и путь

---

## Knowledge Graph из данных

### Построение графа

```python
# GraphClient загружает граф из всех блоков
graph_client.load_graphs_from_all_documents()

# Структура графа
graph_client.nodes        # Dict[str, GraphNode]
graph_client.edges        # List[GraphEdge]
graph_client.adjacency    # Dict[str, List[str]]
```

### Типы узлов

- **CONCEPT** — абстрактный концепт (осознавание, трансформация)
- **PRACTICE** — практика (медитация, дыхание)
- **TECHNIQUE** — техника (конкретный метод)
- **EXERCISE** — упражнение
- **PATTERN** — паттерн поведения
- **PROCESS_STAGE** — этап процесса

### Типы связей

- **IS_PRACTICE_FOR** — практика для концепта
- **IS_TECHNIQUE_FOR** — техника для концепта
- **REQUIRES** — требует
- **ENABLES** — делает возможным
- **IS_PART_OF** — является частью
- **HAS_PART** — содержит часть
- **RELATED_TO** — связан с
- **PREREQUISITE** — предпосылка

---

## Поток данных в системе

```
voice_bot_pipeline/data/sag_final/
    ↓
[DataLoader.load_all_data()]
    ↓
Парсинг JSON → Document + Block объекты
    ↓
Кэширование в памяти
    ↓
[Retriever] → Поиск блоков
    ↓
[GraphClient] → Построение Knowledge Graph
    ↓
[Bot Agent] → Использование данных для ответов
    ↓
Ответ с источниками (таймкоды, ссылки)
```

---

## Оптимизации

### Кэширование

- **В памяти**: все документы и блоки загружаются один раз при старте
- **На диске**: история диалогов в `.cache_bot_agent/conversations/`

### Индексация

- **По video_id**: быстрый поиск документа по ID видео
- **По block_id**: быстрый поиск блока по ID
- **TF-IDF индекс**: построение при первом запросе

### Ленивая загрузка

- **Knowledge Graph**: загружается при первом использовании
- **История диалога**: загружается при первом запросе пользователя

---

## Навигация

- [Обзор проекта](./overview.md)
- [Архитектура](./architecture.md)
- [SAG v2.0](./sag_v2.md)
- [Knowledge Graph](./knowledge_graph.md)
