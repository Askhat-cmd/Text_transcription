# Trace Runtime Guide (Neo)

## Назначение
Трейс в Web UI нужен для быстрой диагностики каждого ответа бота в рантайме:
- какой режим/маршрут был выбран;
- какие чанки и память реально попали в ответ;
- какие LLM-вызовы ушли по API;
- сколько токенов и стоимости получено за ход и за сессию;
- где возникли аномалии/ошибки.

Цель: дать разработчику прозрачность `request -> routing -> retrieval -> llm -> response` без чтения сырых логов.

## Где это в коде
- Backend trace API: `api/debug_routes.py`
- Формирование runtime trace: `bot_agent/answer_adaptive.py`
- Memory trace context: `bot_agent/conversation_memory.py`, `bot_agent/memory_v11.py`
- Inline trace UI (в сообщении): `web_ui/src/components/chat/InlineDebugTrace.tsx`
- Статус-полоса (8 чипов): `web_ui/src/components/debug/StatusBar.tsx`
- Полотно LLM: `web_ui/src/components/debug/LLMPayloadPanel.tsx`
- Session panel (агрегации по чату): `web_ui/src/components/debug/SessionTracePanel.tsx`
- Загрузка сессионных метрик: `web_ui/src/hooks/useSessionTrace.ts`

## Условия доступа
Debug endpoints защищены dev-ключом.

Требования:
- заголовок `X-API-Key: dev-key-001`;
- при обычных ключах debug-эндпоинты возвращают `403 Debug access denied`.

## Основные debug API
Базовый префикс: `/api/debug`

1. `GET /api/debug/session/{session_id}/metrics`
- агрегаты по сессии: tokens, cost, fast-path %, avg/max LLM time, anomaly turns.

2. `GET /api/debug/session/{session_id}/traces?format=full|compact`
- список trace по ходам.
- `compact` убирает тяжёлые поля для быстрого просмотра/экспорта.

3. `GET /api/debug/session/{session_id}/llm-payload?format=structured|flat`
- последнее полотно LLM по сессии.
- `flat` удобен для UI-панели и копирования.

4. `GET /api/debug/blob/{blob_id}`
- получение сохранённого blob-контента (с sanitization PII).

## Что показывает UI-трейс

### 1) Status Bar (8 чипов)
Показывается в верхней строке trace-блока:
- `MODE` — выбранный runtime mode.
- `STATE` — классифицированное пользовательское состояние.
- `RULE` — decision rule id, сработавшее правило маршрутизации.
- `CHUNKS` — сколько чанков прошло в ответ / какой cap.
- `HITS` — число semantic hits памяти.
- `TOKENS` — токены текущего хода.
- `LLM` — длительность LLM стадии.
- `WARN` — количество non-info аномалий.

### 2) Роутинг и классификация
Нужно для валидации правильности выбора ветки:
- mode/rule/state/confidence;
- fast-path и причина (если активен);
- block cap и related ограничения.

### 3) Pipeline Timeline
Нужно для диагностики производительности:
- длительность стадий (classifier/retrieval/rerank/llm/format/validation);
- визуальный вклад каждой стадии.

### 4) Чанки и retrieval
Нужно для качества ответа:
- сколько получено, сколько прошло фильтр;
- какие блоки вошли в ответ;
- какие блоки отсечены и по какой причине.

### 5) LLM Calls
Нужно для быстрой проверки одного хода:
- модель, токены, время;
- system/user prompt preview;
- response preview.

### 6) Контекст памяти
Нужно для контроля continuity:
- turns/summary/semantic hits;
- содержимое turns;
- summary text;
- что именно записано в память после хода.

### 7) Модели, токены и стоимость
Нужно для операционного контроля:
- модель(и) текущего хода;
- prompt/completion/total tokens;
- стоимость хода.

### 8) Anomalies
Нужно для контроля качества рантайма:
- предупреждения и ошибки;
- тяжесть (`info/warn/error`);
- контекст проблемного узла.

### 9) Полотно LLM
Нужно для глубокой отладки payload в API:
- `hybrid_query`;
- полный набор `llm_calls` (каждый section сворачиваемый);
- memory snapshot;
- кнопки copy по секциям/целиком.

## Session Trace Panel (агрегация по чату)
Показывает уже не один ход, а всю текущую сессию:
- Session Totals (prompt/completion/total, cost, turns);
- Session Dashboard (fast path %, avg/max LLM, anomalies);
- Trace History;
- Config Snapshot + diff к предыдущему ходу.

Используется для анализа трендов по чату, а не точечной диагностики хода.

## Рекомендуемый рабочий сценарий дебага
1. Открой trace у проблемного ответа.
2. Проверь `Status Bar` (mode/state/rule/warn).
3. Проверь `Pipeline Timeline` (узкое место по времени).
4. Проверь `Chunks and retrieval` (релевантность/отсечения).
5. Проверь `Контекст памяти` (не потерялся ли контекст).
6. Открой `Полотно LLM` и сравни ожидаемый vs фактический prompt/payload.
7. Сверь Session Totals в `Session Trace Panel` для оценки накопительного расхода.

## Частые проблемы и как читать
1. `Полотно LLM: Failed to fetch`
- чаще всего не dev-key или stale session id.
- проверить `X-API-Key` и актуальность `session_id`.

2. В ответе «обрезка» или неожиданная краткость
- смотреть `tokens_completion`, `output validator`, `anomalies` и `response preview` в LLM calls.

3. Неверная ветка режима
- смотреть `rule`, `confidence`, `state` + memory context и signals.

4. Высокая стоимость
- сначала Session Totals, затем разрез по ходам в Trace History и LLM duration/tokens.

## Правила развития трейса
- Любая новая trace-секция должна быть:
  - операционно полезной;
  - недублирующей существующие секции;
  - сворачиваемой (`details/summary`);
  - покрытой минимум одним контрактным тестом UI или API.
- Не добавлять SD legacy-поля в trace контракт.
- Для тяжёлых полей хранить compact/full варианты.

## Минимальные проверки при изменениях
- `tests/ui/test_trace_ia_refactor_contract.py`
- `tests/test_debug_metrics_and_export.py`
- `tests/test_llm_payload_endpoint.py`
- smoke в UI: открыть чат, отправить сообщение, проверить загрузку `Полотно LLM` и `Session Trace Panel`.