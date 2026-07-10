# PRD-047.42-APPLY-4 — God-File Decomposition, Stage 2d: writer_agent.py slice 3 (mixin) v1 RU

**Проект:** Bot Psychologist / Neo MindBot
**Репозиторий:** `Askhat-cmd/Text_transcription`
**Локальный путь пользователя:** `C:\My_practice\Text_transcription`
**Дата:** 2026-07-10
**Статус:** ACCEPTED / implemented
**Implementation commit:** `fadd43f`
**Completion metadata:** synced in follow-up delivery commit
**Основание:** PRD-047.42-APPLY-3 принят (`ACCEPTED`) — slice 2 (8 static-методов) вынесен чисто. Master Plan §5.3, Stage 2d. Владелец подтвердил: укрупнять шаги там, где риск объективно позволяет (2026-07-10).

---

## 0. Короткое решение

```text
Slice 3 отличается от slice 1 и 2: эти 8 методов используют self
по-настоящему (мутируют self.last_debug, self._client, вызывают друг
друга через self.). Раньше (slice 1-2) можно было просто вынести код
как module-level функции. Здесь так не получится, не поломав вызовы.

Поэтому механика другая: НЕ функции, а mixin-класс. Все 8 методов
переезжают как есть, один-в-один (тела не меняются вообще, даже
пробел), в отдельный класс WriterAgentFallbackStateMixin в новом файле.
WriterAgent начинает наследоваться от этого mixin'а. self. работает
ровно так же, как работал -- Python отдаёт атрибуты через обычное
наследование, вызывающим местам ВООБЩЕ не нужно ничего менять.

Именно поэтому этот шаг можно сделать крупнее (все 8 методов сразу,
не по одному) -- риск здесь определяется не количеством методов,
а способом переноса. Mixin-перенос одинаково безопасен что для одного
метода, что для восьми.
```

---

## 1. Проверка перед написанием (архитектор, 2026-07-10)

```text
git fetch: HEAD == origin/main == 0bdb297, без расхождений.

writer_agent.py сейчас 2066 строк. Прочитал блок целиком (строки
1909-2061), не по старой карте PRD-047.42 (номера давно сдвинулись
после slice 1 и 2).

8 методов и их реальные связи с состоянием:
  _repair_greeting_without_mechanism_lecture(self, *, user_message)
    -> зовёт self._set_final_answer_shape_debug
  _resolve_one_step_or_no_practice_fallback(self, ...)
    -> зовёт self._set_final_answer_shape_debug,
       self._strip_optional_followup_invitation (уже static-делегат),
       self._build_no_practice_fallback_text (уже static-делегат)
  _set_final_answer_shape_debug(self, shape)
    -> мутирует self.last_debug["final_answer_shape"] -- "хаб", его
       зовут остальные
  _defer_no_stub_repair(self, ...)
    -> читает/мутирует self.last_debug (несколько ключей), зовёт
       self._set_final_answer_shape_debug,
       self._strip_optional_followup_invitation
  _get_client(self)
    -> читает/пишет self._client, импортирует openai.AsyncOpenAI,
       читает config.OPENAI_API_KEY -- реальный фабричный метод
       LLM-клиента, единственный из восьми с внешней (не debug) стороной
  _estimate_cost(self, ...)
    -> читает self.last_debug.get("model"), зовёт self._resolve_model()
       (ОСТАЁТСЯ в WriterAgent, не в этом срезе), использует
       _COST_PER_1K_TOKENS (см. ниже)
  _apply_name_continuity(self, ...)
    -> зовёт self._extract_user_name
  _extract_user_name(self, ...)
    -> зовёт self._normalize_name (уже static-делегат), использует
       _RU_NAME_PATTERNS / _EN_NAME_PATTERNS (см. ниже)

Три модульные константы используются ИСКЛЮЧИТЕЛЬНО этими методами
(проверено grep по всему writer_agent.py -- больше нигде не
встречаются, безопасно переносить вместе с методами, не оставляя
циркулярный импорт):
  _COST_PER_1K_TOKENS (строка 71) -- только в _estimate_cost
  _RU_NAME_PATTERNS   (строка 77) -- только в _extract_user_name
  _EN_NAME_PATTERNS   (строка 81) -- только в _extract_user_name

self._resolve_model() (строка 151) -- ОСТАЁТСЯ в основном классе,
  это не часть этого среза; _estimate_cost продолжит звать его через
  self., что работает автоматически при mixin-наследовании.
```

---

## 2. Scope

```text
A. Создать bot_agent/multiagent/agents/writer_agent_fallback_state_mixin.py
   с классом WriterAgentFallbackStateMixin, содержащим все 8 методов
   -- тела переносятся 1-в-1, без единого изменения логики.
   Перенести туда же 3 константы (_COST_PER_1K_TOKENS, _RU_NAME_PATTERNS,
   _EN_NAME_PATTERNS).
B. class WriterAgent(...) -> добавить WriterAgentFallbackStateMixin в
   список родительских классов. Удалить 8 тел методов + 3 константы из
   writer_agent.py (они теперь наследуются).
C. Contract-test: прямые unit-тесты на не менее рискованные из восьми
   (_get_client -- с моком OPENAI_API_KEY set/unset; _estimate_cost --
   несколько моделей; _extract_user_name/_apply_name_continuity --
   RU/EN паттерны, отсутствие имени).
```

---

## 3. Non-goals

```text
- НЕ трогает slice 1 (writer_agent_constants.py) и slice 2
  (writer_agent_fallback_helpers.py) -- отдельные, уже принятые файлы.
- НЕ трогает writer_contract.py, admin_routes.py + 10 admin-модулей,
  diagnostic_center_* файлы.
- НЕ трогает write(), _resolve_runtime_settings, _call_llm (803 строки),
  _enforce_answer_compliance (608 строк), _enforce_mvp_free_dialogue_
  compliance -- следующие, более осторожные срезы, не этот PRD.
- НЕ меняет ни одно тело метода -- только физическое место
  (class body переезжает целиком в mixin).
- НЕ меняет self._resolve_model() -- остаётся в основном классе.
```

---

## 4. Required implementation

```text
1. Snapshot "ДО": прогнать tests/multiagent/test_writer_agent.py,
   test_writer_agent_constants.py, test_writer_agent_fallback_helpers.py
   -- записать полный результат (ожидаемо: тот же 1 pre-existing fail
   test_semantic_hits_limit_to_two).
2. Создать writer_agent_fallback_state_mixin.py, перенести 8 методов +
   3 константы как есть.
3. WriterAgent наследует от mixin'а; удалить перенесённые тела и
   константы из writer_agent.py.
4. Прогнать тот же набор тестов -- идентичный результат.
5. git hash-object для writer_agent_constants.py,
   writer_agent_fallback_helpers.py, writer_contract.py, admin_routes.py
   + все 10 admin-модулей -- подтвердить 0 изменений.
```

---

## 5. Output reports

```text
TO_DO_LIST/logs/PRD-047.42-APPLY-4/extraction_log.md
TO_DO_LIST/logs/PRD-047.42-APPLY-4/test_results_before.log
TO_DO_LIST/logs/PRD-047.42-APPLY-4/test_results_after.log
TO_DO_LIST/logs/PRD-047.42-APPLY-4/no_mutation_proof.md
TO_DO_LIST/logs/PRD-047.42-APPLY-4/next_recommendation.md (следующий
  срез -- write()/_resolve_runtime_settings, рекомендация не решение)
```

---

## 6. Acceptance decision

```text
ACCEPTED               -> 8 методов + 3 константы перенесены в mixin,
                           WriterAgent наследует его, тесты идентичны
                           до/после, все ранее принятые файлы (slice 1,
                           slice 2, writer_contract.py, admin_routes.py
                           + 10 модулей) доказанно не тронуты.
BLOCKED                 -> любой тест разошёлся ИЛИ найден внешний
                           вызыватель одной из этих 8 методов/3 констант,
                           пропущенный architect-проверкой.
```

---

## 7. Simple explanation

```text
В прошлые два раза выносили функции, которым вообще не нужен был сам
объект класса. Сейчас эти 8 методов объект использовать -- они читают
и меняют его внутренние поля (например "что сейчас происходит с
ответом" и "клиент для связи с моделью"). Такие штуки нельзя просто
скопипастить в отдельный файл как функции -- сломаются все места,
которые их вызывают через self.

Решение — Python-приём "mixin": берём эти 8 методов, кладём их в
отдельный класс в отдельном файле, и говорим основному классу
"унаследуй эти методы оттуда". Снаружи всё выглядит и работает ровно
так же, как раньше — просто код физически лежит в другом файле.
Именно поэтому в этот раз можно взять все 8 сразу одним PRD, а не по
одному — безопасность здесь не зависит от количества методов.
```
