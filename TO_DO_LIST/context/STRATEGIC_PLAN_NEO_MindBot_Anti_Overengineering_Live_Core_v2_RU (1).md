# STRATEGIC_PLAN_NEO_MindBot_Anti_Overengineering_Live_Core_v2_RU

**Проект:** Bot Psychologist / Neo MindBot  
**Версия:** v2.0  
**Дата:** 2026-06-10  
**Статус:** стратегический план для дальнейших PRD, GitHub-аудитов и IDE-агента  
**Назначение:** зафиксировать новый курс проекта: живой бот, простая модульная архитектура, наблюдаемость, настраиваемость и защита от переусложнения.

---

## 0. Главная формула v2

NEO / Bot Psychologist не должен превращаться в систему жёстких правил, бесконечных эвристик, маршрутов и диагностических клеток.

Целевая формула v2:

```text
NEO = живой Writer
    + минимальный управляемый multiagent harness
    + advisory-only диагностика
    + точный Context/Retrieval слой
    + понятный Trace
    + настраиваемая Web Admin
    + строгие, но минимальные safety boundaries.
```

Ключевой принцип:

```text
Внутренние слои не должны сковывать Writer’а.
Они должны готовить сцену, контекст и мягкий вектор.
```

---

## 1. Почему нужен новый стратегический план

Проект уже проходил этап, когда большое количество safety-правил, диагностических эвристик, маршрутов и внутренних ограничений сделало бота менее живым. Затем систему пришлось упрощать, чтобы “развязать руки” Writer’у.

Этот план нужен, чтобы не повторить старую ошибку.

Главный риск следующего этапа:

```text
попытаться сделать бота умнее
через добавление всё новых правил,
агентов,
маршрутов,
диагностических флагов,
retrieval-исключений
и validator-проверок.
```

Такой путь может снова привести к боту, который:

```text
- звучит как протокол;
- боится сделать живой ход;
- подчиняется ранней ошибочной классификации;
- перегружает ответ диагностикой;
- теряет простоту;
- становится сложным для настройки и аудита.
```

Новый курс:

```text
не больше контроля,
а лучше подготовленная сцена для живого ответа.
```

---

## 2. Product North Star

Главный продуктовый критерий:

```text
Бот должен помогать человеку увидеть себя яснее,
не становясь терапевтом, гуру, наставником или системой директив.
```

Он должен звучать как:

```text
живой, внимательный, умный собеседник,
который держит линию разговора,
видит состояние пользователя,
отвечает по ситуации,
не перегружает,
и помогает сделать один следующий микро-сдвиг.
```

Бот не должен звучать как:

```text
- методичка;
- диагностический протокол;
- spiritual authority;
- набор психологических техник;
- пересказ базы знаний;
- система маршрутов;
- “защищённый, но мёртвый” помощник.
```

---

## 3. Конституционные принципы проекта

### 3.1. Writer Freedom First

Writer — единственный автор финального пользовательского ответа.

Все остальные слои:

```text
- State Analyzer;
- Thread Manager;
- Diagnostic Center;
- Retrieval Planner;
- Memory Retrieval;
- Knowledge Policy;
- Validator;
- Trace;
- Web Admin
```

не должны писать пользовательский ответ и не должны диктовать Writer’у готовый текст.

Их задача:

```text
дать Writer’у ясный, компактный и безопасный контекст.
```

---

### 3.2. Hard Rules Minimalism

Жёсткими правилами должны быть только:

```text
- safety / crisis boundaries;
- запрет на диагноз;
- запрет на медицинские, юридические, финансовые директивы;
- запрет быть духовным авторитетом;
- запрет на manipulation / coercion;
- privacy / raw private logs protection;
- KB governance;
- запрет на raw quote dump;
- запрет на практики без основания;
- запрет обходить governance через debug/trace.
```

Всё остальное должно быть soft guidance.

---

### 3.3. Soft Guidance, Not Commands

Диагностика, retrieval, active frame и planner должны говорить не:

```text
Сделай такой ответ.
```

А:

```text
Похоже, уместен такой вектор.
Возможный механизм такой.
Глубина лучше невысокая.
Вот чего лучше избежать.
Вот какой материал может помочь.
```

Пример правильного advisory-output:

```json
{
  "suggested_depth": 1,
  "possible_mechanism": "контроль как попытка снизить тревогу",
  "recommended_move": "validate_then_pragmatic_boundary",
  "avoid": ["не обвинять", "не углублять травму", "не читать лекцию"],
  "writer_can_ignore": true
}
```

---

### 3.4. Trace Before Control

Если бот отвечает плохо, сначала нужно сделать ошибку видимой в trace, а не сразу добавлять новое правило.

Правильный порядок:

```text
1. Увидеть, где сломалось.
2. Зафиксировать evidence.
3. Понять, какой слой ошибся.
4. Исправить минимально.
5. Проверить regression.
```

Неправильный порядок:

```text
бот ответил плохо
→ добавим ещё одно правило
→ добавим исключение
→ добавим новый routing
→ добавим validator
→ бот стал ещё скованнее.
```

---

### 3.5. No New Agent Without Evidence

Новый агент разрешён только если выполнены условия:

```text
1. Есть повторяющаяся проблема в live/baseline evidence.
2. Проблему нельзя решить настройкой prompt/contract/trace.
3. Проблему нельзя решить маленьким deterministic module.
4. Новый агент имеет узкий input/output contract.
5. Новый агент не пишет user-facing текст.
6. Новый агент можно отключить feature flag’ом.
7. Его результат виден в trace.
```

Запрещено создавать агентов “на будущее”, “для умности” или “потому что так архитектурно красиво”.

---

### 3.6. One Runtime Path

Проект не должен снова расползаться на несколько конкурирующих runtime.

Правило:

```text
один основной active runtime;
legacy/shim только для совместимости;
никаких параллельных экспериментальных user-facing путей без отдельного PRD.
```

Если создаётся экспериментальный режим, он должен быть:

```text
- shadow;
- disabled by default;
- trace-visible;
- rollback-safe;
- с no-mutation proof.
```

---

### 3.7. Modularity Over Entanglement

Каждая новая функция или скрипт должны быть модульными.

Требования:

```text
- маленький файл / модуль с ясной ответственностью;
- явный input contract;
- явный output contract;
- тестируемость отдельно от всего runtime;
- feature flag, если поведение меняет путь ответа;
- trace/debug fields, если решение влияет на ответ;
- отсутствие скрытых зависимостей от глобального состояния.
```

Запрещено:

```text
- раздувать orchestrator бизнес-логикой;
- смешивать retrieval, diagnosis, writer prompt и trace в одном файле;
- делать “временные” хаки без task/comment/evidence;
- добавлять domain-specific правила в универсальные слои.
```

---

### 3.8. Configurable, Not Hardcoded

То, что должно настраиваться через Web Admin, не должно навечно зашиваться в код.

В перспективе через Web Admin должны быть управляемы:

```text
- модели агентов;
- temperature/max_tokens;
- prompt versions;
- включение/выключение Planner;
- включение/выключение quality flags;
- RAG top-k/min score;
- trace verbosity;
- safe/full trace mode;
- runtime feature flags;
- response length/depth tendencies.
```

До полноценной Web Admin это должно идти через единый config registry, а не через разбросанные константы.

---

### 3.9. Documentation Every Iteration

Каждый PRD должен обновлять актуальную документацию проекта.

Минимально:

```text
docs/PROJECT_STATE.md
docs/ROADMAP.md
docs/PRD_INDEX.md
docs/DECISIONS.md, если принято архитектурное решение
```

Правило:

```text
TO_DO_LIST = подробный архив операций.
docs = компактная operational map текущего состояния.
```

TO_DO_LIST может быть большим, docs должны оставаться короткими и полезными.

---

### 3.10. File Hierarchy Discipline

Проект должен иметь понятную иерархию файлов.

Новые файлы должны попадать в правильные зоны:

```text
bot_psychologist/
  runtime, agents, contracts, API, backend integration

Bot_data_base/
  ingestion, source storage, chunking, governance, KB admin, Chroma/API

docs/
  актуальная living-документация проекта

TO_DO_LIST/
  PRD, task lists, implementation reports, logs, evidence

frontend / web / admin directories
  Web Admin, Web Trace, UI components, если есть в текущей структуре
```

Запрещено:

```text
- класть runtime-логи в docs;
- класть архитектурные PRD в runtime modules;
- создавать дубли docs в разных местах без синхронизации;
- смешивать generated logs и hand-written docs;
- оставлять “временные” скрипты без понятного места.
```

---

## 4. Архитектурная иерархия слоёв

Важно: это не список агентов, которых надо обязательно создать. Это conceptual hierarchy.

```text
User Message
→ Safety / Crisis Gate
→ Fresh Context Gate
→ Dialogue Pragmatics
→ State Analyzer
→ Thread Manager
→ Diagnostic Hints / Active Frame
→ Hybrid Retrieval Planner, если нужен
→ Memory / KB Retrieval
→ Knowledge Policy / Chunk Gate
→ Writer Context Package
→ Writer
→ Validator / Quality Trace
→ Memory Update
→ Web Trace / Admin Evidence
```

Главное:

```text
Чем ближе слой к Writer’у, тем меньше он должен командовать и тем больше должен помогать.
```

---

## 5. Роли слоёв

### 5.1. Safety / Crisis Gate

Тип: hard boundary.

Задача:

```text
остановить небезопасный путь,
перевести в безопасную поддержку,
не позволить глубокой диагностике вредить.
```

Не должен превращаться в общий регулятор стиля.

---

### 5.2. Dialogue Pragmatics

Тип: lightweight deterministic / simple semantic.

Задача:

```text
понять форму хода:
да/нет,
продолжай,
сделай короче,
без практик,
подведи итог,
ответь проще,
это не то.
```

Не должен заниматься психологической диагностикой.

---

### 5.3. State Analyzer

Тип: интерпретирующий слой, возможно LLM.

Задача:

```text
оценить состояние текущего хода:
nervous_state,
intent,
openness,
ok_position,
confidence.
```

Важно:

```text
это не диагноз пользователя,
а временное состояние текущего сообщения.
```

---

### 5.4. Thread Manager

Тип: continuity layer.

Задача:

```text
держать линию:
continue / branch / new / return,
phase,
core_direction,
open_loops,
closed_loops,
last_meaningful_shift.
```

Не должен решать стиль финального ответа.

---

### 5.5. Diagnostic Hints / Active Frame

Тип: advisory-only.

Задача:

```text
собрать мягкую карту:
possible_mechanism,
depth_hint,
risk_hint,
suggested_next_micro_shift,
what_to_avoid.
```

Нельзя:

```text
- давать диагноз;
- давать Writer’у готовую фразу;
- блокировать живой ответ без safety-причины.
```

---

### 5.6. Hybrid Retrieval Planner

Тип: metadata-only planner.

Задача:

```text
до RAG понять:
нужен ли поиск,
где искать,
какой query,
какие типы чанков желательны,
какую глубину не превышать.
```

Не должен:

```text
- писать user-facing text;
- становиться Router всего диалога;
- подменять Diagnostic Center;
- заставлять Writer использовать найденное.
```

---

### 5.7. Memory / KB Retrieval

Тип: executor.

Задача:

```text
исполнить approved retrieval_plan,
вернуть top-k relevant context,
не тащить лишнее.
```

Не должен сам изобретать глубокую психологическую интерпретацию.

---

### 5.8. Knowledge Policy / Chunk Gate

Тип: governance + inclusion.

Задача:

```text
решить, какие найденные chunks можно дать Writer’у.
```

Важно:

```text
KB = lens library, not authority.
```

---

### 5.9. Writer Context Package

Тип: компактная сцена для Writer.

Должен включать:

```text
- user message;
- recent turns;
- active thread;
- soft hints;
- allowed/relevant chunks;
- safety boundaries;
- response constraints;
- what not to repeat.
```

Не должен быть огромной простынёй.

---

### 5.10. Writer

Тип: единственный user-facing автор.

Задача:

```text
ответить живо,
по ситуации,
с учётом контекста,
без механического исполнения внутренних JSON.
```

---

### 5.11. Validator / Quality Trace

Тип: safety + observability.

Задача:

```text
проверить грубые нарушения,
пометить quality risks,
не переписывать ответ без необходимости.
```

Quality flags сначала должны быть advisory-only.

---

### 5.12. Memory Update

Тип: asynchronous / post-response.

Задача:

```text
сохранять только meaningful shifts,
summary,
важные факты,
не засорять память мелочами.
```

---

## 6. База знаний: роль и границы

### 6.1. KB не должна быть цитатником

`КУЗНИЦА ДУХА` и другие материалы — это не источник прямых цитат для пользователя.

Правильная роль:

```text
internal lens library:
- диагностические линзы;
- понятия;
- механизмы;
- практики;
- use_when / avoid_when;
- mirror-фразы;
- мягкие response moves.
```

Неправильная роль:

```text
пользователь спросил
→ достали кусок книги
→ пересказали книгу
→ бот звучит как лектор.
```

---

### 6.2. KB не должна быть выше состояния пользователя

Если пользователь перегружен, в кризисе, злится, не готов к глубине — retrieval не должен тащить глубокую теорию.

Правило:

```text
state-fit важнее semantic-fit.
```

---

### 6.3. Подготовка БД — отдельный большой этап

Mechanism-aware chunking, relation graph, lens_family, user_markers, use_when/avoid_when — это важно, но не должно раздувать текущие runtime PRD.

Рекомендуемая стратегия:

```text
Сначала runtime должен научиться понимать, какой тип знания ему нужен.
Потом отдельный PRD должен подготовить БД так, чтобы такие знания действительно существовали.
```

---

## 7. Web Admin / Web Trace / Backend-Frontend Sync

### 7.1. Почему нужен отдельный цикл синхронизации

Проект движется к тому, что через Web Admin и Web Trace нужно будет видеть и настраивать:

```text
- качество ответа;
- trace каждого слоя;
- включённые feature flags;
- модели агентов;
- prompt versions;
- retrieval plans;
- diagnostic hints;
- chunk decisions;
- validator flags.
```

Если backend будет развиваться отдельно от frontend, возникнет рассинхрон:

```text
backend уже выдаёт quality_trace,
а UI его не показывает;

backend умеет planner_trace,
а Web Trace не умеет его читать;

config registry есть,
а Web Admin всё ещё редактирует старые поля.
```

Поэтому нужен отдельный обязательный PRD-цикл:

```text
Backend ↔ Web Admin ↔ Web Trace Sync
```

---

### 7.2. Когда делать sync-cycle

Рекомендуемый момент:

```text
после PRD-047.15-HF2 core implementation
и до следующего крупного усложнения retrieval/KB/Active Frame.
```

Почему:

```text
HF2 добавит retrieval_plan / query_before_rag / chunk_type hints.
Эти данные обязательно должны быть видны в trace.
Иначе мы снова будем строить “умные” внутренние слои, которые невозможно нормально аудитить.
```

---

### 7.3. Что должен включать sync-cycle

Будущий PRD должен проверить и синхронизировать:

```text
1. Backend API schemas.
2. Chat response trace payload.
3. /api/debug endpoints.
4. Web Trace UI.
5. Web Admin runtime config view.
6. Prompt/version/config registry display.
7. Quality trace display.
8. Retrieval planner trace display.
9. Safe/full trace режимы.
10. Browser smoke screenshots.
11. API-to-UI field mapping report.
```

Non-goal этого PRD:

```text
не делать красивый финальный дизайн;
не строить большую админку;
не менять поведение бота;
только добиться честной доставки и отображения runtime evidence.
```

---

## 8. Roadmap v2

### Wave A — Clean Observable Core

Цель:

```text
сделать текущее качество измеримым и trace-visible.
```

Сюда входят:

```text
- quality baseline;
- quality_trace;
- trace delivery to API;
- Writer Prompt v2;
- State Analyzer calibration;
- response mode routing audit;
- Thread Manager diagnostics.
```

Принцип:

```text
сначала увидеть, потом менять.
```

---

### Wave B — Writer Freedom + Soft Planning

Цель:

```text
дать Writer’у больше свободы при лучшем контексте.
```

Сюда входят:

```text
- soft advisory diagnostic hints;
- active frame / pattern core;
- response planner как soft guidance;
- quality validator flags advisory-only;
- сокращение жёстких directive fields.
```

Принцип:

```text
меньше команд, больше сцены.
```

---

### Wave C — Query-Before-RAG / Hybrid Retrieval

Цель:

```text
не искать в БД механически,
а сначала понять, нужен ли поиск и какой тип знания требуется.
```

Сюда входит:

```text
- Hybrid Retrieval Planner;
- minimal universal gates;
- metadata-only LLM planner;
- query-before-RAG;
- chunk gate;
- retrieval trace;
- writer_can_ignore_rag.
```

Принцип:

```text
retrieval optional, not mandatory.
```

---

### Wave D — Backend/Web Admin/Web Trace Sync

Цель:

```text
синхронизировать backend evidence с UI/admin visibility.
```

Сюда входит:

```text
- API schemas;
- debug endpoints;
- Web Trace panels;
- Web Admin config visibility;
- browser smoke;
- field mapping report.
```

Принцип:

```text
если это влияет на ответ, это должно быть видно и настраиваемо.
```

---

### Wave E — Mechanism-Aware KB Preparation

Цель:

```text
сделать БД библиотекой механизмов, линз, практик и dialogue moves,
а не складом фрагментов.
```

Сюда входит:

```text
- chunk_type schema;
- lens_family;
- user_markers;
- mechanism;
- depth_level;
- use_when / avoid_when;
- allowed_use;
- relation graph v1;
- Web Admin preview;
- dry-run without broad reindex.
```

Принцип:

```text
сначала metadata и preview,
потом reindex только через отдельный gated PRD.
```

---

### Wave F — Runtime Config Registry / Web Admin v1

Цель:

```text
вынести настройки из кода в управляемый registry и Web Admin.
```

Сюда входит:

```text
- agent model config;
- temperature/max_tokens;
- prompt version registry;
- retrieval thresholds;
- feature flags;
- debug verbosity;
- safe/full trace.
```

Принцип:

```text
настройка без переписывания кода.
```

---

## 9. Приоритеты ближайших шагов

На текущем этапе приоритет такой:

```text
1. Зафиксировать Strategic Plan v2.
2. Проверить текущий HEAD / PRD-045.3 evidence, если требуется.
3. Продолжить калибровку response_mode routing, если live evidence показывает ошибки.
4. Перед HF2 убедиться, что он не нарушает anti-overengineering principles.
5. Реализовать HF2 узко: Query-Before-RAG, metadata-only, trace-visible.
6. После HF2 сделать Backend/Web Trace/Admin sync-cycle.
7. Только потом идти в глубокую подготовку БД.
```

Важно:

```text
Не перескакивать сразу в большую KB-перестройку.
Не строить новый Diagnostic Center.
Не добавлять нового большого Router.
Не делать Planner центром всей системы.
```

---

## 10. PRD-writing rules v2

Каждый PRD должен быть отдельным markdown-файлом для скачивания.

В чат выводить только:

```text
- краткий итог аудита;
- решение: passed / warning / blocker / docs mismatch;
- что делает следующий PRD;
- что он НЕ делает;
- ссылка на файл.
```

PRD должен быть на русском языке.  
Технические имена можно оставлять на английском.

Обязательная структура PRD:

```text
0. Краткое резюме
1. Контекст
2. Цель
3. Non-goals
4. Source gates / pre-audit
5. Runtime requirements
6. Web Admin requirements, если затрагивается настройка
7. Web Chat / UI requirements, если затрагивается UI
8. Trace / evidence requirements
9. Tests
10. Live / browser smoke checks
11. Required artifacts
12. No-mutation proof
13. Acceptance criteria
14. Implementation report requirements
15. Next PRD recommendation
16. Final instruction for IDE agent
```

Перед кодингом IDE-агент обязан создать:

```text
TO_DO_LIST/PRD-XXX_TASK_LIST.md
```

TASK_LIST должен содержать:

```text
- этапы;
- задачи;
- файлы;
- тесты;
- safety checks;
- docs checks;
- encoding checks;
- команды;
- acceptance criteria.
```

Запрет:

```text
IDE-агент не начинает кодить, пока TASK_LIST не создан.
```

---

## 11. Documentation sync rules

Каждая итерация должна обновлять docs.

Минимально:

```text
docs/PROJECT_STATE.md
docs/ROADMAP.md
docs/PRD_INDEX.md
docs/DECISIONS.md, если есть новое ADR
```

Дополнительно:

```text
TO_DO_LIST/reports/PRD-XXX_IMPLEMENTATION_REPORT.md
TO_DO_LIST/reports/PRD-XXX_NEXT_PRD_RECOMMENDATION.md
TO_DO_LIST/logs/PRD-XXX/*.json
TO_DO_LIST/logs/PRD-XXX/*.md
```

Implementation report должен быть обновлён после финального commit/push.

Он должен содержать:

```text
- source_head_before;
- main_commit;
- post_push_metadata_commit, если есть;
- push_status;
- final_status;
- tests_status;
- docs_status;
- evidence_status;
- known_warnings;
- known_blockers;
- next_prd.
```

---

## 12. Git / logs / artifacts policy

Коммитить нужно:

```text
- PRD-файлы;
- TASK_LIST;
- implementation reports;
- next PRD recommendations;
- sanitized logs;
- runner reports;
- JSON evidence;
- screenshots/browser smoke, если есть UI-задача;
- docs updates.
```

Не коммитить:

```text
- .env;
- ключи;
- secrets;
- raw provider payload;
- raw private logs;
- sqlite/db/cache;
- .venv;
- node_modules;
- большие бинарные dumps;
- чувствительные пользовательские данные.
```

Если нужны live logs:

```text
они должны быть sanitized.
```

Если нужен raw trace для архитектурного аудита:

```text
хранить только безопасный экспорт,
без приватных данных и секретов.
```

---

## 13. Encoding hygiene

Все новые текстовые артефакты:

```text
UTF-8
без mojibake
без управляющего мусора
```

Проверять:

```text
*.md
*.txt
*.json
*.py
*.ts
*.tsx
*.html
*.css
```

Запрещённые признаки:

```text
Рџ
Рґ
Рё
РЅ
СЃ
С‚
СЊ
РЎ
Рќ
�
\x07
\x0c
```

Новые файлы писать так:

```python
Path(path).write_text(text, encoding="utf-8", newline="\n")
```

---

## 14. Decision filter before every new feature

Перед каждым новым PRD или новой функцией архитектор должен ответить:

```text
1. Какая реальная проблема evidence-backed?
2. Можно ли решить её без нового агента?
3. Можно ли решить её prompt/config/trace-правкой?
4. Не станет ли Writer более скованным?
5. Будет ли новая функция видна в trace?
6. Можно ли её отключить?
7. Не создаёт ли она новый runtime path?
8. Не дублирует ли существующий слой?
9. Есть ли тесты и acceptance criteria?
10. Какой минимальный безопасный вариант?
```

Если на эти вопросы нет ясного ответа — PRD не писать.

---

## 15. Acceptance критерии стратегического курса

Проект движется правильно, если:

```text
- бот становится живее, а не сложнее;
- Writer получает лучший контекст, а не больше команд;
- trace показывает причины слабых ответов;
- Web Admin постепенно получает реальные настройки;
- docs остаются актуальными;
- TO_DO_LIST содержит полную историю;
- новые модули маленькие и тестируемые;
- retrieval становится точнее, но не обязательнее;
- Diagnostic Center остаётся advisory-only;
- БД используется как lens library, а не как цитатник.
```

Проект уходит в опасную сторону, если:

```text
- появляется много новых флагов без evidence;
- Writer начинает исполнять JSON вместо живого ответа;
- каждый плохой ответ лечится новым правилом;
- в trace много данных, но непонятно, где ошибка;
- Web Admin отстаёт от backend;
- docs не обновляются;
- Planner начинает писать user-facing text;
- KB начинает диктовать ответ;
- появляются параллельные runtime paths.
```

---

## 16. Когда создавать Transfer Brief и переходить в новый чат

Новый Transfer Brief нужен, если:

```text
1. Завершён крупный PRD-цикл с GitHub-аудитом и несколькими коммитами.
2. В чате накопилось больше 2–3 PRD-аудитов подряд.
3. Следующий шаг требует большого GitHub-аудита.
4. Нужно писать крупный PRD на новую архитектурную фазу.
5. Контекст разговора стал слишком длинным и есть риск потерять ранние решения.
6. Начинается HF2/HF3 или большая KB/Web Admin итерация.
```

Перед переходом в новый чат нужно создать:

```text
TRANSFER_BRIEF_Bot_Psychologist_Neo_MindBot_AFTER_<CURRENT_STAGE>_DETAILED_RU.md
```

Он должен содержать:

```text
- последний проверенный HEAD;
- последние PRD и статусы;
- current warnings/blockers;
- стратегические принципы v2;
- актуальный roadmap;
- важные документы;
- правила PRD;
- правила Git/logs/docs;
- следующий рекомендуемый шаг.
```

---

## 17. Финальная формула курса

```text
Меньше маршрутов.
Больше ясности.

Меньше команд Writer’у.
Больше хорошего контекста.

Меньше диагностики наружу.
Больше живого ответа.

Меньше “умной системы”.
Больше системы, которая не мешает уму модели.

Меньше бесконечных эвристик.
Больше evidence, trace и маленьких проверяемых модулей.
```

---

## 18. Как использовать этот документ

Этот Strategic Plan v2 должен быть прикреплён в проектное пространство и использоваться как верхний фильтр для всех следующих PRD.

Перед каждым новым PRD архитектор должен сверяться с ним.

Если PRD противоречит этому плану, его нужно:

```text
- упростить;
- разбить;
- перевести в shadow/evidence режим;
- или отложить.
```

Главное:

```text
Живое качество ответа важнее архитектурной красоты.
```
