# Обзор проекта

## Что это

`Bot Psychologist` — это runtime-система Neo MindBot для рефлексивного диалога с пользователем.
Система объединяет retrieval, LLM-генерацию, контекст памяти и наблюдаемость через trace.

## Для кого

- Для разработчиков, которые поддерживают и развивают runtime.
- Для владельца продукта, который проверяет качество ответов и прозрачность поведения бота.
- Для Dev/QA-проверок перед релизом (через Web UI и API).

## Текущий статус

- Основной runtime: `adaptive`.
- `answer_adaptive.py` переведен в фасад-оркестратор, логика вынесена в `adaptive_runtime/`.
- Модуляризация завершена: 144 волны.
- Актуальная тестовая база после завершения: `501 passed, 13 skipped`.
- Trace contract: `v2`.

## Технологический стек

- Backend: Python, FastAPI, Pydantic.
- Frontend: Web UI на React/Vite.
- AI-слой: LLM + retrieval + rerank.
- Память: session/memory слой в runtime и storage-компоненты.
- Наблюдаемость: debug endpoints + inline trace в Web UI.

## Как работает поток запроса

1. Пользователь отправляет сообщение из Web UI.
2. API принимает запрос и передает его в adaptive runtime.
3. Runtime определяет route/state, собирает контекст и выполняет retrieval/rerank.
4. Формируется prompt stack и вызывается LLM.
5. Ответ проходит валидацию, сохраняется в память, формируется trace.
6. Web UI отображает ответ и диагностические данные (для dev-режима).

## Основные точки входа

- Backend: `api/main.py`
- Основные chat-роуты: `api/routes.py`
- Debug-роуты: `api/debug_routes.py`
- Runtime-оркестратор: `bot_agent/answer_adaptive.py`
- Runtime-модули: `bot_agent/adaptive_runtime/*`

## Ключевые документы

- [Архитектура](./architecture.md)
- [Bot Agent](./bot_agent.md)
- [API](./api.md)
- [Web UI](./web_ui.md)
- [Тестирование](./testing.md)
- [Roadmap](./roadmap.md)
