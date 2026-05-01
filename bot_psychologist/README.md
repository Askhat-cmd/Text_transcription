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
- Реализована мультиагентная система (PRD-017..025, Эпоха 4):
  - State Analyzer Agent — классификация состояния пользователя
  - Thread Manager Agent — управление нитями диалога
  - Memory Retrieval Agent — контекстное извлечение памяти
  - Writer Agent NEO — генерация ответов бота
  - Validator Agent — контроль качества ответов
  - Orchestrator — координация всех агентов
  - Thread Storage — персистентное хранилище нитей (JSON, стабильный путь от `__file__`)
- Первый живой прогон мультиагентной системы: 5/5 TC passed (2026-04-26)
- `pytest tests/multiagent -q` → 190 passed

### Что планируется

- PRD-026: обновление трейса под мультиагентную архитектуру
- PRD-027: веб-AdminPage с управлением агентами на лету
- PRD-028: Legacy Cleanup — удаление старой каскадной системы (после 2+ недель стабильной работы)

## Мультиагентная система (Эпоха 4)

### Статус: активна, работает параллельно старой системе

Мультиагентная система включается флагом `MULTIAGENT_ENABLED=true` в `.env`.
При `MULTIAGENT_ENABLED=false` бот работает по старой каскадной системе (`answer_adaptive.py`).

### Переходный период

Обе системы существуют одновременно. Это осознанное решение:
- Новая система проходит накопление реального трафика
- Старая — страховочная сеть на случай непредвиденных сценариев
- После 2+ недель стабильной работы и готовности трейса/AdminPage
  будет выполнен PRD-028: Legacy Cleanup — осторожное удаление каскадной системы

### Как работает новая система

Каждое сообщение пользователя проходит через цепочку агентов:

```text
Сообщение пользователя
        ↓
[1] State Analyzer Agent
    → nervous_state (window/hyper/hypo)
    → intent (clarify/vent/explore/contact/solution)
    → openness (open/mixed/defensive/collapsed)
    → ok_position (I+W+/I-W+/I+W-/I-W-)
    → safety_flag (bool)
    → confidence (0.0–1.0)
        ↓
[2] Thread Manager Agent (детерминированный, без LLM)
    → thread_id (UUID нити)
    → phase (stabilize/clarify/explore/integrate)
    → relation_to_thread (continue/branch/new_thread/return_to_old)
    → continuity_score (float)
        ↓
[3] Memory Retrieval Agent
    → memory_bundle (контекст диалога + профиль + semantic_hits)
        ↓
[4] Writer Agent NEO
    → draft ответа
    → response_mode (reflect/validate/explore/regulate/practice/safe_override)
        ↓
[5] Validator Agent
    → is_blocked / block_reason / quality_flags
        ↓
Финальный ответ NEO
```

⚠️ Если `safety_flag=True`, цепочка уходит в защитный режим `safe_override`.

### Ключевые файлы

| Компонент | Файл |
|---|---|
| Оркестратор | `bot_agent/multiagent/orchestrator.py` |
| State Analyzer | `bot_agent/multiagent/agents/state_analyzer.py` |
| Thread Manager | `bot_agent/multiagent/agents/thread_manager.py` |
| Memory Agent | `bot_agent/multiagent/agents/memory_retrieval.py` |
| Writer Agent | `bot_agent/multiagent/agents/writer_agent.py` |
| Validator Agent | `bot_agent/multiagent/agents/validator_agent.py` |
| Thread Storage | `bot_agent/multiagent/thread_storage.py` |
| Контракты | `bot_agent/multiagent/contracts/` |
| Feature flags | `bot_agent/feature_flags.py` |
| Тесты | `tests/multiagent/` |

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

### Мультиагентная система

```bash
# Полный прогон тестов мультиагентной системы
pytest tests/multiagent -q

# Отдельные модули
pytest tests/multiagent/test_state_analyzer.py -q
pytest tests/multiagent/test_thread_manager.py -q
pytest tests/multiagent/test_orchestrator_e2e.py -q
pytest tests/multiagent/test_safety_detection.py -q
pytest tests/multiagent/test_thread_storage_persistence.py -q

# Feature flags
pytest tests/test_feature_flags.py -q
```

## Что дальше

1. Довести PRD-026: богатый мультиагентный трейс в UI.
2. Довести PRD-027: AdminPage для оперативного управления агентами.
3. Подготовить PRD-028: Legacy Cleanup после периода стабилизации.

## Документация

- [Overview](docs/overview.md)
- [Architecture](docs/architecture.md)
- [Architecture: Identity + Conversations](docs/architecture_identity_and_conversations.md)
- [Registration](docs/registration.md)
- [Local Dev Runbook](docs/local_dev_runbook.md)
- [Testing Matrix](docs/testing_matrix.md)
- [Telegram Integration Strategy](docs/telegram_integration_strategy.md)
- [Bot Agent](docs/bot_agent.md)
- [API](docs/api.md)
- [Web UI](docs/web_ui.md)
- [Trace runtime](docs/trace_runtime.md)

### Мультиагентная система
- [Multiagent Architecture](docs/multiagent_architecture.md)
- [Agent Contracts](docs/multiagent_contracts.md)
- [Thread Lifecycle](docs/thread_lifecycle.md)
- [Safety System](docs/safety_system.md)
- [Migration Guide](docs/migration_legacy_to_multiagent.md)

## Ограничения и безопасность

- Telegram transport включается только через env-флаги (`TELEGRAM_ENABLED=true`, mode polling/webhook).
- `/api/v1/auth/telegram/confirm-link` требует `X-Internal-Key` и `X-Request-HMAC`.
- Для внешнего деплоя требуется строгая настройка CORS (без `allow_origins=["*"]`).
