<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Гайд для Cursor AI-агента

**Тема:** Доработка первой части пайплайна подготовки базы знаний (SAG v2.0) под масштаб 500+ роликов по 180 минут

Цель: описать конкретные шаги доработки пайплайна так, чтобы агент в Cursor мог по инструкции внести изменения в проект.

***

## 0. Контекст проекта (что уже есть)

В проекте уже реализовано:

1. **Pipeline Orchestrator**
    - `pipeline_orchestrator.py` — оркестрация стадий:
        - Stage 1: загрузка субтитров с YouTube
        - Stage 2: подготовка SAG v2.0 (GPT‑4o‑mini)
        - Stage 3: финализация файла
        - Stage 4: индексация в ChromaDB
2. **SAG v2.0 блоки**
    - Структура блока включает:
        - `title`, `summary`, `keywords`, `content`
        - временные метки `start`, `end`, `youtube_link`
        - базовые метаданные: `speaker`, `block_type`, `emotional_tone`, `conceptual_depth`, `complexity_score`, `contains_practice`
        - `graph_entities` (концепты)
        - `semantic_relationships` (conceptual/causal/practical links — базовые)
3. **Vector DB**
    - ChromaDB с коллекциями:
        - `sag_v2_documents`
        - `sag_v2_blocks`
        - `sag_v2_graph_entities`
4. **Масштабирование**
    - Уже протестировано на нескольких видео (3+)
    - В планах: ~500 роликов по 180 минут реального контента

Задача этого гайда — **углубить семантический слой** и **обеспечить масштабируемость** первой части (подготовка данных) перед массовой загрузкой 500+ роликов.

***

## 1. Общий план доработок

Нужно добавить в **первую часть пайплайна**:

1. **Извлечение информации о безопасности (Safety Extractor)**
Противопоказания, ограничения, когда нужна помощь специалиста.
2. **Извлечение причинно‑следственных цепочек (Causal Chain Extractor)**
Многошаговые процессы: триггер → паттерн → эмоция → поведение → последствия.
3. **Иерархия концептов (Concept Hierarchy Extractor)**
Уровни: root / domain / practice / technique / exercise, связи между ними.
4. **Структурированные кейсы (Case Study Extractor)**
Реальные случаи: ситуация, корневая причина, процесс, результат, выводы.
5. **Предпосылки и последовательность обучения (Prerequisite Extractor)**
Что нужно освоить до сложных практик, логика прогрессии.
6. (Опционально) **Контекстные применения концептов (Application Extractor)**
В каких контекстах используется концепт и как.

Все это интегрируется как **дополнительные поля** в тот же JSON `*.for_vector.json`, который затем индексируется в ChromaDB.

***

## 2. Архитектурные принципы для агента

1. **Не ломать существующий формат SAG v2.0**, а расширять его:
    - Добавляем новые поля в блоки/документы.
    - Не меняем уже используемые ключи.
2. **Все извлечения — отдельные классы/модули**, чтобы:
    - Их можно было тестировать изолированно.
    - Их можно было отключать/включать конфигурацией.
3. **Работа через OpenAI GPT‑4o‑mini**:
    - Использовать `response_format={"type": "json_object"}`.
    - Возвращать строго валидный JSON.
    - Ограничить промпты по размеру (подсовывать текст блока, а не всего видео).
4. **Все новые данные должны быть совместимы с ChromaDB**:
    - Либо как отдельные коллекции (`sag_v2_safety`, `sag_v2_causal_chains` и т.п.),
    - Либо как метаданные внутри `sag_v2_blocks`.

***

## 3. Структура проекта (рекомендованные новые файлы)

Агенту нужно создать/изменить:

### 3.1. Новые модули в `text_processor/`

Создать файлы:

- `text_processor/safety_extractor.py`
- `text_processor/causal_chain_extractor.py`
- `text_processor/concept_hierarchy_extractor.py`
- `text_processor/case_study_extractor.py`
- `text_processor/prerequisite_extractor.py`

Каждый модуль — один класс, одна главная публичная функция.

### 3.2. Обновление основного процессора SAG

Файл:

- `text_processor/sarsekenov_processor.py` (или тот, который отвечает за SAG v2.0 обработку чанков)

Необходимо:

- Импортировать новые экстракторы.
- Добавить вызовы этих экстракторов после базового формирования блока.
- Включить результаты в структуру блока.

***

## 4. Safety Extractor (критично для безопасности)

### 4.1. Цель

Извлекать из текста **противопоказания, ограничения, риски, сигналы для остановки практики, необходимость профессиональной помощи**, если такие вещи явно или неявно проговариваются.

### 4.2. Создание модуля

Файл: `text_processor/safety_extractor.py`

```python
import json
from openai import OpenAI

class SafetyInformationExtractor:
    """
    Извлечение информации о безопасности, ограничениях и противопоказаниях
    для практик и концепций.
    """

    def __init__(self, client: OpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    def extract(self, block_content: str, practice_or_concept_name: str) -> dict:
        """
        Анализирует текст блока и извлекает safety-информацию.

        Возвращает словарь структуры:
        {
          "contraindications": [...],
          "limitations": [...],
          "when_to_stop": [...],
          "when_to_seek_professional_help": [...],
          "notes": [...]
        }
        """
        prompt = f"""
Ты — эксперт по психологии и безопасности психопрактик.

Проанализируй текст ниже, который относится к практике/концепции: "{practice_or_concept_name}".

Тебе нужно извлечь ИСКЛЮЧИТЕЛЬНО информацию о безопасности, если она там есть 
(либо явно, либо по смыслу, даже если не проговорена дословно).

Структура ответа (строгий JSON):

{{
  "contraindications": [
    {{
      "condition": "краткое название состояния, при котором практика противопоказана",
      "reason": "почему эта практика может быть вредна при этом состоянии",
      "alternative": "какие более мягкие или безопасные подходы можно использовать"
    }}
  ],
  "limitations": [
    "ограничение или то, чего практика делать не должна/не может"
  ],
  "when_to_stop": [
    "симптомы или состояния, при которых практику нужно прекратить немедленно"
  ],
  "when_to_seek_professional_help": [
    "описания ситуаций, когда явно нужна помощь психотерапевта/психиатра/специалиста"
  ],
  "notes": [
    "любые дополнительные замечания по безопасности, если есть"
  ]
}}

Если в тексте НЕТ информации по какому-то разделу — верни для него пустой список.

Текст для анализа:
\"\"\"{block_content}\"\"\"        
"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(response.choices[0].message.content)
        except Exception:
            # На всякий случай защита от невалидного JSON
            data = {
                "contraindications": [],
                "limitations": [],
                "when_to_stop": [],
                "when_to_seek_professional_help": [],
                "notes": [],
            }

        # Гарантия наличия всех ключей
        for key in [
            "contraindications",
            "limitations",
            "when_to_stop",
            "when_to_seek_professional_help",
            "notes",
        ]:
            data.setdefault(key, [])

        return data
```


### 4.3. Интеграция в SAG-процессор

В `sarsekenov_processor.py`:

1. Импортировать:
```python
from text_processor.safety_extractor import SafetyInformationExtractor
```

2. В `__init__` или setup метода процессора создать экземпляр:
```python
self.safety_extractor = SafetyInformationExtractor(
    client=self.primary_client,
    model=self.config.get("safety_model", "gpt-4o-mini")
)
```

3. В месте, где уже сформирован `block` (после базового анализа) добавить:
```python
safety_info = self.safety_extractor.extract(
    block_content=block["content"],
    practice_or_concept_name=block.get("title", "не указано")
)

block["safety"] = safety_info
```


***

## 5. Causal Chain Extractor (причинно‑следственные цепочки)

### 5.1. Цель

Для каждого блока извлекать **процессы** в виде последовательности шагов:
событие → активация паттерна → эмоция → поведение → последствия, а также **точки вмешательства** (какие практики где помогают).

### 5.2. Модуль

Файл: `text_processor/causal_chain_extractor.py`

```python
import json
from openai import OpenAI

class CausalChainExtractor:
    """
    Извлечение причинно-следственных цепочек психологических процессов
    и точек вмешательства.
    """

    def __init__(self, client: OpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    def extract(self, block_content: str) -> dict:
        """
        Возвращает структуру вида:
        {
          "processes": [
            {
              "name": "короткое название процесса",
              "steps": [
                {"step": 1, "event": "...", "description": "..."},
                ...
              ],
              "intervention_points": [
                {
                  "after_step": 2,
                  "practice": "метанаблюдение",
                  "effect": "что меняется",
                  "related_concepts": ["осознавание", "паттерны"]
                }
              ]
            }
          ]
        }
        """

        prompt = f"""
Ты — специалист по когнитивно-поведенческим и процессуально-ориентированным подходам.

Проанализируй текст и найди ПСИХОЛОГИЧЕСКИЕ ПРОЦЕССЫ в формате причинно-следственных цепочек.

Для каждого процесса определи:
1. Краткое название процесса (name).
2. Последовательность шагов (steps):
   - step: номер шага (1, 2, 3, ...)
   - event: краткое событие/этап
   - description: более подробное описание
3. Точки вмешательства (intervention_points):
   - after_step: после какого шага можно вмешаться
   - practice: какая практика/инструмент может быть применена (из текста, если упоминается)
   - effect: в чем суть влияния этой практики
   - related_concepts: какие концепции из текста связаны с этой точкой

Формат ответа (строгий JSON):
{{
  "processes": [
    {{
      "name": "краткое название процесса",
      "steps": [
        {{"step": 1, "event": "событие", "description": "описание"}},
        {{"step": 2, "event": "событие", "description": "описание"}}
      ],
      "intervention_points": [
        {{
          "after_step": 1,
          "practice": "название практики",
          "effect": "результат применения",
          "related_concepts": ["концепт1", "концепт2"]
        }}
      ]
    }}
  ]
}}

Если явных процессов нет — верни "processes": [].

Текст:
\"\"\"{block_content}\"\"\"        
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(response.choices[0].message.content)
        except Exception:
            data = {"processes": []}

        data.setdefault("processes", [])
        return data
```


### 5.3. Интеграция в SAG-процессор

В `sarsekenov_processor.py`:

1. Импорт:
```python
from text_processor.causal_chain_extractor import CausalChainExtractor
```

2. Инициализация:
```python
self.causal_extractor = CausalChainExtractor(
    client=self.primary_client,
    model=self.config.get("causal_model", "gpt-4o-mini")
)
```

3. Применение к блоку:
```python
causal_data = self.causal_extractor.extract(
    block_content=block["content"]
)

block["causal_chains"] = causal_data.get("processes", [])
```


***

## 6. Concept Hierarchy Extractor (иерархия концептов)

### 6.1. Цель

Для каждого блока (и/или документа) извлекать **уровень** концепта и его **родительские связи**:
`root / domain / practice / technique / exercise`.

### 6.2. Модуль

Файл: `text_processor/concept_hierarchy_extractor.py`

```python
import json
from openai import OpenAI

class ConceptHierarchyExtractor:
    """
    Извлечение иерархии концептов (root/domain/practice/technique/exercise)
    и их отношений.
    """

    def __init__(self, client: OpenAI, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model

    def extract(self, block_content: str, known_entities: list[str]) -> dict:
        """
        known_entities — список graph_entities уже извлеченных для блока.

        Возвращает:
        {
          "concepts": [
            {
              "name": "осознавание",
              "level": "domain",
              "parent": "нейросталкинг",
              "relationship": "is_core_component_of"
            },
            ...
          ]
        }
        """

        entities_str = ", ".join(known_entities) if known_entities else "нет"

        prompt = f"""
Ты — эксперт по систематизации знаний.

У тебя есть список концептов (graph_entities): [{entities_str}].

Твоя задача — определить ИЕРАРХИЮ этих концептов в контексте текста.

Уровни:
- "root": корневые учения/подходы (например, "нейросталкинг")
- "domain": доменные понятия (например, "осознавание", "трансформация")
- "practice": практики и методы (например, "метанаблюдение")
- "technique": конкретные техники (например, "наблюдение за умом", "ведение дневника")
- "exercise": отдельные упражнения (например, "5 минут наблюдения утром")

Для каждого концепта определи:
- name: название (как в graph_entities или из текста)
- level: один из [root, domain, practice, technique, exercise]
- parent: родительский концепт (или null, если root)
- relationship: тип связи с родителем
    - "is_core_component_of"
    - "is_part_of"
    - "is_technique_for"
    - "enables"
    - "requires"

Формат ответа (строгий JSON):

{{
  "concepts": [
    {{
      "name": "осознавание",
      "level": "domain",
      "parent": "нейросталкинг",
      "relationship": "is_core_component_of"
    }}
  ]
}}

Текст:
\"\"\"{block_content}\"\"\"        
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(response.choices[0].message.content)
        except Exception:
            data = {"concepts": []}

        data.setdefault("concepts", [])
        return data
```


### 6.3. Интеграция

В `sarsekenov_processor.py`:

1. Импорт:
```python
from text_processor.concept_hierarchy_extractor import ConceptHierarchyExtractor
```

2. Инициализация:
```python
self.hierarchy_extractor = ConceptHierarchyExtractor(
    client=self.primary_client,
    model=self.config.get("hierarchy_model", "gpt-4o-mini")
)
```

3. Встроить после формирования `graph_entities`:
```python
hierarchy_data = self.hierarchy_extractor.extract(
    block_content=block["content"],
    known_entities=block.get("graph_entities", [])
)

block["concept_hierarchy"] = hierarchy_data.get("concepts", [])
```


***

## 7. Case Study Extractor (кейсы) и Prerequisite Extractor (предпосылки)

### 7.1. Кратко по кейсам

Файл: `text_processor/case_study_extractor.py`

Извлекаем:

```json
{
  "case_studies": [
    {
      "id": "case_local_1",
      "situation": "...",
      "root_cause": "...",
      "applied_practices": [...],
      "process": ["шаг 1", "шаг 2", ...],
      "outcome": "...",
      "lessons": "...",
      "related_concepts": [...]
    }
  ]
}
```

Интеграция:

```python
block["case_studies"] = case_data.get("case_studies", [])
```


### 7.2. Кратко по предпосылкам

Файл: `text_processor/prerequisite_extractor.py`

Извлекаем:

```json
{
  "prerequisites": [
    {
      "concept": "основа осознавания",
      "level": "beginner",
      "why_needed": "..."
    }
  ],
  "recommended_sequence": [
    "осознавание → метанаблюдение → распознавание паттернов → работа с паттернами"
  ],
  "common_mistakes": ["..."]
}
```

Интеграция:

```python
block["prerequisites"] = prereq_data
```


***

## 8. Валидация новых полей

Добавить/расширить модуль валидации (если уже есть — обновить):

Файл (пример): `text_processor/validator.py`

- Проверять, что:
    - `safety` содержит нужные ключи и списки.
    - `causal_chains` — массив процессов.
    - `concept_hierarchy` — массив с `name`, `level`.
    - `case_studies` и `prerequisites` — корректной формы.

В случае ошибок:

- Логировать предупреждение.
- Оставлять поле пустым, но не падать.

***

## 9. Обновление схемы индексации в VectorIndexer

Файл: `vector_db/vector_indexer.py` (или аналогичный):

1. Дополнительно индексировать новые поля как:
    - Текстовые поля в основную коллекцию `sag_v2_blocks` (например, `safety_notes`, `causal_summary`, `case_summaries`).
    - И/или создавать отдельные коллекции:
        - `sag_v2_causal_chains`
        - `sag_v2_safety`
        - `sag_v2_cases`
        - `sag_v2_concept_hierarchy`
2. Минимальный вариант (быстро внедрить):
    - В `metadatas` блока добавить:
        - `has_safety_warnings: bool`
        - `has_causal_chains: bool`
        - `has_case_studies: bool`
        - `has_prerequisites: bool`
    - Опционально — агрегировать краткие summary в отдельные текстовые поля для поиска.

***

## 10. Конфигурация (config.yaml)

Добавить секцию, чтобы включать/выключать новые извлечения:

```yaml
pipeline:
  sag_v2:
    use_safety_extractor: true
    use_causal_chain_extractor: true
    use_concept_hierarchy_extractor: true
    use_case_study_extractor: true
    use_prerequisite_extractor: true
    models:
      safety: gpt-4o-mini
      causal: gpt-4o-mini
      hierarchy: gpt-4o-mini
      case_study: gpt-4o-mini
      prerequisite: gpt-4o-mini
```

В коде процессора проверять флаги перед вызовом экстракторов.

***

## 11. Порядок работы для агента Cursor

1. **Проанализировать существующий `sarsekenov_processor.py`**:
    - Найти, где формируются `blocks`.
    - Найти, где вызывается OpenAI.
2. **Создать новые файлы**:
    - `safety_extractor.py`
    - `causal_chain_extractor.py`
    - `concept_hierarchy_extractor.py`
    - (опционально) `case_study_extractor.py`, `prerequisite_extractor.py`
3. **Внедрить новые классы в процессор**:
    - Импортировать.
    - Инициализировать в конструкторе/инициализаторе.
    - Вызывать по блокам, с учетом флагов из `config.yaml`.
4. **Обновить валидацию**:
    - Добавить проверку новых полей в валидаторе.
    - Обеспечить устойчивость к невалидному JSON.
5. **Обновить индексатор**:
    - Расширить метаданные блоков.
    - (Опционально) создать новые коллекции для анализа.
6. **Добавить логирование**:
    - Логировать:
        - найденные safety‑данные (есть/нет),
        - количество выявленных процессов,
        - наличие иерархий, кейсов, предпосылок.
7. **Прогнать тест на нескольких видео**:
    - Проверить, что:
        - пайплайн проходит без ошибок,
        - JSON корректен,
        - новые поля реально появляются в `*.for_vector.json`,
        - векторная индексация не ломается.

***

Если нужно, далее можно сделать второй документ именно по **второй части проекта** (бот, персонализация, память и т.д.), но этот гайд полностью посвящен первой части — **глубокой подготовке базы знаний**.

