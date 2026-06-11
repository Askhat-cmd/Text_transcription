# WAKE_UP_DB_STRUCTURE_ADAPTED_FOR_NEO_MindBot_PRD_Reference_RU_v1.1

**Проект:** Bot Psychologist / Neo MindBot  
**Тип документа:** адаптированный reference-документ для будущих PRD по БД, retrieval, chunk governance, Web Admin и Trace  
**Источник:** переработка материала `Wake Up СТРКУТУРА.md` с учётом текущего курса Neo MindBot  
**Главный стратегический приоритет:** `STRATEGIC_PLAN_NEO_MindBot_Anti_Overengineering_Live_Core_v2_RU.md`  
**Версия:** v1.1 — усилена анти-эвристическими предохранителями  
**Статус:** использовать как архитектурный reference/input для PRD, не как прямое ТЗ на немедленную реализацию  

---

## 0. Назначение документа

Этот документ нужен, чтобы в новых чатах и будущих PRD быстро восстановить суть исследования Wake Up по правильной подготовке БД, но без лишнего шума, повторов и чрезмерных архитектурных разветвлений.

Документ отвечает на вопрос:

```text
Как превратить БД психологического бота
из склада текстов
в управляемую библиотеку механизмов, маркеров, глубины, практик,
safety-ограничений и живых ходов ответа,
не потеряв живость Writer’а и не переусложнив систему?
```

Главная поправка v1.1:

```text
Все markers, mechanism_hints, depth hints и chunk metadata
являются semantic guidance,
а не deterministic routing rules.
```

То есть этот документ не должен использоваться для создания бесконечной системы `if/else`, эвристик, маршрутов и жёстких правил.

---

## 1. Главная формула

Обычный RAG работает так:

```text
текст → чанки → embeddings → похожий фрагмент → Writer пересказывает
```

Для Neo MindBot этого недостаточно.

Нужна такая логика:

```text
материал → смысловые атомы → механизм → user_markers_examples → depth_level
→ allowed_use / avoid_when → retrieval_plan → chunk gate → Writer Context Package → живой ответ Writer’а
```

Ключевая формула:

```text
Чанк = не кусок текста.
Чанк = карточка распознавания, дозировки и применения знания.
```

Но важно:

```text
Чанк не является командой Writer’у.
Чанк не является правилом маршрутизации.
Чанк не является готовым ответом.
```

Чанк — это структурированная опора, которую retrieval может найти, chunk gate может отфильтровать, а Writer может использовать, частично использовать или проигнорировать.

---

## 2. Граница с Strategic Plan v2

Этот документ не отменяет стратегический курс проекта.

Приоритет всегда такой:

```text
1. Текущий исполняемый PRD
2. STRATEGIC_PLAN_NEO_MindBot_Anti_Overengineering_Live_Core_v2_RU.md
3. Последний Transfer Brief
4. Этот reference-документ Wake Up DB Structure v1.1
5. Архивные стратегические документы
```

Если этот документ предлагает широкую систему, а Strategic Plan v2 требует простоты — следовать Strategic Plan v2.

Основные ограничения:

```text
- не строить бесконечную систему эвристик;
- не плодить новых агентов без доказанной боли;
- не делать БД начальником Writer’а;
- не делать Diagnostic Center начальником Writer’а;
- не давать Planner’у писать пользовательский текст;
- не внедрять relation graph, enrichment, Web Admin и reindex в одном PRD;
- не превращать живой ответ в методическую выдачу.
```

Главный продуктовый критерий:

```text
Новая БД должна помогать Writer’у видеть человека точнее,
а не заставлять Writer’а исполнять протокол.
```

---

## 3. Anti-Heuristic Interpretation

### 3.1. Что запрещено

Этот документ нельзя интерпретировать так:

```text
если пользователь сказал “контроль” → mechanism=control_as_safety
если пользователь сказал “мама” → depth_level=3
если пользователь сказал “стыд” → взять shame_chunk
если пользователь сказал “телефон” → parenting_boundary_route
```

Это путь обратно к rule engine.

Такой подход приведёт к:

```text
- бесконечным правкам;
- конфликтующим правилам;
- скованному Writer’у;
- brittle routing;
- ухудшению живости;
- хаосу в trace;
- невозможности понять, почему бот ответил именно так.
```

### 3.2. Что разрешено

Правильная интерпретация:

```text
user_markers_examples — примеры живых фраз, которые помогают распознаванию;
mechanism_hints — возможные смысловые направления поиска;
depth_level — дозировка применения материала;
allowed_use — граница использования;
writer_instruction — мягкая подсказка, а не команда;
avoid_when — safety/context boundary, а не маршрут.
```

Пример правильной логики:

```text
Пользователь: “Если я перестану контролировать, то умру”.

Planner не делает:
if "контролировать" in text → use chunk X.

Planner делает:
- видит текущий контекст;
- учитывает thread_state;
- смотрит retrieval capability card;
- мягко предполагает mechanism_hints:
  ["control_as_safety", "helplessness_shame", "body_alarm"];
- запрашивает chunk types:
  ["mechanism", "safety", "dialogue_move"];
- ограничивает depth_level;
- разрешает Writer’у игнорировать найденное.
```

### 3.3. Главная защита

```text
Маркеры не командуют системе.
Маркеры помогают semantic planning, retrieval и trace.
```

---

## 4. Controlled Vocabulary vs Rule Engine

Neo MindBot нужен controlled vocabulary, но не rule engine.

### 4.1. Controlled vocabulary нужен для общего языка слоёв

Примеры стабильных словарей:

```text
chunk_type:
- concept
- mechanism
- diagnostic_lens
- practice
- dialogue_move
- anti_pattern
- safety
- source_fragment

allowed_use:
- direct_to_writer
- internal_lens
- retrieval_seed
- diagnostic_hint
- practice_suggestion
- not_for_direct_quote
- internal_only

depth_level:
- 0 stabilization/basic support
- 1 practical reflection
- 2 mechanism/lens
- 3 deeper pattern/history-sensitive

quote_policy:
- can_quote_short
- paraphrase_only
- internal_only
- do_not_use
```

Эти значения нужны, чтобы Planner, Retrieval, Chunk Gate, Diagnostic Center, Writer Context Package и Trace говорили на одном языке.

### 4.2. Controlled vocabulary не должен превращаться в rule engine

Плохой путь:

```text
Для каждого mechanism_hint сделать отдельный branch.
Для каждого user_marker сделать отдельное правило.
Для каждого depth_level сделать отдельный prompt.
Для каждого chunk_type сделать отдельный route.
```

Хороший путь:

```text
Использовать vocabulary как metadata language.
Решение принимать через контекст + retrieval + soft planner + chunk gate.
Хранить причины в trace.
Не создавать новый hardcoded route без доказанной необходимости.
```

### 4.3. Hard rules допустимы только в узких случаях

Жёсткие правила допустимы только для:

```text
- crisis/safety boundaries;
- privacy/secrets;
- invalid LLM JSON rejection;
- Planner user-facing text leakage rejection;
- production/broad rollout protection;
- encoding hygiene;
- no-mutation gates;
- raw provider payload / secrets not committed.
```

Все остальные решения должны быть soft/advisory.

---

## 5. Что является “эвристикой”, а что нет

### 5.1. Плохая эвристика

```python
if "мама" in user_message:
    depth_level = 3
    include_chunks("inner_child")
```

Почему плохо:

```text
- игнорирует состояние пользователя;
- игнорирует контекст;
- путает слово и механизм;
- может насильственно углубить ответ;
- создаёт бесконечное количество исключений.
```

### 5.2. Допустимый universal gate

```text
Если сообщение = приветствие, благодарность, прощание, close_ack,
то внешняя БД обычно не нужна.
```

Почему допустимо:

```text
- content-neutral;
- не связано с психологической темой;
- защищает от лишнего retrieval;
- не управляет глубиной ответа;
- не навязывает Writer’у смысл.
```

### 5.3. Допустимая semantic hint

```json
{
  "mechanism_hints": ["control_as_safety"],
  "confidence": 0.66,
  "writer_can_ignore_rag": true,
  "reason": "The user frames control as survival; context suggests safety/helplessness theme."
}
```

Почему допустимо:

```text
- это предположение, а не команда;
- есть confidence;
- есть reason;
- Writer может игнорировать;
- Chunk Gate может не пропустить чанки;
- trace показывает основание.
```

---

## 6. Типы чанков первой очереди

Для первой версии новой БД не нужен полный graph/ontology. Нужен минимальный набор типов, которые реально помогают runtime.

### 6.1. `source_fragment`

Сырой или почти сырой фрагмент источника.

Использовать:

```text
- для trace/source attribution;
- для offline enrichment;
- как backing source для derived chunks.
```

Не использовать:

```text
- как основной direct-to-writer материал без обработки;
- как длинную цитату;
- как authority над Writer’ом.
```

### 6.2. `concept`

Краткое объяснение понятия.

Примеры:

```text
- автоматизм;
- карта не территория;
- контролёр;
- внутренний критик;
- факт vs интерпретация;
- защитная часть.
```

### 6.3. `mechanism`

Описание внутреннего механизма: как собирается реакция, защита, страдание, повторение.

Примеры:

```text
- контроль как попытка вернуть безопасность;
- стыд как страх быть увиденным неправильным;
- беспомощность как старая детская позиция;
- телефон как быстрый уход от усилия/пустоты;
- жёсткость к ребёнку как форма родительской тревоги.
```

### 6.4. `diagnostic_lens`

Внутренняя линза для Diagnostic Center / Planner / Writer Context Package.

Важно:

```text
Это не диагноз.
Это мягкое предположение о возможном слое происходящего.
```

### 6.5. `dialogue_move`

Ход ответа, который помогает Writer’у не звучать общо.

Примеры:

```text
- сначала признать заботу, затем разделить границы и контроль;
- не спорить с паникой, а отделить телеский сигнал от интерпретации;
- не обвинять защитную часть, а признать её функцию;
- вернуть выбор без директивы;
- остановиться после одного точного отражения.
```

### 6.6. `practice`

Практическое действие/упражнение.

Практика должна иметь строгие условия применения:

```text
- goal;
- target_mechanisms;
- duration;
- intensity;
- steps;
- use_when;
- avoid_when;
- contraindications;
- preconditions;
- follow_up_question;
- risk_if_wrong_timing.
```

### 6.7. `anti_pattern`

Фрагмент, который описывает, чего не делать.

Примеры:

```text
- не спорить с паникой;
- не давать глубокую практику в остром состоянии;
- не называть защитную часть врагом;
- не давать пять заданий сразу;
- не превращать практику в новую плётку самосовершенствования;
- не тащить детство, если пользователь ещё не стабилизирован.
```

### 6.8. `safety`

Границы применения материала.

Примеры:

```text
- когда нужна стабилизация вместо глубины;
- когда направить к врачу/специалисту;
- когда не давать директиву;
- когда не работать с травмой;
- когда философская/духовная рамка может усилить уход от жизни.
```

---

## 7. Минимальная metadata-схема v1

PRD-047.16 не должен начинать с огромной онтологии. Нужна минимальная схема, которую реально можно внедрить и проверить.

### 7.1. Обязательные поля

```json
{
  "chunk_id": "mechanism_control_as_safety_001",
  "chunk_type": "mechanism",
  "title": "Контроль как попытка вернуть безопасность",
  "core_thesis": "Контроль может быть не жёсткостью, а способом нервной системы вернуть ощущение выживания и предсказуемости.",
  "mechanism_hints": ["control_as_safety", "fear_of_helplessness"],
  "user_markers_examples": [
    "если я перестану контролировать, всё развалится",
    "без меня ничего не получится",
    "я не могу отпустить"
  ],
  "use_when": [
    "пользователь связывает безопасность с контролем",
    "контроль звучит как защита, а не как желание власти"
  ],
  "avoid_when": [
    "острая паника без стабилизации",
    "пользователь просит медицинскую помощь",
    "контекст требует юридического/медицинского решения"
  ],
  "depth_level": 1,
  "allowed_use": ["internal_lens", "direct_to_writer"],
  "quote_policy": "paraphrase_only",
  "writer_instruction": "Не обвинять контролирующую часть. Сначала признать её защитную функцию, затем мягко показать цену контроля.",
  "source_trace": {
    "source_doc": "...",
    "source_span": "...",
    "derived": true
  }
}
```

### 7.2. Необязательные поля v1

```json
{
  "related_chunks": [],
  "forbidden_moves": [],
  "diagnostic_notes": [],
  "practice_preconditions": [],
  "intensity": "low|medium|high",
  "state_fit": [],
  "example_dialogue_move": "",
  "retrieval_aliases": []
}
```

### 7.3. Поля, которые не надо делать обязательными в первой версии

```text
- full relation graph;
- progression paths;
- complex ontology ids;
- multi-school psychological taxonomy;
- advanced spiritual/nondual layer;
- automated LLM-generated safety authority;
- runtime branching scripts per chunk.
```

---

## 8. Retrieval Capability Card

LLM Planner не должен знать всю БД. Но он должен знать карту возможностей БД.

Planner получает не raw KB content, а компактный registry/config:

```json
{
  "available_chunk_types": [
    "concept",
    "mechanism",
    "diagnostic_lens",
    "practice",
    "dialogue_move",
    "anti_pattern",
    "safety",
    "source_fragment"
  ],
  "available_allowed_use": [
    "direct_to_writer",
    "internal_lens",
    "retrieval_seed",
    "diagnostic_hint",
    "practice_suggestion",
    "not_for_direct_quote",
    "internal_only"
  ],
  "available_depth_levels": [0, 1, 2, 3],
  "searchable_metadata_fields": [
    "chunk_type",
    "title",
    "core_thesis",
    "mechanism_hints",
    "user_markers_examples",
    "use_when",
    "avoid_when",
    "depth_level",
    "allowed_use"
  ],
  "planner_limits": [
    "do_not_write_user_answer",
    "do_not_select_specific_chunk_as_final_authority",
    "return_metadata_only",
    "writer_can_ignore_rag"
  ]
}
```

Задача Planner:

```text
не выбрать конкретный ответ;
не процитировать БД;
не решить судьбу пользователя;
а сформулировать retrieval intention.
```

---

## 9. Simple / Complex Retrieval Logic

### 9.1. Простые случаи

Простые случаи должны решаться без LLM Planner.

Примеры:

```text
- приветствие;
- благодарность;
- прощание;
- close_ack;
- “короче”;
- “подведи итог”;
- “без практик”;
- “один шаг”.
```

Здесь достаточно universal gates.

Важно:

```text
Universal gates должны быть content-neutral.
Они не должны знать доменные темы.
```

### 9.2. Сложные случаи

LLM Planner допустим, если:

```text
- короткий ответ зависит от предыдущего предложения;
- пользователь просит связать текущий опыт с прошлой темой;
- есть смешанные ограничения: “да, но на моём примере”, “без теории”, “коротко, но глубоко”;
- literal query будет плохим;
- нужно выбрать тип знания, а не просто тему;
- retrieval должен учитывать механизм и depth_level.
```

### 9.3. Что Planner возвращает

Пример:

```json
{
  "retrieval_needed": true,
  "retrieval_action": "query_kb",
  "composed_query": "контроль безопасность беспомощность паническая атака страх потерять контроль",
  "needed_chunk_types": ["mechanism", "safety", "dialogue_move"],
  "mechanism_hints": ["control_as_safety", "helplessness_shame"],
  "depth_level_hint": 1,
  "excluded_chunk_types": ["deep_trauma_practice", "advanced_spiritual_lens"],
  "writer_constraints": [
    "не спорить с паникой",
    "не обвинять контролирующую часть",
    "не углублять травму резко"
  ],
  "writer_can_ignore_rag": true,
  "confidence": 0.74,
  "no_user_facing_text_created": true
}
```

---

## 10. Diagnostic Center в новой БД

Diagnostic Center может использовать metadata, но не должен становиться начальником ответа.

### 10.1. Разрешённая роль

Diagnostic Center может давать:

```json
{
  "diagnostic_hints": {
    "possible_mechanisms": ["control_as_safety"],
    "depth_recommendation": 1,
    "avoid_deep_interpretation": true,
    "suggested_writer_move": "validate_then_pragmatic_boundary",
    "risk_flags": ["do_not_pathologize", "do_not_blame"]
  }
}
```

### 10.2. Запрещённая роль

Diagnostic Center не должен говорить:

```text
У пользователя травма контроля.
Применить сценарий X.
Взять chunk Y.
Сказать пользователю Z.
```

Формула:

```text
Diagnostic Center = soft diagnostic lens.
Writer = живой автор ответа.
```

---

## 11. Chunk Inclusion Gate

Chunk Inclusion Gate решает не “что сказать”, а “что безопасно и уместно положить Writer’у на стол”.

Он учитывает:

```text
- retrieval_plan;
- score;
- chunk_type;
- allowed_use;
- quote_policy;
- depth_level;
- avoid_when;
- current user state;
- thread_state;
- Diagnostic Center hints;
- writer_can_ignore_rag.
```

Результат должен быть metadata-rich:

```json
{
  "included_chunks": ["mechanism_control_as_safety_001"],
  "excluded_chunks": [
    {
      "chunk_id": "deep_inner_child_004",
      "reason": "depth_too_high_for_current_state"
    },
    {
      "chunk_id": "practice_breathwork_002",
      "reason": "practice_not_requested_and_state_uncertain"
    }
  ],
  "writer_can_ignore_rag": true,
  "retrieval_gap_reason": null
}
```

---

## 12. Writer Context Package

Writer должен получать не “кучу найденных фрагментов”, а компактный пакет.

Минимальный пакет:

```json
{
  "user_message": "...",
  "active_frame": {
    "main_thread": "...",
    "current_need": "...",
    "possible_mechanism": "...",
    "depth_limit": 1
  },
  "retrieval_plan": {},
  "diagnostic_hints": {},
  "included_chunks": [],
  "writer_constraints": [
    "не звучать как методичка",
    "не делать диагноз",
    "не давать 5 шагов сразу",
    "можно игнорировать chunks, если живой ответ лучше"
  ]
}
```

Главная формула:

```text
Writer Context Package готовит сцену.
Writer отвечает живо.
```

---

## 13. Active Frame

Для живого удержания линии БД и retrieval должны работать не только с последней репликой, а с active frame.

Минимальные поля:

```json
{
  "main_thread": "что на самом деле сейчас разворачивается",
  "surface_topic": "о чём пользователь говорит словами",
  "possible_mechanism": "какой механизм может быть активен",
  "current_need": "что сейчас нужно: поддержка, ясность, практика, граница, safety",
  "open_loops": [],
  "closed_loops": [],
  "last_meaningful_shift": "последний смысловой сдвиг",
  "depth_limit": 1
}
```

Важно:

```text
Active Frame не должен быть ещё одним жёстким маршрутизатором.
Это краткая карта диалога.
```

---

## 14. How to Use This Document in PRD

### 14.1. Использовать для

```text
- проектирования минимальной metadata-схемы чанков;
- создания chunk_type registry;
- проектирования Retrieval Capability Card;
- уточнения LLM Planner JSON contract;
- проектирования Chunk Inclusion Gate;
- улучшения Writer Context Package;
- создания evaluation cases;
- проектирования trace fields;
- будущей Web Admin preview/review логики.
```

### 14.2. Не использовать для

```text
- добавления hardcoded психологических эвристик;
- прямого маппинга слов пользователя на механизм;
- создания новых route для каждой темы;
- превращения Diagnostic Center в диагнозатор;
- превращения БД в authority;
- ограничения Writer’а;
- полного reindex всей базы в одном PRD;
- внедрения relation graph без доказанной необходимости.
```

---

## 15. Minimal First Implementation для PRD-047.16

Если этот документ используется как основа для следующего PRD по БД, первая реализация должна быть узкой.

### 15.1. Взять в первую очередь

```text
- chunk_type;
- title;
- core_thesis;
- mechanism_hints;
- user_markers_examples;
- use_when;
- avoid_when;
- depth_level;
- allowed_use;
- quote_policy;
- writer_instruction;
- source_trace;
- minimal validation;
- dry-run conversion sample;
- trace preview;
- no reindex by default.
```

### 15.2. Не брать в первую очередь

```text
- полный relation graph;
- graph database;
- complex ontology;
- автоматическое LLM enrichment всей базы;
- Web Admin editing;
- runtime routes per mechanism;
- large taxonomy of hundreds of mechanisms;
- advanced spiritual/nondual layer;
- production rollout.
```

### 15.3. Acceptance criteria первой реализации

```text
1. Есть минимальная schema для mechanism-aware chunks.
2. Есть registry chunk_type / allowed_use / depth_level / quote_policy.
3. Есть converter или sample builder для небольшого набора chunks.
4. Есть validation report.
5. Есть trace preview: почему chunk подходит / не подходит.
6. Есть no-overengineering proof.
7. Нет новых hardcoded psychological rules.
8. Writer remains final author.
9. БД не становится authority.
10. Docs обновлены.
```

---

## 16. Evaluation: как понять, что мы не скатились в эвристики

Для каждого будущего PRD по БД добавлять проверку:

```text
1. Добавлены ли новые if/else по психологическим словам?
2. Появился ли новый route для конкретной темы?
3. Есть ли жёсткое правило “слово → механизм”?
4. Может ли Writer проигнорировать chunk?
5. Видно ли в trace, что это hint, а не command?
6. Есть ли confidence/reason/fallback?
7. Не стал ли Diagnostic Center диагнозатором?
8. Не появился ли новый agent без evidence?
9. Не ухудшилась ли живость ответа?
10. Можно ли объяснить изменение одним предложением?
```

Если ответы на 1–3 “да” — PRD должен быть пересмотрен.

---

## 17. Примеры хорошей и плохой реализации

### 17.1. Плохо

```python
if "стыд" in user_message:
    retrieval_action = "query_kb"
    chunk_type = "mechanism"
    mechanism = "shame_as_seen_wrong"
    depth_level = 3
```

### 17.2. Лучше

```json
{
  "retrieval_action": "query_kb",
  "needed_chunk_types": ["mechanism", "dialogue_move"],
  "mechanism_hints": ["shame_as_fear_of_being_seen_wrong"],
  "depth_level_hint": 1,
  "confidence": 0.61,
  "reason": "User mentions fear of being seen as wrong; recent context suggests shame, but state requires gentle depth.",
  "writer_can_ignore_rag": true
}
```

### 17.3. Ещё лучше

```text
Planner предлагает hint.
Retrieval ищет.
Chunk Gate исключает слишком глубокий chunk.
Writer получает один мягкий mechanism chunk и один dialogue_move chunk.
Writer отвечает живо, без термина “стыд”, если это звучало бы давяще.
Trace показывает всю цепочку.
```

---

## 18. Будущая декомпозиция PRD

### 18.1. PRD-047.16 — Mechanism-Aware KB Schema v1

Цель:

```text
Ввести минимальную schema и registry для mechanism-aware chunks.
```

Не цель:

```text
Переразметить всю БД и построить идеальную онтологию.
```

### 18.2. PRD-047.17 — Offline LLM Enrichment / Suggestion Mode

Цель:

```text
LLM предлагает metadata для chunks offline, но не является authority.
```

### 18.3. PRD-047.18 — KB Admin Review / Trace Preview

Цель:

```text
Web Admin показывает chunks, metadata, source_trace, retrieval reasoning и позволяет review/edit.
```

### 18.4. Отдельный будущий цикл — Backend ↔ Web Admin ↔ Trace Sync

Цель:

```text
Синхронизировать backend trace payload, Web Admin отображение, debug routes и evidence artifacts.
```

---

## 19. Короткая памятка для будущего архитектора

```text
Мы не строим систему:
“если пользователь сказал X — сделать Y”.

Мы строим систему:
“понять живой контекст,
мягко предположить нужный тип знания,
дать Writer’у компактную опору,
и оставить ему свободу ответить по-человечески”.
```

```text
БД — не цитатник.
БД — библиотека распознавания, дозировки и применения.
```

```text
Markers — не правила.
Mechanism hints — не диагноз.
Depth level — не маршрут.
Chunk — не команда.
Planner — не Writer.
Diagnostic Center — не судья.
Writer — живой автор ответа.
```

---

## 20. Change log v1.1

Добавлено относительно v1.0:

```text
- Anti-Heuristic Interpretation;
- Controlled Vocabulary vs Rule Engine;
- жёсткое различие markers examples и routing rules;
- список допустимых hard rules;
- bad/good implementation examples;
- Minimal First Implementation для PRD-047.16;
- evaluation checklist против скатывания в эвристики;
- усиление роли Writer freedom;
- запрет прямого маппинга слов пользователя на механизм;
- явное правило: этот документ — semantic reference, не rulebook.
```
