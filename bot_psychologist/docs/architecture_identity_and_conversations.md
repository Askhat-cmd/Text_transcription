# Архитектура Identity и Conversations

## Назначение

Документ фиксирует текущий runtime-контракт после PRD-013 и PRD-014:
- identity-слой определяет стабильного пользователя;
- conversation-слой определяет жизненный цикл конкретного диалога;
- chat-слой использует уже разрешенный контекст и не управляет identity напрямую.

## Ключевые контексты

### IdentityContext

IdentityContext формируется в `api/dependencies.py` и содержит:
- `user_id` — стабильный UUID пользователя;
- `session_id` — идентификатор текущей сессии/устройства;
- `channel` — `web` / `telegram` / `api`;
- `provider` и `external_id` — источник внешней идентичности;
- `is_anonymous` — fallback-режим при проблемах резолва;
- `conversation_id` — текущий диалог, связанный с identity.

### ConversationContext

ConversationContext формируется в `api/conversations/service.py`:
- `conversation_id` — UUID диалога;
- `user_id` — владелец диалога;
- `session_id` — сессия, из которой активирован диалог;
- `channel` — канал диалога;
- `status` — `active` / `paused` / `closed` / `archived`;
- `started_at` — время старта;
- `is_new` — создан ли диалог в текущем запросе.

## Поток обработки запроса

1. HTTP-запрос попадает в `api/routes/*`.
2. `get_identity_context()` в `api/dependencies.py` резолвит identity через `api/identity/service.py`.
3. `get_conversation_service()` возвращает сервис conversation-уровня.
4. Conversation service резолвит или создает нужный `ConversationContext`.
5. Chat endpoint передает управление в adaptive-runtime и возвращает ответ.
6. После ответа обновляется `last_message_at`/статус диалога.

## Почему `conversation_id != session_id`

- `session_id` — транспортно-клиентский уровень (браузер/устройство/временная сессия).
- `conversation_id` — бизнес-уровень конкретного диалога.
- Один `session_id` может породить несколько `conversation_id` (например, новые ветки обсуждения).
- Это предотвращает смешивание истории и делает корректным закрытие/архивацию диалогов.

## Границы модулей

Правило модульности:
- runtime/агенты не читают и не пишут напрямую в таблицы identity/conversations;
- доступ к данным идет через `IdentityService` и `ConversationService`;
- SQL-доступ инкапсулирован в `api/identity/repository.py` и `api/conversations/repository.py`.

## Реализовано vs планируется

### Реализовано
- Identity Layer с устойчивым `user_id`.
- Conversation Layer с отдельным `conversation_id` и lifecycle-операциями.
- API-маршруты `/api/v1/identity/*` и `/api/v1/conversations/*`.

### Планируется
- Контрактная интеграция Telegram через identity/conversation слой (PRD-015A).
- Реальный transport-слой Telegram на следующем этапе.
