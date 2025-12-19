# SAG v2.0 + Семантика

## Навигация

- [Назад к README](../README.md)
- [Обзор проекта](./overview.md)
- [Поток данных](./data_flow.md)
- [Knowledge Graph](./knowledge_graph.md)

---

## Описание и назначение

**Назначение документа**: Описать использование SAG v2.0 данных в Bot Psychologist, семантический анализ и адаптацию по уровням.

**Для кого**: Разработчики, работающие с семантикой и адаптацией ответов.

**Что содержит**:
- SAG v2.0 структура данных
- Семантический анализ запросов
- Адаптация по уровням пользователя
- Использование complexity_score

---

## SAG v2.0 в Bot Psychologist

### Что такое SAG v2.0

**SAG (Structured Adaptive Generation) v2.0** — структурированный формат данных из `voice_bot_pipeline`, содержащий:

- Семантические блоки лекций
- Метаданные блоков (таймкоды, сложность)
- Граф-сущности (концепты, практики)
- Связи между сущностями

### Использование в Bot Agent

Bot Psychologist использует SAG v2.0 данные для:

1. **Поиска релевантных блоков** — TF-IDF по title/keywords/summary
2. **Семантического анализа** — извлечение концептов из запросов
3. **Адаптации по уровню** — фильтрация по complexity_score
4. **Knowledge Graph** — построение графа из graph_entities/graph_relations

---

## Семантический анализ

### SemanticAnalyzer (`bot_agent/semantic_analyzer.py`)

**Назначение**: Извлечение ключевых концептов из пользовательских запросов.

**Процесс**:

1. **Извлечение концептов**
   ```python
   concepts = semantic_analyzer.extract_concepts(query)
   # ["осознавание", "трансформация", "медитация"]
   ```

2. **Анализ связей**
   ```python
   connections = semantic_analyzer.find_connections(concepts)
   # Связи между концептами в Knowledge Graph
   ```

3. **Определение тематической области**
   ```python
   domain = semantic_analyzer.identify_domain(concepts)
   # "практики", "концепты", "техники"
   ```

### Использование концептов

- **Поиск в Knowledge Graph**: поиск узлов по именам концептов
- **Рекомендация практик**: поиск практик для концептов через граф
- **Фильтрация блоков**: поиск блоков, содержащих концепты

---

## Адаптация по уровням пользователя

### UserLevelAdapter (`bot_agent/user_level_adapter.py`)

**Уровни пользователя**:

- **BEGINNER** — новичок, только начинает изучать
- **INTERMEDIATE** — средний уровень, уже знаком с основами
- **ADVANCED** — продвинутый, глубокое понимание

### Использование complexity_score

Каждый блок имеет `complexity_score` (0.0-1.0):

- **0.0-0.3** — простой материал (для BEGINNER)
- **0.3-0.7** — средний материал (для INTERMEDIATE)
- **0.7-1.0** — сложный материал (для ADVANCED)

**Фильтрация блоков**:

```python
# BEGINNER: только простые блоки
filtered_blocks = [b for b in blocks if b.complexity_score <= 0.4]

# INTERMEDIATE: средние блоки
filtered_blocks = [b for b in blocks if 0.3 <= b.complexity_score <= 0.7]

# ADVANCED: все блоки
filtered_blocks = blocks
```

### Адаптация ответов

**BEGINNER**:
- Простые объяснения
- Меньше терминов
- Больше примеров
- Пошаговые инструкции

**INTERMEDIATE**:
- Баланс простоты и глубины
- Умеренное использование терминов
- Связи между концептами

**ADVANCED**:
- Глубокие объяснения
- Использование терминологии
- Сложные связи и паттерны
- Продвинутые практики

---

## Типы блоков (block_type)

### Доступные типы

- **concept_explanation** — объяснение концепта
- **practice_description** — описание практики
- **technique_instruction** — инструкция по технике
- **example_case** — пример/кейс
- **theory_background** — теоретическая основа
- **warning_note** — предупреждение/замечание

### Использование в поиске

```python
# Фильтрация по типу блока
if user_question_about_practice:
    blocks = [b for b in blocks if b.block_type == "practice_description"]
```

---

## Граф-сущности в SAG v2.0

### Структура graph_entities

```json
{
  "graph_entities": [
    {
      "entity_id": "concept_001",
      "name": "осознавание",
      "entity_type": "CONCEPT",
      "normalized_name": "осознавание"
    }
  ]
}
```

### Типы сущностей

- **CONCEPT** — концепт (осознавание, трансформация)
- **PRACTICE** — практика (медитация, дыхание)
- **TECHNIQUE** — техника (конкретный метод)
- **EXERCISE** — упражнение
- **PATTERN** — паттерн поведения
- **PROCESS_STAGE** — этап процесса

### Использование в Bot Agent

1. **Извлечение из блоков**: все `graph_entities` из всех блоков собираются в Knowledge Graph
2. **Поиск по имени**: поиск узлов в графе по именам сущностей
3. **Рекомендация практик**: поиск практик для концептов через связи

---

## Связи в SAG v2.0

### Структура graph_relations

```json
{
  "graph_relations": [
    {
      "from_id": "concept_001",
      "to_id": "practice_001",
      "relation_type": "IS_PRACTICE_FOR",
      "explanation": "Медитация является практикой для развития осознавания"
    }
  ]
}
```

### Типы связей

- **IS_PRACTICE_FOR** — практика для концепта
- **IS_TECHNIQUE_FOR** — техника для концепта
- **REQUIRES** — требует
- **ENABLES** — делает возможным
- **IS_PART_OF** — является частью
- **HAS_PART** — содержит часть
- **RELATED_TO** — связан с
- **PREREQUISITE** — предпосылка

### Использование в Bot Agent

1. **Построение графа**: все `graph_relations` собираются в Knowledge Graph
2. **Поиск путей**: поиск путей между узлами через связи
3. **Рекомендация практик**: поиск практик через связи типа IS_PRACTICE_FOR

---

## Интеграция с Knowledge Graph

### Загрузка графа из SAG v2.0

```python
# GraphClient загружает граф из всех блоков
graph_client.load_graphs_from_all_documents()

# Процесс:
# 1. Проход по всем блокам
# 2. Извлечение graph_entities → узлы графа
# 3. Извлечение graph_relations → связи графа
# 4. Построение adjacency списка для быстрого поиска
```

### Статистика графа

После загрузки граф содержит:
- **95 узлов** (концепты, практики, техники)
- **2182 связи** между узлами
- **6 типов узлов**
- **8+ типов связей**

---

## Примеры использования

### Пример 1: Поиск блоков по концепту

```python
# Запрос пользователя
query = "Что такое осознавание?"

# Семантический анализ
concepts = semantic_analyzer.extract_concepts(query)
# ["осознавание"]

# Поиск блоков, содержащих концепт
blocks = [b for b in all_blocks 
          if any(e["name"] == "осознавание" 
                 for e in b.graph_entities)]
```

### Пример 2: Адаптация по уровню

```python
# BEGINNER пользователь
user_level = UserLevel.BEGINNER

# Фильтрация блоков по complexity_score
filtered_blocks = [
    b for b in blocks 
    if b.complexity_score <= 0.4
]

# Адаптация ответа
answer = llm_answerer.generate_answer(
    query, 
    filtered_blocks,
    adaptation_level="beginner"
)
```

### Пример 3: Рекомендация практик через граф

```python
# Извлечение концепта
concept = "осознавание"

# Поиск практик через граф
practices = graph_client.find_practices_for_concept(concept)
# ["медитация", "дыхательные практики"]

# Рекомендация
recommendation = practices_recommender.recommend(
    practices, 
    user_level=UserLevel.BEGINNER
)
```

---

## Навигация

- [Обзор проекта](./overview.md)
- [Поток данных](./data_flow.md)
- [Knowledge Graph](./knowledge_graph.md)
- [Bot Agent](./bot_agent.md)
