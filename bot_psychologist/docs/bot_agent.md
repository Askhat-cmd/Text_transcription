# Bot Agent — Состояния, Логика, Компоненты

## Навигация

- [Назад к README](../README.md)
- [Обзор проекта](./overview.md)
- [Архитектура](./architecture.md)
- [Knowledge Graph](./knowledge_graph.md)

---

## Описание и назначение

**Назначение документа**: Полное описание Bot Agent, его компонентов, логики работы, состояний пользователя и персональных путей.

**Для кого**: Разработчики, работающие с Bot Agent, Phase 1-4.

**Что содержит**:
- Компоненты Bot Agent
- Логика работы Phase 1-4
- Состояния пользователя (10 состояний)
- Память диалога
- Персональные пути трансформации

---

## Компоненты Bot Agent

### Core Components

#### DataLoader (`data_loader.py`)
Загрузка и кэширование данных из `voice_bot_pipeline`.

**Функции**:
- Загрузка всех `*.for_vector.json` файлов
- Парсинг блоков и метаданных
- Кэширование в памяти
- Индексация по ID

#### Retriever (`retriever.py`)
Поиск релевантных блоков на основе TF-IDF.

**Функции**:
- Построение TF-IDF индекса
- Поиск Top-K релевантных блоков
- Фильтрация по минимальному порогу релевантности

#### LLMAnswerer (`llm_answerer.py`)
Генерация ответов через OpenAI API.

**Функции**:
- Формирование системного промпта
- Сбор контекста из блоков
- Генерация ответа через GPT
- Обработка ошибок API

### Phase-Specific Components

#### UserLevelAdapter (`user_level_adapter.py`) — Phase 2
Адаптация ответов по уровню пользователя.

**Уровни**:
- BEGINNER — новичок
- INTERMEDIATE — средний уровень
- ADVANCED — продвинутый

**Функции**:
- Определение уровня пользователя
- Фильтрация блоков по `complexity_score`
- Адаптация ответов под уровень

#### SemanticAnalyzer (`semantic_analyzer.py`) — Phase 2
Семантический анализ запросов.

**Функции**:
- Извлечение ключевых концептов
- Анализ связей между концептами
- Определение тематической области

#### GraphClient (`graph_client.py`) — Phase 3
Работа с Knowledge Graph.

**Функции**:
- Загрузка графа из блоков
- Поиск узлов и связей
- Поиск путей между узлами
- Рекомендация практик

#### PracticesRecommender (`practices_recommender.py`) — Phase 3
Рекомендация практик через граф.

**Функции**:
- Поиск практик для концептов
- Фильтрация по уровню пользователя
- Ранжирование практик

#### StateClassifier (`state_classifier.py`) — Phase 4
Классификация состояния пользователя.

**Функции**:
- Определение состояния (10 состояний)
- Анализ эмоционального тона
- Определение глубины запроса
- Рекомендации для состояния

#### ConversationMemory (`conversation_memory.py`) — Phase 4
Долгосрочная память диалога.

**Функции**:
- Хранение истории диалога
- Отслеживание интересов
- Отслеживание вызовов и прорывов
- Персистентное хранилище (JSON)

#### PathBuilder (`path_builder.py`) — Phase 4
Построение персональных путей трансформации.

**Функции**:
- Построение пути от текущего к целевому состоянию
- Интеграция с Knowledge Graph
- Рекомендация практик для каждого шага
- Адаптация под уровень пользователя

---

## Phase 1: Базовый QA

### Компоненты

- **DataLoader**: загрузка данных
- **Retriever**: TF-IDF поиск
- **LLMAnswerer**: генерация ответов

### Логика работы

```
1. Пользовательский вопрос
   ↓
2. [Retriever] → TF-IDF поиск → Top-K блоков
   ↓
3. [LLMAnswerer] → Формирование промпта → OpenAI API
   ↓
4. Ответ с источниками (таймкоды, ссылки)
```

### Функция: `answer_question_basic(query: str)`

**Входные данные**:
- `query`: вопрос пользователя

**Выходные данные**:
```python
{
    "status": "success",
    "answer": "Ответ на вопрос...",
    "sources": [
        {
            "block_id": "block_001",
            "title": "Что такое осознавание",
            "youtube_link": "https://youtube.com/watch?v=abc123&t=330s",
            "start": "00:05:30",
            "end": "00:08:15"
        }
    ],
    "concepts": ["осознавание"],
    "processing_time_seconds": 2.5
}
```

---

## Phase 2: SAG-aware QA

### Компоненты

- Все компоненты Phase 1
- **UserLevelAdapter**: адаптация по уровню
- **SemanticAnalyzer**: семантический анализ

### Логика работы

```
1. Пользовательский вопрос + уровень пользователя
   ↓
2. [SemanticAnalyzer] → Извлечение концептов
   ↓
3. [Retriever] → Поиск блоков
   ↓
4. [UserLevelAdapter] → Фильтрация по complexity_score
   ↓
5. [LLMAnswerer] → Адаптированный ответ
   ↓
6. Ответ с учётом уровня пользователя
```

### Функция: `answer_question_sag_aware(query: str, user_level: str)`

**Входные данные**:
- `query`: вопрос пользователя
- `user_level`: "beginner" | "intermediate" | "advanced"

**Выходные данные**:
```python
{
    "status": "success",
    "answer": "Адаптированный ответ...",
    "sources": [...],
    "concepts": [...],
    "user_level": "beginner",
    "complexity_filter": "0.0-0.4",
    "metadata": {
        "semantic_analysis": {
            "concepts": ["осознавание"],
            "domain": "concepts"
        }
    }
}
```

---

## Phase 3: Knowledge Graph Powered QA

### Компоненты

- Все компоненты Phase 1-2
- **GraphClient**: работа с графом
- **PracticesRecommender**: рекомендация практик

### Логика работы

```
1. Пользовательский вопрос
   ↓
2. [SemanticAnalyzer] → Извлечение концептов
   ↓
3. [GraphClient] → Поиск узлов в графе
   ↓
4. [GraphClient] → Поиск практик через IS_PRACTICE_FOR
   ↓
5. [PracticesRecommender] → Рекомендация практик
   ↓
6. [Retriever] → Поиск блоков с практиками
   ↓
7. [LLMAnswerer] → Ответ с практиками из графа
```

### Функция: `answer_question_graph_powered(query: str, user_level: str)`

**Входные данные**:
- `query`: вопрос пользователя
- `user_level`: уровень пользователя

**Выходные данные**:
```python
{
    "status": "success",
    "answer": "Ответ с практиками...",
    "sources": [...],
    "concepts": [...],
    "practices": [
        {
            "name": "медитация",
            "description": "Практика развития осознавания",
            "techniques": ["дыхание", "сканирование тела"]
        }
    ],
    "metadata": {
        "graph_nodes_used": 5,
        "graph_edges_used": 12
    }
}
```

---

## Phase 4: Adaptive QA

### Компоненты

- Все компоненты Phase 1-3
- **StateClassifier**: классификация состояний
- **ConversationMemory**: память диалога
- **PathBuilder**: построение путей

### Логика работы

```
1. Пользовательский вопрос + user_id
   ↓
2. [ConversationMemory] → Загрузка истории диалога
   ↓
3. [StateClassifier] → Анализ состояния (10 состояний)
   ↓
4. [SemanticAnalyzer] → Извлечение концептов
   ↓
5. [GraphClient] → Поиск в Knowledge Graph
   ↓
6. [PathBuilder] → Построение персонального пути
   ↓
7. [Retriever] → Поиск релевантных блоков
   ↓
8. [LLMAnswerer] → Адаптированный ответ с учётом состояния
   ↓
9. Ответ + анализ состояния + путь трансформации
   ↓
10. [ConversationMemory] → Сохранение оборота диалога
```

### Функция: `answer_question_adaptive(query: str, user_id: str, user_level: str)`

**Входные данные**:
- `query`: вопрос пользователя
- `user_id`: ID пользователя
- `user_level`: уровень пользователя

**Выходные данные**:
```python
{
    "status": "success",
    "answer": "Адаптированный ответ...",
    "state_analysis": {
        "primary_state": "curious",
        "confidence": 0.85,
        "emotional_tone": "contemplative",
        "depth": "intermediate",
        "recommendations": [
            "Изучить базовые концепты осознавания",
            "Начать с простых практик медитации"
        ]
    },
    "path_recommendation": {
        "current_state": "curious",
        "target_state": "integrated",
        "key_focus": "развитие базового осознавания",
        "steps_count": 5,
        "total_duration_weeks": 8,
        "first_step": {
            "step_number": 1,
            "title": "Развитие базового осознавания",
            "duration_weeks": 2,
            "practices": ["медитация", "дыхательные практики"],
            "key_concepts": ["осознавание", "внимание"]
        }
    },
    "feedback_prompt": "Был ли этот ответ полезен?",
    "sources": [...],
    "concepts": [...],
    "conversation_context": "Пользователь интересуется осознаванием..."
}
```

---

## Состояния пользователя (10 состояний)

### UserState Enum

```python
class UserState(Enum):
    UNAWARE = "unaware"              # Не осознает проблему
    CURIOUS = "curious"              # Любопытство, интерес
    OVERWHELMED = "overwhelmed"      # Перегружен информацией
    RESISTANT = "resistant"          # Сопротивление
    CONFUSED = "confused"            # Запутанность
    COMMITTED = "committed"          # Готов к работе
    PRACTICING = "practicing"        # Практикует
    STAGNANT = "stagnant"            # Застой, плато
    BREAKTHROUGH = "breakthrough"    # Прорыв
    INTEGRATED = "integrated"        # Интегрировал знание
```

### Прогрессия состояний

```
UNAWARE → CURIOUS → CONFUSED → OVERWHELMED → RESISTANT
    ↓
COMMITTED → PRACTICING → STAGNANT → BREAKTHROUGH → INTEGRATED
```

### Классификация состояний

**StateClassifier** использует:

1. **Keyword-based анализ**: поиск ключевых слов в запросе
2. **LLM анализ**: анализ через GPT для точности
3. **История диалога**: учёт предыдущих состояний

**Примеры индикаторов**:

- **UNAWARE**: "что такое", "не понимаю", "первый раз"
- **CURIOUS**: "интересно", "хочу узнать", "расскажи подробнее"
- **OVERWHELMED**: "слишком много", "не могу понять", "запутался"
- **RESISTANT**: "не верю", "не согласен", "сомневаюсь"
- **CONFUSED**: "не понял", "противоречит", "не вижу связи"
- **COMMITTED**: "готов", "хочу", "начинаю", "буду"
- **PRACTICING**: "пробую", "делаю", "практикую"
- **STAGNANT**: "не продвигаюсь", "застрял", "нет прогресса"
- **BREAKTHROUGH**: "понял", "инсайт", "прорыв"
- **INTEGRATED**: "применил", "работает", "интегрировал"

---

## Память диалога

### ConversationMemory (`conversation_memory.py`)

**Структура**:

```python
class ConversationMemory:
    user_id: str
    turns: List[ConversationTurn]  # История диалога
    metadata: Dict                  # Метаданные (интересы, вызовы)
```

**ConversationTurn**:

```python
@dataclass
class ConversationTurn:
    timestamp: str
    user_input: str
    user_state: Optional[str]
    bot_response: Optional[str]
    blocks_used: int
    concepts: List[str]
    user_feedback: Optional[str]  # positive/negative/neutral
    user_rating: Optional[int]     # 1-5
```

**Хранение**:
- Файл: `.cache_bot_agent/conversations/{user_id}.json`
- Формат: JSON

**Функции**:
- `add_turn()` — добавить оборот диалога
- `get_last_turns(n)` — получить последние N оборотов
- `get_summary()` — получить сводку (интересы, вызовы, прорывы)
- `add_feedback()` — добавить обратную связь

---

## Персональные пути трансформации

### PathBuilder (`path_builder.py`)

**Назначение**: Построение персональных путей от текущего состояния к целевому.

**Процесс**:

1. **Определение текущего состояния** через StateClassifier
2. **Определение целевого состояния** (обычно INTEGRATED)
3. **Поиск пути** через Knowledge Graph
4. **Рекомендация практик** для каждого шага
5. **Адаптация** под уровень пользователя

**Структура пути**:

```python
PersonalTransformationPath(
    current_state=UserState.CURIOUS,
    target_state=UserState.INTEGRATED,
    path_steps=[
        TransformationPathStep(
            step_number=1,
            title="Развитие базового осознавания",
            duration_weeks=2,
            practices=["медитация", "дыхательные практики"],
            key_concepts=["осознавание", "внимание"],
            expected_outcomes=["понимание основ осознавания"],
            focus_areas=["развитие внимания"],
            warning_signs=["перегрузка информацией"]
        ),
        # ...
    ],
    total_duration_weeks=8,
    key_focus="развитие базового осознавания"
)
```

**Интеграция с Knowledge Graph**:

- Поиск практик через граф (IS_PRACTICE_FOR)
- Построение цепочек через связи (REQUIRES, ENABLES)
- Определение предпосылок (PREREQUISITE)

---

## Примеры использования

### Пример 1: Базовый QA

```python
from bot_agent import answer_question_basic

result = answer_question_basic("Что такое осознавание?")
print(result["answer"])
# "Осознавание — это способность наблюдать за своими мыслями..."
```

### Пример 2: SAG-aware QA

```python
from bot_agent import answer_question_sag_aware

result = answer_question_sag_aware(
    "Как развить осознавание?",
    user_level="beginner"
)
print(result["answer"])
# Адаптированный ответ для новичка...
```

### Пример 3: Graph-powered QA

```python
from bot_agent import answer_question_graph_powered

result = answer_question_graph_powered(
    "Какие практики помогают развить осознавание?",
    user_level="intermediate"
)
print(result["practices"])
# [{"name": "медитация", ...}, {"name": "дыхательные практики", ...}]
```

### Пример 4: Adaptive QA

```python
from bot_agent import answer_question_adaptive

result = answer_question_adaptive(
    "Хочу начать практиковать осознавание",
    user_id="user_123",
    user_level="beginner"
)
print(result["state_analysis"]["primary_state"])
# "committed"
print(result["path_recommendation"]["first_step"]["title"])
# "Развитие базового осознавания"
```

---

## Навигация

- [Обзор проекта](./overview.md)
- [Архитектура](./architecture.md)
- [Knowledge Graph](./knowledge_graph.md)
- [REST API](./api.md)
