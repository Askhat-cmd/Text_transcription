# Local Dev Runbook

## Цель

Быстрый и воспроизводимый локальный запуск всех основных сервисов после миграции проекта.

## Предпосылки

- Репозиторий: `C:\My_practice\Text_transcription`
- `bot_psychologist` venv (Python 3.12)
- `Bot_data_base` venv (Python 3.10)

## Шаг 1. Запуск bot_psychologist API

```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

Проверка:
- `http://localhost:8001/api/v1/health`

## Шаг 2. Запуск Bot_data_base API

```powershell
cd C:\My_practice\Text_transcription\Bot_data_base
.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --host 0.0.0.0 --port 8003
```

Проверка:
- `http://localhost:8003/`
- `http://localhost:8003/api/registry/`

## Шаг 3. Запуск Web UI (опционально)

```powershell
cd C:\My_practice\Text_transcription\bot_psychologist\web_ui
npm install
npm run dev
```

Проверка:
- `http://localhost:3000`

## Как трактовать `health=degraded_fallback`

Если backend `bot_psychologist` работает, но `Bot_data_base` не поднят/недоступен,
`GET /api/v1/health` может вернуть:
- `status: degraded_fallback`
- `bot_data_base_api: unavailable`

Это штатный fallback-режим, а не полная недоступность сервиса.

## Smoke-проверки после старта

1. `GET /api/v1/health` -> `200`
2. `GET /api/admin/runtime/effective` (c `X-API-Key`) -> `active_runtime=multiagent`
3. `GET /api/v1/identity/me` (с `X-API-Key` и identity headers) -> `200`
4. `POST /api/v1/conversations/new` -> `200`
5. `POST /api/v1/questions/adaptive` -> `200` и непустой `answer`
6. `POST /api/v1/conversations/{id}/close` -> `200`

## Runtime flags (PRD-040)

- `MULTIAGENT_ENABLED` и `LEGACY_PIPELINE_ENABLED` считаются deprecated compatibility flags.
- Даже при `LEGACY_PIPELINE_ENABLED=true` active runtime остается `multiagent`.
- Источник истины для runtime: `/api/admin/runtime/effective`.

## Реализовано vs планируется

### Реализовано
- Локальный запуск backend + data service + web-ui.
- Fallback-поведение при недоступности data service.

### Планируется
- Автоматизация smoke-run (скрипт единого старта и проверки).
