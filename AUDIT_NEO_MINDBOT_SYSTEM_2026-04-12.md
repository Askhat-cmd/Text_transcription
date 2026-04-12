# Аудит системы Neo MindBot (deep audit)

Дата: 2026-04-12
Проект: `C:\My_practice\Text_transcription`
Цель: оценить, насколько текущая система ответов/маршрутов/правил «безупречна» и насколько она соответствует документу `Neo MindBot.md`.

## 1) Краткий вердикт

Система **не является безупречной** на текущем этапе.

Что хорошо:
- Архитектурно есть рабочий Neo-контур: `diagnostics-v1` + детерминированный route resolver + prompt stack v2.
- SSE-доставка и фронтовый парсер событий работают стабильно (по тестам фронта).
- Трейс для dev-режима снова доступен и структурирован.

Что критично/существенно:
- «Стриминг» в backend сейчас псевдо-стриминг: сначала считается полный ответ, потом режется на слова и отправляется как токены.
- Есть контрактный рассинхрон SSE `done`-payload (backend vs тест): `answer_fallback` вместо ожидаемого `answer`.
- Формирование ответа в runtime содержит жёсткий посимвольный clip по mode-лимитам.
- Реализация prompt-stack v2 по смысловой насыщенности заметно проще и уже, чем требования `Neo MindBot.md`.
- В runtime отключён output validator (`USE_OUTPUT_VALIDATION=false`), несмотря на наличие модуля.

Итоговая оценка (инженерная):
- Стабильность: **средняя/выше средней**
- Соответствие NEO-замыслу: **частичное**
- Готовность «безупречно» для long-form диалога: **нет**

## 2) Как проверялось

1. Ревью кода ключевых контуров:
- `bot_psychologist/bot_agent/answer_adaptive.py`
- `bot_psychologist/bot_agent/llm_streaming.py`
- `bot_psychologist/bot_agent/response/response_formatter.py`
- `bot_psychologist/bot_agent/prompt_registry_v2.py`
- `bot_psychologist/bot_agent/prompts/*.md`
- `bot_psychologist/api/routes.py`
- `bot_psychologist/api/debug_routes.py`
- `bot_psychologist/web_ui/src/services/api.service.ts`
- `bot_psychologist/web_ui/src/hooks/useChat.ts`
- `bot_psychologist/web_ui/src/components/chat/Message.tsx`
- `bot_psychologist/web_ui/src/styles/index.css`

2. Снятие живого runtime-состояния с поднятого сервера:
- `GET /api/v1/admin/status`
- `GET /api/v1/admin/runtime/effective`
- `GET /api/v1/admin/diagnostics/effective`
- `GET /api/v1/admin/config`

3. Тесты:
- Backend: `pytest tests/test_sse_payload.py tests/unit/test_route_resolver_rules.py tests/test_output_validator_neo.py tests/unit/test_prompt_stack_order.py tests/unit/test_memory_fallback_chain.py -q`
- Frontend: `npm run test -- src/services/api.stream.test.ts src/hooks/useChat.test.ts --run`

## 3) Фактическое состояние runtime (живой сервер)

Источник: admin endpoints на `http://localhost:8001`.

- `degraded_mode=false`
- `data_source=api`
- `blocks_loaded=229`
- `prompt_stack_version=2.0`
- `USE_NEW_DIAGNOSTICS_V1=true`
- `USE_DETERMINISTIC_ROUTE_RESOLVER=true`
- `USE_PROMPT_STACK_V2=true`
- `USE_OUTPUT_VALIDATION=false`
- `INFORMATIONAL_BRANCH_ENABLED=true`
- `DISABLE_SD_RUNTIME=true`
- `LLM_MODEL=gpt-5-mini`
- `ENABLE_STREAMING=true`
- `FREE_CONVERSATION_MODE=false`
- `MAX_CONTEXT_SIZE=2000`
- `SUMMARY_MAX_CHARS=500`
- `TOP_K_BLOCKS=9` (override)
- `VOYAGE_TOP_K=3` (override)

## 4) Ключевые находки (с доказательствами)

### [Высокий] Псевдо-стриминг вместо нативного LLM streaming

Наблюдение:
- `stream_answer_tokens()` сначала полностью вызывает `answer_question_adaptive(...)`, и только потом разрезает уже готовый текст по словам.

Доказательства:
- `bot_psychologist/bot_agent/llm_streaming.py:39-51` (полный sync run в executor)
- `bot_psychologist/bot_agent/llm_streaming.py:59-64` (split на слова и yield)

Риск:
- Потеря реального «живого набора текста» и UX-эффекта контактного стриминга.
- Сложнее локализовать причину «обрезки» как stream-инцидент, т.к. обрезка может происходить до SSE.

### [Высокий] Контрактный дрейф SSE done payload

Наблюдение:
- Backend отправляет в done-событии `answer_fallback`, а тест ожидает `answer`.

Доказательства:
- `bot_psychologist/api/routes.py:825-829` (`done_payload` содержит `answer_fallback`)
- `bot_psychologist/tests/test_sse_payload.py:71` (ожидание ключа `answer`)
- Тест-результат: `1 failed, 21 passed` (падает `test_done_event_has_no_trace_field`)

Риск:
- Хрупкость контракта между backend/frontend/тестами и внешними агентами.

### [Высокий] Базовый system prompt противоречит части NEO-идей о «богатом» ответе

Наблюдение:
- В `prompt_system_base.md` есть жёсткие установки на короткость/простоту и вопросный стиль, которые могут системно уводить ответы в более короткий формат.

Доказательства:
- `bot_psychologist/bot_agent/prompt_system_base.md:19` (`если можно сказать проще — говори проще`)
- `...:44-46` (`задай вопрос; не давай сразу ответ`)
- Этот prompt включается в stack v2 через `CORE_IDENTITY`:
  - `bot_psychologist/bot_agent/prompt_registry_v2.py:324`

Риск:
- При ряде маршрутов модель может стабильно выбирать «короткий» стиль вместо глубокой развертки.

### [Средний] Жёсткий посимвольный clip в форматтере

Наблюдение:
- После генерации ответ всегда проходит через `_clip(...)` по лимитам mode.

Доказательства:
- `bot_psychologist/bot_agent/response/response_formatter.py:21-28` (mode char limits)
- `...:127-128` (безусловный `return self._clip(text, char_limit)`)
- Применяется в runtime в двух ветках:
  - `bot_psychologist/bot_agent/answer_adaptive.py:1732-1739`
  - `bot_psychologist/bot_agent/answer_adaptive.py:2645-2652`

Риск:
- Потенциальная обрезка «хвоста» при длинных ответах даже без запроса на краткость.

### [Средний] “Полотно ЛЛМ” может вводить в заблуждение как источник «полного ответа»

Наблюдение:
- В `llm_call_info` хранится только `response_preview` первых 300 символов.
- Debug endpoint отдаёт это поле как preview.

Доказательства:
- `bot_psychologist/bot_agent/llm_answerer.py:420` (`response_preview=(answer or '')[:300]`)
- `bot_psychologist/api/debug_routes.py:172` (`response_preview` берется как preview)

Риск:
- Кажется, что «в полотне» есть продолжение/обрыв, но это может быть просто preview-представление, а не полный persisted answer.

### [Средний] Output Validator реализован, но в живом runtime отключён

Наблюдение:
- Модуль в коде есть, проверки довольно строгие, но флаг выключен в runtime.

Доказательства:
- `bot_psychologist/bot_agent/output_validator.py` (реализован)
- runtime snapshot: `USE_OUTPUT_VALIDATION=false`
- Встроенная точка включения есть:
  - `bot_psychologist/bot_agent/answer_adaptive.py:406-407`, `...:417-427`

Риск:
- Непойманные underfilled/контрактные проблемы уходят в прод-диалог.

### [Позитив] Явного UI-обрезания сообщения стилями не найдено

Наблюдение:
- В message-компоненте и стилях нет line-clamp/ellipsis для тела сообщения бота.

Доказательства:
- `bot_psychologist/web_ui/src/components/chat/Message.tsx:42`
- `bot_psychologist/web_ui/src/styles/index.css:156-162` (`message-bot`, `overflow: visible`)

Вывод:
- Основная зона проблемы длины/обрезки сейчас вероятнее backend prompt/policy/formatter/contract, а не CSS.

## 5) Результаты тестов

### Backend

Команда:
`python -m pytest tests/test_sse_payload.py tests/unit/test_route_resolver_rules.py tests/test_output_validator_neo.py tests/unit/test_prompt_stack_order.py tests/unit/test_memory_fallback_chain.py -q`

Результат:
- **1 failed, 21 passed**
- Падение:
  - `tests/test_sse_payload.py::test_done_event_has_no_trace_field`
  - причина: ожидание `answer`, фактически `answer_fallback`.

### Frontend

Команда:
`npm run test -- src/services/api.stream.test.ts src/hooks/useChat.test.ts --run`

Результат:
- **18 passed, 0 failed**

## 6) Соответствие `Neo MindBot.md` (матрица)

Важно: документ NEO — широкий стратегический blueprint. Ниже оценка по главам с точки зрения текущего runtime.

### Глава 1 (миссия, роли, каскад, приоритеты)

Статус: **Частично соответствует**

Что совпадает:
- Каскадная сборка prompt stack v2 с фиксированным порядком:
  - `bot_psychologist/bot_agent/prompt_registry_v2.py:14-22`
- Приоритет safety и route-level guardrails отражены в логике.

Что расходится:
- Содержательная глубина prompt-слоев в `prompts/*.md` сильно компактнее NEO-текста.
- `prompt_system_base.md` частично тянет стиль в сторону краткости/вопросности.

### Глава 2 (память и контекст)

Статус: **Частично/хорошо соответствует**

Что реализовано:
- short-term + semantic + summary контекст:
  - `bot_psychologist/bot_agent/conversation_memory.py:715-793`
- сохранение summary и working state.
- кросс-сессионный summary bootstrap.

Ограничения:
- Контекстные лимиты достаточно жёсткие (`MAX_CONTEXT_SIZE=2000`, summary cap).
- Graph-memory из главы 8 отдельно и в runtime выключен.

### Глава 3 (диагностика)

Статус: **Частично соответствует**

Что реализовано:
- `diagnostics-v1` контракт (interaction_mode, nervous_system_state, request_function, core_theme):
  - `bot_psychologist/bot_agent/diagnostics_classifier.py`

Ограничения:
- Диагностика сейчас эвристическая (regex+state), глубина ниже описанной в NEO методологии.

### Глава 4/маршрутизация (детерминизм)

Статус: **Скорее соответствует**

Что реализовано:
- Детерминированный route resolver с rule_id и forbid:
  - `bot_psychologist/bot_agent/route_resolver.py`
- Runtime подтверждает флаг `USE_DETERMINISTIC_ROUTE_RESOLVER=true`.

### Глава 6 (процедурные сценарии)

Статус: **Частично соответствует**

Что реализовано:
- first-turn policy, mixed query bridge, correction protocol:
  - `bot_psychologist/bot_agent/onboarding_flow.py:124-162`

Ограничения:
- runtime-политика first-turn richness сейчас выключена на уровне diagnostics effective (`first_turn_richness_policy_enabled=false`).

### Глава 7 (output layer: anti-bland, HTML/emoji-протокол)

Статус: **Слабо соответствует**

Причины:
- В NEO описан жёсткий Telegram HTML + emoji функциональный слой.
- Текущая web-реализация ориентирована на web-safe rich text/markdown-путь, без NEO-уровня emoji-протокола и anti-bland-гейта в полном объёме.
- Validator отключён в runtime.

### Глава 8 (масштабирование: multi-agent + graph memory)

Статус: **Пока не реализовано в active runtime**

Доказательства:
- Multi-agent runtime не обнаружен.
- Knowledge Graph client есть, но выключен флагом:
  - `bot_psychologist/bot_agent/graph_client.py:156-160`
  - admin config: `ENABLE_KNOWLEDGE_GRAPH=false`

## 7) Ответ на главный вопрос (п.1 пользователя)

Насколько «безупречно отлажена» система ответов/маршрутов/правил сейчас?

Кратко: **нет, не безупречно**.

Технически система уже в рабочем зрелом состоянии, но есть минимум 3 фундаментальные зоны риска:
1. Псевдо-стриминг вместо нативного стриминга.
2. Несогласованный SSE-контракт (`answer_fallback` vs `answer`).
3. Политики генерации/форматирования, которые могут ограничивать полноту и глубину ответа.

## 8) Ответ на вопрос соответствия NEO (п.2 пользователя)

Насколько соответствует всем идеям `Neo MindBot.md`?

Кратко: **частично соответствует**.

- Архитектурный каркас (diagnostics + routing + stack) — есть.
- Полная глубина методологии, стилистический output layer NEO и стратегические пункты Chapter 8 — реализованы не полностью или отключены в active runtime.

Оценка соответствия (рабочая, экспертная):
- Архитектурный каркас: ~70%
- Поведенческая/методологическая полнота NEO: ~45-55%
- Итого общий уровень: **~55%**

## 9) Приоритетный план исправлений (если идти к «безупречно»)

P0 (критический, сначала):
1. Привести SSE done-контракт к одному виду (`answer` + fallback совместимость) и синхронизировать тесты/frontend.
2. Перевести `adaptive-stream` на реальный токеновый стрим из LLM (`LLMAnswerer.answer_stream`) вместо post-factum word-split.

P1:
3. Ослабить/сделать управляемым форматтерный char-clip (feature flag + метрики срабатывания).
4. Выровнять `prompt_system_base.md` с NEO-целями long-form (убрать конфликтные директивы «не давай ответ/только вопрос» для соответствующих режимов).

P2:
5. Включить и откалибровать `USE_OUTPUT_VALIDATION` в runtime с безопасным roll-out.
6. Согласовать prompt assets v2 с NEO-глубиной (не только каркас, но и содержательная спецификация).

P3:
7. Планомерно внедрить Chapter 8 элементы (graph-memory / multi-agent decomposition) как отдельную дорожную карту.

---

## Приложение: ключевые ссылки на код

- `bot_psychologist/bot_agent/llm_streaming.py:18-65`
- `bot_psychologist/api/routes.py:803-847`
- `bot_psychologist/tests/test_sse_payload.py:55-73`
- `bot_psychologist/bot_agent/response/response_formatter.py:21-28`
- `bot_psychologist/bot_agent/response/response_formatter.py:127-128`
- `bot_psychologist/bot_agent/prompt_registry_v2.py:14-22`
- `bot_psychologist/bot_agent/prompt_system_base.md:19-46`
- `bot_psychologist/bot_agent/output_validator.py:122-202`
- `bot_psychologist/web_ui/src/components/chat/Message.tsx:38-43`
- `bot_psychologist/web_ui/src/styles/index.css:156-162`
- `bot_psychologist/bot_agent/graph_client.py:156-160`
