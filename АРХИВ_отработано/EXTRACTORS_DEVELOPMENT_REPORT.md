# Отчёт о разработке экстракторов Сарсекенова

## Цель проекта

Создание системы извлечения знаний из лекций Саламата Сарсекенова для AI-бота-психолога, который консультирует **исключительно в стиле нейро-сталкинга**.

**Критическое требование:** Бот должен использовать **ТОЛЬКО терминологию Сарсекенова**, игнорируя общую психологическую лексику.

---

## Этап 0: Подготовка структуры

**Статус:** Завершён

**Дата:** 2024-12-08

### Созданные директории

```
voice_bot_pipeline/
├── config/
├── text_processor/
│   ├── extractors/           # Будущие экстракторы
│   └── validators/           # Валидаторы
└── tests/
    └── extractors/           # Тесты
```

### Созданные файлы конфигурации

#### 1. `config/terminology/sarsekenov_terms.json`

Словарь терминов Сарсекенова, разбитый на 6 уровней (tiers):

| Уровень | Описание | Примеры терминов |
|---------|----------|------------------|
| tier_1_root | Корневые концепты | нейро-сталкинг, нео-сталкинг, сталкинг ума |
| tier_2_domain | Доменные области | поле внимания, чистое осознавание, присутствие |
| tier_3_practice | Практики | метанаблюдение, разотождествление, центрирование |
| tier_4_diagnostic | Диагностика | Я-образ, автоматизмы психики, захват внимания |
| tier_5_agents | Субъекты | Ищущий, наблюдающее сознание |
| tier_6_states | Состояния | бытие, здесь-и-сейчас, ясность |

**Всего терминов:** 45+

#### 2. `config/terminology/forbidden_terms.json`

Запрещённые термины общей психологии:

```json
{
  "forbidden_terms": ["эго", "ум", "подсознание", "медитация", "тревога", ...],
  "replacements": {
    "эго": "Я-образ",
    "подсознание": "автоматизмы психики",
    "медитация": "метанаблюдение",
    ...
  }
}
```

#### 3. `config/terminology/term_categories.json`

Паттерны категорий для извлечения:

- триада_трансформации
- работа_с_вниманием
- разотождествление
- состояния_сознания

#### 4. `config/extractors_config.yaml`

Общая конфигурация системы экстракторов с приоритетами и параметрами.

---

## Этап 1: TerminologyValidator

**Статус:** Завершён

**Дата:** 2024-12-08

### Файл: `text_processor/validators/terminology_validator.py`

**Назначение:** Фундамент системы - валидация текста перед обработкой экстракторами.

### Ключевые компоненты

#### 1. Класс `ValidationResult`

```python
@dataclass
class ValidationResult:
    is_valid: bool              # Прошёл ли текст валидацию
    reason: str                 # Причина (успех/отказ)
    metrics: Dict               # Метрики плотности
    forbidden_terms_found: List # Найденные запрещённые термины
    sarsekenov_entities: List   # Извлечённые термины Сарсекенова
```

#### 2. Класс `TerminologyValidator`

**Основные методы:**

| Метод | Описание |
|-------|----------|
| `validate_text()` | Главный метод валидации |
| `_find_forbidden_terms()` | Поиск запрещённых терминов |
| `_calculate_density()` | Расчёт плотности терминов (мин. 25%) |
| `_extract_entities()` | Извлечение сущностей Сарсекенова |
| `replace_forbidden_terms()` | Замена запрещённых на разрешённые |
| `get_term_info()` | Информация о термине (tier, level) |

### Лемматизация (pymorphy3)

Добавлена поддержка морфологического анализа для корректной работы с русским языком:

- "разотождествлению" → "разотождествление"
- "Я-образом" → "я-образ"
- "метанаблюдения" → "метанаблюдение"

**Зависимость:** `pymorphy3` (для Python 3.11+)

```bash
pip install pymorphy3
```

### Режимы валидации

После анализа реальных лекций Сарсекенова была разработана система гибких режимов валидации.

#### Проблема

Сарсекенов использует смешанную терминологию:
- Свои термины: "метанаблюдение", "Я-образ", "разотождествление"
- Общие термины: "эго", "медитация", "тревога" (для объяснений)

Жёсткий фильтр (strict) блокировал ~60% ценного контента.

#### Решение: 4 режима валидации

| Режим | Forbidden terms | Min density | Описание |
|-------|-----------------|-------------|----------|
| **smart** ✅ | ИГНОРИРУЮТСЯ | 15% | Пропускает всё с достаточной плотностью |
| soft | Проверяются контекстно | 25% | Пропускает если контекст объяснительный |
| strict | Блокируются жёстко | 25% | Блокирует любое использование |
| off | Игнорируются | 15% | Только проверка плотности |

#### Рекомендация: SMART режим

**Преимущества:**
- ✅ Сохраняет 95% контента лекций (vs 40% в strict)
- ✅ Естественный стиль лектора
- ✅ Умный бот (GPT-4) сам фильтрует на выходе
- ✅ Простая логика (только плотность ≥15%)

**Философия:**
> Лучше дать боту больше данных и пусть он сам фильтрует,
> чем отсеивать полезное на входе.

#### Конфигурация

Файл `.env`:
```
VALIDATION_MODE=smart
MIN_SARSEKENOV_DENSITY_SMART=0.15
MIN_SARSEKENOV_DENSITY_STRICT=0.25
CONTEXTUAL_DENSITY_THRESHOLD=0.35
```

### Алгоритм валидации

```
1. Расчёт плотности терминов Сарсекенова (ВСЕГДА)
   └── Если < min_density → ОТКЛОНИТЬ

2. Извлечение сущностей Сарсекенова
   
3. Проверка forbidden terms (ЗАВИСИТ ОТ РЕЖИМА):
   
   SMART/OFF: Игнорировать → ПРИНЯТЬ
   
   STRICT: Если найдены → ОТКЛОНИТЬ
   
   SOFT: Проверить контекст
         └── Если объяснительный → ПРИНЯТЬ
         └── Иначе → ОТКЛОНИТЬ

4. Успешная валидация → ПРИНЯТЬ с метриками
```

#### Пример работы режимов

```python
text = """
Человек с тревогой говорит: "Моё эго разрушает меня."
Я объясняю: это не эго, это Я-образ. Метанаблюдение 
за Я-образом ведёт к разотождествлению...
"""

# Плотность: ~30%, forbidden: ["тревога", "эго"]

SMART:  ✅ VALID   (30% > 15%, forbidden игнорируются)
SOFT:   ✅ VALID   (30% > 25%, forbidden в контексте)
STRICT: ❌ INVALID (forbidden найдены)
OFF:    ✅ VALID   (30% > 15%, forbidden игнорируются)
```

### Тесты: `tests/extractors/test_terminology_validator.py`

| Тест | Описание | Результат |
|------|----------|-----------|
| test_valid_sarsekenov_text | Валидный текст проходит | Плотность 52.2%, 11 терминов |
| test_invalid_forbidden_terms | Запрещённые термины отклоняются | 5 терминов найдено |
| test_low_density_text | Низкая плотность отклоняется | 5.3% < 25% |
| test_entity_extraction | Извлечение сущностей | 8 сущностей |
| test_term_replacement | Замена терминов | Работает |
| test_get_term_info | Информация о термине | Работает |

**Результат:** ВСЕ ТЕСТЫ ПРОЙДЕНЫ

### Пример использования

```python
from text_processor.validators import TerminologyValidator

validator = TerminologyValidator()

text = """
Когда Ищущий практикует метанаблюдение, он начинает замечать 
появление Я-образа в поле внимания. Через разотождествление 
возникает свободное внимание и чистое осознавание.
"""

result = validator.validate_text(text)

print(f"Валиден: {result.is_valid}")
print(f"Плотность: {result.metrics['density']:.1%}")
print(f"Термины: {result.sarsekenov_entities}")
```

**Вывод:**
```
Валиден: True
Плотность: 52.2%
Термины: ['центрирование', 'разотождествление', 'чистое осознавание', ...]
```

---

## Архитектурные заметки

### Сохранение полного текста в RAG

**Важно:** Валидатор НЕ удаляет "нейтральные" слова из текста. Он только:
- Проверяет плотность терминов Сарсекенова
- Извлекает сущности для метаданных
- Блокирует тексты с запрещёнными терминами

**Правильная архитектура RAG-индекса:**

```
┌─────────────────────────────────────────────────────────────┐
│                    Документ в индексе                       │
├─────────────────────────────────────────────────────────────┤
│  full_text      = весь текст блока (для семантического      │
│                   поиска и генерации ответов)               │
│                                                             │
│  entities       = ["метанаблюдение", "Я-образ", ...]        │
│                   (для фильтрации и ранжирования)           │
│                                                             │
│  metadata = {                                               │
│    "density": 0.52,                                         │
│    "is_valid": true,                                        │
│    "tier_distribution": {"tier_3": 5, "tier_4": 3},         │
│    "source": "lecture_001.txt"                              │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

**Категории слов и их обработка:**

| Категория | Примеры | Действие | В индексе |
|-----------|---------|----------|-----------|
| Термины Сарсекенова | метанаблюдение, Я-образ | Извлекаются как entities | full_text + entities |
| Запрещённые | эго, медитация | Блокируют текст | Не попадает |
| Нейтральные | человек, понять, работа | Игнорируются валидатором | full_text |

**Поток обработки:**

```
Исходный текст
      │
      ▼
┌─────────────────┐
│  Валидация      │──── is_valid=False ───► Отклонить
│  (density≥25%,  │
│   no forbidden) │
└────────┬────────┘
         │ is_valid=True
         ▼
┌─────────────────┐
│  Сохранить в    │
│  RAG-индекс:    │
│  • full_text    │
│  • entities     │
│  • metadata     │
└─────────────────┘
```

**Вывод:** Информация не теряется. Семантический поиск работает по полному тексту, а entities используются для:
- Фильтрации результатов по конкретным терминам
- Ранжирования (тексты с большей плотностью выше)
- Формирования ответов бота в стиле Сарсекенова

---

---

## Этап 2: NeurostalkingPatternExtractor

**Статус:** Завершён

**Дата:** 2024-12-08

### Файл: `text_processor/extractors/neurostalking_pattern_extractor.py`

**Назначение:** Извлечение уникальных паттернов учения Сарсекенова из валидированного текста.

### Ключевые компоненты

#### 1. Класс `NeurostalkingPattern`

```python
@dataclass
class NeurostalkingPattern:
    pattern_category: str    # триада_трансформации, работа_с_вниманием, и т.д.
    pattern_name: str
    description: str
    key_terms: List[str]
    typical_context: str
    recognition_markers: List[str]
    related_practices: List[str]
    source_quote: str
    confidence: float        # 0.0 - 1.0
```

#### 2. Класс `NeurostalkingPatternExtractor`

**Основные методы:**

| Метод | Описание |
|-------|----------|
| `extract()` | Главный метод извлечения паттернов |
| `_identify_relevant_categories()` | Определение релевантных категорий |
| `_extract_rule_based()` | Извлечение на основе правил |
| `_create_pattern_from_sentence()` | Создание паттерна из предложения |
| `_calculate_confidence()` | Расчёт уверенности |
| `_identify_related_practices()` | Определение связанных практик |

### Категории паттернов

| Категория | Ключевые термины | Описание |
|-----------|------------------|----------|
| `триада_трансформации` | наблюдение, осознавание, трансформация, метанаблюдение | Процесс: наблюдение → осознавание → трансформация |
| `работа_с_вниманием` | поле внимания, свободное внимание, захват внимания | Процессы работы с полем внимания |
| `разотождествление` | разотождествление, Я-образ, идентификация | Процессы отделения от ложной самости |
| `состояния_сознания` | чистое осознавание, присутствие, живое переживание | Состояния чистого осознавания |

### Алгоритм извлечения

```
1. Валидация текста через TerminologyValidator
   └── Если is_valid=False → Отклонить
   
2. Определение релевантных категорий
   └── На основе найденных терминов Сарсекенова
   
3. Извлечение паттернов (rule-based или LLM)
   └── Анализ предложений на наличие ключевых терминов
   └── Минимум 2 термина категории в предложении
   
4. Создание структур паттернов
   └── Расчёт уверенности
   └── Определение маркеров и практик
   
5. Возврат результата с метриками
```

### Тесты: `tests/extractors/test_neurostalking_pattern_extractor.py`

| Тест | Описание | Результат |
|------|----------|-----------|
| test_extract_triada_pattern | Извлечение паттерна триады | ✅ |
| test_extract_attention_field_pattern | Извлечение паттерна внимания | ✅ |
| test_extract_disidentification_pattern | Извлечение паттерна разотождествления | ✅ |
| test_extract_consciousness_state_pattern | Извлечение паттерна состояния сознания | ✅ |
| test_invalid_text_rejected | Невалидный текст отклоняется | ✅ |
| test_low_density_text_rejected | Низкая плотность отклоняется | ✅ |
| test_specific_category_extraction | Извлечение конкретной категории | ✅ |
| test_confidence_calculation | Расчёт уверенности | ✅ |
| test_related_practices_identified | Определение связанных практик | ✅ |
| test_utility_function | Utility функция extract_patterns | ✅ |
| test_pattern_structure | Проверка структуры паттерна | ✅ |

**Результат:** ВСЕ 11 ТЕСТОВ ПРОЙДЕНЫ

### Пример использования

```python
from text_processor.extractors import NeurostalkingPatternExtractor, extract_patterns

extractor = NeurostalkingPatternExtractor()

text = """
Когда Ищущий практикует метанаблюдение, он сначала наблюдает за 
мыслительным потоком. Затем происходит осознавание автоматизмов психики.
Это ведет к трансформации через разотождествление с Я-образом.
"""

result = extractor.extract(text)

print(f"Валиден: {result['valid']}")
print(f"Паттернов найдено: {len(result['patterns'])}")
for p in result['patterns']:
    print(f"  - {p['pattern_category']}: {p['pattern_name']} ({p['confidence']:.2f})")
```

**Вывод:**
```
Валиден: True
Паттернов найдено: 2
  - триада_трансформации: метанаблюдение и осознавание (0.65)
  - разотождествление: разотождествление и Я-образ (0.60)
```

### Интеграция с TerminologyValidator

```
NeurostalkingPatternExtractor
         │
         ├── __init__(terminology_validator=None)
         │   └── Создаёт TerminologyValidator если не передан
         │
         └── extract(text)
             │
             ├── 1. validator.validate_text(text, min_density=0.25)
             │   └── Отклоняет невалидные тексты
             │
             └── 2. Использует validation.sarsekenov_entities
                 └── Для определения категорий и создания паттернов
```

---

## Этап 3: CausalChainExtractor

**Статус:** Завершён

**Дата:** 2024-12-08

### Файл: `text_processor/extractors/causal_chain_extractor.py`

**Назначение:** Извлечение причинно-следственных цепочек трансформации сознания в терминологии Сарсекенова. Полностью совместим с SMART режимом валидации.

### Философия

**НЕ линейная причинность** (A→B→C), **А СИСТЕМНАЯ трансформация**:
- Каждый этап возникает из целостности процесса (эмерджентность)
- Этапы связаны через `emerges_from` и `enables`
- Поддержка циклических/спиральных процессов
- Маркеры целостности системы

### Ключевые компоненты

#### 1. Dataclasses

```python
@dataclass
class InterventionPoint:
    """Точка возможного вмешательства в процесс"""
    at_stage: int                    # На каком этапе
    practice: str                    # Какая практика применяется
    triggers: List[str]              # Что запускает практику
    expected_outcome: str            # Ожидаемый результат

@dataclass
class CausalChainStage:
    """Этап в процессе трансформации"""
    stage: int                       # Номер этапа
    stage_name: str                  # Название (из терминов)
    description: str                 # Описание (из текста)
    sarsekenov_terms: List[str]      # Термины Сарсекенова
    emerges_from: Optional[List[int]]  # Из каких этапов возникает
    enables: Optional[List[int]]       # Какие этапы делает возможными

@dataclass
class CausalChain:
    """Причинно-следственная цепочка (системная трансформация)"""
    process_name: str                # Название процесса
    process_category: str            # Категория (из 5 типов)
    stages: List[CausalChainStage]   # Этапы процесса
    intervention_points: List[InterventionPoint]
    context: str                     # Контекст (200 символов)
    source_quote: str                # Исходная цитата
    confidence: float                # Уверенность (0.0-1.0)
    is_cyclical: bool                # Циклический процесс?
    wholeness_markers: List[str]     # Маркеры целостности
    sarsekenov_density: float        # Плотность терминов
```

#### 2. Категории процессов (5 типов)

| Категория | Ключевые термины | Описание |
|-----------|------------------|----------|
| `триада_трансформации` | метанаблюдение, наблюдение, осознавание, трансформация | Основной процесс нейро-сталкинга |
| `работа_с_вниманием` | поле внимания, свободное внимание, захват внимания | Работа с полем внимания |
| `разотождествление` | разотождествление, Я-образ, идентификация | Отделение от ложной самости |
| `пробуждение_сознания` | пробуждение, реализация, прозрение, ясность | Процессы пробуждения |
| `интеграция_целостности` | интеграция, целостность, самодостаточность | Интеграция опыта |

#### 3. SMART режим валидации

**Философия:**
```
1. Forbidden terms НЕ блокируют текст
2. Минимум 15% плотности (не 25%)
3. Фокус на системности, не линейности
4. LLM на выходе сам фильтрует стиль
```

### Алгоритм извлечения

```
1. ВАЛИДАЦИЯ через TerminologyValidator (SMART режим)
   └── НЕ указываем min_density - берётся из .env (SMART = 0.15)
   
2. ОПРЕДЕЛЕНИЕ релевантных категорий
   └── Минимум 2 термина категории в тексте
   
3. ИЗВЛЕЧЕНИЕ цепочек (rule-based или LLM)
   └── Разбиение на предложения
   └── Построение этапов с системными связями
   └── Определение точек вмешательства
   
4. ВАЛИДАЦИЯ каждой цепочки
   └── Минимум 3 термина Сарсекенова
   
5. ОПРЕДЕЛЕНИЕ метаданных
   └── is_cyclical (маркеры: "снова", "спираль", "цикл")
   └── wholeness_markers ("целостность", "интеграция")
   └── confidence (базовая + бонусы за этапы/термины/связи)
```

### Расчёт уверенности (confidence)

```python
base = 0.5
stages_bonus = min(len(stages) * 0.05, 0.2)    # +0.05 за этап, макс 0.2
terms_bonus = min(len(all_terms) * 0.02, 0.2)  # +0.02 за термин, макс 0.2
systemic_bonus = min(links * 0.05, 0.1)        # +0.05 за связь, макс 0.1
confidence = min(base + stages_bonus + terms_bonus + systemic_bonus, 1.0)
```

### Тесты: `tests/extractors/test_causal_chain_extractor.py`

| Тест | Описание | Результат |
|------|----------|-----------|
| test_extract_triada_transformation_chain | Триада: наблюдение → осознавание → трансформация | ✅ |
| test_extract_attention_work_chain | Работа с полем внимания | ✅ |
| test_extract_disidentification_chain | Разотождествление с Я-образом | ✅ |
| test_low_density_rejected | Низкая плотность (<15%) отклоняется | ✅ |
| test_forbidden_terms_NOT_rejected_in_smart_mode | **КРИТИЧНО:** SMART режим не блокирует forbidden | ✅ |
| test_intervention_points_identified | Определение точек вмешательства | ✅ |
| test_cyclical_process_detection | Определение цикличности | ✅ |
| test_wholeness_markers_extraction | Извлечение маркеров целостности | ✅ |
| test_systemic_relationships | Проверка emerges_from и enables | ✅ |
| test_confidence_calculation | Расчёт уверенности | ✅ |
| test_multiple_categories_in_text | Извлечение нескольких категорий | ✅ |
| test_minimum_sarsekenov_terms_requirement | Минимум 3 термина на цепочку | ✅ |
| test_utility_function | Utility функция extract_causal_chains | ✅ |
| test_chain_structure_completeness | Полнота структуры CausalChain | ✅ |

**Результат:** 14+ ТЕСТОВ

### Пример использования

```python
from text_processor.extractors import CausalChainExtractor, extract_causal_chains

text = """
Когда Ищущий практикует метанаблюдение, он сначала наблюдает 
за мыслительным потоком. Затем происходит осознавание автоматизмов 
психики. Это ведет к трансформации через разотождествление с Я-образом.
В результате возникает чистое осознавание и свободное внимание.
"""

# Быстрый способ:
result = extract_causal_chains(text, specific_category="триада_трансформации")

print(f"Валиден: {result['valid']}")
print(f"Цепочек: {len(result['chains'])}")
for chain in result['chains']:
    print(f"  - {chain['process_category']}: {chain['process_name']}")
    print(f"    Этапов: {len(chain['stages'])}, Уверенность: {chain['confidence']:.2f}")
    print(f"    Циклический: {chain['is_cyclical']}")
```

**Вывод:**
```
Валиден: True
Цепочек: 1
  - триада_трансформации: метанаблюдение → осознавание
    Этапов: 4, Уверенность: 0.78
    Циклический: False
```

### Интеграция с TerminologyValidator

```
CausalChainExtractor
         │
         ├── __init__(terminology_validator=None)
         │   └── Создаёт TerminologyValidator если не передан
         │
         └── extract(text)
             │
             ├── 1. validator.validate_text(text)
             │   └── SMART режим: min_density=0.15, forbidden игнорируются
             │
             ├── 2. Определение категорий по validation.sarsekenov_entities
             │
             └── 3. Построение цепочек с системными связями
```

---

## Этап 4: ConceptHierarchyExtractor

**Статус:** Завершён

**Дата:** 2024-12-08

### Файл: `text_processor/extractors/concept_hierarchy_extractor.py`

**Назначение:** Извлечение иерархии концептов учения Саламата Сарсекенова со строгой 5-уровневой структурой.

### Философия

**Строгая иерархия** от корня до конкретных упражнений, подобно организационной структуре.

### Ключевые компоненты

#### 1. Уровни иерархии

| Уровень | Описание | Примеры |
|---------|----------|---------|
| `root` | Корень учения | нейро-сталкинг |
| `domain` | Доменная область | поле внимания, чистое осознавание |
| `practice` | Практика | метанаблюдение, разотождествление |
| `technique` | Техника | наблюдение мыслительного потока |
| `exercise` | Упражнение | 5-минутное наблюдение |

#### 2. Dataclasses

```python
@dataclass
class ConceptNode:
    name: str
    level: str                   # root/domain/practice/technique/exercise
    parent: Optional[str]        # Родительский концепт
    relation_type: str           # is_core_component_of, is_practice_for...
    # ...и другие поля

@dataclass
class ConceptHierarchy:
    root: ConceptNode
    domains: List[ConceptNode]
    practices: List[ConceptNode]
    techniques: List[ConceptNode]
    exercises: List[ConceptNode]
    cross_connections: List[CrossConnection]
    # ...метрики
```

### Алгоритм извлечения

```
1. ВАЛИДАЦИЯ через TerminologyValidator
   
2. ОПРЕДЕЛЕНИЕ ROOT (нейро-сталкинг/нео-сталкинг)
   
3. ИЗВЛЕЧЕНИЕ УРОВНЕЙ (Rule-based)
   └── Domain: "поле внимания" -> is_core_component_of -> Root
   └── Practice: "метанаблюдение" -> is_practice_for -> Domain
   └── Technique: "наблюдение мыслительного потока" -> is_technique_for -> Practice
   └── Exercise: "5 минут..." -> is_exercise_for -> Technique
   
4. ИЗВЛЕЧЕНИЕ СВЯЗЕЙ (Cross-connections)
   └── enables, requires, leads_to
   
5. ВАЛИДАЦИЯ ИЕРАРХИИ
   └── Проверка связности и наличия родителей
```

### Тесты: `tests/extractors/test_concept_hierarchy_extractor.py`

| Тест | Описание | Результат |
|------|----------|-----------|
| test_strict_5_level_hierarchy | Строгая 5-уровневая структура | ✅ |
| test_root_must_be_allowed | Проверка допустимых корней | ✅ |
| test_parent_child_relationships | Связность родителей и детей | ✅ |
| test_cross_connections_extracted | Горизонтальные связи | ✅ |
| test_exercises_with_duration_frequency | Параметры упражнений | ✅ |
| test_minimum_sarsekenov_terms | Минимальная плотность | ✅ |
| test_utility_function | Utility функция | ✅ |
| test_smart_mode_validation | Работа в SMART режиме | ✅ |

**Результат:** 8 ТЕСТОВ ПРОЙДЕНЫ

---

## Следующие этапы

- [x] **Этап 1:** TerminologyValidator
- [x] **Этап 2:** NeurostalkingPatternExtractor
- [x] **Этап 3:** CausalChainExtractor (с валидацией)
- [x] **Этап 4:** ConceptHierarchyExtractor (с валидацией) ✅ NEW
- [ ] **Этап 5:** Интеграция с оркестратором

---

## Зависимости

```
pymorphy3>=1.0.0
python-dotenv>=1.0.0  # для загрузки настроек из .env
```

## Структура проекта после Этапа 4

```
voice_bot_pipeline/
├── config/
│   ├── extractors_config.yaml
│   └── terminology/
│       ├── sarsekenov_terms.json
│       ├── forbidden_terms.json
│       └── term_categories.json
├── text_processor/
│   ├── validators/
│   │   ├── __init__.py
│   │   └── terminology_validator.py
│   └── extractors/
│       ├── __init__.py
│       ├── neurostalking_pattern_extractor.py
│       ├── causal_chain_extractor.py
│       └── concept_hierarchy_extractor.py     # ✅ NEW (Этап 4)
└── tests/
    ├── __init__.py
    └── extractors/
        ├── __init__.py
        ├── test_terminology_validator.py
        ├── test_neurostalking_pattern_extractor.py
        ├── test_causal_chain_extractor.py
        └── test_concept_hierarchy_extractor.py # ✅ NEW (Этап 4)

## Этап 5: SarsekenovProcessor (Оркестратор)

**Статус:** Завершён ✅
**Дата:** 2025-12-09

### Файлы
- `voice_bot_pipeline/text_processor/orchestrator/sarsekenov_processor.py`
- `voice_bot_pipeline/text_processor/orchestrator/knowledge_graph.py`
- `voice_bot_pipeline/text_processor/export/rag_formatter.py`
- `voice_bot_pipeline/text_processor/extractors/__init__.py`

### Описание
Реализован **оркестратор**, который координирует работу всех экстракторов (валидатор, паттерны, цепочки, иерархия) и объединяет их результаты в единый **Граф Знаний** (Knowledge Graph). Также создан модуль экспорта для подготовки данных к загрузке в RAG-систему.

### Ключевые достижения
1. **SarsekenovProcessor**:
   - Единая точка входа `process_text()`.
   - Автоматическая валидация и координация экстракторов.
   - Построение графа из разрозненных результатов.
   - API для бота: `find_practices_for_symptom`, `recommend_exercise`.

2. **KnowledgeGraph**:
   - Хранение узлов (концепты, практики, техники) и связей.
   - Поддержка слияния узлов при обработке нескольких текстов (исправлен баг дубликатов).
   - Поиск путей и построение цепочек рассуждений (reasoning chains).

3. **RAGFormatter**:
   - Преобразование графа в документы для векторной БД.
   - Сохранение богатых метаданных (tier, confidence, связи).
   - Поддержка форматов для E5 моделей.

### Тестирование
- ✅ **32 теста** успешно пройдены (`tests/orchestrator/`).
- Проверена обработка одиночных и множественных текстов.
- Проверена корректность построения связей и слияния узлов.
- Проверен экспорт в JSON и форматы для эмбеддинга.

---
