# PRD_10.3_Response_Richness_Recalibration

## Product Requirements Document

**Версия:** 10.3  
**Статус:** ACTIVE — proposed for implementation by IDE agent  
**Тип итерации:** Behavioral Calibration / Response Richness / Routing & Prompt Tuning  
**Репозиторий:** `Askhat-cmd/Text_transcription`  
**Основные области:** `bot_psychologist/bot_agent/`, `api/`, `prompts/`, `tests/`  
**Предшествующий документ:** `PRD_10.2_Legacy_Runtime_Purge.md`  
**Правило совместимости:** PRD_10.3 не заменяет PRD_10.1 как базовую целевую архитектуру. Он определяет следующую итерацию калибровки поведения после частичной purge-очистки 10.2.

---

# 0. Executive Summary

После PRD_10.2 Neo MindBot стал архитектурно чище:
- path-builder side effects ослаблены или убраны из обычного потока;
- adaptive-stream ближе к основному adaptive path;
- live runtime стабильно использует retrieval + rerank + confidence cap;
- Bot_data_base API работает как основной источник знаний.

Однако по live-логам и текущему коду проявилась новая проблема:

**бот отвечает слишком скупо, нейтрально и “справочно”, даже там, где пользователь ожидает более живой, насыщенный и сопровождающий ответ.**

Причина не выглядит случайной. Она почти наверняка является следствием сочетания трёх факторов:

1. Слишком широкое попадание запросов в informational-like behavior  
2. Слишком нейтральная и ограничительная style policy для `inform`  
3. Слишком жёсткие first-turn / informational guardrails, которые режут глубину и теплоту ответа

При этом проблема **не похожа на token ceiling issue** и не выглядит как падение retrieval-качества.  
Речь идёт не о слабом контенте, а о **слишком узкой генеративной политике**.

**Цель PRD_10.3:**  
сделать ответы снова живыми, тёплыми, полноценными и полезными,  
не ломая при этом:
- Neo routing,
- safety layer,
- informational branch,
- retrieval discipline,
- output validation.

---

# 1. Why this iteration exists

## 1.1 Наблюдаемая проблема

Пользовательское наблюдение:
- бот стал отвечать слишком скупо;
- ответы стали суше;
- общение потеряло часть живости и развернутости.

Техническая интерпретация:
- это не похоже на системный crash;
- это не похоже на retrieval breakdown;
- это не похоже на обрезание ответа токенами;
- это похоже на **поведенческую перекалибровку не в ту сторону**.

## 1.2 Что изменилось после 10.2

Purge-итерация правильно зачистила часть legacy-шумов, но одновременно сделала active runtime строже:
- informational branch стал влиятельнее;
- style policy для `inform` стала более нейтральной;
- first-turn restrictions начали сильнее ограничивать полноту первого ответа;
- часть conversational richness была потеряна.

## 1.3 Что не нужно делать в 10.3

PRD_10.3 **не должен**:
- заново переписывать всю архитектуру;
- возвращать старый хаотичный бот;
- отменять safety constraints;
- ломать informational branch;
- вводить новые большие подсистемы.

Это не migration release.  
Это **behavior recalibration release**.

---

# 2. Scope of PRD_10.3

## 2.1 Входит в scope

1. Калибровка попадания в informational behavior  
2. Ослабление чрезмерно сухой style policy для `inform`  
3. Перекалибровка first-turn richness policy  
4. Калибровка mixed-query behavior  
5. Калибровка route-to-style coupling  
6. Калибровка response length policy  
7. Добавление richer-output acceptance tests  
8. Добавление golden tests на “живость без потери структуры”

## 2.2 Не входит в scope

В 10.3 не входят:
- новый memory contract;
- новый retrieval engine;
- новые practice channels;
- новая admin-панель;
- новая кризисная логика;
- новый глобальный prompt stack version beyond behavior tuning;
- новый orchestration graph.

## 2.3 Scope discipline rule

Любое изменение должно отвечать на вопрос:

**Это повышает живость, полноту и полезность ответа без отката в хаос?**

Если нет — задача out-of-scope.

---

# 3. Root Cause Hypothesis

## 3.1 Root Cause A — overly broad informational tendency

Текущее поведение слишком легко интерпретирует exploratory / curious messages как informational-like flow.

Это приводит к тому, что вместо:
- сопровождения,
- мягкой рефлексии,
- глубокой развёрнутой помощи,

бот выдаёт:
- объяснение концепта,
- структурный мини-ответ,
- 1 вопрос-мост,
- и на этом останавливается.

## 3.2 Root Cause B — style policy for `inform` is too dry

Нынешняя style policy для informational route слишком близка к “справочному режиму”.

Она полезна для:
- энциклопедического ответа,
- определения,
- краткого разъяснения,

но слишком слаба для:
- живого объяснения с нюансами,
- тёплого первого контакта,
- насыщенного смыслом ответа на философский / introspective query.

## 3.3 Root Cause C — first-turn anti-overload policy is over-tight

Изначально first-turn simplification была полезна, чтобы бот:
- не перегружал,
- не начинал с лекции,
- не выглядел как терапевтический intake form.

Но сейчас это похоже начало резать:
- глубину,
- теплоту,
- ощущение “меня действительно услышали”,
- нормальный conversational body.

## 3.4 Root Cause D — mixed queries are under-expanded

Если пользователь задаёт запрос вида:
- “объясни и покажи на моём опыте”
- “что это значит и как это увидеть у себя”
- “как начать это практиковать”

бот не всегда разворачивает ответ в полноценный mixed mode.  
Часто он остаётся в почти informational delivery.

## 3.5 Root Cause E — richness is not explicitly protected

В текущем runtime хорошо защищены:
- safety,
- structure,
- route consistency,
- no forbidden advice,
- no broken formatting.

Но почти не защищено:
- ощущение полноты ответа,
- conversational warmth,
- смысловая насыщенность,
- non-sparse answer body.

---

# 4. Product Goal of 10.3

## 4.1 Core goal

Сделать ответы Neo MindBot:
- более живыми,
- более насыщенными,
- более развёрнутыми,
- более человечески тёплыми,
- более полезными на первом контакте,

не разрушая при этом:
- safety,
- determinism,
- route clarity,
- informational branch discipline,
- retrieval grounding.

## 4.2 Success perception

После 10.3 пользователь должен чаще ощущать:
- “бот меня не только понял, но и реально развил тему”;
- “ответ не скупой и не бюрократический”;
- “мне дали не сухую справку, а живой, умный и полезный ответ”;
- “бот не давит, но и не недодаёт”.

---

# 5. Product Principles for 10.3

## 5.1 Richness without bloat
Цель не в том, чтобы делать длинные полотна всегда.  
Цель — чтобы ответ был **достаточно полным** для типа запроса.

## 5.2 Warmth without theatricality
Теплота нужна, но без навязчивой поэтизации и без искусственной “мягкости ради мягкости”.

## 5.3 Informational does not mean emotionally flat
Даже объяснительный ответ может быть:
- ясным,
- живым,
- образным,
- с хорошими примерами,
- с ощущением сопровождения.

## 5.4 First turn should reduce anxiety, not meaning
Первый ответ не должен быть перегруженным, но и не должен ощущаться пустым.

## 5.5 Mixed queries deserve mixed answers
Если человек одновременно просит:
- понять концепт,
- применить к себе,
- начать практиковать,

бот не должен отвечать так, как будто это только glossary question.

## 5.6 Preserve safety, keep humanity
Safety не должна автоматически делать ответ сухим.

---

# 6. Fixed Decisions for 10.3

## 6.1 Remove the hard coupling of `curious` to informational override
Состояние `curious` не должно по умолчанию означать:
- informational prompt override,
- полу-справочный стиль,
- route narrowing.

`curious` = exploratory openness, а не автоматический `inform`.

## 6.2 Informational route must become narrower
`inform` должен срабатывать только когда запрос действительно в первую очередь:
- explanatory,
- definitional,
- educational,
- concept-first.

Если запрос содержит личный контекст, интерес к применению, самоисследование или практику — нужен richer mixed or coaching-biased behavior.

## 6.3 Informational style must become richer
Для `inform` стиль должен стать:
- ясным,
- структурным,
- но не сухим,
- допускающим 2-4 примера,
- допускающим мягкую интерпретацию смысла,
- допускающим короткий смысловой мост к опыту пользователя.

## 6.4 First-turn policy must be softened
Первый ответ должен быть:
- не перегруженным,
- но не минималистично-скупым,
- с ощущением полноты мысли,
- с достаточной смысловой массой.

## 6.5 Mixed query must trigger richer answer form
Mixed query должен вести не к “микро-объяснению + 1 вопросу”, а к более полноценной структуре:
1. короткое объяснение,
2. привязка к пользовательскому опыту,
3. один практический угол,
4. мягкий следующий шаг.

## 6.6 Add explicit anti-sparse policy
В prompt/task/output validation нужно ввести policy против “смысловой скупости”.

---

# 7. Target Behavioral Model After 10.3

## 7.1 Informational answer should feel like this
- объясняет;
- даёт различия и нюансы;
- показывает 2-4 примера;
- не уходит в лекцию;
- не холоден;
- не выглядит как FAQ snippet.

## 7.2 First-turn coaching answer should feel like this
- отражает суть запроса;
- даёт содержательное раскрытие;
- создаёт ощущение контакта;
- не перегружает техническими рамками;
- не сводится к 2-3 абзацам ни о чём.

## 7.3 Mixed query answer should feel like this
- “я понял, что ты хочешь и понять концепт, и увидеть, как это относится к тебе”;
- объяснение + применение + мягкий практический ракурс;
- не сухой мост, а полноценный связный ответ.

## 7.4 Practice request answer should feel like this
Если человек спрашивает “как начать это практиковать?”:
- ответ должен не просто назвать практику;
- он должен коротко объяснить логику;
- дать понятный вход;
- убрать ощущение “ещё одной задачи”.

---

# 8. Required Runtime Changes

## 8.1 Recalibrate informational gating

### Сделать
- пересмотреть логику `mode_prompt_override`;
- убрать автоматическую связку `curious -> prompt_mode_informational`;
- сузить критерии true informational behavior;
- в mixed/exploratory cases смещать поведение в richer mixed/coaching branch.

### Цель
Чтобы exploratory curiosity больше не обнуляла richness.

---

## 8.2 Introduce `inform_rich` style policy

### Сделать
Вместо current informational dryness ввести richer policy:
- нейтрально, но живо;
- 2-4 примера вместо 1-2;
- допускается краткий смысловой мост;
- допускается короткое сравнение / различение;
- допускается “почему это важно”.

### Новый behavioural intent
`inform` = “объясняющий и живой”, а не “почти справочный”.

---

## 8.3 Soften first-turn constraint

### Сделать
Заменить правило:
- “не перегружай. Коротко, ясно и с одним рабочим вопросом”

на более гибкое:
- не перегружай;
- но дай полноценный первый смысловой каркас;
- допускается 1 ключевой вопрос в конце;
- не урезай основную часть ответа до минимума.

### Цель
Убрать ощущение “бот недодаёт”.

---

## 8.4 Upgrade mixed-query handling

### Сделать
Для mixed-query responses явным образом требовать структуру:
1. short concept framing
2. user-relevant interpretation
3. one practical lens or example
4. optional bridge question

### Цель
Не скатываться в сухой informational stub.

---

## 8.5 Add response richness hints to task instruction

### Сделать
В `TASK_INSTRUCTION` добавить policy вида:
- answer must be substantively complete for the query class;
- do not under-answer when the user asks an expansive or introspective question;
- avoid sparse mini-answers unless route/state explicitly require brevity.

### Цель
Явно защитить richness как системное качество.

---

## 8.6 Add anti-sparse validation

### Сделать
В `output_validator` добавить дополнительные проверки не на длину как таковую, а на содержательную полноту.

Примеры сигналов sparse-output:
- ответ состоит из определения + 1 общего предложения + 1 вопроса;
- нет раскрытия различий, хотя запрос спрашивает различие;
- нет примеров, хотя route=inform и concept explanation requested;
- есть вежливость, но мало смысловой массы.

### Важно
Validator не должен принуждать к длинным ответам всегда.  
Он должен ловить **неадекватно бедный** ответ для данного запроса.

---

# 9. Prompt Stack Changes

## 9.1 `A_STYLE_POLICY` revision

### Текущая проблема
Inform style слишком сухой.

### Требование
Ввести отдельную richer policy для:
- `inform`
- `mixed_inform`
- `first_turn_inform`
- `first_turn_coaching`

### Пример целевого направления
Не:
- “нейтрально и структурно”

А:
- “ясно, структурно, но живо; раскрой идею, различия, примеры и практический смысл без лекционности”.

---

## 9.2 `TASK_INSTRUCTION` revision

### Для `inform`
Добавить:
- раскрой концепт достаточно полно;
- объясни различия, если пользователь спрашивает “чем отличается”;
- используй 2-4 примера, если это помогает;
- не своди ответ к glossary style.

### Для `mixed_query`
Добавить:
- объяснение + пользовательская перспектива + мягкий практический ракурс.

### Для `first_turn`
Добавить:
- полноценный первый смысловой ответ допустим;
- не нужно намеренно ужимать тело ответа до минимума.

---

## 9.3 `CORE_IDENTITY` should protect richness
Базовая identity должна не только запрещать токсичность и псевдо-уверенность, но и поощрять:
- ясность,
- глубину,
- смысловую щедрость,
- живой интеллектуальный контакт.

---

# 10. Routing Calibration Changes

## 10.1 Narrow true `inform`

### Should route to `inform`
- “что такое X?”
- “объясни разницу между A и B”
- “что означает термин?”
- “в чём суть метода?”

### Should not default to pure `inform`
- “кажется это про меня”
- “как это увидеть у себя?”
- “как начать это практиковать?”
- “что это значит в реальном опыте?”
- “покажи на моём случае”

## 10.2 Introduce mixed-inform behavior without new route explosion
Не обязательно вводить новый route enum.  
Можно реализовать richer behavior через:
- task instruction modifiers,
- mixed query flag,
- style policy modifiers.

Важно не плодить лишние route types, если это можно решить policy-layer.

---

# 11. Output Richness Policy

## 11.1 Response richness dimensions

Нужно проверять не только длину, но и наличие:
- раскрытия сути;
- различения понятий;
- примеров;
- связи с запросом пользователя;
- минимального practical relevance;
- живого tone.

## 11.2 Sparse response anti-patterns

Считать подозрительными:
- “это X. Оно отличается от Y тем, что ... Что из этого тебе ближе?”
- определение + 1 общая фраза + 1 вопрос;
- слишком стерильный ответ при богатом retrieval;
- уклонение в сверхкраткость без route/state justification.

## 11.3 Allowed brevity
Краткость по-прежнему допустима для:
- safe_override;
- acute regulate;
- hypo with overload risk;
- explicit user preference for short answer.

---

# 12. Required Code Changes

## 12.1 `answer_adaptive.py`
- убрать или ослабить `MODE_PROMPT_MAP` coupling для `curious`;
- пересмотреть `informational_mode` derivation;
- улучшить mixed-query modifiers;
- добавить richer runtime flags/metadata for diagnostics.

## 12.2 `prompt_registry_v2.py`
- переписать style policy для `inform`;
- смягчить first-turn instruction;
- усилить mixed-query instruction;
- добавить anti-sparse task hints.

## 12.3 `output_validator.py`
- добавить anti-sparse validation rules;
- добавить regenerate hint, если ответ слишком бедный по смыслу;
- не путать “коротко” и “недостаточно”.

## 12.4 `diagnostics_classifier.py` / route policy
- пересмотреть пороги и условия informational classification;
- не использовать curiosity as shorthand for informationality.

---

# 13. Feature Flag Policy

## 13.1 Allowed migration flags
Можно временно ввести:
- `USE_RICH_INFORMATIONAL_STYLE`
- `SOFTEN_FIRST_TURN_RICHNESS_POLICY`
- `ANTI_SPARSE_VALIDATION_ENABLED`
- `NARROW_INFORMATIONAL_ROUTING`

## 13.2 Completion rule
После подтверждения качества эти флаги должны стать:
- либо default-on,
- либо быть удалены как временные.

---

# 14. Testing Strategy

## 14.1 Main test intent
В 10.3 нужно доказывать не просто корректность ответа, а **достаточную содержательную полноту**.

## 14.2 Required test layers
Обязательны:
- unit
- integration
- golden
- regression
- e2e
- qualitative rubric tests

## 14.3 New golden tests

### Inform richness
- `tests/golden/test_informational_answer_not_sparse.py`
- `tests/golden/test_difference_question_has_real_comparison.py`

### Mixed query richness
- `tests/golden/test_mixed_query_response_has_concept_plus_application.py`

### First turn richness
- `tests/golden/test_first_turn_not_underfilled.py`

### Practice entry richness
- `tests/golden/test_how_to_start_practice_is_not_glossary_like.py`

## 14.4 Qualitative rubric tests

Для selected fixtures проверить:
- response has explanation depth;
- response has examples where appropriate;
- response is not emotionally flat;
- response is not merely definition + bridge question;
- response remains safe and non-directive.

## 14.5 Regression tests
Сохранить защиту от:
- unsafe directive answers;
- over-poetic crisis outputs;
- overly long rambling outputs;
- route inconsistency.

---

# 15. Acceptance Criteria

## 15.1 Inform recalibration accepted only if
- informational answers стали ощутимо богаче по смыслу;
- они остаются структурными;
- они больше не ощущаются как сухой FAQ default.

## 15.2 Mixed query recalibration accepted only if
- mixed queries получают explanation + relevance + practice lens;
- ответ не заканчивается слишком рано;
- есть ощущение живого понимания запроса.

## 15.3 First-turn recalibration accepted only if
- первый ответ перестаёт быть недоданным;
- при этом не превращается в перегруз или длинную лекцию.

## 15.4 Output richness validation accepted only if
- validator умеет ловить действительно бедные ответы;
- validator не ломает нормальную краткость там, где она уместна.

## 15.5 Whole 10.3 accepted only if
- пользовательская субъективная оценка “бот стал скупым” заметно уменьшается;
- retrieval grounding и safety не ухудшаются;
- route clarity сохраняется;
- new richer behavior подтверждён logs + golden outputs.

---

# 16. Delivery Plan

## Phase 0 — Richness Baseline
- собрать примеры sparse outputs;
- зафиксировать representative fixtures;
- выделить current routing + style bottlenecks.

## Phase 1 — Informational Routing Recalibration
- убрать hard coupling curiosity → informational override;
- сузить true informational gating.

## Phase 2 — Prompt Richness Recalibration
- переписать informational style policy;
- смягчить first-turn constraints;
- усилить mixed-query instruction.

## Phase 3 — Output Validation Enrichment
- ввести anti-sparse validation;
- добавить regenerate hint for underfilled responses.

## Phase 4 — Golden / Qualitative Test Hardening
- добавить rubric-based golden tests;
- зафиксировать richer target outputs.

## Phase 5 — Runtime Verification
- прогнать реальные сценарии;
- сравнить before/after;
- подтвердить, что ответы стали богаче без потери safety.

---

# 17. Risk Management

## 17.1 Main risk
Можно перестараться и вернуть:
- многословие,
- размытость,
- “тёплую воду”,
- лишнюю психо-лирику.

## 17.2 Mitigation
- richness measured by completeness, not verbosity alone;
- retain structure;
- retain route discipline;
- use qualitative golden fixtures.

## 17.3 Secondary risk
Слишком узкий `inform` может перегрузить coaching path.

### Mitigation
Использовать mixed-policy modifiers, а не механический переворот всего в coaching.

---

# 18. Definition of Done

PRD_10.3 считается выполненным только если одновременно верно всё:

1. `curious` больше не ведёт автоматически к informational dryness.  
2. `inform` route стал уже и точнее.  
3. Informational responses стали содержательнее и теплее.  
4. First-turn responses перестали быть недозаполненными.  
5. Mixed queries получают richer combined answers.  
6. Anti-sparse validation работает.  
7. Safety, route consistency и retrieval grounding сохранены.  
8. Golden/qualitative tests подтверждают improvement.  
9. Live user-perceived “скупость” заметно снижена.  

---

# 19. Instructions to IDE Agent

1. Не делай 10.3 “новой архитектурной революцией”.  
2. Работай как инженер behavioral tuning.  
3. Лечи именно sparse-output behavior, а не всё подряд.  
4. Не путай richness с verbosity.  
5. После каждой фазы:
   - обнови код;
   - обнови golden tests;
   - сохрани примеры before/after;
   - проверь, что safety не деградировал.
6. Если ответ стал длиннее, но не стал полезнее — фаза не считается успешной.

---

# 20. Final Note

PRD_10.3 intentionally focuses on one concrete product truth:

**Пользователь должен чувствовать, что бот не жмётся на смысл.**

Neo MindBot не должен быть:
- сухим,
- полу-справочным,
- недодающим.

Он должен быть:
- ясным,
- живым,
- содержательным,
- бережным,
- достаточно полным для того вопроса, который ему принесли.
