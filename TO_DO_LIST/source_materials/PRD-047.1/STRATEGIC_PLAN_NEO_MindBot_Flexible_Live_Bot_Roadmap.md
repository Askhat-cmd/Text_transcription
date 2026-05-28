# СТРАТЕГИЧЕСКИЙ ПЛАН — Neo MindBot / Bot Psychologist

**Версия:** v1.0  
**Назначение:** опорный документ для дальнейших PRD, аудитов GitHub и продолжения проекта в новом чате без потери контекста.  
**Текущий фокус:** сделать бота более гибким, живым и понимающим на основе философии «Кузницы Духа», сохраняя модульность, Web Admin-настраиваемость, trace-аудит и безопасность.

---

## 0. Главная формула проекта

Bot Psychologist / Neo MindBot не должен быть просто «психологическим чат-ботом» и не должен быть системой жёстких сценариев.

Целевая формула:

```text
NEO = живой диалоговый агент + управляемый multiagent harness + философское ядро Кузницы Духа + наблюдаемый trace + Web Admin control plane.
```

Бот должен:

- отвечать свободно и по ситуации;
- держать линию разговора;
- видеть состояние и готовность пользователя;
- не вставлять практики без основания;
- использовать «Кузницу Духа» как внутреннюю философию и библиотеку линз, а не как цитатник;
- не становиться духовным авторитетом или терапевтом;
- быть полностью наблюдаемым через trace;
- быть настраиваемым через Web Admin;
- оставаться простым, модульным и расширяемым.

---

## 1. Рабочая модель архитектора и IDE-агента

### 1.1. Роль архитектора в чате

Архитектор:

```text
аудит GitHub
→ архитектурный вывод
→ план / PRD / transfer document
→ IDE-агент реализует
→ пользователь сообщает о выполнении
→ новый аудит GitHub
→ следующий PRD
```

Архитектор не должен перекладывать проектирование на IDE-агента. IDE-агент — исполнитель.

### 1.2. Формат будущих PRD

Каждый новый PRD должен создаваться как отдельный `.md` файл для скачивания. Не расписывать весь PRD в чат, чтобы не перегружать контекст.

В чат выводить только:

```text
1. Краткий итог аудита GitHub.
2. Решение: accept / warning / blocker.
3. Краткое содержание следующего PRD.
4. Ссылку на файл PRD для скачивания.
```

### 1.3. Обязательная структура каждого PRD

Каждый PRD должен включать:

```text
0. Краткое резюме
1. Контекст
2. Цель
3. Non-goals
4. Source gates / pre-audit
5. Требования к runtime
6. Требования к Web Admin, если затрагивается настройка
7. Требования к trace / evaluation
8. Требования к документации
9. Тесты
10. Smoke/live проверки
11. Required artifacts
12. No-mutation proof
13. Acceptance criteria
14. Implementation report requirements
15. Next PRD recommendation
16. Final instruction for IDE agent
```

### 1.4. Обязательные артефакты каждого PRD

Перед кодингом IDE-агент обязан создать:

```text
TO_DO_LIST/PRD-XXX_TASK_LIST.md
```

После реализации:

```text
TO_DO_LIST/reports/PRD-XXX_IMPLEMENTATION_REPORT.md
TO_DO_LIST/reports/PRD-XXX_NEXT_PRD_RECOMMENDATION.md
TO_DO_LIST/logs/PRD-XXX/test_command_output.txt
TO_DO_LIST/logs/PRD-XXX/*.json
TO_DO_LIST/logs/PRD-XXX/no_mutation_proof.json
```

Implementation report должен быть обновлён **после финального commit/push**.

### 1.5. Git и документация

Каждый PRD должен требовать:

```text
- commit в main;
- push в origin/main;
- post-push metadata sync;
- обновление docs/PROJECT_STATE.md;
- обновление docs/ROADMAP.md;
- обновление docs/PRD_INDEX.md;
- обновление docs/DECISIONS.md, если принято архитектурное решение;
- сохранение безопасных/sanitized логов в TO_DO_LIST;
- не коммитить .env, ключи, secrets, raw provider payload, raw private logs, sqlite/db/cache, .venv, node_modules.
```

---

## 2. Текущий статус после PRD-047.0-HF1

### 2.1. Что принято

`PRD-047.0-HF1` закрыл важный разрыв: evaluator теперь проверяет не только internal guard flags, но и итоговый текст ответа.

Принято:

```text
- evaluator false positives закрыты на answer-level;
- greeting больше не должен запускать практику без основания;
- known internal concept answer-first укреплён;
- relation case получает fallback grounding;
- direct baseline 5/5 passed;
- no-mutation proof зелёный;
- implementation report и task list есть;
- docs обновлены.
```

### 2.2. Что остаётся warning, но не blocker

HF1 можно принять как технически завершённый, но качество ответов всё ещё не является целевым.

Наблюдаемые warnings:

```text
- некоторые direct-ответы всё ещё звучат слишком технически;
- местами тон скачет между «ты» и «вы»;
- relation answer по нейросталкингу пока может звучать как объяснительный текст, а не живой ответ;
- live mode был skipped из-за stale/not restarted backend;
- текущий evaluator ловит грубые ошибки, но ещё не оценивает глубину, живость и удержание линии.
```

Это не требует немедленного HF2, если следующий трек будет направлен на общую живость, философское ядро, Active Frame и Writer Freedom Contract.

---

## 3. Главная архитектурная проблема текущего бота

Текущая multiagent-система стала достаточно мощной, но местами слишком директивной для Writer.

Проблема:

```text
State Analyzer / Thread Manager / Diagnostic Card / Writer Contract
дают Writer’у слишком жёсткие команды.
Если ранний слой ошибся, Writer добросовестно выполняет ошибочный режим.
```

Пример уже проявился:

```text
RAG нашёл определение НейроСталкинга,
но Writer получил режим clarify/reflect + ask_one_question
и попросил пользователя определить термин заново.
```

Правильное направление:

```text
Не убрать multiagent-систему.
А изменить её роль:
не командовать Writer’ом,
а готовить для него ясную сцену и мягкий вектор.
```

---

## 4. Целевая архитектурная философия

### 4.1. Hard rules vs Soft guidance

Нужно разделить жёсткие правила и мягкие подсказки.

**Hard rules:**

```text
- safety;
- crisis routing;
- не диагноз;
- не медицинский/финансовый/юридический совет;
- не духовный авторитет;
- не raw-цитатник Кузницы;
- не практика без основания;
- не раскрывать приватные данные;
- не обходить governance через debug/trace.
```

**Soft guidance:**

```text
- состояние пользователя;
- active line;
- pattern core;
- possible next move;
- suggested depth;
- useful lens;
- response mode;
- target micro-shift.
```

Writer должен быть ограничен hard rules, но внутри soft guidance должен иметь свободу писать живо.

### 4.2. Writer как живой автор ответа

Writer не должен быть «исполнителем JSON-команды». Он должен быть живым автором ответа, которому система дала:

```text
- кто перед ним;
- что уже было;
- какая линия разговора;
- какая внутренняя линза уместна;
- какие знания точно релевантны;
- что нельзя делать;
- какой следующий микро-сдвиг возможен.
```

И дальше:

```text
Ответь естественно, по ситуации, не шаблонно.
```

---

## 5. Роль «Кузницы Духа»

### 5.1. Кузница не должна быть цитатником

Кузница должна работать не как:

```text
пользователь спросил → достали кусок → пересказали книгу
```

А как:

```text
пользовательский запрос
→ Diagnostic/Planner понимает состояние и линию
→ выбирается внутренняя линза
→ Writer отвечает живо, опираясь на философию, но не цитируя её как авторитет.
```

### 5.2. Два слоя Кузницы

Нужно разделить:

#### A. Philosophy Kernel

Компактное постоянное ядро бота:

```text
- с человеком всё в порядке;
- программа — не человек;
- автоматизм — адаптация;
- страдание часто является защитой;
- наблюдение важнее насильственного исправления;
- видение создаёт пространство;
- практика не должна подменять понимание;
- бот — зеркало/навигатор/катализатор, не гуру;
- ясность не драматична;
- жизнь не нужно исправлять.
```

Это ядро должно быть доступно Writer’у почти всегда, но компактно.

#### B. Knowledge / Lens Library

RAG-база:

```text
- понятия;
- главы;
- практики;
- драйверы;
- примеры;
- use_when / avoid_when;
- mirror-фразы;
- диагностические линзы.
```

Этот слой используется по необходимости, а не каждый раз.

### 5.3. Иерархическая карта НейроСталкинга

Документ `🧭 ИЕРАРХИЧЕСКАЯ КАРТА НЕЙРОСТАЛКИНГА.md` полезен как основа для Philosophy Kernel и concept map.

Из него можно выделить:

```text
- онтологическое основание;
- нейрофизиологическую архитектуру;
- программу «несовершенное Я»;
- драйверы;
- метанаблюдение;
- ловушки;
- практические принципы;
- заключительные основания.
```

Но его нельзя просто превратить в длинный prompt. Нужно сделать компактное машинно-читаемое ядро.

---

## 6. Wake_up как референс механики, не стиля

Wake_up полезен не как стиль для копирования, а как пример механики:

```text
- держит одну линию;
- не начинает каждый ответ заново;
- использует ответ пользователя как материал следующего хода;
- видит паттерн за разными темами;
- не даёт практику автоматически;
- задаёт один сильный вопрос;
- делает один следующий смысловой шаг;
- связывает текущий ответ с предыдущим выбором пользователя.
```

Не копировать:

```text
- драматизацию;
- давление;
- чрезмерные «щелчки»;
- авторитарные интерпретации;
- стиль «я вижу тебя насквозь».
```

Цель не «говорить как Wake_up», а:

```text
вести линию разговора так же устойчиво,
но в более безопасной, мягкой и управляемой манере Neo MindBot.
```

---

## 7. Целевая multiagent architecture v2

### 7.1. Runtime Plane

```text
User Message
  ↓
State Analyzer
  ↓
Thread Manager
  ↓
Memory Retrieval
  ↓
Knowledge / Lens Routing
  ↓
Active Frame Builder
  ↓
Response Planner
  ↓
Writer Contract v3
  ↓
Writer
  ↓
Validator / Quality Evaluator
  ↓
Memory Writer / Trace
```

### 7.2. Роли компонентов

#### State Analyzer

Определяет текущее состояние:

```json
{
  "nervous_state": "window|hyper|hypo",
  "intent": "contact|clarify|explore|validate|solution|practice|vent|safety",
  "openness": "open|mixed|defensive|collapsed",
  "ok_position": "I+W+|I-W+|I+W-|I-W-",
  "confidence": 0.0
}
```

#### Thread Manager

Держит структуру диалога:

```json
{
  "thread_id": "...",
  "relation_to_thread": "continue|branch|new_thread|return",
  "phase": "contact|clarify|explore|integrate|action|stabilize",
  "open_loops": [],
  "closed_loops": [],
  "core_direction": "..."
}
```

#### Active Frame Builder

Собирает живую смысловую рамку:

```json
{
  "active_line": "...",
  "pattern_core": "...",
  "last_meaningful_shift": "...",
  "current_open_loop": "...",
  "what_user_is_really_asking": "...",
  "what_not_to_repeat": [],
  "line_confidence": 0.0
}
```

#### Knowledge / Lens Routing

Решает, нужна ли база:

```json
{
  "kb_needed": true,
  "kb_role": "concept_answer|lens_support|practice_support|not_needed",
  "concepts": [],
  "selected_lens": [],
  "rag_hits_allowed_for_writer": [],
  "kernel_only_sufficient": false
}
```

#### Response Planner

Не пишет ответ. Выбирает следующий ход:

```json
{
  "answer_move": "contact|reflect|inform|deepen|decenter|stabilize|practice|repair|integrate",
  "target_micro_shift": "...",
  "depth": "short|medium|deep",
  "practice_allowed": false,
  "question_allowed": true,
  "max_questions": 1,
  "must_include": [],
  "must_avoid": [],
  "tone_vector": "warm_clear|soft_direct|grounding|conceptual"
}
```

#### Writer

Пишет только финальный человеческий ответ.

Writer не должен:

```text
- сам менять thread;
- сам решать safety;
- сам делать произвольный RAG;
- сам превращать ответ в практику без разрешения;
- сам раскрывать внутренние labels.
```

#### Validator / Quality Evaluator

Проверяет:

```text
- safety;
- no diagnosis;
- no unsolicited practice;
- no generic answer;
- line preserved;
- no closed-loop repetition;
- answer follows target_micro_shift;
- not too long / not too short;
- tone fit;
- no raw quote misuse.
```

---

## 8. Web Admin как Control Plane

Пользователь изначально задумывал бота как систему, полностью настраиваемую через Web Admin. Это должно стать архитектурным принципом.

### 8.1. Что должно настраиваться через Web Admin

Постепенно вынести в Web Admin:

```text
- prompts агентов;
- Philosophy Kernel версии;
- Writer freedom level;
- response mode routing strictness;
- Practice Gate policy;
- RAG thresholds;
- max RAG hits;
- context budget;
- model per agent;
- temperature / max_tokens per agent;
- validator quality strictness;
- debug verbosity;
- enabled/disabled toggles для новых модулей;
- rollout mode: shadow/test_apply/developer_local.
```

### 8.2. Принцип runtime overrides

Web Admin должен писать в runtime overrides / admin config, а не напрямую ломать код.

Предпочтительная модель:

```text
base defaults in code
+ config registry
+ admin overrides
+ effective runtime payload
```

### 8.3. Effective state везде

Каждая настройка должна иметь:

```json
{
  "default_value": "...",
  "admin_override": "...",
  "effective_value": "...",
  "source": "default|admin_override|env|safe_fallback"
}
```

### 8.4. Web Admin не должен быть просто UI

Web Admin = control plane.

Для каждого нового модуля будущий PRD должен задавать:

```text
- backend effective endpoint;
- optional control endpoint;
- UI tab/section;
- reset to safe default;
- trace visibility;
- docs update;
- tests.
```

---

## 9. Trace / Observability как Evaluation Plane

Trace должен отвечать не только на вопрос:

```text
что произошло?
```

Но и на вопрос:

```text
почему ответ получился именно таким?
```

### 9.1. Целевой trace snapshot

```json
{
  "state_analyzer": {...},
  "thread_manager": {...},
  "active_frame": {...},
  "knowledge_routing": {...},
  "response_planner": {...},
  "writer_contract": {...},
  "quality_trace": {...},
  "validator": {...},
  "final_answer_summary": {
    "length_bucket": "short|medium|long",
    "question_count": 0,
    "practice_present": false,
    "line_continuity": "ok|weak",
    "generic_risk": "low|medium|high"
  }
}
```

### 9.2. Trace как аудит качества

Quality flags должны включать:

```text
- too_generic;
- too_long_for_state;
- too_short_for_context;
- lost_active_line;
- repeated_closed_loop;
- practice_without_gate;
- kb_answer_missing;
- over_explained;
- too_many_questions;
- externalized_authority;
- wrong_tone;
- missing_micro_shift.
```

Сначала flags могут быть deterministic. Позже можно добавить LLM judge, но только после хорошего deterministic baseline.

---

## 10. Модульная файловая архитектура

Будущие PRD должны придерживаться читаемой файловой структуры.

### 10.1. Общий принцип

```text
Один модуль = одна ответственность.
Один PRD = минимум затронутых зон.
Никаких огромных файлов, куда складывается всё подряд.
```

### 10.2. Рекомендуемая структура runtime-модулей

```text
bot_psychologist/bot_agent/multiagent/
  agents/
    state_analyzer.py
    thread_manager.py
    memory_retrieval.py
    writer_agent.py
    validator_agent.py
  contracts/
    writer_contract.py
    planner_contract.py
  planning/
    active_frame_builder.py
    response_planner.py
    practice_gate.py
    answer_move_policy.py
  knowledge/
    philosophy_kernel.py
    knowledge_lens_router.py
    concept_registry.py
  evaluation/
    quality_flags.py
    answer_compliance.py
    dialogue_line_eval.py
  config/
    runtime_config_registry.py
    admin_overrides.py
  trace/
    trace_sanitizer.py
    quality_trace.py
```

Не обязательно сразу создавать все директории. Но новые PRD должны добавлять файлы в логичные места, а не расширять бесконечно один orchestrator.

### 10.3. Scripts

```text
bot_psychologist/scripts/
  run_prd_XXX_*.py
  audit_prd_XXX_*.py
  smoke_prd_XXX_*.py
```

Каждый script должен иметь:

```text
--mode dry|direct|live
--case-id
--limit
--output
--trace-output
```

### 10.4. Tests

```text
bot_psychologist/tests/
  test_*.py
  evaluation/
    prd_XXX_cases.json
    prd_XXX_expected.json
```

### 10.5. Docs

```text
bot_psychologist/docs/
  philosophy_kernel.md
  response_planner.md
  active_frame.md
  web_admin_control_plane.md
  trace_quality.md
```

Top-level docs:

```text
docs/PROJECT_STATE.md
docs/ROADMAP.md
docs/PRD_INDEX.md
docs/DECISIONS.md
```

---

## 11. Дорожная карта реализации

### Stage 0 — HF1 Acceptance + Live Verification

Статус: PRD-047.0-HF1 можно принять с warning.

Цель следующего микро-шагa при необходимости:

```text
проверить live backend после restart и убедиться,
что HF1 реально работает в Web UI / live API.
```

Если в живом UI вновь проявятся старые ошибки — делать `PRD-047.0-HF2`.

Если нет — двигаться дальше.

---

### Stage 1 — NEO Philosophy Kernel v1

Цель:

```text
Вынести философию Кузницы из случайного RAG в компактное управляемое ядро Writer’а.
```

Что сделать:

```text
- создать Philosophy Kernel data structure;
- выделить 12–20 принципов;
- разделить user-facing и internal-only formulations;
- добавить kernel_version;
- добавить trace поля: kernel_used, kernel_version, kernel_principles_applied;
- добавить Web Admin read-only/editable surface;
- не менять RAG/Chroma;
- не превращать Kernel в длинный prompt.
```

Кандидат PRD:

```text
PRD-047.1 — NEO Philosophy Kernel + Writer Freedom Contract Foundation v1
```

---

### Stage 2 — Writer Freedom Contract v1

Цель:

```text
Сделать Writer менее зажатым, но не менее безопасным.
```

Смысл:

```text
Меньше hard must-do.
Больше мягкого guidance.
Writer получает сцену и вектор, а не клетку.
```

Что сделать:

```text
- разделить hard_rules и soft_guidance в WriterContract;
- добавить writer_freedom_level;
- добавить answer_move вместо жёсткого response_mode там, где возможно;
- убрать обязательный question, если knowledge_answer_first или contact/no-practice;
- добавить prompt rule: choose natural form according to situation;
- оценивать итоговый ответ, а не только compliance flags.
```

---

### Stage 3 — Active Frame / Dialogue Line v1

Цель:

```text
Бот должен держать линию разговора как смысловой процесс,
а не только как последние реплики.
```

Что сделать:

```text
- active_line;
- pattern_core;
- last_meaningful_shift;
- current_open_loop;
- closed_loop_semantic_summary;
- return_to_line detection;
- branch vs same-pattern detection;
- trace display.
```

Примеры полей:

```json
{
  "active_line": "страх проявиться и быть оценённым",
  "pattern_core": "я недостаточен / я не справлюсь",
  "last_meaningful_shift": "пользователь увидел разрыв между навыками и убеждением 'я никому не нужен'",
  "current_open_loop": "что мешает начать делать бота по-настоящему",
  "recommended_next_move": "deepen_without_practice"
}
```

---

### Stage 4 — Response Planner v1

Цель:

```text
Planner выбирает следующий смысловой ход,
но не пишет пользователю.
```

Вход:

```text
StateSnapshot + ThreadState + ActiveFrame + KnowledgeRouting + PracticeGate
```

Выход:

```json
{
  "answer_move": "reflect|inform|deepen|repair|stabilize|practice|integrate",
  "target_micro_shift": "...",
  "depth": "short|medium|deep",
  "must_include": [],
  "must_avoid": [],
  "practice_allowed": false,
  "question_policy": "none|optional_one|required_one"
}
```

Planner должен быть сначала deterministic/rule-based. LLM Planner — позже, если понадобится.

---

### Stage 5 — Practice Gate v1

Цель:

```text
Практика только когда она уместна.
```

Practice allowed:

```text
- пользователь явно просит шаг/упражнение;
- состояние требует стабилизации;
- phase=integrate/action;
- Planner выбрал practice;
- практика прямо продолжает active_line.
```

Practice blocked:

```text
- greeting;
- concept question;
- correction/challenge;
- пользователь просит просто поддержку;
- низкий ресурс без запроса на упражнение, если достаточно короткого контакта;
- когда практика подменяет понимание.
```

---

### Stage 6 — Knowledge / Lens Routing v2

Цель:

```text
Решить, когда использовать Philosophy Kernel, когда RAG, а когда не использовать знания вообще.
```

Режимы:

```text
kernel_only
rag_concept_answer
rag_lens_support
rag_practice_support
no_kb_needed
memory_only
```

Важно:

```text
- если пользователь спрашивает известное понятие — отвечать по KB;
- если пользователь в живом переживании — KB только как внутренняя линза;
- если пользователь перегружен — меньше теории;
- если RAG low confidence — не делать вид, что знаем.
```

---

### Stage 7 — Real Dialogue Evaluation v2

Цель:

```text
Оценивать бота на живых диалогах, а не только synthetic cases.
```

Нужно собрать datasets:

```text
- live_bad_answers;
- Wake_up_reference_mechanics;
- Bot_current_failures;
- Knowledge_concept_cases;
- Practice_gate_cases;
- Continuity_cases;
- Tone_and_depth_cases.
```

Критерии:

```text
- держит линию;
- использует предыдущие реплики;
- не начинает заново;
- отвечает на реальное состояние;
- не суёт практику;
- не цитирует книгу;
- не теряет философскую основу;
- делает один микро-сдвиг;
- не звучит механически.
```

---

### Stage 8 — Memory / Profile / Episodic Layer v2

Цель:

```text
Бот должен помнить не всё подряд, а то, что поддерживает смысловую непрерывность.
```

Слои памяти:

```text
- recent turns;
- thread summary;
- active frame;
- user profile;
- episodic memories;
- pattern history;
- important user formulations;
- rejected hypotheses.
```

Memory Writer должен работать фоном и не тормозить ответ.

---

### Stage 9 — Web Admin Quality Control Plane

Цель:

```text
Все ключевые настройки quality-track должны быть видны и управляемы через Web Admin.
```

Разделы Web Admin:

```text
- Philosophy Kernel;
- Writer Freedom Contract;
- Active Frame;
- Response Planner;
- Practice Gate;
- Knowledge Routing;
- Quality Evaluator;
- Model Config;
- Trace Verbosity;
- Evaluation Runner.
```

Каждый раздел:

```text
- effective state;
- defaults;
- admin override;
- reset;
- save;
- last updated;
- trace preview;
- docs link.
```

---

### Stage 10 — BotDB / KB Quality Rework

Цель:

```text
Подготовить Кузницу и будущие материалы так,
чтобы retrieval действительно помогал Writer’у.
```

Но этот этап лучше делать после Kernel/Planner/ActiveFrame, чтобы понимать, какие metadata реально нужны runtime.

Направления:

```text
- markdown quality audit;
- chunk boundary quality;
- lens_family enrichment;
- practice extraction;
- concept map;
- use_when / avoid_when;
- internal_only vs writer_allowed;
- summary quality;
- safe trace redaction.
```

---

## 12. Рекомендуемый порядок PRD

### Ближайшая последовательность

```text
PRD-047.1 — NEO Philosophy Kernel + Writer Freedom Contract Foundation v1
PRD-047.2 — Active Frame / Dialogue Line v1
PRD-047.3 — Response Planner v1
PRD-047.4 — Practice Gate v1 + Answer Move Policy
PRD-047.5 — Web Admin Quality Controls v1
PRD-047.6 — Real Dialogue Evaluation v2
PRD-047.7 — Knowledge / Lens Routing v2
PRD-047.8 — Memory / Profile / Episodic Layer v2
PRD-048.0 — BotDB / KB Quality Rework for Кузница Духа
```

### Когда делать hotfix вместо следующего PRD

Hotfix нужен, если:

```text
- live UI показывает регресс по нейросталкингу;
- evaluator снова даёт false positive;
- Web Admin ломает runtime config;
- trace теряет quality fields;
- Writer снова даёт практику на greeting;
- RAG начинает цитировать raw content;
- tests/direct baseline красные.
```

---

## 13. Definition of Done для будущих PRD

Каждый PRD считается завершённым только если:

```text
1. TASK_LIST создан до кодинга.
2. Source gates выполнены.
3. Код реализован модульно.
4. Есть tests.
5. Есть dry/direct runner, если применимо.
6. Live run выполнен или честно skipped.
7. Trace обновлён, если меняется runtime.
8. Web Admin обновлён, если добавлена настройка.
9. Docs обновлены.
10. no_mutation_proof создан.
11. Implementation report обновлён после final push.
12. Commit/push в main выполнен.
13. GitHub audit может проверить результат без локального доступа.
```

---

## 14. Принципы качества ответа

Целевой ответ NEO:

```text
- видит состояние;
- не спешит исправлять;
- опирается на конкретные слова пользователя;
- удерживает активную линию;
- использует философию Кузницы как внутреннюю оптику;
- отвечает свободно и естественно;
- не превращается в лекцию;
- не задаёт много вопросов;
- не предлагает практику без основания;
- делает один следующий микро-сдвиг.
```

Анти-паттерны:

```text
- универсальная психологическая фраза;
- «это нормально» без смысла;
- дыхательная практика на любой вход;
- просьба определить известный термин;
- пересказ книги;
- новый framework в каждом ответе;
- слишком много глубины при низком ресурсе;
- авторитарный «щелчок»;
- потеря линии;
- формальное выполнение response_mode вместо живого ответа.
```

---

## 15. Как продолжать проект в новом чате

Если текущий чат перегрузится, в новый чат нужно передать:

```text
1. Этот стратегический план.
2. Последний TRANSFER_BRIEF.
3. Ссылку на GitHub repo.
4. Последний принятый PRD и implementation report.
5. Последние live/direct baseline reports.
6. Файлы:
   - КУЗНИЦА ДУХА v.2.md
   - Neo MindBot КОНСПЕКТ.md
   - Чат с ботом Wake_up.md
   - 🧭 ИЕРАРХИЧЕСКАЯ КАРТА НЕЙРОСТАЛКИНГА.md
   - KB_quality_recommendations_for_architect_agent.md
```

Новый чат должен продолжить с:

```text
1. GitHub audit.
2. Проверка последнего PRD acceptance.
3. Следующий PRD по этому плану.
```

---

## 16. Главный вывод

Проект не нужно упрощать до одного монолитного prompt и не нужно усложнять до хаотической сети агентов.

Правильный путь:

```text
Простая модульная multiagent-система,
где каждый слой делает маленькую работу,
Web Admin управляет настройками,
Trace показывает качество,
Writer получает свободу внутри безопасных границ,
а философия Кузницы живёт как внутреннее ядро,
а не как случайный RAG-кусок.
```

Следующий логичный PRD после PRD-047.0-HF1:

```text
PRD-047.1 — NEO Philosophy Kernel + Writer Freedom Contract Foundation v1
```
