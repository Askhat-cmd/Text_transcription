# TASKLIST-026 — Мультиагентный трейс NEO
## Для агента IDE

**PRD:** PRD-026  
**Репозиторий:** https://github.com/Askhat-cmd/Text_transcription  
**Рабочая директория:** `bot_psychologist/`

---

## ИНСТРУКЦИЯ ДЛЯ АГЕНТА

1. Выполняй задачи **строго по порядку** — каждая следующая зависит от предыдущей
2. После каждой задачи запускай проверочные команды из раздела "Verify"
3. **Не удалять** существующие функции, классы, эндпоинты — только добавлять
4. Все изменения должны проходить через `MULTIAGENT_ENABLED` feature flag
5. Коммитить после каждой успешно закрытой задачи

---

## TASK-B1 | orchestrator.py — тайминги агентов

**Файл:** `bot_psychologist/bot_agent/multiagent/orchestrator.py`  
**Приоритет:** CRITICAL  
**Зависимости:** нет

**Действие:**
1. Добавить `import time` в начало файла
2. Обернуть каждый вызов агента в `time.perf_counter()` (5 замеров: state, thread, memory, writer, validator)
3. Добавить в возвращаемый `debug` dict:
   - `"pipeline_version": "multiagent_v1"`
   - `"total_latency_ms": int`
   - `"timings": { "state_analyzer_ms": int, "thread_manager_ms": int, "memory_retrieval_ms": int, "writer_ms": int, "validator_ms": int }`
4. Полный код метода run() — см. PRD-026 раздел TASK-B1

**Verify:**
```bash
cd bot_psychologist
python -c "
import asyncio
from bot_agent.multiagent.orchestrator import orchestrator
result = asyncio.run(orchestrator.run(query='тест', user_id='debug_user'))
assert 'timings' in result['debug'], 'timings missing'
assert 'pipeline_version' in result['debug'], 'pipeline_version missing'
assert result['debug']['pipeline_version'] == 'multiagent_v1'
assert result['debug']['timings']['writer_ms'] > 0
print('TASK-B1 OK:', result['debug']['timings'])
"
```

**Done when:** скрипт выводит `TASK-B1 OK:` без ошибок

---

## TASK-B2 | models.py — Pydantic-модели

**Файл:** `bot_psychologist/api/models.py`  
**Приоритет:** HIGH  
**Зависимости:** нет (параллельно с B1)

**Действие:**
1. Добавить 7 новых моделей в конец файла (не трогать существующие):
   - `AgentTimings`
   - `StateAnalyzerTrace`
   - `ThreadManagerTrace`
   - `MemoryRetrievalTrace`
   - `WriterTrace`
   - `ValidatorTrace`
   - `MultiAgentPipelineTrace`
   - `MultiAgentTraceResponse`
2. Полные определения моделей — см. PRD-026 раздел TASK-B2

**Verify:**
```bash
cd bot_psychologist
python -c "
from api.models import MultiAgentTraceResponse, MultiAgentPipelineTrace
print('TASK-B2 OK: models imported')
"
```

**Done when:** импорт без ошибок

---

## TASK-B3 | session_store.py + chat_routes.py — сохранение debug

**Файлы:**  
- `bot_psychologist/api/session_store.py`  
- `bot_psychologist/api/chat_routes.py` (или аналогичный файл где вызывается orchestrator)  
**Приоритет:** CRITICAL  
**Зависимости:** TASK-B1

**Действие в session_store.py:**
1. Добавить 3 метода: `save_multiagent_debug`, `get_multiagent_debug`, `get_latest_multiagent_debug`
2. Полный код методов — см. PRD-026 раздел TASK-B3

**Действие в chat_routes.py:**
1. Найти место где вызывается `orchestrator.run()`
2. После получения `result` — сохранять `result["debug"]` в store если `multiagent_enabled=True`
3. Добавить `turn_index` в `debug` перед сохранением (брать из текущего хода сессии)

**Verify:**
```bash
cd bot_psychologist
python -c "
from api.session_store import SessionStore
store = SessionStore()
store.save_multiagent_debug('sess_test', 1, {'multiagent_enabled': True, 'pipeline_version': 'multiagent_v1'})
result = store.get_multiagent_debug('sess_test', 1)
assert result is not None
latest = store.get_latest_multiagent_debug('sess_test')
assert latest is not None
print('TASK-B3 OK')
"
```

**Done when:** скрипт выводит `TASK-B3 OK`

---

## TASK-B4 | debug_routes.py — новый эндпоинт

**Файл:** `bot_psychologist/api/debug_routes.py`  
**Приоритет:** HIGH  
**Зависимости:** TASK-B2, TASK-B3

**Действие:**
1. Добавить импорт новых моделей: `from .models import MultiAgentTraceResponse, ...`
2. Добавить эндпоинт `GET /session/{session_id}/multiagent-trace` в конец файла
3. Полный код эндпоинта — см. PRD-026 раздел TASK-B4

**Verify:**
```bash
# Запустить сервер
cd bot_psychologist && uvicorn api.main:app --port 8001 &

# Проверить что эндпоинт зарегистрирован
curl http://localhost:8001/openapi.json | python -c "
import sys, json
spec = json.load(sys.stdin)
paths = spec['paths']
assert any('multiagent-trace' in p for p in paths), 'endpoint not found'
print('TASK-B4 OK: endpoint registered')
"
```

**Done when:** endpoint присутствует в OpenAPI spec

---

## TASK-F1 | TypeScript-типы

**Файл:** `bot_psychologist/web_ui/src/types/index.ts`  
**Приоритет:** HIGH  
**Зависимости:** TASK-B2 (для сверки)

**Действие:**
1. Добавить 8 TypeScript интерфейсов в конец файла types (не удалять существующие)
2. Полные интерфейсы — см. PRD-026 раздел TASK-F1

**Verify:**
```bash
cd bot_psychologist/web_ui
npx tsc --noEmit
# должно завершиться без ошибок
```

**Done when:** `tsc --noEmit` без ошибок

---

## TASK-F2 | api.service.ts — метод getMultiAgentTrace

**Файл:** `bot_psychologist/web_ui/src/services/api.service.ts`  
**Приоритет:** HIGH  
**Зависимости:** TASK-F1

**Действие:**
1. Добавить импорт `MultiAgentTraceData` из types
2. Добавить метод `getMultiAgentTrace(sessionId, turnIndex?)` в класс apiService
3. Полный код метода — см. PRD-026 раздел TASK-F2

**Verify:**
```bash
cd bot_psychologist/web_ui
npx tsc --noEmit
```

**Done when:** tsc без ошибок, метод присутствует в классе

---

## TASK-F5 | useMultiAgentTrace.ts — хук

**Файл:** `bot_psychologist/web_ui/src/hooks/useMultiAgentTrace.ts`  
**Приоритет:** MEDIUM  
**Зависимости:** TASK-F2

**Действие:**
1. Создать новый файл `useMultiAgentTrace.ts`
2. Реализовать хук согласно коду в PRD-026 раздел TASK-F5
3. Экспортировать через `hooks/index.ts` если он существует

**Verify:**
```bash
cd bot_psychologist/web_ui
npx tsc --noEmit
```

**Done when:** файл создан, tsc без ошибок

---

## TASK-F3 | MultiAgentTraceWidget.tsx — компонент

**Файл:** `bot_psychologist/web_ui/src/components/chat/MultiAgentTraceWidget.tsx`  
**Приоритет:** CRITICAL  
**Зависимости:** TASK-F1, TASK-F5

**Действие:**
1. Создать новый файл `MultiAgentTraceWidget.tsx`
2. Реализовать компонент согласно структуре в PRD-026 раздел TASK-F3:
   - Accordion заголовок с total_latency и статусом
   - 5 секций агентов (collapse по отдельности)
   - Цветовая семантика (red/yellow/blue/green)
   - Timeline-бар латентности (горизонтальные сегменты)
   - Skeleton-лоадер при isLoading
   - Graceful null-guard при `trace=null`
3. Стилизация: Tailwind CSS (как в остальных компонентах проекта)
4. Экспортировать из `components/chat/index.ts` если он существует

**Структура компонента (обязательные секции):**
```
<div className="multiagent-trace-widget">
  <TraceHeader />         // статус + total_latency + toggle
  {isExpanded && (
    <>
      <StateAnalyzerSection />
      <ThreadManagerSection />
      <MemoryRetrievalSection />
      <WriterSection />
      <ValidatorSection />
      <LatencyTimelineBar />
    </>
  )}
</div>
```

**Verify:**
```bash
cd bot_psychologist/web_ui
npx tsc --noEmit
# Проверить рендер в браузере через Storybook или dev-сервер с mock данными
```

**Done when:** компонент рендерится, tsc без ошибок

---

## TASK-F4 | Интеграция в ChatWindow / BotMessage

**Файлы:** определить точный файл, рендерящий bot-сообщения (ChatWindow.tsx или дочерний компонент)  
**Приоритет:** CRITICAL  
**Зависимости:** TASK-F3, TASK-F5

**Действие:**
1. Найти компонент, рендерящий ответ бота (сообщение с `role === 'bot'`)
2. Добавить `useMultiAgentTrace(sessionId, message.id, isDevMode)`
3. Под контентом сообщения добавить `<MultiAgentTraceWidget>` с guard `{maTrace && <MultiAgentTraceWidget ... />}`
4. `isDevMode` = `apiService.hasDevKey()` или аналогичная проверка уже существующего механизма авторизации

**Verify:**
```bash
# 1. Запустить dev-сервер
cd bot_psychologist/web_ui && npm run dev

# 2. Открыть браузер, ввести dev API key в настройках
# 3. Отправить сообщение боту
# 4. Убедиться что под ответом NEO появился виджет с заголовком "Pipeline NEO"
# 5. Кликнуть заголовок — должны развернуться 5 секций
# 6. Проверить Timeline-бар
```

**Done when:** виджет виден в браузере под ответом бота

---

## ИТОГОВАЯ ПРОВЕРКА (после всех задач)

```bash
# Backend integration test
cd bot_psychologist
pytest tests/test_multiagent_trace.py -v

# Frontend type check
cd web_ui && npx tsc --noEmit

# Frontend unit tests
cd web_ui && npm run test

# E2E smoke:
# 1. Отправить сообщение через UI
# 2. curl GET /api/debug/session/{id}/multiagent-trace с dev key
# 3. Сравнить данные в curl-ответе с тем что отображает виджет — должно совпадать
```

---

## ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ (полный список)

| Файл | Действие |
|---|---|
| `bot_agent/multiagent/orchestrator.py` | MODIFY — тайминги |
| `api/models.py` | MODIFY — добавить 8 моделей |
| `api/session_store.py` | MODIFY — добавить 3 метода |
| `api/chat_routes.py` | MODIFY — сохранять debug |
| `api/debug_routes.py` | MODIFY — новый эндпоинт |
| `web_ui/src/types/index.ts` | MODIFY — добавить 8 интерфейсов |
| `web_ui/src/services/api.service.ts` | MODIFY — добавить метод |
| `web_ui/src/hooks/useMultiAgentTrace.ts` | CREATE |
| `web_ui/src/components/chat/MultiAgentTraceWidget.tsx` | CREATE |
| `web_ui/src/components/chat/index.ts` | MODIFY — добавить экспорт |
| `tests/test_multiagent_trace.py` | CREATE — тесты |

---

*TASKLIST-026 v1.0 | NEO Bot | PRD-026*
