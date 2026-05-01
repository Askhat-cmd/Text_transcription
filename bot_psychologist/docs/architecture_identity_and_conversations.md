# Архитектура Identity и Conversations

## Назначение

Документ фиксирует runtime-контракт после PRD-013, PRD-014 и PRD-016-v2:
- identity-слой определяет устойчивого пользователя;
- conversation-слой определяет жизненный цикл конкретного диалога;
- registration-слой добавляет управляемый доступ (register/login/session/linking);
- chat-слой работает только с уже разрешенным контекстом.

## Ключевые контексты

### IdentityContext

`IdentityContext` формируется в `api/dependencies.py` и содержит:
- `user_id` — устойчивый UUID пользователя;
- `session_id` — идентификатор клиентской сессии;
- `conversation_id` — активный диалог в рамках текущего запроса;
- `channel` — `web` / `telegram` / `api`;
- `provider` и `external_id` — источник внешней идентичности;
- `is_anonymous` — fallback-режим при проблемах резолва;
- `role: str` (default: `"anonymous"`);
- `username: Optional[str]` (default: `None`);
- `is_registered: bool` (default: `False`).

Новые поля (`role`, `username`, `is_registered`) добавлены с дефолтами, чтобы сохранить обратную совместимость.

### ConversationContext

`ConversationContext` формируется в `api/conversations/service.py`:
- `conversation_id` — UUID диалога;
- `user_id` — владелец диалога;
- `session_id` — сессия, из которой активирован диалог;
- `channel` — канал диалога;
- `status` — `active` / `paused` / `closed` / `archived`;
- `started_at` — время старта;
- `is_new` — создан ли диалог в текущем запросе.

## Поток обработки запроса

1. HTTP-запрос попадает в `api/routes/*`.
2. `get_identity_context()` резолвит identity через `api/identity/service.py`.
3. `ConversationService` резолвит или создает `ConversationContext`.
4. Chat endpoint передает управление в runtime (single-agent или multiagent).
5. После ответа обновляется состояние диалога (`last_message_at`, `status`).

## Связь identity и registration

`api/registration/service.py` интегрирован с identity-слоем:
- при `register` создается пользовательский профиль с ролью и username;
- при `login` выдается session token, связанный с user;
- при `confirm-link` создается `linked_identity` с `provider="telegram"` и `external_id=telegram_user_id`;
- связь всегда строится через общий `user_id`.

Схема связи:

```text
users.id (user_id)
  ├─ identity context (runtime)
  ├─ user profile (role, username, status)
  └─ linked_identities(provider, external_id)
       └─ telegram link after confirm-link
```

## Иерархия идентификаторов

| Уровень | Поле | Назначение | Жизненный цикл |
|---|---|---|---|
| Человек | `user_id` | Канонический идентификатор пользователя | Долгоживущий |
| Внешний канал | `linked_identity` | Привязка `provider + external_id` | До отвязки/удаления |
| Клиентская сессия | `session_id` | Устройство/браузер/клиент | Временный |
| Диалог | `conversation_id` | Отдельная ветка общения | На время жизни диалога |

Почему `conversation_id != session_id`:
- `session_id` описывает техническую сессию клиента;
- `conversation_id` описывает бизнес-диалог;
- одна сессия может иметь несколько диалогов.

## Границы модулей

Правило модульности:
- runtime-агенты не пишут напрямую в identity/conversation таблицы;
- доступ идет через `IdentityService` и `ConversationService`;
- SQL-слой изолирован в `api/identity/repository.py` и `api/conversations/repository.py`.

## Что изменилось в PRD-016-v2

Было:
- identity в основном опирался на `user_id` и fallback-анонимность;
- не было полного контракта регистрации/логина/привязки в одном слое.

Стало:
- добавлены `role`, `username`, `is_registered` в identity-контекст;
- добавлен registration-пакет (`register`, `login`, `invite keys`, `link-code`, `confirm-link`);
- привязка Telegram выполняется через явную linked identity, а не через неявное слияние.
