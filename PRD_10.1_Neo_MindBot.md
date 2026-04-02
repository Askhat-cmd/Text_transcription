# PRD_10.1 — Neo MindBot

## Product Requirements Document

**Версия:** 10.1  
**Статус:** ACTIVE — approved for phased implementation by IDE agent  
**Формат:** Engineering-first PRD for phased migration and controlled rollout  
**Репозиторий:** `Askhat-cmd/Text_transcription`  
**Целевые области:** `bot_psychologist/`, `Bot_data_base/`  
**Основной исполнитель:** IDE-агент с обязательным прохождением тестов после каждой фазы

---

# 0. Executive Summary

Neo MindBot v10.1 — это новая целевая архитектура бота, который работает как **AI-сопровождающий для честного самоисследования**, а не как советчик, классификатор людей или универсальный “духовный движок”.

Версия 10.1 намеренно **уже и инженерно жёстче**, чем PRD_10.0.

Этот документ исправляет главные проблемы предыдущей версии:

- убирает перегруженность v1;
- фиксирует реалистичный call graph;
- ограничивает обязательную диагностику только теми метками, которые реально нужны в runtime;
- переводит кризисную логику из “режима” в **safety override layer**;
- делает informational ветку ограниченным, но полезным режимом;
- жёстко разделяет:
  - vision,
  - runtime architecture,
  - migration phases,
  - admin scope,
  - failure modes,
  - tests.

---

# 1. Product Intent

## 1.1 Что такое Neo MindBot

Neo MindBot — это Telegram-бот, который помогает пользователю:

- замечать своё состояние;
- лучше понимать, что с ним происходит;
- не сливаться с автоматическими мыслями и паттернами;
- получать маленькие, конкретные, бережные интервенции;
- сохранять смысловую непрерывность между сессиями.

Бот не заменяет психотерапевта, врача, кризисную службу, финансового консультанта или живого человека.

## 1.2 Главная роль системы

В продакшене Neo MindBot должен вести себя как:

- **зеркало** — отражает суть переживания без штампов;
- **навигатор** — помогает выбрать следующий шаг;
- **контейнер** — удерживает безопасность и непротиворечивость;
- **оркестратор практик** — подбирает интервенцию по состоянию, а не “по вдохновению модели”.

## 1.3 Методологическая база

Система использует как внутреннюю методологию:

- ACT
- IFS
- Polyvagal Theory / Somatic grounding
- Metacognitive Therapy
- AQAL

Важно: это не “режимы” и не отдельные ветки продукта. Это методологический слой, который влияет на структуру ответа и подбор практики.

---

# 2. Scope Definition

## 2.1 Что входит в v10.1 / v1 runtime scope

В релиз v10.1 входят только следующие обязательные возможности:

1. Coaching-first диалоговый контур  
2. Safety override layer  
3. Ограниченная informational ветка  
4. Diagnostics v1  
5. Memory v1.1  
6. Retrieval без SD-фильтра  
7. Practice engine v1  
8. Prompt stack v2  
9. Output validation layer  
10. Traceability и phased rollout через feature flags

## 2.2 Что НЕ входит в обязательный scope v10.1

Следующие элементы НЕ блокируют выпуск v10.1 и не должны раздувать первую реализацию:

- продвинутая статистика admin-панели;
- сложные аналитические дашборды;
- динамическая настройка весов ранжирования из UI;
- полная hot-editability любой системной сущности без валидации;
- расширенная психотипизация пользователя;
- обязательная runtime-классификация IFS-частей и AQAL-квадрантов;
- “универсальный” multi-persona бот;
- сложные многошаговые треки сверх базового каркаса.

## 2.3 Жёсткие non-goals

Система не должна:

- возвращаться к SD как runtime-маршрутизатору;
- фильтровать БД по предполагаемому “уровню” пользователя;
- наслаивать несколько конкурирующих decision-gate LLM-вызовов;
- имитировать “точную глубинную диагностику личности” там, где модель неуверенна;
- строить архитектуру вокруг красивых метафор ценой инженерной ясности.

---

# 3. Product Principles

## 3.1 Принцип 1 — Safety first

Безопасность имеет абсолютный приоритет над стилем, теплотой, глубиной и “красотой” ответа.

## 3.2 Принцип 2 — Coaching-first, not everything-first

Neo MindBot в v10.1 — это прежде всего бот для сопровождения внутреннего процесса.  
Информационные ответы поддерживаются, но как ограниченная ветка, а не как самостоятельный равноправный продукт.

## 3.3 Принцип 3 — Runtime minimalism

В runtime остаются только те диагностические и логические слои, которые реально нужны для ответа.

## 3.4 Принцип 4 — Deterministic orchestration over prompt magic

Маршрутизация, подбор практик, fallback-политики и валидация должны быть по возможности детерминированными и проверяемыми кодом.

## 3.5 Принцип 5 — Migration without blind rewrite

Новая архитектура внедряется поэтапно поверх существующего проекта, под feature flags, с обязательными тестами.

---

# 4. High-Level Product Model

## 4.1 Основная модель взаимодействия

В v10.1 система мыслится как:

**user message → safety interpretation → lightweight diagnostics → deterministic orchestration → response generation → validation → memory update**

## 4.2 Главный результат для пользователя

После взаимодействия пользователь должен получить одно из следующего:

- более ясное понимание своего состояния;
- ощущение, что его состояние контейнировано и отражено точно;
- маленькое практическое действие;
- понятное информационное объяснение;
- безопасное перенаправление, если случай кризисный или вне границ бота.

---

# 5. Runtime Modes and Overlays

## 5.1 Не использовать термин “кризисный режим” как обычный runtime mode

В v10.1 есть только:

- `coaching`
- `informational`

И отдельно поверх них существует:

- `safety_override`

То есть кризис — не равноправный пользовательский режим, а перехватывающий слой.

## 5.2 Runtime mode definitions

### Mode: coaching
Используется, если пользователь говорит о своём опыте, состоянии, паттернах, затруднениях, отношениях, выборе, внутреннем конфликте.

### Mode: informational
Используется, если основной запрос — объяснить концепт, термин, технику или модель без явного запроса на сопровождение процесса.

### Overlay: safety_override
Активируется при:

- маркерах суицидального риска;
- признаках острой дезорганизации;
- опасных прямых запросах;
- запретных классах советов.

При активации safety override обычный коучинговый flow прерывается или упрощается.

---

# 6. Fixed Architecture Decisions

## 6.1 Зафиксированные решения

1. SD полностью убирается из runtime-маршрутизации.  
2. SD-метки в данных могут существовать только как пассивные исторические данные, не влияющие на live routing.  
3. `user_level_adapter` удаляется из активного пайплайна.  
4. Retrieval не фильтрует знания по уровню пользователя.  
5. Маршрутизация должна быть одной и однозначной.  
6. Количество синхронных LLM-вызовов на типовой coaching-turn — максимум 2.  
7. Summary работает асинхронно или по событию, но runtime обязан иметь явный fallback.  
8. Admin-панель в v10.1 ограничивается must-have набором.  

## 6.2 Реалистичный call graph

### Coaching flow (типовой)
1. `SafetyPrefilter` — deterministic  
2. `DiagnosticsClassifier` — LLM call #1  
3. `QueryBuilder` — deterministic  
4. `Retriever` — deterministic / API  
5. `Reranker` — deterministic / external model if already in system  
6. `RouteResolver` — deterministic  
7. `PracticeSelector` — deterministic  
8. `ResponseGenerator` — LLM call #2  
9. `OutputValidator` — deterministic  
10. `MemoryUpdater` — deterministic  
11. `Summarizer` — async / delayed

### Informational flow
1. `SafetyPrefilter`
2. `DiagnosticsClassifier` or `ModeLiteClassifier` depending on feature flag strategy
3. `Retriever`
4. `ResponseGenerator`
5. `OutputValidator`
6. `MemoryUpdater`

### Safety override flow
1. `SafetyPrefilter`
2. if risk high → bypass normal coaching route
3. safe crisis response template or dedicated safe-generation prompt
4. validation
5. memory flagging

## 6.3 Почему в v10.1 нет LLM DecisionGate

Отдельный LLM DecisionGate удаляется из v10.1 runtime.  
Причина: он создаёт лишнюю задержку, противоречивые решения и размывает инженерную управляемость.

Вместо него вводится `RouteResolver` как детерминированный модуль, который принимает:

- diagnostics result
- retrieval stats
- safety flags
- memory hints

и выбирает один route.

---

# 7. Diagnostics v1

## 7.1 Обязательные runtime-поля диагностики

Только эти поля считаются обязательными для runtime v10.1:

- `interaction_mode`
- `nervous_system_state`
- `request_function`
- `core_theme`

## 7.2 Optional enrichment fields

Следующие поля разрешены только как optional enrichment и НЕ должны быть обязательными для маршрутизации v10.1:

- `distance_to_experience`
- `dominant_part`
- `active_quadrant`
- `readiness_markers`

Если они не определены или confidence низкий, система не должна ломаться и не должна делать вид, что знает их точно.

## 7.3 Runtime contract for diagnostics

```json
{
  "interaction_mode": "coaching | informational",
  "nervous_system_state": "hyper | window | hypo",
  "request_function": "discharge | understand | directive | validation | explore | contact",
  "core_theme": "string",
  "confidence": {
    "interaction_mode": 0.0,
    "nervous_system_state": 0.0,
    "request_function": 0.0,
    "core_theme": 0.0
  },
  "optional": {
    "distance_to_experience": null,
    "dominant_part": null,
    "active_quadrant": null,
    "readiness_markers": []
  }
}
```

## 7.4 Confidence policy

### High-confidence fields
- `interaction_mode`
- `nervous_system_state`
- `request_function`

Если confidence по одному из этих полей ниже порога, применяется fallback logic.

### Low-confidence policy
- для optional fields низкая уверенность допустима;
- они не влияют на route;
- они могут вообще не сохраняться в snapshot.

## 7.5 Nervous system state rules

### `hyper`
Признаки:
- срочность
- перегруз
- паника
- катастрофизация
- злость с высокой активацией
- поток текста / много восклицаний / резкая фрагментация

### `window`
Признаки:
- связность
- способность наблюдать
- готовность к исследованию
- переносимость неопределённости

### `hypo`
Признаки:
- пустота
- апатия
- обрывистость
- отчуждение
- ощущение “не чувствую ничего”
- глобальное бессилие

## 7.6 Request function taxonomy

Использовать только 6 функций:

- `discharge` — выговориться / разрядиться
- `understand` — понять, что происходит
- `directive` — попросить сказать, что делать
- `validation` — подтвердить правоту / интерпретацию
- `explore` — исследовать глубже
- `contact` — просто контакт, без аналитического запроса

## 7.7 Diagnostic fallback rules

Если классификатор не может надёжно определить:

- `interaction_mode` → default `coaching`
- `nervous_system_state` → default `window`
- `request_function` → default `understand`
- `core_theme` → `"unspecified_current_issue"`

Это лучше, чем симулировать ложную точность.

---

# 8. RouteResolver

## 8.1 Разрешённые route values

`RouteResolver` должен возвращать только одно значение из списка:

- `safe_override`
- `regulate`
- `reflect`
- `practice`
- `inform`
- `contact_hold`

## 8.2 Route semantics

### `safe_override`
Используется, если Safety Layer перехватывает ответ.

### `regulate`
Используется, если состояние `hyper` или `hypo` требует сначала телесной или контейнирующей регуляции.

### `reflect`
Используется при `window` и функциях `understand` / `explore`.

### `practice`
Используется, если пользователь готов к явной интервенции или после отражения нужен следующий шаг.

### `inform`
Используется в informational ветке или когда запрос преимущественно образовательный.

### `contact_hold`
Используется, когда человеку прежде всего нужно присутствие, мягкое отражение, без избыточного анализа.

## 8.3 Deterministic route rules

Пример базовых правил:

- if `safety_override == true` → `safe_override`
- elif `interaction_mode == informational` → `inform`
- elif `nervous_system_state in [hyper, hypo]` → `regulate`
- elif `request_function == contact` → `contact_hold`
- elif `request_function in [understand, explore]` and `nervous_system_state == window` → `reflect`
- elif practice candidate score above threshold → `practice`
- else → `reflect`

---

# 9. Safety Layer

## 9.1 Абсолютные ограничения

Нельзя:

- ставить медицинские диагнозы;
- назначать лечение;
- давать финансовые советы;
- давать директивные советы по высокорисковым личным решениям так, как будто система знает истину;
- подменять собой кризисную поддержку;
- усиливать вредные или саморазрушительные действия;
- изображать живого человека или скрывать искусственную природу системы.

## 9.2 Safety override categories

### Category A — hard stop / crisis containment
- суицидальные маркеры
- прямой вред себе
- опасные кризисные сигналы

### Category B — unsafe directive
- “скажи, мне бросать отношения или нет”
- “скажи, мне уволиться или нет”
- “подтверди, что этот человек токсичен”
- любые высокорисковые директивы с тяжёлыми последствиями

### Category C — boundary limitation
- медицина
- юриспруденция
- инвестиции
- психиатрические обещания

## 9.3 Safety response policy

### Для Category A
- признать тяжесть состояния
- перейти в кризисный протокол
- выдать безопасное сообщение
- предложить немедленное обращение к человеку/службе
- не продолжать обычную коучинговую ветку

### Для Category B
- не отвечать “да/нет”
- объяснить ограничение
- перевести в исследовательский или контейнирующий формат

### Для Category C
- коротко обозначить границу
- предложить безопасную альтернативу в рамках возможностей бота

## 9.4 Crisis protocol design requirement

Кризисный протокол должен быть configurable:
- шаблоны сообщений
- локализованные контакты помощи
- язык
- fallback при отсутствии региональных данных

---

# 10. Prompt Stack v2

## 10.1 Prompt stack order

Порядок жёстко фиксирован:

1. `AA_SAFETY`
2. `A_STYLE_POLICY`
3. `CORE_IDENTITY`
4. `CONTEXT_MEMORY`
5. `DIAGNOSTIC_CONTEXT`
6. `RETRIEVED_CONTEXT`
7. `TASK_INSTRUCTION`

## 10.2 Почему убран отдельный DIAG/METHOD как отдельные “громоздкие блоки”

В v10.1 диагностика не живёт как огромный концептуальный промт внутри response generation.  
Диагностика уже выполнена ранее и приходит в ответный промт как **структурированный контекст**, а не как философский трактат.

То же касается Reflective Method: это не самостоятельный монолитный prompt-section “на все случаи”, а policy, которая активируется только если route этого требует.

## 10.3 `AA_SAFETY`

Содержит:
- запреты;
- safety override policy;
- отказ от небезопасных директив;
- кризисный протокол;
- приоритет над всеми остальными блоками.

## 10.4 `A_STYLE_POLICY`

Это не “обязательный сезонный художественный фильтр”, а **адаптивная стиль-политика**.

Внутри:
- anti-bland policy;
- warmth policy;
- non-toxic tone policy;
- optional seasonal accent.

### Важное ограничение
Seasonal styling не должен быть жёстким обязательным образным префиксом для всех состояний.

## 10.5 Seasonal accent policy

Допускается seasonal accent:
- `spring`
- `summer`
- `autumn`
- `winter`
- `neutral`

Но:
- для `inform` допускается `neutral`;
- для `hypo` по умолчанию `neutral` или `winter_soft`;
- для `safe_override` — только безопасная нейтральность, без “поэтизации”.

## 10.6 `CORE_IDENTITY`

Кратко фиксирует:
- что бот делает;
- чего не делает;
- какова его роль;
- какую методологию он использует.

Запрещено раздувать этот блок до длинного философского текста.

## 10.7 `CONTEXT_MEMORY`

Вставляется только проверенный и ограниченный контекст:
- summary
- snapshot subset
- active track info if relevant
- recent message window fallback if summary stale

## 10.8 `DIAGNOSTIC_CONTEXT`

В response prompt инжектируются:
- interaction_mode
- nervous_system_state
- request_function
- core_theme
- selected route
- optional enrichment if confident

## 10.9 `RETRIEVED_CONTEXT`

Вставляется только релевантный и уже отранжированный контекст из БД.  
Запрещено передавать в prompt весь retrieval output без ограничений.

## 10.10 `TASK_INSTRUCTION`

Формулирует конкретную задачу текущего хода:
- reflect
- regulate
- inform
- offer practice
- contact hold
- safe override

---

# 11. Reflective Method v10.1

## 11.1 Reflective Method больше не считается “всегдашней сутью бота”

Он применяется только по route.

## 11.2 Когда применяется

Разрешён при:
- `reflect`
- `practice`
- частично при `contact_hold`

## 11.3 Когда не применяется полноценно

Не применять как полную 4-шаговую последовательность при:
- `inform`
- `safe_override`
- `regulate` в острых hyper/hypo состояниях

## 11.4 Формат Reflective Method

1. Recognition  
2. Decentering  
3. Perspective  
4. Micro-action

Но в runtime допускается сокращённый вариант:
- 1+4
- 1+2
- 1 only

в зависимости от route и состояния.

---

# 12. Retrieval and Knowledge Access

## 12.1 Источник знаний

Основной источник — `Bot_data_base` через API / текущий согласованный интеграционный интерфейс.

## 12.2 Retrieval principles

- без SD-фильтра;
- без level filter;
- по смыслу текущего запроса;
- с учётом `core_theme`, `interaction_mode`, route;
- с ограничением по объёму контекста.

## 12.3 Retrieval contract

Вход:
- raw user message
- diagnostics
- memory hints
- feature flags

Выход:
- ranked content blocks
- retrieval metadata
- optional practice candidates
- retrieval confidence / stats

## 12.4 Failure handling

Если retrieval пустой:
- coaching flow не должен ломаться;
- response generator должен уметь отвечать без retrieved knowledge.

Если retrieval слишком шумный:
- ограничить top-k;
- усилить rerank;
- fallback к generic methodological answer.

---

# 13. Practice Engine v1

## 13.1 Цель

Практика должна подбираться системно, а не как свободная импровизация LLM.

## 13.2 Minimal required schema

```json
{
  "id": "string",
  "title": "string",
  "channel": "body | thinking | action",
  "scientific_basis": ["string"],
  "triggers": ["string"],
  "nervous_system_states": ["hyper", "window", "hypo"],
  "request_functions": ["discharge", "understand", "directive", "validation", "explore", "contact"],
  "core_themes": ["string"],
  "instruction": "string",
  "micro_tuning": "string",
  "closure": "string",
  "time_limit_minutes": 5,
  "contraindications": []
}
```

## 13.3 Channel policy

- `hyper` → приоритет `body`
- `hypo` → `body` или очень мягкий `action`
- `window` → доступны `thinking` и `action`, при необходимости `body`

## 13.4 Rotation policy

Нельзя повторять один и тот же канал подряд бесконечно.  
Минимальная политика v10.1:

- не повторять `last_practice_channel`, если есть равнозначная альтернатива;
- повтор разрешён, если состояние строго требует того же канала.

## 13.5 Selection algorithm v1

Сначала фильтры:
1. by safety / contraindications
2. by nervous_system_state
3. by route relevance
4. by request_function
5. by recent channel history

Потом scoring:
- state match
- request match
- core_theme match
- recency penalty
- time_limit fit

## 13.6 Alternative offer policy

Если пользователь просит альтернативу:
- показать не более 2 альтернатив;
- не открывать весь каталог;
- альтернативы должны быть реальными, а не “что угодно”.

## 13.7 Tracks policy

В v10.1 треки допускаются, но как упрощённая надстройка.  
Если треки усложняют основной rollout, их можно включить под feature flag позже.

---

# 14. Memory v1.1

## 14.1 Runtime memory components

- `last_state_snapshot`
- `current_summary`
- `dialog_cache`
- `active_track` (optional)
- `insights_log` (optional lightweight)

## 14.2 Required snapshot schema

```json
{
  "schema_version": "1.1",
  "updated_at": "ISO8601",
  "diagnostics": {
    "interaction_mode": "coaching | informational",
    "nervous_system_state": "hyper | window | hypo",
    "request_function": "discharge | understand | directive | validation | explore | contact",
    "core_theme": "string"
  },
  "routing": {
    "last_route": "safe_override | regulate | reflect | practice | inform | contact_hold"
  },
  "engagement": {
    "last_practice_id": null,
    "last_practice_channel": null,
    "active_track": null
  },
  "meta": {
    "summary_staleness": "fresh | stale | missing",
    "needs_context_continuity": true
  }
}
```

## 14.3 Summary schema requirements

`current_summary` должен быть кратким и пригодным для prompt injection.

Обязательные смысловые блоки:
1. кто пользователь по контексту;
2. что обсуждалось;
3. на чём остановились;
4. что важно помнить;
5. какой стиль взаимодействия уместен.

## 14.4 Summary update policy

Обновление `current_summary`:
- по таймауту сессии;
- или каждые N ходов;
- или при явном завершении смыслового блока.

## 14.5 Memory fallback chain

Если summary `fresh`:
1. use `current_summary`
2. add small snapshot subset
3. optionally add recent 2-4 messages

Если summary `stale`:
1. use `current_summary`
2. add larger recent message window
3. mark in runtime trace that stale summary fallback was used

Если summary `missing`:
1. use snapshot
2. use recent message window
3. continue without summary

Если snapshot corrupted:
1. ignore broken fields
2. log validation error
3. continue from recent dialog cache

## 14.6 Memory validation

Перед использованием memory:
- проверить `schema_version`
- проверить допустимые enum values
- проверить размер summary
- проверить timestamp freshness

## 14.7 Memory non-goal

Memory не должна создавать иллюзию “идеального знания человека”.  
Она нужна для continuity, а не для псевдопсихологического профилирования.

---

# 15. Output Validation Layer

## 15.1 Output generation and output validation must be separate

Ответ сначала генерируется, потом валидируется.

## 15.2 Validator checks

Минимальные проверки:

- route-consistency
- safety consistency
- format validity
- no forbidden directive advice
- correct mode behavior
- no broken HTML if Telegram HTML mode active
- reasonable length
- no empty answer
- no hallucinated certainty about unknown personal facts

## 15.3 Adaptive style rules

Валидация не должна быть догматичной.

### Examples
- для `inform` допустим нейтральный стиль и меньше образности;
- для `hypo` допустим сверхминималистичный ответ;
- для `safe_override` запрещено “эстетизировать” кризис;
- для короткого ответа не нужно требовать фиксированное число эмодзи.

## 15.4 Telegram formatting policy

Если система работает в Telegram HTML mode:
- использовать только разрешённые теги;
- не использовать markdown;
- не ломать теги;
- plain text допустим для коротких ответов.

## 15.5 Emoji policy v10.1

Эмодзи — необязательный адаптивный слой, а не тоталитарное требование.

Allowed policy:
- `inform` → 0-2
- `safe_override` → 0-1
- short coaching response → 0-3
- richer coaching answer → optional 1-5

Запрещено фиксировать стиль через обязательный диапазон “6–12 всегда”.

## 15.6 Invalid output policy

Если ответ не прошёл validation:
1. попытка local repair, если ошибка форматная;
2. regenerate once with stricter instruction, если ошибка содержательная;
3. safe fallback response, если повторная генерация тоже невалидна.

---

# 16. Informational Branch

## 16.1 Что такое informational branch в v10.1

Это ограниченная ветка для объяснения понятий, методов, терминов и моделей без глубокого коучингового сопровождения.

## 16.2 Требования к informational branch

- не запускать полную reflective-логику;
- не предлагать практики без явного запроса;
- не навязывать коучинговую рамку;
- не симулировать терапевтическое вмешательство;
- при явном личном контексте уметь мягко предложить перейти в coaching.

## 16.3 Mixed query handling

Если запрос смешанный:
пример: “Объясни, что такое избегание, потому что кажется это про меня”

система может:
- дать короткое объяснение;
- затем добавить мягкий мост к coaching-ветке.

Это должно быть частью `TASK_INSTRUCTION`, а не отдельным режимом хаоса.

---

# 17. Onboarding v10.1

## 17.1 Цель онбординга

Не проводить допрос.  
Снять тревогу первого контакта.  
Быстро понять, что пользователь ждёт сейчас.

## 17.2 `/start`

Минимальный сценарий:
- короткое приветствие;
- объяснение роли бота;
- приглашение написать, с чем человек пришёл.

## 17.3 First-turn handling

Первое сообщение проходит через:
- safety prefilter
- diagnostics classifier
- route resolution

## 17.4 First coaching response requirements

Первый ответ должен:
- показать, что запрос понят;
- не перегрузить пользователя схемами;
- не выглядеть как бюрократический intake form;
- задать рабочую глубину контакта.

## 17.5 User correction protocol

Если пользователь пишет:
- “нет, не то”
- “ты меня не понял”
- “я не об этом”

система должна:
1. признать промах;
2. снизить уверенность в прошлой интерпретации;
3. не спорить;
4. перекалиброваться по последнему сообщению.

---

# 18. Admin Panel Scope

## 18.1 Must-have for v10.1

Только это обязательно:

- feature flags
- просмотр `last_state_snapshot`
- просмотр и ручная правка `current_summary`
- редактирование prompt blocks с версионированием
- просмотр trace последних ходов
- включение/выключение key policies

## 18.2 Should-have after v10.1

- CRUD практик
- diagnostics rules editor
- track management UI
- usage statistics

## 18.3 Nice-to-have later

- весовые коэффициенты через UI
- аналитические дашборды
- алерты и расширенный мониторинг
- сложные сравнения prompt versions

## 18.4 Admin safety requirements

Любое редактирование через admin UI должно иметь:
- versioning
- validation
- rollback
- audit trail

Hot editing без версии и rollback запрещён.

---

# 19. Config and Feature Flags

## 19.1 Required flags

- `NEO_MINDBOT_ENABLED`
- `LEGACY_PIPELINE_ENABLED`
- `INFORMATIONAL_BRANCH_ENABLED`
- `MEMORY_V11_ENABLED`
- `PRACTICE_ENGINE_ENABLED`
- `TRACKS_ENABLED`
- `STRICT_OUTPUT_VALIDATION_ENABLED`

## 19.2 Migration flags

Допускаются временные флаги:
- `USE_DETERMINISTIC_ROUTE_RESOLVER`
- `USE_NEW_DIAGNOSTICS_V1`
- `DISABLE_SD_RUNTIME`
- `DISABLE_USER_LEVEL_ADAPTER`

## 19.3 Config validation

При старте системы конфиг обязан валидироваться.
Некорректный config не должен silently ломать runtime.

---

# 20. Observability and Trace

## 20.1 Each turn trace must include

- input metadata
- safety flags
- diagnostics result
- route selected
- retrieval stats
- selected practice id if any
- response validation result
- memory update result

## 20.2 LLM trace requirements

Для каждого LLM-вызова:
- prompt version
- model name
- elapsed time
- success/failure
- parse success
- fallback used or not

## 20.3 Privacy note

Логи не должны тащить лишние чувствительные данные сверх необходимого для отладки.

---

# 21. Failure Modes

## 21.1 Diagnostics failure
Если классификатор вернул битый JSON или неполные поля:
- парсить всё, что можно;
- применить defaults;
- залогировать ошибку;
- продолжить безопасный flow.

## 21.2 Retrieval failure
Если retrieval недоступен:
- не падать;
- ответить без retrieval;
- пометить degraded mode.

## 21.3 Summary missing/stale
Использовать fallback chain из memory policy.

## 21.4 Validator failure
Попытаться repair/regenerate once, затем safe fallback.

## 21.5 Admin misconfiguration
При невалидной конфигурации:
- не включать опасный режим;
- откатываться на последнюю валидную версию;
- логировать событие.

## 21.6 Partial subsystem outage
Если внешняя БД практик или knowledge API недоступны:
- coaching контур продолжает работать в минимальном режиме;
- не обещать доступ к практике, которой нельзя воспользоваться.

## 21.7 User state ambiguity
При смешанных сигналах:
- выбирать более безопасный и менее амбициозный маршрут;
- не симулировать глубокую точность.

---

# 22. Data Contracts

## 22.1 Schema versioning is mandatory

Все ключевые структуры должны иметь версию:
- diagnostics schema
- snapshot schema
- summary template version
- practice library schema
- prompt stack version

## 22.2 Backward compatibility policy

Во время миграции:
- старые поля можно читать;
- новые модули не должны зависеть от legacy-only полей;
- удаление legacy-полей только после e2e-проверки.

---

# 23. Target File Structure

```text
bot_psychologist/
├── core/
│   ├── diagnostics_classifier.py
│   ├── route_resolver.py
│   ├── safety_prefilter.py
│   ├── query_builder.py
│   ├── retriever.py
│   ├── reranker.py
│   ├── response_generator.py
│   └── output_validator.py
│
├── memory/
│   ├── memory_updater.py
│   ├── summary_manager.py
│   ├── snapshot_schema.py
│   └── dialog_cache.py
│
├── practices/
│   ├── practice_selector.py
│   ├── track_manager.py
│   ├── practice_schema.py
│   └── practices_db.json
│
├── prompts/
│   ├── aa_safety.md
│   ├── a_style_policy.md
│   ├── core_identity.md
│   ├── task_templates/
│   └── versions.yaml
│
├── config/
│   ├── feature_flags.yaml
│   ├── system_config.yaml
│   ├── diagnostics_rules.yaml
│   └── validation_schema/
│
├── legacy/
│   ├── sd_classifier.py
│   ├── user_level_adapter.py
│   └── old_routing/
│
└── tests/
    ├── unit/
    ├── integration/
    ├── contract/
    ├── regression/
    ├── golden/
    └── e2e/
```

---

# 24. Delivery Plan

## Phase 0 — Baseline and Safety Net
- inventory current runtime
- map legacy dependencies
- add smoke tests
- add feature flags
- freeze baseline fixtures

## Phase 1 — Remove SD Runtime Dependency
- disable SD in runtime
- remove SD assumptions from pipeline
- prove no SD path is required

## Phase 2 — Remove SD Retrieval Filtering
- delete `sd_level` runtime usage
- ensure full knowledge access

## Phase 3 — Remove UserLevelAdapter
- eliminate level-based block filtering
- clean response assembly

## Phase 4 — Introduce Diagnostics v1 + Deterministic RouteResolver
- implement required runtime fields
- remove multi-gate logic
- establish one route per turn

## Phase 5 — Memory v1.1
- snapshot
- summary
- fallback chain
- validation and versioning

## Phase 6 — Prompt Stack v2 + Output Validation
- prompt registry
- strict order
- adaptive style policy
- validator separation

## Phase 7 — Practice Engine v1
- library schema
- deterministic selection
- channel rotation
- optional alternatives

## Phase 8 — Informational Branch + Onboarding
- limited informational behavior
- mixed-query handling
- first-session flow

## Phase 9 — Observability + Failure Hardening
- trace
- config rollback
- degraded mode handling
- contract validation

## Phase 10 — E2E Hardening and Cleanup
- full regression pack
- remove remaining dead runtime paths
- update docs
- prepare rollout

---

# 25. Testing Strategy

## 25.1 Test layers

Обязательны:
- unit
- integration
- contract
- regression
- golden
- e2e

## 25.2 Contract tests

Проверять:
- diagnostics JSON schema
- snapshot schema
- practice schema
- prompt registry schema
- config validity

## 25.3 Negative tests

Обязательны:
- битый diagnostics JSON
- missing summary
- stale summary
- retrieval timeout
- malformed admin config
- mixed coaching+informational query
- unsafe directive request
- ambiguous state classification
- validator rejection path

## 25.4 Golden tests

Минимальный набор:
- panic / hyper case
- reflective window case
- shutdown / hypo case
- directive relationship conflict
- pure informational request
- mixed informational+personal request
- returning user with stale summary
- practice alternative request
- user correction case

## 25.5 E2E acceptance requirements

Система считается готовой только если:
- no SD runtime dependency remains
- full retrieval works without level gating
- one route per turn is enforced
- diagnostics v1 stable on golden set
- memory fallback chain works
- validator catches bad outputs
- degraded modes do not crash the pipeline
- legacy fallback still works while flag is off

---

# 26. Performance Constraints

## 26.1 LLM budget

Типовой coaching-turn:
- `DiagnosticsClassifier` — sync LLM call #1
- `ResponseGenerator` — sync LLM call #2

`Summarizer`:
- async or deferred

## 26.2 Latency target

Целевой ориентир v10.1:
- p50 acceptable user experience over raw speed
- no hard optimization before correctness
- measure per subsystem

## 26.3 No hidden LLM calls

Запрещено добавлять незадокументированные LLM-вызовы в runtime.

---

# 27. Definition of Done

Neo MindBot v10.1 считается готовым только если одновременно выполнено всё:

1. SD убран из runtime.  
2. Retrieval открыт без level/SD фильтра.  
3. UserLevelAdapter не участвует в live pipeline.  
4. Routing однозначен и детерминирован.  
5. Diagnostics v1 использует только обязательные runtime-поля.  
6. Memory v1.1 работает с fallback chain и schema validation.  
7. Prompt stack v2 собран и версионируется.  
8. Output validation отделён от generation.  
9. Informational branch ограничен и не ломает coaching-first модель.  
10. Safety override работает как верхний слой, а не как обычный режим.  
11. Все required test suites зелёные.  
12. Документация обновлена.  
13. Есть traceability и rollback strategy.  

---

# 28. Instructions to IDE Agent

1. Работай строго по фазам.  
2. Не прыгай к следующей фазе при красных тестах текущей.  
3. Не делай гигантский “магический” рефакторинг одним коммитом.  
4. После каждой фазы:
   - обнови код;
   - обнови тесты;
   - обнови контракты;
   - сделай отдельный коммит.
5. При любой архитектурной неопределённости выбирай:
   - более безопасную,
   - менее магическую,
   - более детерминированную,
   - более тестируемую реализацию.

---

# 29. Final Note

PRD_10.1 intentionally sacrifices some “красивую тотальность” ради инженерной честности.  
Это не упрощение идеи. Это очистка идеи от всего, что мешает ей стать работающей системой.

Neo MindBot v10.1 должен стать не самым красивым документом, а самым надёжным каркасом для живого бота.
