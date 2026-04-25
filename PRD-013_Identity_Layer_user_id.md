# PRD-013 — Identity Layer: Стабильная привязка к `user_id`

**Проект:** Bot Psychologist  
**Документ:** PRD-013  
**Версия:** 1.0  
**Дата:** 2026-04-25  
**Статус:** READY FOR IMPLEMENTATION  
**Автор:** Архитектурный анализ на основе кодовой базы v0.6.x  
**Следует за:** PRD-012 (Neo Trace Contract v2 & SD Legacy Purge)

---

## 1. Контекст и мотивация

### 1.1 Текущее состояние

Анализ кодовой базы (`api/auth.py`, `api/session_store.py`, `api/models.py`) показывает следующую картину:

- `user_id` в `AskQuestionRequest` имеет дефолт `"default"` — это означает, что в отсутствие явной передачи все запросы оседают в одну "кучу"
- `SessionStore` оперирует только `session_id` (строки в словаре), без привязки к канону пользователя
- `auth.py` управляет **API-ключами**, но не идентичностью пользователей — это два разных слоя, которые сейчас не связаны
- В `models.py` уже есть `ChatSessionInfoResponse` с полями `user_id` и `session_id`, что говорит о том, что семантика этих сущностей заложена, но не реализована как отдельный слой
- `telegram_adapter` существует как заглушка в `C:\My_practice\Text_transcription\telegram_adapter` — подключение TG потребует стабильного `user_id`

### 1.2 Ключевая проблема

Текущий `user_id` — это **device-scoped identifier**: при заходе с нового браузера или устройства пользователь получает новый id, теряя всю персональную память, историю и профиль. При добавлении Telegram-канала без предварительной стабилизации identity layer возникнет дублирование профилей.

### 1.3 Почему нельзя откладывать

Каждый новый агент (retrieval-agent, memory-writer, summary-agent), который будет добавлен в мультиагентную систему, принимает `user_id` как первичный ключ для фильтрации памяти. Если этот ключ нестабилен — агенты будут работать с неправильным контекстом. Переделывать memory-слой после построения агентов значительно дороже, чем заложить правильный identity layer сейчас.

---

## 2. Цели PRD

| # | Цель | Измеримый результат |
|---|---|---|
| G-1 | Ввести стабильный внутренний `user_id` (UUID) | Все сущности базы данных имеют FK на `users.id` |
| G-2 | Понизить browser-generated id до `session_id` | `SessionStore` работает как session/device layer, не как identity |
| G-3 | Создать `linked_identities` для будущего TG | Таблица готова к приёму `telegram_user_id` без изменения схемы |
| G-4 | Централизовать разрешение идентификаторов в `IdentityService` | Все агенты и роуты получают `user_id` только через `IdentityService` |
| G-5 | Сохранить 100% обратной совместимости API | Существующие клиенты (web UI) не ломаются |

---

## 3. Не в скоупе этого PRD

- Telegram-адаптер (реализация) — это следующий PRD
- Account linking UI (код привязки аккаунта в веб-чате) — следующий PRD  
- Мультиагентная система — строится поверх этого PRD
- Аутентификация пользователей (OAuth, JWT) — отдельный PRD
- Шифрование данных в покое — отдельный PRD

---

## 4. Архитектура Identity Layer

### 4.1 Четырёхуровневая иерархия идентификаторов

```
┌─────────────────────────────────────────────────────────┐
│  УРОВЕНЬ 1: ЧЕЛОВЕК                                      │
│  users.id  (UUID, stable, internal)                     │
│  "Это конкретная личность в системе"                    │
├─────────────────────────────────────────────────────────┤
│  УРОВЕНЬ 2: КАНАЛ                                        │
│  linked_identities (provider, external_id)              │
│  "Откуда пользователь подключается: web, telegram, ..."  │
├─────────────────────────────────────────────────────────┤
│  УРОВЕНЬ 3: СЕССИЯ                                       │
│  sessions (session_id, device_fingerprint)              │
│  "Конкретный браузер/вкладка/устройство прямо сейчас"  │
├─────────────────────────────────────────────────────────┤
│  УРОВЕНЬ 4: ДИАЛОГ                                       │
│  conversations (conversation_id)                        │
│  "Отдельный чат или тред внутри сессии"                 │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Контракт входящего запроса для всех агентов

Каждый агент и каждый роут обязан работать через следующий объект контекста:

```python
@dataclass
class IdentityContext:
    user_id: str          # UUID — стабильный, из таблицы users
    session_id: str       # Текущая сессия/браузер
    conversation_id: str  # Текущий чат
    channel: str          # "web" | "telegram" | "api"
    is_anonymous: bool    # True если user не идентифицирован (гость)
```

Этот контракт является входным параметром для:
- `AgentOrchestrator`
- `MemoryService`
- `RetrievalService`
- `ConversationService`

---

## 5. Схема базы данных

### 5.1 Новые таблицы

#### `users`
```sql
CREATE TABLE users (
    id              TEXT PRIMARY KEY,          -- UUID, генерируется сервером
    created_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active', 'suspended', 'deleted')),
    canonical_name  TEXT,                      -- Опциональный display name
    timezone        TEXT DEFAULT 'UTC',
    language        TEXT DEFAULT 'ru',
    metadata_json   TEXT DEFAULT '{}'          -- JSONB-style, расширяемо
);

CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_created_at ON users(created_at);
```

#### `linked_identities`
```sql
CREATE TABLE linked_identities (
    id              TEXT PRIMARY KEY,          -- UUID
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider        TEXT NOT NULL,             -- 'web', 'telegram', 'email'
    external_id     TEXT NOT NULL,             -- ID во внешней системе
    verified_at     DATETIME,
    created_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    metadata_json   TEXT DEFAULT '{}',

    UNIQUE(provider, external_id)              -- один external_id на провайдер
);

CREATE INDEX idx_linked_identities_user_id ON linked_identities(user_id);
CREATE INDEX idx_linked_identities_provider ON linked_identities(provider, external_id);
```

#### `sessions`
```sql
CREATE TABLE sessions (
    id                  TEXT PRIMARY KEY,      -- UUID
    user_id             TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel             TEXT NOT NULL DEFAULT 'web',
    device_fingerprint  TEXT,                  -- Browser fingerprint или device token
    created_at          DATETIME NOT NULL DEFAULT (datetime('now')),
    last_seen_at        DATETIME NOT NULL DEFAULT (datetime('now')),
    expires_at          DATETIME,
    metadata_json       TEXT DEFAULT '{}'
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_last_seen_at ON sessions(last_seen_at);
```

### 5.2 Модификации существующих таблиц

Следующие существующие таблицы получают FK на `users.id`:

```sql
-- conversations: добавить user_id FK
ALTER TABLE conversations ADD COLUMN user_id TEXT REFERENCES users(id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);

-- messages: уже должны быть привязаны через conversation_id,
-- но добавить прямой user_id для быстрой фильтрации
ALTER TABLE messages ADD COLUMN user_id TEXT REFERENCES users(id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
```

---

## 6. Новый модуль: `IdentityService`

### 6.1 Расположение в проекте

```
bot_psychologist/
├── api/
│   ├── identity/
│   │   ├── __init__.py
│   │   ├── service.py       ← IdentityService (главный класс)
│   │   ├── models.py        ← Pydantic-модели: IdentityContext, UserRecord, etc.
│   │   ├── repository.py    ← Слой работы с БД (CRUD)
│   │   └── middleware.py    ← FastAPI middleware для автоматического разрешения
```

### 6.2 Интерфейс `IdentityService`

```python
class IdentityService:
    """
    Единая точка разрешения идентификаторов пользователей.
    Все агенты и роуты работают через этот сервис.
    Никто не обращается к таблицам users/sessions/linked_identities напрямую.
    """

    async def resolve_or_create(
        self,
        *,
        provider: str,          # 'web' | 'telegram' | 'api'
        external_id: str,       # Browser fingerprint, telegram user id, etc.
        session_id: Optional[str] = None,
        channel: str = 'web',
        metadata: dict = None,
    ) -> IdentityContext:
        """
        Основной метод.
        1. Ищет linked_identities по (provider, external_id)
        2. Если найдено → возвращает привязанный user_id
        3. Если НЕ найдено → создаёт нового пользователя + linked_identity
        4. Создаёт или обновляет session
        Возвращает полный IdentityContext.
        """

    async def get_by_user_id(self, user_id: str) -> Optional[UserRecord]:
        """Получить пользователя по стабильному UUID."""

    async def link_identity(
        self,
        user_id: str,
        provider: str,
        external_id: str,
        verified: bool = False,
    ) -> LinkedIdentity:
        """
        Привязать новый канал к существующему пользователю.
        Используется при account linking (например, привязка Telegram к web-аккаунту).
        """

    async def get_linked_identities(self, user_id: str) -> List[LinkedIdentity]:
        """Получить все привязки пользователя."""

    async def refresh_session(self, session_id: str) -> Session:
        """Обновить last_seen_at сессии."""

    async def get_identity_context_from_session(
        self, session_id: str
    ) -> Optional[IdentityContext]:
        """Восстановить IdentityContext по session_id (для повторных запросов)."""
```

### 6.3 FastAPI Dependency

```python
# api/identity/middleware.py

async def get_identity_context(
    request: Request,
    x_session_id: Optional[str] = Header(None),
    x_device_fingerprint: Optional[str] = Header(None),
    identity_service: IdentityService = Depends(get_identity_service),
) -> IdentityContext:
    """
    FastAPI dependency — автоматически разрешает IdentityContext для каждого запроса.
    Используется через: identity: IdentityContext = Depends(get_identity_context)
    """
    fingerprint = x_device_fingerprint or _generate_fingerprint(request)
    return await identity_service.resolve_or_create(
        provider="web",
        external_id=fingerprint,
        session_id=x_session_id,
        channel="web",
    )
```

---

## 7. Миграция существующего кода

### 7.1 `api/models.py` — обновление `AskQuestionRequest`

```python
# БЫЛО:
class AskQuestionRequest(BaseModel):
    user_id: str = Field(default="default", ...)

# СТАЛО:
class AskQuestionRequest(BaseModel):
    # user_id больше НЕ приходит от клиента как строка.
    # Он разрешается через IdentityContext на уровне dependency.
    # Поле остаётся для обратной совместимости, но маркируется deprecated.
    user_id: Optional[str] = Field(
        default=None,
        description="[DEPRECATED] Используйте заголовки X-Session-Id и X-Device-Fingerprint",
    )
    session_id: Optional[str] = Field(default=None, ...)
```

**Стратегия обратной совместимости:** Если клиент передаёт старый `user_id` строкой, роут проверяет, существует ли такой пользователь в `linked_identities` с `provider='legacy'`. Если нет — создаёт запись. Это позволяет существующему web UI работать без изменений на время переходного периода.

### 7.2 `api/session_store.py` — понижение до device layer

`SessionStore` остаётся, но теперь его `session_id` является ключом `sessions.device_fingerprint`, а не идентификатором пользователя. Данные трейсов в `SessionStore` продолжают быть привязаны к `session_id`, но через `IdentityService` всегда можно получить `user_id` по `session_id`.

### 7.3 `api/auth.py` — разделение слоёв

`APIKeyManager` остаётся без изменений. Добавляется логика: `api_key` → `user_id` маппинг для dev/test ключей, чтобы `dev-key-001` всегда резолвился в фиксированный `user_id = "dev-user-00000000-0000-0000-0000-000000000001"`.

---

## 8. Список задач (Task List)

### ФАЗА 1 — Схема БД и базовый сервис

---

#### TASK-013-01: Создать SQL-миграцию для identity tables

**Описание:** Создать файл миграции, добавляющий таблицы `users`, `linked_identities`, `sessions` и FK в `conversations`, `messages`.

**Файл:** `bot_psychologist/scripts/migrations/013_identity_layer.sql`

**Критерии приёмки:**
- [ ] Файл миграции создан и идемпотентен (`IF NOT EXISTS`)
- [ ] Таблицы `users`, `linked_identities`, `sessions` созданы
- [ ] Все индексы добавлены
- [ ] FK добавлены в `conversations.user_id` и `messages.user_id`
- [ ] Миграция проходит на пустой и на существующей БД без ошибок
- [ ] Откат миграции описан в комментарии

**Тест:** `tests/identity/test_migration_013.py::test_migration_idempotent`

---

#### TASK-013-02: Создать Pydantic-модели для Identity Layer

**Описание:** Создать `api/identity/models.py` с моделями `IdentityContext`, `UserRecord`, `LinkedIdentity`, `Session`.

**Файл:** `bot_psychologist/api/identity/models.py`

```python
# Минимальный контракт моделей:

class IdentityContext(BaseModel):
    user_id: str
    session_id: str
    conversation_id: Optional[str]
    channel: Literal["web", "telegram", "api"]
    is_anonymous: bool = False
    created_new_user: bool = False  # Флаг для логирования

class UserRecord(BaseModel):
    id: str
    created_at: datetime
    status: Literal["active", "suspended", "deleted"]
    canonical_name: Optional[str]
    timezone: str
    language: str

class LinkedIdentity(BaseModel):
    id: str
    user_id: str
    provider: str
    external_id: str
    verified_at: Optional[datetime]
    created_at: datetime

class Session(BaseModel):
    id: str
    user_id: str
    channel: str
    device_fingerprint: Optional[str]
    created_at: datetime
    last_seen_at: datetime
    expires_at: Optional[datetime]
```

**Критерии приёмки:**
- [ ] Все модели имеют строгую валидацию через Pydantic v2
- [ ] `IdentityContext` сериализуется в JSON без потерь
- [ ] Добавлены `model_config` с примерами для OpenAPI-документации

**Тест:** `tests/identity/test_identity_models.py`

---

#### TASK-013-03: Реализовать `IdentityRepository`

**Описание:** Создать `api/identity/repository.py` — слой работы с БД. Никакой бизнес-логики, только CRUD.

**Файл:** `bot_psychologist/api/identity/repository.py`

**Методы:**
```python
class IdentityRepository:
    async def create_user(self, user_id: str, ...) -> UserRecord
    async def get_user_by_id(self, user_id: str) -> Optional[UserRecord]
    async def find_by_linked_identity(self, provider: str, external_id: str) -> Optional[UserRecord]
    async def create_linked_identity(self, ...) -> LinkedIdentity
    async def get_linked_identities(self, user_id: str) -> List[LinkedIdentity]
    async def create_session(self, ...) -> Session
    async def update_session_last_seen(self, session_id: str) -> None
    async def get_session(self, session_id: str) -> Optional[Session]
```

**Критерии приёмки:**
- [ ] Все методы используют параметризованные SQL-запросы (no f-strings with user data)
- [ ] Транзакции используются там, где нужны атомарные операции
- [ ] Все методы покрыты unit-тестами с in-memory SQLite
- [ ] Логирование ошибок через `logger` из `logging_config.py`

**Тест:** `tests/identity/test_identity_repository.py`

---

#### TASK-013-04: Реализовать `IdentityService`

**Описание:** Реализовать `api/identity/service.py` — бизнес-логика разрешения идентификаторов.

**Файл:** `bot_psychologist/api/identity/service.py`

**Ключевая логика `resolve_or_create`:**
```
1. fingerprint → ищем в linked_identities WHERE provider='web' AND external_id=fingerprint
2. ЕСЛИ НАШЛИ:
   a. Обновляем last_seen_at сессии
   b. Возвращаем IdentityContext с существующим user_id
3. ЕСЛИ НЕ НАШЛИ:
   a. Создаём нового пользователя (генерируем UUID)
   b. Создаём linked_identity (provider='web', external_id=fingerprint)
   c. Создаём новую сессию
   d. Возвращаем IdentityContext с created_new_user=True
4. Логируем все события через structured logging
```

**Критерии приёмки:**
- [ ] `resolve_or_create` атомарна (нет race condition при параллельных запросах)
- [ ] При передаче legacy `user_id` строкой — корректная миграция в linked_identities
- [ ] Метод `link_identity` добавляет запись без удаления существующих
- [ ] Сервис инжектируется через FastAPI `Depends()`

**Тест:** `tests/identity/test_identity_service.py`

---

### ФАЗА 2 — Интеграция в API

---

#### TASK-013-05: Создать FastAPI dependency `get_identity_context`

**Описание:** Реализовать `api/identity/middleware.py` с зависимостью для автоматического разрешения идентичности.

**Файл:** `bot_psychologist/api/identity/middleware.py`

**Логика извлечения fingerprint:**
```python
def _generate_fingerprint(request: Request) -> str:
    """
    Генерирует device fingerprint из request.
    Порядок приоритетов:
    1. X-Device-Fingerprint заголовок (явно передан клиентом)
    2. Хэш от (IP + User-Agent) — временный fallback
    """
    ua = request.headers.get("user-agent", "")
    ip = request.client.host if request.client else "unknown"
    raw = f"{ip}:{ua}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
```

**Критерии приёмки:**
- [ ] Dependency работает без заголовков (fallback на IP+UA)
- [ ] Dependency работает с явным `X-Device-Fingerprint`
- [ ] Dependency работает с явным `X-Session-Id`
- [ ] При ошибке БД — логирует и возвращает анонимный контекст (не ломает запрос)
- [ ] Добавлено в `api/dependencies.py` для централизованного экспорта

**Тест:** `tests/identity/test_identity_middleware.py`

---

#### TASK-013-06: Обновить существующие роуты для использования `IdentityContext`

**Описание:** Заменить прямое использование `user_id` из тела запроса на `IdentityContext` из dependency.

**Файлы для обновления:**
- `bot_psychologist/api/routes/` (все роуты чата и истории)
- `bot_psychologist/api/admin_routes.py` (только чтение, не изменение)

**Паттерн миграции роута:**
```python
# БЫЛО:
@router.post("/ask")
async def ask_question(request: AskQuestionRequest):
    user_id = request.user_id or "default"
    ...

# СТАЛО:
@router.post("/ask")
async def ask_question(
    request: AskQuestionRequest,
    identity: IdentityContext = Depends(get_identity_context),
):
    user_id = identity.user_id  # Всегда стабильный UUID
    # request.user_id игнорируется (deprecated fallback обрабатывается в middleware)
    ...
```

**Критерии приёмки:**
- [ ] Все роуты `/ask`, `/history`, `/sessions`, `/feedback` используют `IdentityContext`
- [ ] Роуты `/admin/*` используют `user_id` только для чтения (без изменения identity)
- [ ] `request.user_id = "default"` больше не попадает в базу данных
- [ ] Swagger-документация обновлена с новыми заголовками

**Тест:** `tests/api/test_routes_identity_integration.py`

---

#### TASK-013-07: Legacy-совместимость для `user_id` из body request

**Описание:** Реализовать bridge-логику: если клиент передаёт `user_id` строкой в теле запроса, система должна попытаться найти его в `linked_identities(provider='legacy', external_id=user_id)`. Если не найдено — создать linked_identity для существующего пользователя (разрешённого через fingerprint).

**Цель:** Web UI продолжает работать без изменений на время переходного периода.

**Критерии приёмки:**
- [ ] Запросы со старым `user_id = "user_123"` не теряют историю
- [ ] Дублирования профилей не возникает
- [ ] В логах появляется `WARN: legacy_user_id_used` с fingerprint для диагностики
- [ ] Через 30 дней после деплоя — можно удалить этот bridge (добавить TODO с датой)

**Тест:** `tests/identity/test_legacy_user_id_bridge.py`

---

### ФАЗА 3 — Подготовка к Telegram

---

#### TASK-013-08: Endpoint для account linking (заглушка)

**Описание:** Создать endpoint `POST /api/v1/identity/link-telegram` и `GET /api/v1/identity/generate-link-code`, которые пока возвращают `501 Not Implemented`, но уже документированы в OpenAPI.

**Файл:** `bot_psychologist/api/routes/identity_routes.py`

```python
@router.post("/identity/link-telegram")
async def link_telegram_account(
    body: LinkTelegramRequest,
    identity: IdentityContext = Depends(get_identity_context),
) -> LinkTelegramResponse:
    """
    Привязать Telegram-аккаунт к текущему пользователю через one-time code.
    
    Флоу:
    1. Пользователь в веб-чате запрашивает код → GET /identity/generate-link-code
    2. Пользователь отправляет код Telegram-боту → /start <code>
    3. Telegram-бот POST /identity/link-telegram с кодом и telegram_user_id
    4. Backend привязывает telegram_user_id к user_id
    """
    raise HTTPException(status_code=501, detail="Telegram linking: coming in next PRD")
```

**Критерии приёмки:**
- [ ] Endpoint задокументирован в Swagger с полным описанием флоу
- [ ] `LinkTelegramRequest` и `LinkTelegramResponse` модели добавлены в `models.py`
- [ ] Таблица `link_codes(code, user_id, created_at, expires_at, used_at)` создана в миграции
- [ ] 501 ответ не ломает фронт (фронт скрывает кнопку при 501)

**Тест:** `tests/identity/test_link_telegram_stub.py`

---

#### TASK-013-09: `IdentityService.resolve_telegram` — метод-заглушка

**Описание:** Добавить в `IdentityService` метод `resolve_telegram(telegram_user_id: str)` с реализацией поиска по `linked_identities(provider='telegram', external_id=telegram_user_id)`. Этот метод будет использован при подключении реального Telegram-адаптера.

**Критерии приёмки:**
- [ ] Метод существует и документирован
- [ ] Возвращает `Optional[IdentityContext]` — `None` если пользователь ещё не привязан
- [ ] Покрыт тестом с mock-данными

**Тест:** `tests/identity/test_resolve_telegram.py`

---

### ФАЗА 4 — Наблюдаемость и admin

---

#### TASK-013-10: Добавить identity-события в structured logging

**Описание:** Все события identity layer должны логироваться через `logging_config.py` в структурированном формате.

**События для логирования:**
```python
# Примеры log-записей:
logger.info("identity.user_created", extra={"user_id": uid, "provider": "web"})
logger.info("identity.user_resolved", extra={"user_id": uid, "session_id": sid})
logger.warning("identity.legacy_user_id_used", extra={"legacy_id": lid, "fingerprint": fp})
logger.info("identity.session_refreshed", extra={"session_id": sid, "user_id": uid})
logger.error("identity.resolve_failed", extra={"error": str(e), "fingerprint": fp})
```

**Критерии приёмки:**
- [ ] Все 5 событий логируются
- [ ] Логи не содержат PII (только хэши fingerprint, UUID пользователей)
- [ ] Структура логов совместима с существующим `logging_config.py`

**Тест:** `tests/identity/test_identity_logging.py`

---

#### TASK-013-11: Admin endpoint для просмотра identity-данных пользователя

**Описание:** Добавить в `admin_routes.py` endpoint `GET /admin/users/{user_id}/identity`, возвращающий linked identities и активные сессии.

**Формат ответа:**
```json
{
  "user_id": "uuid",
  "created_at": "...",
  "status": "active",
  "linked_identities": [
    {"provider": "web", "external_id": "sha256:...", "verified_at": null},
    {"provider": "telegram", "external_id": "123456789", "verified_at": "..."}
  ],
  "active_sessions": [
    {"session_id": "uuid", "channel": "web", "last_seen_at": "..."}
  ]
}
```

**Критерии приёмки:**
- [ ] Endpoint доступен только с `dev-key-001` (проверка через `is_dev_key`)
- [ ] `external_id` для web-provider показывается как `sha256:<first_8_chars>...` (не полный fingerprint)
- [ ] Endpoint не раскрывает содержимое диалогов

**Тест:** `tests/api/test_admin_identity_endpoint.py`

---

## 9. Тест-план

### 9.1 Unit-тесты

#### `tests/identity/test_migration_013.py`

```python
def test_migration_idempotent(tmp_db):
    """Миграция проходит дважды без ошибок."""

def test_tables_created(tmp_db):
    """После миграции существуют таблицы users, linked_identities, sessions."""

def test_fk_constraints_active(tmp_db):
    """FK ограничения работают: нельзя создать linked_identity без users.id."""
```

#### `tests/identity/test_identity_models.py`

```python
def test_identity_context_serialization():
    """IdentityContext корректно сериализуется в JSON и десериализуется обратно."""

def test_identity_context_required_fields():
    """IdentityContext не создаётся без user_id и session_id."""

def test_channel_enum_validation():
    """channel принимает только 'web', 'telegram', 'api'."""
```

#### `tests/identity/test_identity_repository.py`

```python
def test_create_and_get_user(tmp_db):
    """Создать пользователя → получить его по id."""

def test_find_by_linked_identity(tmp_db):
    """Найти пользователя по (provider, external_id)."""

def test_find_missing_identity_returns_none(tmp_db):
    """Поиск несуществующего external_id возвращает None."""

def test_create_linked_identity_unique_constraint(tmp_db):
    """Нельзя создать две записи с одинаковым (provider, external_id)."""

def test_session_update_last_seen(tmp_db):
    """update_session_last_seen обновляет поле last_seen_at."""
```

#### `tests/identity/test_identity_service.py`

```python
def test_resolve_creates_new_user_on_first_call(service):
    """Первый вызов resolve_or_create создаёт пользователя."""

def test_resolve_returns_same_user_on_second_call(service):
    """Второй вызов с тем же fingerprint возвращает того же пользователя."""

def test_resolve_created_new_user_flag(service):
    """created_new_user=True только при реальном создании."""

def test_link_identity_adds_second_provider(service):
    """link_identity добавляет telegram к уже существующему пользователю."""

def test_link_identity_does_not_duplicate(service):
    """Повторный вызов link_identity с теми же данными не создаёт дублей."""

def test_resolve_returns_existing_after_link(service):
    """После link_identity resolve по telegram_user_id возвращает того же пользователя."""
```

#### `tests/identity/test_legacy_user_id_bridge.py`

```python
def test_legacy_user_id_is_preserved(service):
    """Запрос с user_id='user_123' находит или создаёт корректный users.id."""

def test_no_duplicate_on_repeated_legacy_calls(service):
    """Повторные запросы с user_id='user_123' не создают новых пользователей."""

def test_legacy_warn_is_logged(service, caplog):
    """При legacy user_id появляется WARN-запись в логах."""
```

### 9.2 Интеграционные тесты

#### `tests/api/test_routes_identity_integration.py`

```python
async def test_ask_without_headers_succeeds(client):
    """POST /ask без identity-заголовков возвращает 200 (анонимный контекст)."""

async def test_ask_with_fingerprint_header_creates_user(client):
    """POST /ask с X-Device-Fingerprint создаёт пользователя в БД."""

async def test_ask_same_fingerprint_uses_same_user(client):
    """Два POST /ask с одинаковым fingerprint используют одного пользователя."""

async def test_ask_legacy_user_id_still_works(client):
    """POST /ask с body.user_id='user_123' возвращает 200 без ошибок."""

async def test_history_scoped_to_user(client):
    """GET /history возвращает только историю текущего пользователя."""
```

#### `tests/api/test_admin_identity_endpoint.py`

```python
async def test_admin_identity_requires_dev_key(client):
    """GET /admin/users/{id}/identity без dev_key возвращает 403."""

async def test_admin_identity_returns_linked_identities(client):
    """GET /admin/users/{id}/identity возвращает correct структуру."""

async def test_admin_identity_hides_full_fingerprint(client):
    """external_id для web-provider не раскрывает полный fingerprint."""
```

### 9.3 E2E сценарии

#### Сценарий 1: Новый пользователь, первый запрос

```
1. Клиент отправляет POST /ask без каких-либо заголовков
2. Middleware генерирует fingerprint из IP+UA
3. IdentityService создаёт нового пользователя (UUID) + linked_identity
4. Запрос обрабатывается, user_id правильно привязан
5. История сохранена под корректным user_id
ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: users таблица содержит 1 новую запись
```

#### Сценарий 2: Возвращающийся пользователь

```
1. Тот же клиент отправляет второй POST /ask
2. Fingerprint совпадает
3. IdentityService находит существующего пользователя
4. created_new_user=False, user_id тот же
ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: users таблица не создала новую запись
```

#### Сценарий 3: Пользователь со старым legacy user_id

```
1. Клиент POST /ask с body: {"query": "...", "user_id": "legacy_user_42"}
2. Bridge проверяет linked_identities(provider='legacy', external_id='legacy_user_42')
3. Находит или создаёт запись, возвращает стабильный user_id
4. WARN-запись в логах
ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: история сохранена, предупреждение залогировано
```

#### Сценарий 4: Пользователь переходит с веба на Telegram (будущий флоу)

```
1. Пользователь в вебе: GET /identity/generate-link-code → code="ABC123"
2. Пользователь в Telegram: /start ABC123
3. TG-адаптер: POST /identity/link-telegram {code: "ABC123", telegram_user_id: "987654321"}
4. IdentityService.link_identity(user_id=..., provider='telegram', external_id='987654321')
5. Память между каналами становится общей
ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: linked_identities содержит обе записи для одного user_id
[Этот сценарий реализуется в следующем PRD]
```

---

## 10. Структура файлов после реализации

```
bot_psychologist/
├── api/
│   ├── identity/               ← НОВЫЙ МОДУЛЬ
│   │   ├── __init__.py
│   │   ├── service.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── middleware.py
│   ├── auth.py                 ← ИЗМЕНЁН: добавлен dev_user_id маппинг
│   ├── dependencies.py         ← ИЗМЕНЁН: экспортирует get_identity_context
│   ├── models.py               ← ИЗМЕНЁН: user_id deprecated, link models добавлены
│   ├── session_store.py        ← НЕ ИЗМЕНЁН (понижен до device layer)
│   └── routes/
│       ├── identity_routes.py  ← НОВЫЙ: /identity/link-telegram stub
│       └── ...                 ← ИЗМЕНЕНЫ: используют IdentityContext
├── scripts/
│   └── migrations/
│       └── 013_identity_layer.sql  ← НОВЫЙ
└── tests/
    ├── identity/               ← НОВАЯ ДИРЕКТОРИЯ
    │   ├── test_migration_013.py
    │   ├── test_identity_models.py
    │   ├── test_identity_repository.py
    │   ├── test_identity_service.py
    │   ├── test_identity_middleware.py
    │   ├── test_legacy_user_id_bridge.py
    │   ├── test_link_telegram_stub.py
    │   └── test_resolve_telegram.py
    └── api/
        ├── test_routes_identity_integration.py  ← НОВЫЙ
        └── test_admin_identity_endpoint.py      ← НОВЫЙ
```

---

## 11. Зависимости и предусловия

| Зависимость | Статус | Примечание |
|---|---|---|
| PRD-012 выполнен | ✅ | Neo Trace Contract v2 активен |
| SQLite или PostgreSQL как основная БД | Проверить | Миграция написана для SQLite, PostgreSQL-вариант указан в комментарии |
| FastAPI >= 0.100 | Проверить по `requirements.txt` | Используется `Depends()` паттерн |
| Pydantic v2 | ✅ | Используется в `models.py` |
| `pytest-asyncio` | Проверить | Нужен для async-тестов |

---

## 12. Определение выполненности (Definition of Done)

- [ ] Все 11 тасков выполнены
- [ ] Все тесты проходят: `pytest tests/identity/ tests/api/ -v`
- [ ] `user_id = "default"` не появляется в базе данных ни при каком запросе
- [ ] Существующий web UI работает без изменений на клиентской стороне
- [ ] `CHANGELOG.md` обновлён (добавлен раздел PRD-013)
- [ ] `README.md` обновлён: добавлены заголовки `X-Device-Fingerprint`, `X-Session-Id`
- [ ] Код-ревью пройдено
- [ ] Ни один из существующих тестов (`tests_v060_after.txt`) не упал

---

## 13. Риски

| Риск | Вероятность | Влияние | Митигация |
|---|---|---|---|
| Race condition при параллельном `resolve_or_create` | Средняя | Дублирование пользователей | Unique constraint на `linked_identities(provider, external_id)` + retry логика |
| Потеря истории при legacy migration | Низкая | Критическое | Legacy bridge + тесты сценария 3 |
| IP-based fingerprint нестабилен (NAT, VPN) | Высокая | Средняя | Клиент должен передавать явный `X-Device-Fingerprint`; IP — только fallback |
| Рост таблицы `sessions` | Низкая | Низкая | TTL + периодическая очистка (можно взять из `SessionStore.cleanup_expired`) |

---

*Документ является исполняемым PRD для Агента IDE. Каждый таск имеет точные критерии приёмки и ссылки на тесты. Реализация ведётся поэтапно: Фаза 1 → Фаза 2 → Фаза 3 → Фаза 4.*
