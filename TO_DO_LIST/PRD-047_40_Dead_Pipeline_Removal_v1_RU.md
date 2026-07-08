# PRD-047.40 — Dead Pipeline Removal v1 RU

**Проект:** Bot Psychologist / Neo MindBot
**Репозиторий:** `Askhat-cmd/Text_transcription`
**Локальный путь пользователя:** `C:\My_practice\Text_transcription`
**Дата:** 2026-07-08
**Статус:** draft / ready for IDE-agent implementation
**Основание:** PRD-047.39 принят (`ACCEPTED_WITH_WARNINGS`, commits `3c9cf15` / `0fb34ab`). Это первый исполнительный PRD Фазы B Эпохи 1 — единственный кодовый PRD, следующий строго после инвентаризации.

---

## 0. Короткое решение

```text
Этот PRD делает четыре вещи и только четыре:

1. Untrack 532 raw-артефактов (63.2MB) из TO_DO_LIST/logs — отложенное
   действие PRD-047.39, теперь выполняется явно.
2. Физически убирает последние следы 13 dead_confirmed компонентов —
   не из активного рантайма (он уже чист, см. раздел 3), а из тестовой
   обвязки, которая на них всё ещё ссылается и физически лежит в дереве.
3. Проводит trace user_level_adapter (unclear_needs_trace) и фиксирует
   его итоговый статус — без удаления, независимо от результата.
4. Заменяет test_no_legacy.py (негативные assert'ы "маркера тут нет")
   на test_dead_code_removed.py (позитивное доказательство отсутствия +
   зафиксированный вердикт по user_level_adapter).
```

---

## 1. Проверка перед написанием (архитектор, 2026-07-08)

Бриф предупреждал не доверять ему слепо. Репозиторий проверен напрямую:

```text
git clone Askhat-cmd/Text_transcription — commit 27d53f0 (HEAD, main)
Последние 3 PRD в истории: 047.39 (accepted_with_warnings) -> 047.38 -> 047.37.
docs/PROJECT_STATE.md и docs/MASTER_STRATEGIC_PLAN_NEO_MindBot_v4_RU.md §4/§5.3
совпадают с transfer brief дословно по числам (13 компонентов, 532 raw-пути,
63.2MB, user_level_adapter unclear_needs_trace). Расхождений с брифом не найдено.
```

Дополнительно — то, чего в брифе не было, но важно для scope этого PRD:

```text
- tests/contract/test_no_legacy.py прогнан напрямую: 3/3 PASSED.
  Это значит: активные рантайм-пути (bot_agent/retriever.py, __init__.py,
  api/routes/chat.py, prompt_registry_v2.py, runtime_config.py, api/main.py,
  response/response_generator.py, answer_adaptive.py, route_resolver.py)
  УЖЕ не содержат маркеров 13 компонентов. Физических файлов
  bot_agent/answer_basic.py, answer_sag_aware.py, answer_graph_powered.py,
  sd_classifier.py в дереве нет вообще — ни в active, ни в legacy/.
  Прежних prompt_sd_*.md / prompt_system_level_*.md файлов тоже нет нигде
  в репозитории (find по всему дереву — пусто).

- Но 5 тестовых файлов физически лежат в дереве и падают на импорте
  несуществующих модулей — подтверждено прямым запуском:
    tests/test_phase1.py               -> ModuleNotFoundError: bot_agent.answer_basic
    tests/test_phase2.py               -> ImportError: answer_question_sag_aware
    tests/test_phase3.py               -> ImportError: answer_question_graph_powered
    tests/test_fast_detector.py        -> ModuleNotFoundError: bot_agent.sd_classifier
    tests/test_full_dialogue_pipeline.py -> ModuleNotFoundError: bot_agent.answer_basic
  Все пять уже находятся в pytest.ini под --ignore (значит "full regression"
  в текущем понимании CI их не видит) — но сами файлы никуда не делись.
  Это ровно то расхождение между "код мёртв" и "могила ещё стоит",
  которое Master Plan §5.2 (North Star) требует убрать.

- Второстепенные, не-import упоминания (не являются целью удаления,
  см. раздел 2.C): tests/test_debug_metrics_and_export.py — строковый
  fixture-литерал "sd_classifier" в примере pipeline_stages (не импорт);
  scripts/bootstrap_eval_sets.py — импорт sd_classifier обёрнут в try/except
  с безопасным fallback (sd_acc=0.0), уже не ломает скрипт.

- user_level_adapter подтверждён как referenced_by_active_path:
  response/response_generator.py принимает user_level_adapter=None как
  compat no-op (строки ~115/130/215/224, "accepted but intentionally
  ignored in Neo runtime"); api/debug_routes.py и api/routes/common.py
  используют "user_level_adapter_applied" как compat-only ключ метаданных.
  При этом tests/inventory/test_no_active_legacy_trace_metadata_keys.py
  уже требует, чтобы этот ключ отсутствовал в активном runtime_contract,
  а tests/unit/test_user_level_adapter_removed.py уже подтверждает, что
  answer_adaptive не содержит класс UserLevelAdapter и
  _resolve_path_user_level всегда возвращает INTERMEDIATE независимо от
  входа. Это сильный сигнал в сторону dead_confirmed, но это статический
  вывод из существующих тестов — не заменяет требуемый trace/coverage
  прогон (раздел 4).

- Полный `pytest -q` в песочнице архитектора даёт 133 collection errors —
  но первая проверенная причина (tests/test_decision_gate.py) это
  ModuleNotFoundError: httpx, то есть отсутствие зависимостей в песочнице,
  а не проблема кода. Эта цифра НЕ используется как evidence в этом PRD
  и не путается с 5 файлами выше, у которых причина падения — реально
  отсутствующий модуль проекта, а не отсутствующий pip-пакет. Полный
  чистый прогон "133 -> 0" — предмет PRD-047.45 (Test Suite Health Audit),
  не этого PRD.
```

---

## 2. Scope PRD-047.40

```text
A. Raw-log untrack (предварительный шаг, выполняется первым).
B. Удаление 5 мёртвых тестовых файлов, ссылающихся на 13 dead_confirmed
   компонентов, + снятие соответствующих --ignore строк из pytest.ini.
C. Точечная зачистка второстепенных ссылок (debug-fixture строка,
   try/except импорт в bootstrap-скрипте) — best-effort, не gate-блокер.
D. Trace user_level_adapter -> зафиксировать итоговый статус
   (dead_confirmed | active). Без удаления в этом PRD.
E. Замена test_no_legacy.py на test_dead_code_removed.py.
```

### 2.A. Raw-log untrack — точный источник

```text
Источник истины: TO_DO_LIST/logs/PRD-047.39/logs_tracking_manifest.md,
раздел "Raw Artifact Candidate Paths" — 532 пути, 63.2MB, тир raw_artifact.

Действие: git rm -r --cached <каждый путь из списка> (файлы остаются на
диске). НЕ трогать evidence_of_record (424, 1.6MB) и light_evidence_keep
(1602, 12.5MB) — они тем же манифестом явно исключены из untrack.

Обязательное доказательство перед коммитом: пересчитать количество
untracked путей и сверить == 532; убедиться, что ни один из 424
markdown-файлов evidence_of_record не попал в diff untrack (полное
множественное пересечение списков должно быть пустым).
```

### 2.B. Удаление мёртвых тестовых файлов — точный список

```text
tests/test_phase1.py
tests/test_phase2.py
tests/test_phase3.py
tests/test_fast_detector.py
tests/test_full_dialogue_pipeline.py

Действие: удалить (не переносить в _retired/ — они не проверяют ничего
живого, это не quarantine уровня PRD-047.39 Risk H, а прямое следствие
уже нулевого import-графа). Из pytest.ini убрать 5 соответствующих строк
--ignore=tests/test_phase1.py и т.д. — они станут не нужны и будут вводить
в заблуждение, если останутся (создают видимость, что где-то ещё есть
файл, который приходится игнорировать).

Перед удалением каждого файла — Risk H-проверка (унаследована из
PRD-047.39 §10): git blame + grep по всему репо на предмет any
string-based dispatch (importlib.import_module("bot_agent.answer_basic"),
getattr(bot_agent, "answer_question_sag_aware", None) и т.п.), не
видимого статическому import-графу. Если такой динамический вызов
найден — этот файл выходит из dead_confirmed, PRD блокируется по этому
пункту, остальные пункты можно завершать отдельно.
```

### 2.C. Второстепенные ссылки (не gate-блокер)

```text
tests/test_debug_metrics_and_export.py — заменить строковый литерал
  "sd_classifier" в примере pipeline_stages на нейтральное имя
  (например "retrieval_prefilter") — это только пример данных для
  debug-экспорта, не тест самого классификатора.

scripts/bootstrap_eval_sets.py — импорт "from bot_agent.sd_classifier
  import SDClassifier" внутри try/except с fallback уже безопасен
  (sd_acc=0.0 при ImportError), но сам мёртвый импорт можно убрать вместе
  с веткой sd_classifier_accuracy_at_1, раз источник навсегда исчез.
  Не блокирует acceptance, если Executor решит отложить — тогда фиксирует
  как известный остаток в отчёте.
```

---

## 3. Non-goals

```text
- Не удаляет user_level_adapter (ни параметр, ни ключ метаданных,
  ни файлы) — только трассирует и классифицирует.
- Не трогает 128 (133 минус 5 из раздела 2.B) прочих collection errors,
  вызванных отсутствующими зависимостями/другими причинами — это
  PRD-047.45 (Test Suite Health Audit), явно идущий после этого PRD
  по Master Plan §5.4.
- Не начинает PRD-047.41 (flag consolidation) — ни один env-флаг не
  трогается.
- Не переписывает writer_agent.py, admin_routes.py, writer_contract.py.
- Не трогает Chroma, Bot_data_base, registry, processed blocks, source
  documents, Writer prompt, retrieval ranking, safety-логику.
- Не переписывает git-историю.
- Не удаляет ни одного markdown-файла отчёта/PRD из TO_DO_LIST — только
  untrack 532 raw-путей по точному списку раздела 2.A.
- Не удаляет tools/run_prd_047_39_architecture_inventory.py — это
  историческая инвентаризационная утилита, её ссылки на имена мёртвых
  компонентов — часть отчёта, не runtime-код.
```

---

## 4. Required trace — user_level_adapter

```text
Задача: превратить unclear_needs_trace в dead_confirmed или active —
третьего состояния после этого PRD быть не должно (Master Plan §4).

Шаги:
1. Полный grep-граф: все файлы, где встречается user_level_adapter или
   user_level_adapter_applied (актуализировать список из раздела 1 —
   response_generator.py, debug_routes.py, api/routes/common.py, плюс
   тестовые файлы).
2. Для каждого активного referencing-сайта (response_generator.py L115,
   L130, L215, L224) подтвердить документально, что это compat no-op
   (`_ = user_level_adapter  # ... intentionally ignored`), а не скрытая
   ветка логики.
3. Прогнать 12 pilot-сценариев (тот же набор, что PRD-047.38 gate) или
   эквивалентный live smoke с включённым trace/coverage — подтвердить,
   что ни один сценарий не проходит через код, реально читающий значение
   user_level_adapter (в отличие от игнорирования параметра).
4. Явно сверить с уже существующими тестами:
   tests/unit/test_user_level_adapter_removed.py и
   tests/inventory/test_no_active_legacy_trace_metadata_keys.py — они
   формулируют ожидание "отсутствует в активном пути", но это ожидание
   нужно подтвердить рантайм-трассировкой, а не переприсвоением того же
   вывода, который эти тесты уже статически делают (иначе trace ничего
   не добавляет к тому, что уже известно из раздела 1).
5. Зафиксировать вердикт в TO_DO_LIST/logs/PRD-047.40/
   user_level_adapter_trace.md:
   dead_confirmed -> становится кандидатом отдельного будущего PRD
     (не удаляется здесь);
   active -> документируется в PROJECT_STATE.md с указанием, что именно
     оно делает и почему compat-параметр остаётся.
```

---

## 5. Required implementation

```text
Repo-level путь (как в PRD-047.39):
tools/run_prd_047_40_dead_pipeline_removal.py

Runner должен:
1. Выполнить 2.A (raw-log untrack) первым шагом, с доказательством
   пересечения множеств (раздел 2.A).
2. Для каждого файла из 2.B — Risk H-проверка -> удаление -> коммит
   отдельно от остальных изменений (чтобы diff читался).
3. Убрать соответствующие 5 строк --ignore из pytest.ini.
4. Прогнать full regression (все тесты, которые pytest.ini больше не
   игнорирует после шага 3) + live smoke — до и после удаления файлов
   из 2.B, приложить оба лога. Ожидаемый результат: 0 новых failures
   помимо уже известных из раздела 1 (133 collection errors по причинам
   вне scope этого PRD остаются как есть и фиксируются отдельной
   строкой, не путать с "новыми регрессиями").
5. Выполнить 2.C (best-effort, не блокирует acceptance).
6. Выполнить раздел 4 (user_level_adapter trace) и записать вердикт.
7. Заменить tests/contract/test_no_legacy.py на
   tests/contract/test_dead_code_removed.py:
   - позитивные assert'ы: файлы 2.B физически отсутствуют
     (repo-wide, не только в bot_agent/) AND ни один .py/.md файл во всём
     репозитории не содержит `import bot_agent.answer_basic` /
     `bot_agent.answer_sag_aware` / `bot_agent.answer_graph_powered` /
     `bot_agent.sd_classifier` как исполняемого импорта (grep-based
     proof, не только "файла по такому пути нет" — см. Risk K ниже);
   - один assert, фиксирующий текущий вердикт user_level_adapter
     (dead_confirmed или active) — чтобы регресс в третье состояние был
     виден автоматически, если кто-то тронет этот код в будущем PRD.
```

---

## 6. Output reports

```text
TO_DO_LIST/logs/PRD-047.40/raw_log_untrack_manifest.md
TO_DO_LIST/logs/PRD-047.40/dead_test_removal_report.md
TO_DO_LIST/logs/PRD-047.40/user_level_adapter_trace.md
TO_DO_LIST/logs/PRD-047.40/regression_before.log
TO_DO_LIST/logs/PRD-047.40/regression_after.log
TO_DO_LIST/logs/PRD-047.40/live_smoke_before.md
TO_DO_LIST/logs/PRD-047.40/live_smoke_after.md
TO_DO_LIST/logs/PRD-047.40/no_mutation_proof.md
TO_DO_LIST/logs/PRD-047.40/next_recommendation.md
```

---

## 7. Safe-action checklist

```text
[ ] Сверить logs_tracking_manifest.md raw_artifact список == 532 путей
[ ] git rm -r --cached по списку 532 путей; подтвердить 0 пересечений
    с evidence_of_record (424) и light_evidence_keep (1602)
[ ] Risk H grep-проверка на string-based dispatch для каждого из 5
    файлов раздела 2.B
[ ] git rm tests/test_phase1.py tests/test_phase2.py tests/test_phase3.py
    tests/test_fast_detector.py tests/test_full_dialogue_pipeline.py
[ ] Убрать 5 строк --ignore из pytest.ini
[ ] full regression до/после, live smoke до/после — приложить логи
[ ] 2.C best-effort правки (debug-fixture строка, bootstrap-скрипт)
[ ] user_level_adapter trace -> зафиксировать вердикт
[ ] tests/contract/test_no_legacy.py -> tests/contract/test_dead_code_removed.py
```

---

## 8. Acceptance decision

```text
ACCEPTED               -> raw-log untrack завершён (532/532, 0 пересечений
                           с evidence), все 5 файлов удалены и Risk H чист,
                           full regression + live smoke без новых
                           regressions, trace user_level_adapter завершён
                           (dead_confirmed либо active — не unclear),
                           test_dead_code_removed.py на месте и зелёный.
ACCEPTED_WITH_WARNINGS -> основное выполнено, но 2.C отложен ИЛИ trace
                           user_level_adapter дал inconclusive результат
                           на 12 сценариях (не на весь live smoke) —
                           тогда доп. trace становится отдельным
                           follow-up, а не блокирует всё остальное.
BLOCKED                 -> Risk H нашёл живой string-based dispatch на
                           один из 5 файлов ИЛИ raw-log untrack задел
                           хотя бы один markdown evidence-файл ИЛИ
                           regression показал расхождение до/после.
INCONCLUSIVE             -> trace user_level_adapter не смог дать
                           dead_confirmed/active даже после coverage-
                           прогона по всем 12 сценариям — нужен отдельный
                           PRD именно под этот компонент перед PRD-047.41.
```

---

## 9. Risk register (дополнение к PRD-047.39 §10)

```text
Risk H (унаследован) — Quarantine/удаление скрывает реальную регрессию
  Response: см. раздел 2.B, обязательная проверка перед каждым удалением.

Risk I — Untrack 532 путей случайно задевает markdown evidence
  Symptom: git rm --cached захватывает файл, который PRD_INDEX.md,
           PROJECT_STATE.md или другой отчёт ссылается по имени.
  Response: пересечение множеств "532 raw" и "424 evidence_of_record +
            1602 light_evidence_keep" должно быть математически пустым
            (manifest уже это разделяет) — доказательство обязательно
            в raw_log_untrack_manifest.md, не на словах.

Risk J — test_dead_code_removed.py проходит тривиально
  Symptom: тест проверяет только "файл по пути X не существует", но
           если кто-то физически скопирует логику компонента под другим
           именем/путём, тест этого не поймает — ложное чувство
           завершённости.
  Response: тест обязан включать repo-wide grep на исполняемый импорт
            конкретных имён модулей (не только путь), как описано в
            разделе 5, пункт 7.

Risk K — pytest.ini молча накапливает --ignore вместо реальной чистки
  Symptom: вместо удаления файла из 2.B кто-то в будущем добавляет ещё
           один --ignore для новой мёртвой ссылки, и список игнора растёт
           бесконечно, маскируя реальный объём долга.
  Response: этот PRD — прецедент "--ignore снимается вместе с удалением
            причины", не накапливается. Зафиксировать это явно в
            dead_test_removal_report.md как норму для будущих PRD.
```

---

## 10. IDE-agent rules (дополнение)

```text
Must not:
- удалять или трогать user_level_adapter в любом виде;
- untrack-ить что-либо за пределами точного списка 532 путей из
  logs_tracking_manifest.md;
- объединять raw-log untrack и удаление тестовых файлов в один коммит
  (разные оси риска — держать diff читаемым, как того требует
  Master Plan §5.4);
- расширять scope на PRD-047.41 (флаги) даже если "заодно уже здесь".

Must:
- приложить regression/live-smoke логи до и после отдельно для каждого
  из двух главных действий (2.A и 2.B), не общий лог "всё вместе";
- явно указать в отчёте, что 133 (минус 5 закрытых этим PRD = 128)
  прочих collection errors не являются регрессией этого PRD и остаются
  задачей PRD-047.45;
- обновить единственный обновляемый раздел Master Plan (ЧАСТЬ 4) только
  после ACCEPTED/ACCEPTED_WITH_WARNINGS вердикта архитектора, не
  самостоятельно.
```

---

## 11. Simple explanation

```text
Прошлый PRD (047.39) только посчитал и разложил по полочкам, что в
проекте мёртвого. Ничего не удалял. Сейчас проверка показала: сам "труп"
(старые файлы answer_basic.py и его братья) на самом деле уже вынесен —
его физически нет. А вот 5 тестов, которые когда-то его проверяли,
всё ещё лежат в папке и в буквальном смысле не открываются (пытаются
позвать то, чего больше нет). Их придётся либо игнорировать вечно (что
и происходит прямо сейчас через pytest.ini), либо один раз убрать. Этот
PRD убирает. Плюс — довозим то, что 047.39 отложил: 532 старых файла
логов (63.2MB) официально перестают попадать в git (сами файлы никуда
с диска не денутся). И отдельно разбираемся с одной штукой
(user_level_adapter), про которую пока непонятно, живая она или нет —
разбираемся, но не удаляем, пока не убедимся.
```
