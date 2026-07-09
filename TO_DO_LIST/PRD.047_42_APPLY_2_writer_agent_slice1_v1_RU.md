# PRD-047.42-APPLY-2 — God-File Decomposition, Stage 2b: writer_agent.py slice 1 v1 RU

**Проект:** Bot Psychologist / Neo MindBot
**Репозиторий:** `Askhat-cmd/Text_transcription`
**Локальный путь пользователя:** `C:\My_practice\Text_transcription`
**Дата:** 2026-07-09
**Статус:** draft / ready for IDE-agent implementation
**Основание:** PRD-047.42-APPLY принят (`ACCEPTED`) — admin_routes.py разрезан чисто. Master Plan §5.3, Stage 2b.

---

## 0. Короткое решение

```text
writer_agent.py — не admin_routes.py. Это один класс (WriterAgent),
методы которого делят внутреннее состояние (self.client, self.model
и т.д.) и вызывают друг друга. Резать весь файл по карте PRD-047.42
одним PRD, как admin_routes.py, здесь НЕЛЬЗЯ -- там были независимые
route-хендлеры, здесь связанный класс.

Поэтому этот PRD — только первый, самый безопасный срез: 4 функции
блока "constants" (125 строк из 2188), которые уже сейчас, ДО переноса,
являются чистыми модульными функциями без self и без побочных эффектов:
  _extract_literal_markdown_echo_request, _to_int, _to_float, _contains_any

Проверено архитектором: эти 4 функции нигде за пределами
writer_agent.py не импортируются (в проекте есть десятки одноимённых
_contains_any/_to_int в других файлах — это не общий импорт, а
идиома "свой приватный хелпер в каждом модуле", подтверждено grep).
Значит перенос не затрагивает ничего снаружи файла.

Остальные 9 блоков карты PRD-047.42 -- отдельные, более осторожные
PRD дальше: сначала static-методы (не требуют self), потом методы с
self, самое последнее -- _call_llm (803 строки) и
_enforce_answer_compliance (608 строк), два по-настоящему сросшихся
метода с общим состоянием.
```

---

## 1. Проверка перед написанием (архитектор, 2026-07-09)

```text
git fetch: HEAD == origin/main == 7445f31, без расхождений.

Перечитал сам writer_agent.py строки 45-169 напрямую (не полагаюсь на
карту PRD-047.42 как на неприкосновенную истину -- она правильно
разметила границы блока, но не проверяла "можно ли безопасно резать
именно эту часть первой", это моя оценка):

  строка 93:  def _extract_literal_markdown_echo_request(user_message: str) -> str
  строка 109: def _to_int(value: str, default: int) -> int
  строка 116: def _to_float(value: str, default: float) -> float
  строка 123: def _contains_any(text: str, markers: tuple[str, ...]) -> bool

Все 4 -- module-level функции (не методы класса), без self, без
обращения к WriterAgent-состоянию, без сайд-эффектов. Class WriterAgent
начинается только на строке 172, ПОСЛЕ этого блока.

grep по всему репозиторию подтвердил: ни _to_int, ни _contains_any,
ни _to_float, ни _extract_literal_markdown_echo_request из
writer_agent.py никем не импортируются снаружи -- у каждого модуля
проекта своя приватная копия похожих хелперов (типичный паттерн
здесь), не общий shared-импорт.
```

---

## 2. Scope

```text
A. Перенести 4 функции (строки 45-169, ~125 строк с учётом отступов и
   докстрингов) в новый файл bot_agent/multiagent/agents/
   writer_agent_constants.py -- код 1-в-1, без переписывания логики.
B. В writer_agent.py заменить эти 4 определения на импорт из нового
   файла: "from .writer_agent_constants import
   _extract_literal_markdown_echo_request, _to_int, _to_float,
   _contains_any" (или без podчёркивания, если Исполнитель считает
   нужным сделать их публичными в новом файле -- решение за ним, но
   имена вызовов внутри writer_agent.py менять нельзя).
C. Contract-test: 1 unit-тест на каждую из 4 функций напрямую (edge
   cases: пустая строка, None, некорректный формат числа для _to_int/
   _to_float) -- если таких тестов ещё нет.
```

---

## 3. Non-goals

```text
- НЕ трогает ни один из 9 оставшихся блоков карты writer_agent.py.
- НЕ трогает writer_contract.py, admin_routes.py (уже разрезан),
  diagnostic_center_* файлы.
- НЕ меняет логику самих 4 функций -- только их местоположение.
- НЕ меняет ни один вызов этих функций внутри writer_agent.py по
  сигнатуре (только источник импорта).
- НЕ продолжает работу над _call_llm / _enforce_answer_compliance --
  это заведомо не входит в этот PRD.
```

---

## 4. Required implementation

```text
1. Snapshot "ДО": прогнать существующие тесты, которые покрывают
   writer_agent.py (tests/multiagent/test_writer_agent.py и соседние
   из external_dependency_graph.md PRD-047.42), записать полный
   результат.
2. Создать writer_agent_constants.py, перенести 4 функции.
3. Заменить определения в writer_agent.py на импорт.
4. Прогнать тот же набор тестов снова -- идентичный результат.
5. git hash-object для writer_contract.py и admin_routes.py (все 10
   новых admin-модулей включительно) -- подтвердить 0 изменений,
   этот PRD их не касается вообще.
```

---

## 5. Output reports

```text
TO_DO_LIST/logs/PRD-047.42-APPLY-2/extraction_log.md
TO_DO_LIST/logs/PRD-047.42-APPLY-2/test_results_before.log
TO_DO_LIST/logs/PRD-047.42-APPLY-2/test_results_after.log
TO_DO_LIST/logs/PRD-047.42-APPLY-2/no_mutation_proof.md (writer_contract.py,
  admin_routes.py + все 10 admin-модулей -- доказать нетронутость)
TO_DO_LIST/logs/PRD-047.42-APPLY-2/next_recommendation.md (какой блок
  резать следующим -- рекомендация Исполнителя, не решение)
```

---

## 6. Acceptance decision

```text
ACCEPTED               -> 4 функции перенесены, writer_agent.py импортирует
                           их без изменения вызовов, тесты идентичны
                           до/после, writer_contract.py/admin_routes.py
                           доказанно не тронуты.
BLOCKED                 -> любой тест до/после разошёлся ЛИБО найден
                           внешний импортёр этих 4 функций, которого
                           architect-проверка пропустила.
```

---

## 7. Simple explanation

```text
Резать writer_agent.py опаснее, чем резали админку -- там всё было
независимыми кусками, здесь один слитный класс. Поэтому берём
единственный кусок, который уже сейчас лежит ОТДЕЛЬНО от класса и ни
от чего не зависит -- 4 маленькие вспомогательные функции (перевести
текст в число, проверить есть ли слово в списке и т.п.). Это разминка
перед по-настоящему сложными кусками, которые придут позже, по одному,
самое сложное -- в самом конце.
```
