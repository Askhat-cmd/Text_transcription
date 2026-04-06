# PRD 11.0 — Neo MindBot: Полная миграция Legacy → Neo Runtime

**Статус:** ACTIVE  
**Версия:** 11.0  
**Дата:** 06.04.2026  
**Репозиторий:** github.com/Askhat-cmd/Text_transcription / bot_psychologist  
**Контекст:** Продолжение миграции, начатой в PRD 10.0. Цель — полностью завершить переход на Neo-архитектуру, устранив все legacy-зависимости, SD-наследие и избыточные маршрутизационные слои.

---

## 0. Контекст и цель

### 0.1 Предыстория

Neo MindBot — AI-психологический Telegram-бот, работающий через API LLM (GPT-4o-mini / GPT-5-mini). Проект прошёл три архитектурных поколения:

1. **Поколение 1 (Graph-era):** Монолит на базе граф-структуры, ориентированный на единственного автора (Саламат Сарсекенов). Избыточная схема сущностей, пригодная только для бота-библиотекаря.
2. **Поколение 2 (SD-era):** Переход к мультиавторной базе, классификация пользователей по Спиральной динамике (SD) Эрла Грейвза. Итог — сложная, запутанная, конкурирующая система инструкций; SD-фильтрация знаний и SD-адаптация ответов давали искажённые результаты при хорошей модели.
3. **Поколение 3 (Neo-era, PRD 10.x):** Переход к архитектуре бота «X» — единый prompt stack с приоритетом `AA → A → Core → Diag → Method → Output`, state-model на базе `HYPER/WINDOW/HYPO`, 6 функций запроса, JSON memory snapshot, библиотека практик с 3 каналами и 7-дневными треками.

Фазы 1–10 PRD 10.0 завершены. Однако в репозитории по-прежнему присутствуют legacy-файлы, не удалённые из рабочего runtime: SD-промты, SD-классификатор, `user_level_adapter`, тройная структура `DecisionGate`, 10-state модель пользователя, старые pipeline-файлы и конкурирующие prompt-фрагменты.

### 0.2 Цель PRD 11.0

Провести **финальную, необратимую миграцию** кодовой базы: удалить все legacy-компоненты из активного runtime, выровнять архитектуру под Neo-канон, обеспечить прохождение полного acceptance-теста без единого обращения к SD, `user_level_adapter` или множественным routing-шлюзам.

**Definition of Done:**
- SD-классификатор не задействован ни в одном активном code path
- `user_level_adapter` полностью выведен из pipeline
- Активный routing — один `DecisionGate` с одним LLM-решением
- State-layer использует исключительно `HYPER/WINDOW/HYPO` + 6 функций запроса
- Prompt stack строго соответствует блокам `AA / A / Core / Diag / Method / Output`
- Memory snapshot содержит только Neo-поля
- Все legacy-файлы перемещены в `legacy/` или удалены
- 100% acceptance-тестов проходят на Neo-ветке

---

## 1. Архитектурная цель

### 1.1 Целевой Neo Pipeline

```
User Input (Telegram)
    │
    ▼
[AA Safety Layer]  ← абсолютный приоритет, блокирует до любой логики
    │
    ▼
[A Seasonal Filter]  ← Spring / Summer / Autumn / Winter контекст
    │
    ▼
[Mode Detector]  ← informational | coaching | crisis
    │
    ▼
[State Classifier]  ← HYPER / WINDOW / HYPO + request_function (6 типов)
    │
    ▼
[Hybrid Query Builder]  ← формирует поисковый запрос к Bot_data_base
    │
    ▼
[Retriever]  ← Bot_data_base HTTP API, без SD-фильтрации
    │
    ▼
[VoyageReranker]  ← один проход rerank
    │
    ▼
[DecisionGate]  ← один LLM-вызов → routing_result
    │
    ▼
[Response Generator]  ← Reflective Method (4 шага) + Practice Engine
    │
    ▼
[Output Validator]  ← Telegram HTML, Anti-Bland, Pre-Send Checklist
    │
    ▼
[Memory Updater]  ← laststatesnapshot + currentsummary + dialogcache
    │
    ▼
User Output (Telegram HTML)
```

### 1.2 Целевой Prompt Stack

```
[AA]  safety_aa.txt          ← Safety Rules + Psychological Boundaries
[A]   seasonal_a.txt         ← Seasonal Filter + Anti-Bland Rule + Emoji Rule
[Core] core_identity.txt     ← Identity / Mission / Persona
[Diag] diagnostic_algorithm.txt  ← 5-шаговый алгоритм диагностики
[Method] reflective_method.txt   ← Reflective Method 4 шага
[Proc]  procedural_scripts.txt   ← Workflow Scripts, CLEAR, if-then
[Out]   output_layer.txt     ← Telegram HTML Strict Mode, Pre-Send Checklist
```

Один master prompt собирается последовательно из этих блоков. Никаких SD-промтов, никаких level-промтов, никаких конкурирующих инструкций.

### 1.3 Целевая State-модель

```json
{
  "user_id": 123456,
  "session_timestamp": "ISO8601",
  "diagnostics": {
    "nervous_system_state": "window | hyper | hypo",
    "request_function": "discharge | understand | solution | validation | explore | contact",
    "distance_to_experience": "reactive | observer | meta",
    "dominant_part": "critic | protector | avoider | wounded_child | explorer | self",
    "active_quadrant": "i | it | we | its",
    "core_theme": "string"
  },
  "engagement": {
    "active_track": null,
    "last_practice_offered": null,
    "last_practice_channel": "body | thinking | action | null"
  },
  "last_state_snapshot": {},
  "current_summary": "string (max 30 предложений)",
  "insights_log": [],
  "system_flags": {
    "interaction_mode": "coaching | informational | crisis",
    "seasonal_filter": "spring | summer | autumn | winter",
    "communication_mode": "empathic | technical | minimal",
    "requires_context_continuity": true
  }
}
```

---

## 2. Legacy Inventory — Полная карта удаления

### 2.1 Файлы для архивирования (→ `legacy/`)

| Файл | Причина | Зависимости |
|------|---------|-------------|
| `bot_agent/sd_classifier.py` | SD-классификатор — центральный legacy-компонент | Импортируется в `answer_adaptive.py`, `runtime_config.py` |
| `bot_agent/user_level_adapter.py` | beginner/intermediate/advanced фильтрация — не нужна в Neo | Импортируется в `answer_adaptive.py`, `decision/` |
| `bot_agent/prompt_sd_blue.md` | SD blue meme промт | Загружается в `prompt_registry_v2.py` |
| `bot_agent/prompt_sd_green.md` | SD green meme промт | Загружается в `prompt_registry_v2.py` |
| `bot_agent/prompt_sd_orange.md` | SD orange meme промт | Загружается в `prompt_registry_v2.py` |
| `bot_agent/prompt_sd_purple.md` | SD purple meme промт | Загружается в `prompt_registry_v2.py` |
| `bot_agent/prompt_sd_red.md` | SD red meme промт | Загружается в `prompt_registry_v2.py` |
| `bot_agent/prompt_sd_yellow.md` | SD yellow meme промт | Загружается в `prompt_registry_v2.py` |
| `bot_agent/answer_basic.py` | Старый базовый pipeline | Дублирует логику Neo |
| `bot_agent/answer_graph_powered.py` | Graph-era pipeline | Устаревший контур |
| `bot_agent/answer_sag_aware.py` | SD-aware pipeline | Содержит SD routing |
| `bot_agent/memory_v11.py` | Промежуточная версия памяти | Заменяется `conversation_memory.py` |
| `bot_agent/decision/` (legacy routes) | pre_routing, pre_rerank_routing | Заменяется одним DecisionGate |

### 2.2 Файлы для глубокого рефакторинга (сохраняются, переписываются изнутри)

| Файл | Текущая проблема | Целевое состояние |
|------|-----------------|-------------------|
| `answer_adaptive.py` (134 КБ) | God Object — содержит SD-ветки, тройной routing, level-adapter | Оркестратор Neo pipeline, ~30–40 КБ |
| `diagnostics_classifier.py` | 10 UserState вместо 3+6 | Только `HYPER/WINDOW/HYPO` + 6 request_functions |
| `prompt_registry_v2.py` | Загружает SD-промты | Загружает только Neo prompt stack блоки |
| `runtime_config.py` (37 КБ) | Содержит SD-конфиги, level-конфиги | Только Neo-конфиги |
| `retriever.py` | Передаёт `sd_level` параметр в запрос | Убрать SD-фильтрацию, открытый доступ к базе |
| `config.py` | SD-поля в структурах | Очистить от SD-сущностей |
| `feature_flags.py` | Флаги SD существуют, но не удалены | Убрать SD-флаги, оставить только Neo-флаги |

### 2.3 Поля для удаления из БД-схемы

| Таблица / объект | Поле | Причина удаления |
|-----------------|------|-----------------|
| `user_profile` / runtime | `sd_level` | SD-классификация не используется |
| `user_profile` / runtime | `user_level` (beginner/intermediate/advanced) | level-adapter выведен |
| `session_state` | legacy trace поля: `pre_routing_result`, `pre_rerank_result` | Заменяются одним `routing_result` |
| `session_state` | `sd_confidence`, `sd_primary`, `sd_secondary` | SD не участвует в Neo |
| prompt registry | все записи с ключами `sd_*` | SD-промты не нужны |

---

## 3. Миграционный план — 6 волн

### Волна 1: Soft Freeze (feature flags)

**Цель:** Отключить legacy runtime без удаления кода. Обеспечить безопасную точку возврата.

**Задачи:**

1. В `feature_flags.py` установить и проверить значения:
   ```python
   NEO_MINDBOT_ENABLED = True
   SD_CLASSIFIER_ENABLED = False
   USER_LEVEL_ADAPTER_ENABLED = False
   LEGACY_PIPELINE_ENABLED = False
   PRE_ROUTING_ENABLED = False
   ```
2. Убедиться, что `answer_adaptive.py` читает эти флаги **до** вызова SD/level логики.
3. Добавить `assert not SD_CLASSIFIER_ENABLED` в начало `sd_classifier.py` как защитный барьер.
4. Прогнать smoke-тест: 10 входящих сообщений разных типов → убедиться, что SD-ветка не вызывается ни разу (проверить через trace в admin).

**Acceptance:**
- [ ] Ни один входящий запрос не проходит через `SDClassifier.classify()` при флаге `False`
- [ ] Ни один ответ не содержит `sd_level` в trace
- [ ] Бот отвечает корректно на все 10 smoke-запросов

---

### Волна 2: Удаление SD из retrieval и memory

**Цель:** Полностью изолировать базу знаний от SD-фильтрации.

**Задачи:**

1. В `retriever.py` найти и удалить все вхождения `sd_level`, `sd_filter`, `sd_confidence` из параметров запроса к Bot_data_base API.
2. Проверить, что `HybridQueryBuilder` не передаёт SD-поля в поисковый запрос.
3. В `chroma_loader.py` убрать SD-теги из метаданных при загрузке документов (если присутствуют).
4. В `conversation_memory.py` удалить сохранение полей `sd_level`, `sd_primary`, `sd_secondary`, `user_level` в `laststatesnapshot`.
5. Обновить JSON-схему `laststatesnapshot` — оставить только Neo-поля (см. раздел 1.3).
6. Обновить `memory_updater.py` — убрать передачу SD-полей в snapshot.

**Acceptance:**
- [ ] `retriever.retrieve(query, user_state)` не принимает и не использует `sd_level`
- [ ] `laststatesnapshot` не содержит ни одного SD-поля ни в одной сессии
- [ ] Поиск по базе возвращает релевантные результаты без SD-фильтрации для всех трёх состояний (HYPER, WINDOW, HYPO)

---

### Волна 3: Удаление user_level_adapter и level-логики

**Цель:** Устранить фильтрацию контента по beginner/intermediate/advanced.

**Задачи:**

1. В `answer_adaptive.py` найти все вызовы `UserLevelAdapter.filter_blocks_by_level()` и `level_adapter.*` — удалить.
2. В `response_generator.py` (или аналоге) убрать передачу `user_level` в prompt-контекст.
3. В `decision/` убрать ветки, зависящие от `user_level`.
4. В `config.py` и `runtime_config.py` удалить секции конфигурации level-adapter.
5. В `prompt_registry_v2.py` удалить загрузку level-промтов (`prompt_system_level_beginner.md`, `prompt_system_level_intermediate.md`, `prompt_system_level_advanced.md`).
6. Перенести файлы `prompt_system_level_*.md` в `legacy/`.

**Acceptance:**
- [ ] `UserLevelAdapter` не импортируется ни в одном активном файле
- [ ] Ответ бота на одинаковый запрос не зависит от `user_level` поля
- [ ] Отсутствуют вызовы `filter_blocks_by_level` в trace

---

### Волна 4: Схлопывание routing — один DecisionGate

**Цель:** Заменить тройной routing (`pre_routing → pre_rerank_routing → routing_result`) одним чистым decision flow.

**Задачи:**

1. Провести аудит `decision/` директории — идентифицировать все routing-функции.
2. Создать новый файл `decision/neo_decision_gate.py` с единственным классом `NeoDecisionGate`:
   ```python
   class NeoDecisionGate:
       async def route(self, state: NeoUserState, reranked_chunks: list) -> RoutingResult:
           # Один LLM-вызов с компактным промтом
           # Возвращает: mode (coaching|informational|crisis), 
           #             track (practice|reflective|direct),
           #             tone (empathic|technical|minimal)
   ```
3. В `answer_adaptive.py` заменить тройной routing-вызов на `NeoDecisionGate.route()`.
4. Убрать промежуточные сохранения `pre_routing_result` и `pre_rerank_result` из session_state.
5. Перенести старые routing-файлы в `legacy/decision_legacy/`.
6. Убедиться, что весь pipeline использует не более 2-х LLM-вызовов на один входящий запрос: `StateClassifier` + `ResponseGenerator` (DecisionGate встроен или делегирован внутрь одного из них).

**Acceptance:**
- [ ] На один входящий запрос — не более 2 LLM-вызовов в trace
- [ ] `pre_routing` и `pre_rerank_routing` отсутствуют в trace
- [ ] `RoutingResult` содержит только Neo-поля: `mode`, `track`, `tone`
- [ ] Latency одного ответа не превышает 5 секунд (target v1)

---

### Волна 5: Перестройка State Classifier и Prompt Stack

**Цель:** Привести `diagnostics_classifier.py` к `HYPER/WINDOW/HYPO` + 6 функций запроса. Собрать единый Neo prompt stack.

**Задачи — State Classifier:**

1. В `diagnostics_classifier.py` заменить 10-state перечисление на Neo-модель:
   ```python
   class NervousSystemState(Enum):
       HYPER = "hyper"
       WINDOW = "window"  
       HYPO = "hypo"

   class RequestFunction(Enum):
       DISCHARGE = "discharge"    # Выговориться, выплеснуть
       UNDERSTAND = "understand"  # Разобраться, осмыслить
       SOLUTION = "solution"      # Директива, конкретный план
       VALIDATION = "validation"  # Подтверждение, "всё нормально?"
       EXPLORE = "explore"        # Погрузиться глубже
       CONTACT = "contact"        # Просто присутствие, не анализ
   ```
2. Обновить промт `StateClassifier` — он должен возвращать JSON с полями: `nervous_system_state`, `request_function`, `dominant_part`, `core_theme`, `distance_to_experience`.
3. Убрать маппинг старых UserState → Neo (если присутствует как промежуточный слой).
4. Добавить валидацию: если `StateClassifier` возвращает значение вне Neo-перечислений — выбрасывать ошибку и использовать `WINDOW / understand` как safe default.

**Задачи — Prompt Stack:**

5. Создать директорию `bot_agent/prompts/` со следующей структурой:
   ```
   prompts/
   ├── aa_safety.md          ← Safety Rules + Psychological Boundaries
   ├── a_seasonal.md         ← Seasonal Filter + Anti-Bland Rule + Emoji Rule
   ├── core_identity.md      ← Identity, Mission, Persona, Role, Persona
   ├── diag_algorithm.md     ← 5-шаговый диагностический алгоритм
   ├── reflective_method.md  ← Reflective Method 4 шага
   ├── procedural_scripts.md ← CLEAR workflow, User Correction Protocol, if-then
   └── output_layer.md       ← Telegram HTML, Anti-Bland, Emoji Rule, Pre-Send Checklist
   ```
6. В `prompt_registry_v2.py` (или новом `neo_prompt_registry.py`) реализовать:
   ```python
   def build_master_prompt(seasonal_filter: str, interaction_mode: str) -> str:
       blocks = [
           load("aa_safety.md"),
           load("a_seasonal.md").format(season=seasonal_filter),
           load("core_identity.md"),
           load("diag_algorithm.md"),
           load("reflective_method.md"),
           load("procedural_scripts.md"),
           load("output_layer.md"),
       ]
       return "\n\n---\n\n".join(blocks)
   ```
7. Удалить загрузку SD-промтов из `prompt_registry_v2.py`.
8. Убедиться, что `aa_safety.md` загружается **первым** и не может быть перезаписан другими блоками.

**Acceptance:**
- [ ] `StateClassifier` возвращает только `nervous_system_state ∈ {hyper, window, hypo}`
- [ ] `StateClassifier` возвращает только `request_function ∈ {discharge, understand, solution, validation, explore, contact}`
- [ ] Master prompt содержит ровно 7 блоков в правильном порядке
- [ ] SD-промты не загружаются ни при каком сценарии
- [ ] 18 тестовых сообщений (6 state × 3 function) классифицируются корректно с точностью ≥ 85%

---

### Волна 6: Декомпозиция `answer_adaptive.py` и финальная очистка

**Цель:** Разбить 134 КБ God Object на чистые модули. Удалить legacy физически.

**Задачи — декомпозиция:**

1. Выделить из `answer_adaptive.py` следующие модули:
   ```
   pipeline/
   ├── neo_orchestrator.py      ← главный оркестратор, ~200 строк
   ├── state_mapper.py          ← маппинг входа → NeoUserState
   ├── context_builder.py       ← сборка контекста для LLM
   ├── practice_injector.py     ← инжект практик в ответ
   └── response_shaper.py       ← финальное форматирование
   ```
2. `neo_orchestrator.py` — единственная точка входа для обработки сообщения. Все остальные модули — зависимости без side-effects.
3. Перенести оригинальный `answer_adaptive.py` в `legacy/`.

**Задачи — финальная очистка:**

4. Физически переместить в `legacy/`:
   - `sd_classifier.py`
   - `user_level_adapter.py`
   - `answer_basic.py`
   - `answer_graph_powered.py`
   - `answer_sag_aware.py`
   - `memory_v11.py`
   - `prompt_sd_*.md` (все 6 файлов)
   - `prompt_system_level_*.md` (все 3 файла)
   - `decision/` (старые routing-файлы)
5. Провести `grep -r "sd_level\|SDClassifier\|UserLevelAdapter\|user_level\|sd_primary\|sd_secondary\|sd_confidence\|pre_routing\|pre_rerank" bot_agent/` — результат должен быть пустым (кроме `legacy/`).
6. Обновить `__init__.py` — убрать legacy-импорты.
7. Обновить `README.md` в `bot_psychologist/` — отразить Neo v11 архитектуру.

**Acceptance:**
- [ ] `grep` по legacy-символам в активных файлах возвращает 0 результатов
- [ ] Все 4 параллельных pipeline-файла заменены одним `neo_orchestrator.py`
- [ ] `neo_orchestrator.py` ≤ 250 строк
- [ ] Полный regression suite проходит без ошибок

---

## 4. Тестовый пакет — Neo Acceptance Tests

### 4.1 T1 — SD Isolation Tests (Волна 1)

| Тест | Сценарий | Ожидаемый результат |
|------|----------|---------------------|
| T1.1 | Запрос "Я чувствую тревогу" | Нет обращений к `SDClassifier` в trace |
| T1.2 | Запрос "Расскажи об ACT-терапии" | `sd_level` отсутствует в retrieval query |
| T1.3 | Любые 10 сообщений подряд | `SDClassifier.classify()` не вызывается ни разу |
| T1.4 | Admin trace | `sd_level`, `sd_confidence` отсутствуют во всех полях |
| T1.5 | `feature_flags.py` | `SD_CLASSIFIER_ENABLED = False` прочитан корректно |

### 4.2 T2 — Memory Snapshot Tests (Волна 2)

| Тест | Сценарий | Ожидаемый результат |
|------|----------|---------------------|
| T2.1 | 5 сообщений подряд | `laststatesnapshot` содержит только Neo-поля |
| T2.2 | Проверка JSON-схемы | Поля `sd_level`, `user_level`, `sd_primary` отсутствуют |
| T2.3 | Смена сессии | `currentsummary` обновляется, SD-поля не появляются |
| T2.4 | Admin-панель | Memory viewer не показывает SD-поля |
| T2.5 | 30 сообщений | `dialogcache` не превышает 20–30 записей |

### 4.3 T3 — State Classifier Tests (Волна 5)

Матрица 3 × 6 = 18 тестовых кейсов:

| Состояние | Функция | Тестовое сообщение | Ожидаемая классификация |
|-----------|---------|-------------------|------------------------|
| HYPER | discharge | "Я в панике, сердце колотится, не могу остановиться!" | `hyper / discharge` |
| HYPER | solution | "Скажи мне что делать прямо сейчас, быстро!" | `hyper / solution` |
| HYPER | contact | "Просто побудь со мной" | `hyper / contact` |
| WINDOW | understand | "Хочу разобраться, почему я так реагирую" | `window / understand` |
| WINDOW | explore | "Расскажи мне подробнее об IFS" | `window / explore` |
| WINDOW | validation | "Это нормально — чувствовать так?" | `window / validation` |
| HYPO | discharge | "Мне всё равно, говори что хочешь" | `hypo / discharge` |
| HYPO | understand | "Объясни мне что со мной" (вялый тон) | `hypo / understand` |
| HYPO | contact | (молчание / точка / "...") | `hypo / contact` |
| WINDOW | solution | "Дай мне конкретный план на неделю" | `window / solution` |
| HYPER | understand | "Почему я вообще такой? Это всегда так!" | `hyper / understand` |
| HYPO | validation | "Я наверное не нормальный" | `hypo / validation` |

Дополнительно: 6 граничных кейсов (HYPER/HYPO переход, смешанные сигналы).

**Acceptance:** Точность ≥ 85% по всей матрице (≥ 15 из 18 корректных).

### 4.4 T4 — Routing Tests (Волна 4)

| Тест | Сценарий | Ожидаемый результат |
|------|----------|---------------------|
| T4.1 | Полный trace одного запроса | Не более 2 LLM-вызовов |
| T4.2 | HYPO состояние | Нет `pre_routing_result` в trace |
| T4.3 | HYPER состояние | Нет `pre_rerank_routing` в trace |
| T4.4 | Informational запрос | `NeoDecisionGate` возвращает `mode=informational` |
| T4.5 | Crisis-сигнал | `AA Safety Layer` блокирует до `DecisionGate` |
| T4.6 | Latency-тест, 20 запросов | Среднее время ответа ≤ 5 секунд |

### 4.5 T5 — Prompt Stack Tests (Волна 5)

| Тест | Сценарий | Ожидаемый результат |
|------|----------|---------------------|
| T5.1 | Инспекция system prompt | 7 блоков в правильном порядке: AA, A, Core, Diag, Method, Proc, Output |
| T5.2 | Поиск SD в system prompt | Нет упоминаний "spiral", "meme", "graves", "sd_level" |
| T5.3 | Anti-Bland Rule | Ответ содержит эмоциональный элемент, не является сухим перечислением |
| T5.4 | Telegram HTML | Ответ содержит только допустимые теги: `<b>`, `<i>`, `<u>`, `<s>`, `<blockquote>`, `<code>` |
| T5.5 | Pre-Send Checklist | Ответ не нарушает ни одного из 8 правил чеклиста |
| T5.6 | Seasonal filter | При `spring` — в тоне присутствует весенняя семантика |

### 4.6 T6 — Practice Engine Tests

| Тест | Сценарий | Ожидаемый результат |
|------|----------|---------------------|
| T6.1 | `hyper` + любая функция запроса | Предложена практика из канала `body` |
| T6.2 | `hypo` + `contact` | Предложена практика из канала `body` (не `action`) |
| T6.3 | `window` + `last_channel=body` | Предложена практика из канала `thinking` или `action` |
| T6.4 | 7-дневный трек | `active_track` обновляется каждый день, не сбрасывается |
| T6.5 | Feedback `positive` | Следующая практика из другого канала |
| T6.6 | Feedback `negative` | Возврат к предыдущему каналу |
| T6.7 | Admin CRUD | Новая практика из admin сохраняется и используется в следующем цикле |

### 4.7 T7 — Legacy Grep Tests (Волна 6)

Эти тесты выполняются через скрипт `tests/test_no_legacy.py`:

```python
import subprocess, pathlib

LEGACY_SYMBOLS = [
    "SDClassifier", "sd_classifier", "sd_level", "sd_primary", "sd_secondary",
    "sd_confidence", "UserLevelAdapter", "user_level_adapter", "filter_blocks_by_level",
    "pre_routing", "pre_rerank_routing", "answer_basic", "answer_graph_powered",
    "answer_sag_aware", "memory_v11", "SD_LEVELS_ORDER", "sd_result"
]

ACTIVE_DIRS = ["bot_agent", "pipeline", "prompts"]

def test_no_legacy_symbols():
    for symbol in LEGACY_SYMBOLS:
        result = subprocess.run(
            ["grep", "-r", symbol, "--include=*.py", "--include=*.md"] + ACTIVE_DIRS,
            capture_output=True, text=True
        )
        assert result.stdout.strip() == "", f"Legacy symbol '{symbol}' found:\n{result.stdout}"
```

**Acceptance:** Все проверки проходят (0 вхождений в активных директориях).

### 4.8 T8 — Regression Suite (финальный, после всех волн)

| Тест | Описание |
|------|----------|
| T8.1 | 20 сообщений разных типов — бот отвечает корректно на все |
| T8.2 | Crisis-сообщение — AA Safety Layer срабатывает первым |
| T8.3 | Informational запрос — выдаётся информация, не практика |
| T8.4 | Запрос практики — выдаётся практика из корректного канала |
| T8.5 | 5 сессий — `laststatesnapshot` корректно формируется для каждой |
| T8.6 | Restart бота — `laststatesnapshot` восстанавливается из БД |
| T8.7 | Смена сезона в admin — seasonal filter применяется сразу |
| T8.8 | Отключение `NEO_MINDBOT_ENABLED` — fallback graceful error или legacy stub |
| T8.9 | Admin trace — все поля в Neo-схеме, нет legacy-полей |
| T8.10 | Полный pipeline trace — все 9 шагов логируются по порядку |

---

## 5. Структура репозитория после миграции

```
bot_psychologist/
├── bot_agent/
│   ├── __init__.py
│   ├── config.py              ← только Neo-конфиги
│   ├── config_validation.py
│   ├── feature_flags.py       ← только Neo-флаги
│   ├── embedding_provider.py
│   ├── chroma_loader.py
│   ├── retriever.py           ← без SD-фильтрации
│   ├── reranker_gate.py
│   ├── diagnostics_classifier.py  ← 3 состояния + 6 функций
│   ├── contradiction_detector.py
│   ├── fast_detector.py
│   ├── output_validator.py
│   ├── onboarding_flow.py
│   ├── db_api_client.py
│   │
│   ├── pipeline/              ← NEW: декомпозиция answer_adaptive
│   │   ├── neo_orchestrator.py
│   │   ├── state_mapper.py
│   │   ├── context_builder.py
│   │   ├── practice_injector.py
│   │   └── response_shaper.py
│   │
│   ├── decision/
│   │   └── neo_decision_gate.py  ← один чистый DecisionGate
│   │
│   ├── prompts/               ← NEW: единый prompt stack
│   │   ├── aa_safety.md
│   │   ├── a_seasonal.md
│   │   ├── core_identity.md
│   │   ├── diag_algorithm.md
│   │   ├── reflective_method.md
│   │   ├── procedural_scripts.md
│   │   └── output_layer.md
│   │
│   ├── memory/
│   │   ├── conversation_memory.py
│   │   ├── memory_updater.py
│   │   └── summarizer_agent.py
│   │
│   ├── practices/
│   │   ├── practices_db.json
│   │   ├── practice_schema.py
│   │   ├── practice_selector.py
│   │   ├── practices_recommender.py
│   │   └── path_builder.py
│   │
│   ├── neo_prompt_registry.py ← заменяет prompt_registry_v2.py
│   ├── runtime_config.py      ← очищен от SD/level
│   └── llm_answerer.py
│
├── legacy/                    ← всё старое, не удалять сразу
│   ├── sd_classifier.py
│   ├── user_level_adapter.py
│   ├── answer_adaptive.py     (оригинал)
│   ├── answer_basic.py
│   ├── answer_graph_powered.py
│   ├── answer_sag_aware.py
│   ├── memory_v11.py
│   ├── decision_legacy/
│   └── prompts_legacy/        ← все prompt_sd_*.md, level_*.md
│
└── tests/
    ├── test_no_legacy.py      ← T7 Legacy Grep
    ├── phase_wave1_tests.py   ← T1
    ├── phase_wave2_tests.py   ← T2
    ├── phase_wave3_tests.py   ← T3 + T5
    ├── phase_wave4_tests.py   ← T4
    ├── phase_wave5_tests.py   ← T6
    └── regression_suite.py    ← T8
```

---

## 6. Конфигурация Neo Feature Flags (финальное состояние)

```yaml
# feature_flags.yaml — Neo v11 final state
NEO_MINDBOT_ENABLED: true          # Главный включатель Neo pipeline
SD_CLASSIFIER_ENABLED: false       # SD-классификатор отключён навсегда
USER_LEVEL_ADAPTER_ENABLED: false  # Level-adapter отключён навсегда
LEGACY_PIPELINE_ENABLED: false     # Legacy pipeline недоступен
PRE_ROUTING_ENABLED: false         # Тройной routing отключён
INFORMATIONAL_MODE_ENABLED: true   # Информационный режим активен
TRACKS_ENABLED: true               # 7-дневные треки практик активны
MEMORY_FULL_ENABLED: true          # Полная память (snapshot + summary)
CRISIS_OVERRIDE_ENABLED: true      # AA Safety Layer всегда активен
```

---

## 7. Технические ограничения и риски

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Скрытые импорты SD-символов в подпроектах | Средняя | T7 Grep-тест покрывает все активные директории |
| Регрессия memory после очистки полей | Высокая | T2 tests + snapshot schema validation в `config_validation.py` |
| Деградация качества routing после упрощения | Средняя | T4.6 latency + T8 regression на 20 сообщениях |
| Неполный prompt stack (отсутствует блок) | Низкая | T5.1 инспекция system prompt перед каждым запросом |
| Потеря данных практик при рефакторинге | Низкая | `practices_db.json` не затрагивается, только логика селектора |
| `answer_adaptive.py` содержит скрытые зависимости | Высокая | Декомпозиция делается через полный import-граф перед нарезкой |

---

## 8. Definition of Done (финальный чеклист)

- [ ] Волна 1 завершена, все T1 тесты зелёные
- [ ] Волна 2 завершена, все T2 тесты зелёные
- [ ] Волна 3 завершена, `UserLevelAdapter` не импортируется нигде
- [ ] Волна 4 завершена, все T4 тесты зелёные, latency ≤ 5 сек
- [ ] Волна 5 завершена, State Classifier точность ≥ 85%, T5 зелёные
- [ ] Волна 6 завершена, T7 Grep возвращает 0 результатов
- [ ] T8 Regression Suite: все 10 тестов зелёные
- [ ] `legacy/` директория создана и содержит все перемещённые файлы
- [ ] `README.md` обновлён под Neo v11 архитектуру
- [ ] Admin-панель отображает только Neo-поля в trace и memory viewer
- [ ] Ни один ответ бота не содержит упоминания SD, "уровня пользователя" или legacy-артефактов
