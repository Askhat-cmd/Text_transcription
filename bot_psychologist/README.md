# Bot Psychologist

Bot Psychologist — активный runtime проекта Neo MindBot для веб-чата, retrieval-пайплайна и наблюдаемости через trace/debug интерфейсы.

## Текущее состояние архитектуры

### Что уже реализовано

- Реализован стабильный `user_id` через Identity Layer (PRD-013).
- `session_id` используется как уровень устройства/клиента, а не как идентификатор человека.
- `conversation_id` выделен в отдельный UUID диалога и не равен `session_id` (PRD-014).
- Модуль `answer_adaptive.py` завершил модуляризацию (waves 1-144) и работает как фасад-оркестратор.
- Реализован PRD-015A + PRD-015B-v2: Telegram adapter + transport (`mock/polling/webhook`) с graceful shutdown.
- Реализован PRD-016-v2: registration/access control (`/auth/register`, `/auth/login`, session token, `/link`).
- `api/auth.py` переведен на DB-backed API keys (без in-memory хардкода ключей).

### Что планируется

- PRD-017: multi-agent orchestration.

## Иерархия идентификаторов

| Уровень | Поле | Назначение |
|---|---|---|
| Человек | `user_id` | Стабильный внутренний UUID пользователя |
| Канал | `linked_identity` | Привязка канала: `web` / `telegram` / `api` |
| Сессия | `session_id` | Текущее устройство / браузер / клиент |
| Диалог | `conversation_id` | Отдельный чат внутри пользовательского контекста |

## Ключевые backend-модули

- `api/identity/` — разрешение идентичности и нормализация канала.
- `api/conversations/` — управление жизненным циклом диалога.
- `api/routes/` — HTTP API-слой.
- `api/dependencies.py` — сборка request context (identity + conversation + runtime deps).
- `Bot_data_base/` — внешний сервис данных/памяти.
- `api/telegram_adapter/` — transport-слой Telegram (`mock/polling/webhook`) и обработка `/link`.
- `api/registration/` — регистрация, логин, invite keys, link-code, confirm-link, bootstrap.

## Локальный запуск

Минимальный dev-flow:

1. Поднять backend `bot_psychologist` (`:8001`).
2. Поднять `Bot_data_base` (`:8003`).
3. При необходимости поднять `web_ui` (`:3000`).
4. Учитывать, что `GET /api/v1/health` может вернуть `degraded_fallback`, если сервис базы не запущен.

### Backend

```powershell
cd C:\My_practice\Text_transcription\bot_psychologist
.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

### Bot_data_base

```powershell
cd C:\My_practice\Text_transcription\Bot_data_base
.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --host 0.0.0.0 --port 8003
```

### Web UI

```powershell
cd C:\My_practice\Text_transcription\bot_psychologist\web_ui
npm install
npm run dev
```

## Ключевые API сценарии

- `GET /api/v1/identity/me` — получить текущий identity context.
- `POST /api/v1/conversations/new` — начать новый диалог.
- `GET /api/v1/conversations/` — получить список диалогов пользователя.
- `POST /api/v1/questions/adaptive` — основной adaptive-runtime ответ.
- `POST /api/v1/conversations/{id}/close` — закрыть выбранный диалог.
- `POST /api/v1/dev/telegram/mock-update` — dev-only mock endpoint для проверки Telegram-контракта.
- `POST /api/v1/auth/register` — регистрация по `username + invite_key`.
- `POST /api/v1/auth/login` — вход по `username + access_key` и выдача `session_token`.
- `POST /api/v1/auth/telegram/link-code` — получить одноразовый код привязки Telegram (Bearer session token).
- `POST /api/v1/auth/telegram/confirm-link` — internal endpoint подтверждения привязки.
- `POST /api/v1/admin/invite-keys` — создание invite key (только `role=admin`, Bearer session token).

## Тестирование

Подтвержденные команды:

```bash
pytest tests/identity tests/conversations tests/api -q
pytest tests/api -q
pytest tests/telegram_adapter/test_models.py tests/telegram_adapter/test_adapter.py tests/telegram_adapter/test_service.py tests/api/test_telegram_mock_routes.py -q
pytest tests/registration tests/telegram_adapter/test_outbound.py tests/telegram_adapter/test_transport.py tests/telegram_adapter/test_webhook.py tests/telegram_adapter/test_link_command.py tests/api/test_auth_routes.py -q
```

## Что дальше

1. Довести production-runbook для Telegram webhook (reverse proxy + TLS + secret rotation).
2. Добавить recovery-flow для утерянного `access_key`.
3. Далее — мультиагентная оркестрация.

## Документация

- [Overview](docs/overview.md)
- [Architecture](docs/architecture.md)
- [Architecture: Identity + Conversations](docs/architecture_identity_and_conversations.md)
- [Local Dev Runbook](docs/local_dev_runbook.md)
- [Testing Matrix](docs/testing_matrix.md)
- [Telegram Integration Strategy](docs/telegram_integration_strategy.md)
- [Bot Agent](docs/bot_agent.md)
- [API](docs/api.md)
- [Web UI](docs/web_ui.md)
- [Trace runtime](docs/trace_runtime.md)

## Ограничения и безопасность

- Telegram transport включается только через env-флаги (`TELEGRAM_ENABLED=true`, mode polling/webhook).
- `/api/v1/auth/telegram/confirm-link` требует `X-Internal-Key` и `X-Request-HMAC`.
- Для внешнего деплоя требуется строгая настройка CORS (без `allow_origins=["*"]`).
