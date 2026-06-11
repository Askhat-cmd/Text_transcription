# TRANSFER BRIEF — Bot Psychologist / Neo MindBot после PRD-047.15-HF1 и стратегического плана PRD-047.15-HF2

> Этот документ нужно прикрепить или скопировать в новый чат ChatGPT, чтобы продолжить проект без потери архитектурного и продуктового контекста.
>
> В новый чат также обязательно прикрепить документ:
>
> `STRATEGIC_PLAN_PRD-047.15-HF2_Hybrid_Retrieval_Architecture_v1_RU`
>
> Его пользователь создавал отдельно как стратегический план перед PRD-047.15-HF2. Этот Transfer Brief ссылается на него как на главный архитектурный документ следующего этапа.

---

## 0. Роль нового чата

Ты продолжаешь проект **Bot Psychologist / Neo MindBot** как **архитектор проекта**.

Рабочая модель остаётся прежней:

```text
пользователь даёт ввод / сообщает, что IDE-агент выполнил PRD
→ архитектор проверяет GitHub
→ делает независимый архитектурный вывод
→ при необходимости создаёт стратегический документ / PRD / transfer brief
→ IDE-агент реализует
→ пользователь возвращается с результатом
→ новый аудит GitHub
```

IDE-агент — исполнитель. Архитектор в чате:

```text
- не верит только словам IDE-агента;
- сам проверяет GitHub через connector;
- сам читает implementation reports, logs, docs, task-list, diff;
- сверяет runtime scope, tests, encoding, no-stub gates;
- не добавляет новые PRD вслепую;
- не плодит эвристические правила;
- не превращает Composer в набор hardcoded тем;
- держит Writer единственным автором финального ответа;
- держит все retrieval/diagnostic/planner слои advisory/metadata-only;
- всегда честно пишет: passed / warning / blocker / docs mismatch.
```

Главная текущая стратегическая мысль:

```text
Мы прекращаем расширять доменные эвристики Composer’а.
Дальше движемся к Minimal Universal Heuristics + Hybrid LLM Retrieval Planner + Query-Before-RAG.
```

---

## 1. Что обязательно прикрепить в новый чат

В новом чате пользователь должен прикрепить два документа:

```text
1. TRANSFER_BRIEF_Bot_Psychologist_Neo_MindBot_AFTER_STRATEGIC_PLAN_PRD-047.15-HF2_DETAILED_RU
2. STRATEGIC_PLAN_PRD-047.15-HF2_Hybrid_Retrieval_Architecture_v1_RU
```

Стратегический план — главный документ для понимания следующего PRD. Transfer Brief — сжатая карта текущего состояния и правил продолжения.

Если новый чат не видит стратегический план, сначала попросить пользователя прикрепить его, а не писать PRD по памяти.

---

## 2. Репозиторий, локальный путь, важные директории

GitHub:

```text
https://github.com/Askhat-cmd/Text_transcription
```

Локальный путь пользователя:

```text
C:\My_practice\Text_transcription
```

Основные директории:

```text
bot_psychologist/       — основной runtime бота, multiagent pipeline, API, Web/Admin части проекта
TO_DO_LIST/             — PRD, task lists, reports, logs, evidence, acceptance artifacts
docs/                   — основная living documentation проекта в GitHub
Bot_data_base/          — возможный контур ingestion/storage/Chroma/API базы знаний, если присутствует локально
```

Важный нюанс по документации:

```text
Пользователь упоминал C:\My_practice\Text_transcription\bot_psychologist\docs.
В последних GitHub-аудитах актуальные living docs находились в корневой папке docs/.
Следующий PRD должен явно проверить и синхронизировать docs-контур, чтобы не было двух расходящихся источников правды.
```

---

## 3. Последний подтверждённый GitHub-статус

Последний проверенный этап:

```text
PRD-047.15-HF1 — Contextual Retrieval Composer Live Calibration / Owner Trace Review v1
```

Коммиты HF1:

```text
7041444 — PRD-047.15-HF1 composer live calibration evidence
22ea6e1 — PRD-047.15-HF1 post-push metadata sync
f2fefd6 — PRD-047.15-HF1 final metadata hash sync
```

Последний известный HEAD после проверки HF1:

```text
f2fefd6ede64150ebb81afd6b9db286fb6036ed2
```

При проверке новой реализации в будущем сравнивать от этого base, если пользователь не сообщил новый base:

```text
base = f2fefd6ede64150ebb81afd6b9db286fb6036ed2
head = текущий origin/main
```

HF1 был принят как:

```text
ACCEPTED WITH WARNING
```

Без blocker’ов.

Ключевые метрики HF1:

```text
cases_total: 40
automated_expected_match_rate: 0.825
literal_short_reply_query_count: 0
summary_external_kb_leak_count: 0
no_stub_violations_count: 0
false_positive_rag_count: 1
false_negative_rag_count: 6
weak_query_count: 0
llm_candidate_cases_count: 8
owner_review_status: sheet_created
live_trace_status: available
decision_recommendation: build_hybrid_llm_assist_for_low_confidence_cases
llm_calls_added: False
new_runtime_path_added: False
new_user_facing_stub_created: False
runtime_mutation_status: passed
encoding_gate_status: passed
tests_status: passed
known_blockers: empty
```

Главный смысл HF1:

```text
HF1 не должен был улучшить Composer.
HF1 должен был доказать, где deterministic Composer работает, а где начинает ломаться.
Он это доказал.
```

---

## 4. Принятое стратегическое решение после HF1

После анализа HF1 пользователь и архитектор согласовали:

```text
PRD-047.15-HF1.1 — Owner Trace Review Completion / Calibration Decisions v1
НЕ ДЕЛАТЬ.
```

Причина:

```text
Ручная разметка owner_trace_review_sheet сейчас создаст ещё один слой шума.
Стратегический вывод уже ясен: нельзя продолжать расширять эвристики.
```

Ключевой тезис пользователя:

```text
Короткие универсальные вещи типа “привет”, “пока”, “да”, “не хочу” можно оставить эвристикой.
Но все смысловые/доменные случаи нельзя пытаться учесть правилами.
Пользователи будут разными, вопросы будут разными, все темы не предусмотреть.
```

Архитектурный вывод:

```text
Heuristic-only Composer как baseline полезен.
Но дальше развивать его доменными правилами нельзя.
Следующий уровень — гибрид:
Minimal Universal Heuristics + LLM-assisted semantic retrieval planner.
```

---

## 5. Главный следующий документ уже создан

Перед Transfer Brief был создан стратегический документ:

```text
STRATEGIC_PLAN_PRD-047.15-HF2_Hybrid_Retrieval_Architecture_v1_RU
```

Он содержит:

```text
- почему HF1.1 пропускается;
- почему нельзя дальше расширять доменные эвристики;
- статус старых adaptive_runtime helper-файлов;
- карту текущих multiagent retrieval-слоёв;
- конфликт: Composer сейчас позже первичного RAG;
- целевую схему Query-Before-RAG;
- минимальные universal heuristics;
- запрет domain-specific hardcoded concepts;
- Hybrid LLM Retrieval Planner;
- JSON-контракт Planner’а;
- guardrails против user-facing текста;
- совместимость с fresh_chat_context_policy / dialogue_pragmatics / memory_retrieval / retrieval_decision;
- требования к Trace и Web Admin Panel;
- Writer Prompt Canvas Loss Audit;
- KB Chunk Quality Audit;
- план обновления документации;
- ADR-076;
- направление будущего PRD-047.15-HF2;
- границу для Transfer Brief и перехода в новый чат.
```

Новый чат должен сначала прочитать этот документ и только потом писать PRD-047.15-HF2.

---

## 6. История Composer и почему направление изменилось

### 6.1. PRD-047.15 — Contextual Retrieval Query Composer v1

PRD-047.15 добавил deterministic Composer:

```text
contextual_retrieval_query_composer_v1
```

Его задача:

```text
Не искать по последней фразе буквально.
Понять retrieval intent из контекста.
Решить: suppress_rag / use_current_context_only / query_kb / trace_only.
Передать Writer только компактный полезный RAG-контекст.
```

Примеры правильной логики:

```text
Пользователь: “Да, хорошо”
Предыдущий offer: “Могу объяснить это через ...”
→ не искать “Да, хорошо” буквально
→ наследовать тему из last_assistant_offer

Пользователь: “Подведи итог беседы”
→ use_current_context_only
→ не тащить внешнюю KB

Пользователь: “Привет”
→ suppress_rag
```

Статус PRD-047.15:

```text
ACCEPTED WITH WARNING
```

Warning был ожидаем: deterministic v1 нужно калибровать на живых/mixed cases.

### 6.2. PRD-047.15-HF1 — Calibration / Owner Trace Review

HF1 собрал 40 кейсов и показал:

```text
- базовые cases проходят;
- short literal query не происходит;
- summary не тащит KB;
- user-facing stubs не создаются;
- но mixed/low-confidence cases дают false negatives и false positives;
- 8 cases уже явно требуют hybrid/LLM assistance.
```

Поэтому дальнейший путь — не Owner Review HF1.1, а переход к Hybrid Retrieval Architecture.

---

## 7. Старые helper-файлы adaptive_runtime: что с ними

Пользователь спрашивал о старой системе:

```text
retrieval_stage_helpers.py
retrieval_pipeline_helpers.py
fast_path_stage_helpers.py
full_path_stage_helpers.py
```

По GitHub-истории эти файлы действительно существовали в старой adaptive_runtime-архитектуре. Старые коммиты говорили о выделении:

```text
adaptive_runtime/fast_path_stage_helpers.py
adaptive_runtime/full_path_stage_helpers.py
adaptive_runtime/retrieval_pipeline_helpers.py
adaptive_runtime/retrieval_stage_helpers.py
```

Но текущий `main` показывает:

```text
bot_psychologist/bot_agent/answer_adaptive.py — deprecated compatibility shim
Active runtime is multiagent_adapter
Legacy cascade was physically removed in PRD-041
```

Фактический текущий entrypoint:

```text
answer_adaptive deprecated shim
→ multiagent_adapter
→ multiagent.orchestrator
```

Вывод:

```text
Старый adaptive_runtime fast/full/retrieval-stage контур не является активным runtime path.
Он не должен прямо конфликтовать с новым Hybrid Composer.
```

Но важный риск не там. Риск в том, что похожие функции уже частично существуют внутри нового multiagent runtime.

---

## 8. Текущие active retrieval-related layers в multiagent

На момент последнего аудита активная retrieval/map chain выглядела так:

```text
State Analyzer
→ Thread Manager
→ MemoryRetrievalAgent.assemble(...)
→ Context Assembly
→ Dialogue Pragmatics
→ Fresh Chat Context Policy
→ Knowledge Answer Guard
→ Contextual Retrieval Decision
→ Final Answer Directive
→ Contextual Retrieval Query Composer
→ Writer Context Package
→ WriterContract
→ Writer
→ Validator
→ Final Answer Acceptance Gate
→ Memory write / trace / admin debug
```

Важно: порядок фактически неидеален для будущей архитектуры.

### 8.1. fresh_chat_context_policy.py

Роль:

```text
Universal fresh-chat / greeting / contact / cross-session memory isolation.
```

Этот слой уже умеет:

```text
- распознавать приветствие/контакт;
- определять fresh window;
- запрещать cross-session memory на свежем приветствии без явного question/continuation;
- разрешать память, если пользователь явно продолжает прошлую тему.
```

Стратегическое решение:

```text
Сохранить.
Не удалять.
Оставить как Universal Fresh Context Gate.
```

### 8.2. dialogue_pragmatics.py

Роль:

```text
Universal dialogue pragmatics:
- short utterance;
- affirmation;
- close_ack;
- imperative follow-up;
- previous assistant offer type;
- inherited user intent;
- should_not_ask_confirmation_again;
- retrieval_need_hint.
```

Стратегическое решение:

```text
Сохранить, но ограничить универсальной прагматикой.
Не превращать в доменный semantic planner.
Не добавлять туда domain-specific concepts.
```

### 8.3. MemoryRetrievalAgent._build_rag_query(...)

Это главный текущий конфликт.

Сейчас MemoryRetrievalAgent строит RAG query рано:

```text
rag_query = user_message + thread_state.core_direction + first_open_loop
```

Потом сразу выполняет `_load_rag(rag_query)`.

То есть первичный DB/RAG search сейчас происходит до того, как Composer сформировал осмысленный `composed_query`.

Текущая проблема:

```text
Если пользователь говорит “Да, хорошо”, primary RAG query может быть построен не из смысла согласия, а из текущей короткой фразы + thread_state.
Composer позже может понять, что нужно было искать иначе, но полноценный новый поиск уже не выполнен.
```

Стратегическое решение:

```text
В HF2 нужно сделать Query-Before-RAG:
retrieval plan должен появляться до DB/RAG execution.
MemoryRetrievalAgent должен уметь принимать approved retrieval_plan/composed_query.
```

### 8.4. build_contextual_retrieval_decision_v1

Роль:

```text
Chunk gate / inclusion policy over already available semantic hits.
```

Этот слой смотрит на:

```text
dialogue_pragmatics
knowledge_answer_guard
semantic_hits
fresh_chat_context_policy
```

и решает, включать ли chunks Writer’у.

Стратегическое решение:

```text
Сохранить как retrieval_decision/chunk gate.
Но не давать ему быть главным semantic query planner’ом.
```

### 8.5. contextual_retrieval_query_composer.py

Текущий Composer v1:

```text
- deterministic;
- post-primary-RAG plan/gate;
- умеет suppress/include;
- виден в debug trace;
- не создаёт user-facing text;
- не добавляет LLM call.
```

Стратегическое решение:

```text
Переработать в Hybrid Retrieval Planner layer:
- minimal universal heuristics pre-pass;
- LLM-assisted planner для semantic/mixed cases;
- strict JSON;
- no-user-facing-text;
- query-before-RAG.
```

---

## 9. Главный архитектурный конфликт, который должен закрыть HF2

Сейчас:

```text
user_message
→ MemoryRetrievalAgent._build_rag_query(...)
→ _load_rag(rag_query)
→ semantic_hits
→ retrieval_decision
→ Composer creates composed_query later
→ Writer context package
```

Должно стать:

```text
user_message + recent context + last assistant offer + thread state
→ Universal Heuristic Gates
→ if obvious: deterministic retrieval_plan
→ if semantic/mixed/ambiguous: LLM Retrieval Planner
→ strict JSON validation
→ approved composed_query
→ MemoryRetrievalAgent executes RAG with approved query
→ score policy / knowledge policy
→ retrieval_decision chunk gate
→ writer_context_package
→ WriterContract
→ Writer
```

Главное изменение:

```text
Composer/Planner должен управлять фактическим DB/RAG query ДО retrieval execution.
```

---

## 10. Минимальные Universal Heuristics, которые можно оставить

Разрешённые эвристики должны быть content-neutral.

Оставить:

```text
- greeting / hello / привет;
- farewell / bye / пока;
- thanks / спасибо;
- explicit yes / accept / да / согласен / давай;
- explicit no / reject / не хочу / не надо;
- explicit summary request / подведи итог / резюме;
- explicit formatting request / списком / markdown / таблицей;
- explicit brevity request / коротко / без теории;
- explicit no-practice request / без практик / не хочу упражнение;
- fresh-chat memory isolation;
- safety boundary, если уже существует отдельно.
```

Запретить в Composer hardcoded domain concepts:

```text
нейросталкинг
неосталкинг
Кузница Духа
автоматизм
защитный механизм
самореализация
стыд
тревога
отношения
родители
работа
деньги
любой другой доменный список тем
```

Причина:

```text
Пользователи будут разными.
Темы будут разными.
Список доменных правил всегда будет неполным.
Это снова приведёт к бесконечному циклу правок.
```

Доменные понятия должны извлекаться динамически:

```text
- из user_message;
- из recent_turns;
- из last_assistant_offer;
- из thread_state;
- из memory;
- из KB;
- из LLM semantic planner.
```

---

## 11. Целевой Hybrid LLM Retrieval Planner

Новый Hybrid Planner должен работать так:

```text
Universal heuristic pre-pass
→ если случай high-confidence и универсальный:
      принять deterministic decision без LLM
→ если случай semantic / mixed / ambiguous / low-confidence:
      вызвать LLM Retrieval Planner
→ получить metadata-only JSON
→ validate JSON
→ no-user-facing-text guard
→ execute approved query before RAG
```

LLM Planner не должен:

```text
- писать финальный ответ;
- писать совет пользователю;
- писать терапевтическую фразу;
- формировать summary text;
- подменять Writer;
- напрямую управлять style финального ответа;
- видеть себя как final-authority.
```

LLM Planner должен возвращать только JSON metadata.

Пример целевой схемы:

```json
{
  "version": "hybrid_llm_retrieval_planner_v1",
  "planner_mode": "llm_assisted_low_confidence",
  "retrieval_need": "knowledge_context|conversation_context|memory_context|mixed|none",
  "retrieval_action": "suppress_rag|use_current_context_only|query_kb|query_memory|query_kb_and_memory|trace_only",
  "query_source": "current_user_message|last_assistant_offer|recent_turns|thread_state|mixed_context",
  "composed_query": "...",
  "query_terms": [],
  "needs_kb": true,
  "needs_memory": false,
  "include_for_writer_if_found": true,
  "max_chunks_for_writer": 3,
  "max_chars_per_chunk": 700,
  "writer_can_ignore_rag": true,
  "confidence": 0.0,
  "reason": "...",
  "evidence": [],
  "no_user_facing_text_created": true
}
```

---

## 12. Важные guardrails для LLM Planner

HF2 должен требовать:

```text
1. LLM Planner output is JSON only.
2. Strict schema validation.
3. Timeout/fallback.
4. No user-facing text allowed.
5. No final answer text allowed.
6. No therapy/advice sentence allowed.
7. If invalid JSON → deterministic safe fallback.
8. If confidence low → trace_only / use_current_context_only / suppress_rag depending on universal gate.
9. Writer remains final answer author.
10. Planner trace must be visible in debug/admin.
```

Если LLM Planner возвращает что-то похожее на пользовательский ответ, это blocker.

---

## 13. Trace и Web Admin Panel

На момент последнего аудита Composer уже попадал в API debug payload:

```text
retrieval_decision
contextual_retrieval_query_composer
rag_query
writer_chunks_detail
writer_chunks_candidate_detail
writer_system_prompt
writer_user_prompt
writer_llm_response_raw
```

Но отдельной нормальной Admin Panel карточки Composer/Planner пока нет.

HF2 должен добавить в Trace/Admin:

```text
- Universal heuristic gate result;
- Planner mode: heuristic_only / llm_assisted / fallback;
- LLM Planner called: yes/no;
- Planner JSON;
- planner validation status;
- composed_query;
- executed_rag_query;
- query_source;
- retrieval_action;
- retrieval_need;
- candidate chunks;
- included chunks;
- rejected chunks + reason;
- writer_can_ignore_rag;
- prompt canvas / writer context delivery status;
- cost/latency for LLM Planner call;
- fallback reason if LLM planner failed.
```

Admin surface should show this in a developer-readable way at:

```text
http://localhost:3000/admin
```

Important:

```text
Admin/Trace must expose Composer/Planner observability.
It must not become a manual tuning UI full of domain-specific rules.
```

---

## 14. Writer Prompt Canvas Loss Audit

Пользователь отдельно попросил заложить ручную проверку:

```text
Проверить в trace / LLM-полотне, полностью ли вся нужная информация доходит до Writer, или что-то режется и теряется.
```

HF2 должен включить `Writer Prompt Canvas Loss Audit`.

Проверять цепочку:

```text
retrieval_plan
→ executed_rag_query
→ raw candidate chunks
→ score-filtered chunks
→ knowledge-policy allowed chunks
→ retrieval_decision included chunks
→ writer_context_package
→ WriterContract prompt context
→ writer_user_prompt / writer_system_prompt
→ final answer
```

Вопросы аудита:

```text
- нужный chunk был найден?
- если найден, был ли он отфильтрован?
- если включён, не был ли он слишком сильно обрезан?
- дошёл ли он до WriterContract?
- попал ли он в writer_user_prompt?
- понял ли его Writer?
- если ответ слабый, это проблема retrieval, prompt canvas или Writer?
```

Обязательные артефакты будущего PRD должны включать:

```text
TO_DO_LIST/logs/PRD-047.15-HF2/prompt_canvas_loss_audit.json
TO_DO_LIST/logs/PRD-047.15-HF2/prompt_canvas_loss_audit.md
TO_DO_LIST/logs/PRD-047.15-HF2/prompt_canvases/**
TO_DO_LIST/logs/PRD-047.15-HF2/raw_traces/**
```

---

## 15. KB Chunk Quality Audit

На вопрос “хорошо ли сейчас подготовлены чанки в БД” честный ответ был:

```text
По одному GitHub-коду нельзя достоверно сказать, хорошо ли нарезаны реальные chunks в Chroma/БД.
Нужно смотреть сами chunks и их metadata.
```

Что известно по коду:

```text
RAG_N_RESULTS = 4
RAG_MIN_SCORE = 0.45
RAG_QUERY_MAX_LEN = 300
low-score salvage enabled
score policy and knowledge policy exist
```

Но неизвестно:

```text
- реальный размер chunks;
- есть ли overlap;
- не обрываются ли мысли;
- самодостаточны ли chunks;
- есть ли title/source/section metadata;
- не смешаны ли разные темы в одном chunk;
- не теряются ли definitions/use_when/avoid_when;
- какие chunks реально доходят до Writer.
```

HF2 или отдельный HF2.x должен включить `KB Chunk Quality Audit v1`.

Минимальные проверки:

```text
- sample 50-100 chunks;
- chunk length distribution;
- metadata completeness;
- source/section consistency;
- boundary quality;
- semantic self-containedness;
- overlap presence;
- duplicate chunks;
- empty/near-empty chunks;
- chunks too large / too small;
- query-to-chunk relevance examples;
- chunks that reached Writer vs chunks filtered out.
```

---

## 16. Документация после перехода на новый уровень

Следующий PRD должен обновить docs:

```text
docs/PROJECT_STATE.md
docs/ROADMAP.md
docs/PRD_INDEX.md
docs/DECISIONS.md
```

И проверить наличие/состояние:

```text
bot_psychologist/docs/**
```

Если `bot_psychologist/docs` существует локально, нужно решить:

```text
- либо синхронизировать с root docs/;
- либо объявить stale/deprecated;
- либо перенести нужные документы;
- либо явно указать, что living docs — root docs/.
```

В docs нужно зафиксировать:

```text
- active runtime is multiagent_adapter;
- old adaptive_runtime stage helpers are non-active/legacy;
- universal heuristic gates are narrow and content-neutral;
- domain-specific Composer heuristics are forbidden;
- semantic retrieval planning is LLM-assisted for mixed/low-confidence cases;
- Planner is metadata-only;
- Writer remains final answer author;
- Query-Before-RAG is target retrieval architecture;
- Composer/Planner must be visible in Trace/Admin;
- prompt canvas loss audit and chunk audit are required evidence.
```

Рекомендуемый ADR:

```text
ADR-076 — Hybrid Retrieval Planner and Query-Before-RAG replace domain-specific Composer heuristics
```

---

## 17. Следующий PRD: что писать

Следующий PRD должен быть:

```text
PRD-047.15-HF2 — Minimal Universal Heuristics + Hybrid LLM Retrieval Planner / Query-Before-RAG v1
```

Но перед его написанием новый чат должен:

```text
1. Прочитать этот Transfer Brief.
2. Прочитать STRATEGIC_PLAN_PRD-047.15-HF2_Hybrid_Retrieval_Architecture_v1_RU.
3. При необходимости кратко проверить GitHub HEAD.
4. Не возвращаться к HF1.1.
5. Не предлагать ручную разметку owner sheet.
6. Не писать ещё одну калибровку эвристик.
7. Писать PRD сразу под архитектурный переход.
```

---

## 18. Обязательная структура PRD-047.15-HF2

PRD-HF2 должен включить:

```text
0. Краткое резюме
1. Контекст и причина перехода
2. Source gates
3. Non-goals
4. Current runtime/retrieval inventory
5. Universal heuristic gates
6. Domain-specific heuristic quarantine
7. Hybrid LLM Retrieval Planner
8. JSON contract and validator
9. Query-Before-RAG integration
10. MemoryRetrievalAgent changes
11. Retrieval decision / chunk gate compatibility
12. WriterContextPackage / WriterContract compatibility
13. Trace/Admin Panel visibility
14. Writer Prompt Canvas Loss Audit
15. KB Chunk Quality Audit
16. Tests
17. Live/browser/admin smoke
18. Required artifacts
19. Runtime mutation scope proof
20. Encoding gate
21. Docs sync
22. Acceptance criteria
23. Implementation report requirements
24. Next PRD recommendation
25. Final instruction for IDE-agent
```

---

## 19. Non-goals для PRD-047.15-HF2

Новый PRD должен прямо запретить:

```text
- LLM Planner writing user-facing answers;
- LLM Planner replacing Writer;
- domain-specific concept lists in Composer code;
- adding new final answer fallback text;
- changing Writer style philosophy;
- broad production rollout;
- DB schema changes unless explicitly necessary;
- KB governance mutation unless scoped;
- removing existing fresh_chat_context_policy;
- removing dialogue_pragmatics entirely;
- reactivating old adaptive_runtime path;
- creating parallel runtime path;
- hiding Planner decisions from trace/admin.
```

---

## 20. Expected implementation status for HF2

HF2 is likely complex. Expected final status may be:

```text
warning
```

Warning is acceptable if:

```text
- hybrid planner is implemented behind strict feature flag / dev mode;
- core query-before-RAG path works in direct tests;
- trace/admin expose decisions;
- live smoke is limited but honest;
- chunk audit is partial but artifacted;
- no user-facing text is created by Planner;
- Writer remains final author.
```

Blocker if:

```text
- LLM Planner writes user answer;
- composed_query is not used before RAG;
- old user_message-only RAG remains primary for semantic/mixed cases;
- no JSON validation;
- invalid LLM output can reach Writer unguarded;
- Planner creates hidden authority over Writer;
- Admin/Trace cannot show decision chain;
- tests fail;
- encoding gate fails;
- docs not synced.
```

---

## 21. Как проверять GitHub после HF2

Когда пользователь в новом чате скажет: “агент ИДЕ закончил реализацию PRD-047.15-HF2”, делать аудит:

```text
1. search_commits PRD-047.15-HF2
2. fetch implementation report
3. fetch task list
4. compare commits from base f2fefd6... to new HEAD unless report gives another base
5. inspect runtime files changed
6. inspect planner module
7. inspect MemoryRetrievalAgent query-before-RAG integration
8. inspect JSON schema/validator
9. inspect no-user-facing-text guard
10. inspect trace/admin exposure
11. inspect tests and acceptance artifacts
12. inspect prompt canvas loss audit
13. inspect chunk quality audit
14. inspect docs sync
15. conclude accepted/warning/blocker
```

Required files likely:

```text
TO_DO_LIST/PRD-047.15-HF2_TASK_LIST.md
TO_DO_LIST/reports/PRD-047.15-HF2_IMPLEMENTATION_REPORT.md
TO_DO_LIST/reports/PRD-047.15-HF2_NEXT_PRD_RECOMMENDATION.md
TO_DO_LIST/logs/PRD-047.15-HF2/**
docs/PROJECT_STATE.md
docs/ROADMAP.md
docs/PRD_INDEX.md
docs/DECISIONS.md
```

---

## 22. User preferences and working style

Пользователь предпочитает:

```text
- русский язык;
- простое объяснение сложной архитектуры;
- честные статусы;
- не раздувать ответы пустой теорией;
- стратегическую ясность;
- downloadable .md/.docx artifacts для PRD/brief/plan;
- проверку GitHub перед архитектурными выводами;
- чтобы assistant говорил прямо, если путь ведёт в замкнутый круг;
- не продолжать бесконечные эвристики;
- не создавать шум.
```

Пользователь уже явно сказал:

```text
“Я не хочу сейчас ручную разметку.”
“Я бы оставил только действительно базовые вещи, которые присущи всем.”
“Всё остальное строил бы на ЛЛМ основе.”
“Не хочу двигаться по замкнутому кругу и плодить шум.”
```

Это является важным продуктовым решением.

---

## 23. Важные системные предупреждения для нового чата

### 23.1. Не повторять вопрос, на который ответ уже есть

Если пользователь говорит “пиши PRD”, не спрашивать снова, делать ли HF1.1. Решение уже принято:

```text
HF1.1 skipped.
Next = PRD-047.15-HF2.
```

### 23.2. Не искать текущие факты из памяти, если нужен GitHub

Для проверки реализации использовать GitHub connector, не внутреннюю память.

### 23.3. Не создавать PRD в теле чата

Для больших PRD/brief/plan создавать файл в `/mnt/data` и давать ссылку:

```text
sandbox:/mnt/data/<filename>.md
sandbox:/mnt/data/<filename>.docx
```

### 23.4. Если создаётся DOCX

Нужно рендерить DOCX в PNG и визуально проверить перед отдачей.

### 23.5. Не ссылаться на старые adaptive_runtime helpers как active runtime

Сейчас active runtime:

```text
multiagent_adapter
```

Старый adaptive runtime — legacy / deprecated / removed from active path.

---

## 24. Короткая карта будущего целевого pipeline

Целевая архитектура после HF2:

```text
User message
→ State Analyzer / Thread Manager
→ Fresh Chat Context Policy
→ Dialogue Pragmatics
→ Universal Heuristic Gate
→ if high-confidence universal:
      deterministic retrieval_plan
  else:
      LLM Retrieval Planner JSON
→ JSON validation / no-user-facing guard
→ approved composed_query
→ MemoryRetrievalAgent executes RAG with approved query
→ score policy / knowledge policy
→ retrieval_decision chunk gate
→ writer_context_package
→ WriterContract prompt context
→ Writer final answer
→ Validator / Final Answer Acceptance Gate
→ Trace/Admin/Prompt Canvas evidence
→ healthy memory write only if accepted
```

Главная разница с текущим состоянием:

```text
Сейчас Composer поздно фильтрует/планирует.
После HF2 Planner должен управлять query до RAG.
```

---

## 25. Минимальная формулировка следующего задания для нового чата

Когда пользователь попросит создать PRD, правильный ответ должен быть не объяснение заново, а действие:

```text
Создаю PRD-047.15-HF2 — Minimal Universal Heuristics + Hybrid LLM Retrieval Planner / Query-Before-RAG v1
на основе Transfer Brief и STRATEGIC_PLAN_PRD-047.15-HF2_Hybrid_Retrieval_Architecture_v1_RU.
```

И затем создать downloadable PRD document.

---

## 26. Что считать успехом следующего шага

Успех PRD-047.15-HF2 как документа:

```text
- он не продолжает эвристический цикл;
- он чётко разводит роли current layers;
- он убирает domain-specific hardcoded Composer logic;
- он задаёт hybrid planner только для semantic/mixed cases;
- он требует query-before-RAG;
- он требует Admin/Trace visibility;
- он требует prompt canvas loss audit;
- он требует chunk quality audit;
- он требует docs sync;
- он сохраняет Writer как final answer author;
- он содержит жёсткие blocker criteria.
```

Успех реализации HF2:

```text
- Planner metadata-only;
- JSON validation работает;
- composed_query реально используется до DB/RAG;
- old user-message-only query больше не является главным для semantic/mixed cases;
- universal gates не разрастаются в domain-specific rules;
- chunks selected/rejected прозрачно видны;
- Writer получает полный нужный context;
- админка показывает Composer/Planner;
- docs обновлены;
- no user-facing stubs;
- tests/lives/admin/browser evidence честные.
```

---

## 27. Финальный контекст для нового архитектора

Проект сейчас находится в точке архитектурного поворота.

До PRD-047.15 система шла к тому, чтобы не искать по последней фразе буквально.
PRD-047.15 дал deterministic Composer.
HF1 доказал, что Composer полезен как baseline, но не должен бесконечно расширяться эвристиками.
Пользователь осознанно отказался от ручной разметки HF1.1 и выбрал переход к гибридной модели.

Следующий чат должен продолжить именно эту линию:

```text
не больше правил;
только минимальные universal gates;
LLM-assisted semantic retrieval planning;
query-before-RAG;
Writer remains final author;
full trace/admin/prompt-canvas visibility;
chunk quality audit;
docs truth sync.
```

Главный документ, который нужно использовать вместе с этим brief:

```text
STRATEGIC_PLAN_PRD-047.15-HF2_Hybrid_Retrieval_Architecture_v1_RU
```

Конечный следующий артефакт:

```text
PRD-047.15-HF2_Minimal_Universal_Heuristics_Hybrid_LLM_Retrieval_Planner_Query_Before_RAG_v1_RU.md
```
