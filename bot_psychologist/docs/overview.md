# Обзор проекта

## Что это

`Bot Psychologist` — runtime-система Neo MindBot для рефлексивного диалога с пользователем.
Система использует multiagent pipeline, retrieval, memory и debug trace observability.

## Текущий статус

- Active runtime: `multiagent_adapter`.
- Pipeline version: `multiagent_v1`.
- Legacy cascade physically removed in PRD-041.
- Post-purge stabilization completed in PRD-042.
- `answer_adaptive.py` сохранен только как compatibility shim.
- Telegram adapter присутствует как future integration layer (не active production channel).

## Для кого

- Для разработчиков, поддерживающих runtime и API.
- Для QA/Dev-проверок через Web UI и debug endpoints.
- Для операционного контроля через admin runtime contract.

## Как работает поток запроса

1. Web UI/API отправляет запрос в FastAPI (`api/main.py`).
2. Chat routes вызывают `multiagent_adapter` runtime.
3. Multiagent orchestrator выполняет state/thread/memory/writer/validator stages.
4. Формируется ответ и debug trace.
5. Ответ и trace доступны в Web UI и debug endpoints.

## Основные точки входа

- Backend: `api/main.py`
- Chat routes: `api/routes/chat.py`
- Debug routes: `api/debug_routes.py`
- Runtime adapter: `bot_agent/multiagent/runtime_adapter.py`
- Compatibility shim: `bot_agent/answer_adaptive.py`

## Ключевые документы

- [Architecture](./architecture.md)
- [Multiagent Architecture](./multiagent_architecture.md)
- [API](./api.md)
- [Web UI](./web_ui.md)
- [Trace Runtime](./trace_runtime.md)
- [Testing Matrix](./testing_matrix.md)
- [Documentation Index](./README.md)
