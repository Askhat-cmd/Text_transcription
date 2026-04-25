# TASKLIST PRD-014 — Conversation Layer & Identity Hardening (PROGRESS)

Статус: `completed`
Дата старта: `2026-04-25`
Источник: `PRD-014 — Conversation Layer & Identity Hardening.md`

## Цель
Довести API identity + conversation layer до состояния PRD-014: закрыть хотфиксы AUDIT-013, ввести независимый `conversation_id`, добавить conversation-модуль/роуты/миграцию и покрыть тестами.

## Фаза 0 — Хотфиксы identity (AUDIT-013)
- [x] `TASK-014-00-A`: убрать silent-merge `user_id` при конфликте `(provider, external_id)` в linked identities.
- [x] `TASK-014-00-B`: fallback в `get_identity_context()` только UUID-подобный `anon_*`, с `identity.resolve_failed` логом.
- [x] `TASK-014-00-C`: fingerprint учитывает `X-Forwarded-For` / `X-Real-IP` с приоритетами.

## Фаза 1 — Новый модуль conversations
- [x] `TASK-014-01`: добавить `scripts/migrations/014_conversation_layer.sql` (idempotent + rollback notes).
- [x] `TASK-014-02`: добавить `api/conversations/models.py`.
- [x] `TASK-014-03`: добавить `api/conversations/repository.py`.
- [x] `TASK-014-04`: добавить `api/conversations/service.py`.
- [x] `TASK-014-05`: добавить `api/conversations/__init__.py` (публичный контракт).

## Фаза 2 — Интеграция в зависимости и роуты
- [x] `TASK-014-06`: обновить `get_identity_context()` с поддержкой `X-Conversation-Id` и `ConversationService`.
- [x] `TASK-014-07`: добавить `api/routes/conversation_routes.py`, подключить роутер.

## Фаза 3 — Тесты
- [x] `TASK-014-08`: закрыть backlog identity-тестов (repository/service/middleware/dependencies).
- [x] `TASK-014-09`: добавить тесты conversations (migration/models/repository/service/routes).

## Фаза 4 — Cleanup + hardening
- [x] `TASK-014-10`: упростить `upsert_session()` (одна SQL-ветка).
- [x] `TASK-014-11`: не хранить сырой IP в session metadata (только hash/prefix).
- [x] `TASK-014-12`: маскировать `external_id` в `/api/v1/identity/me`.
- [x] `TASK-014-13`: обновить changelog/доки под PRD-014.

## Проверки (обязательные)
- [x] Unit/contract: `pytest tests/identity -q`
- [x] Conversation: `pytest tests/conversations -q`
- [x] API integration: `pytest tests/api/test_routes_identity_integration.py tests/api/test_admin_identity_endpoint.py -q`
- [x] Smoke endpoints: `/api/v1/identity/me`, `/api/v1/conversations/`, `/api/v1/conversations/new`

## Acceptance checks
- [x] `IdentityContext.conversation_id` больше не равен автоматически `session_id` (кроме fallback-сценариев).
- [x] Нет утечки полного fingerprint в `/api/v1/identity/me`.
- [x] SQL миграция 014 применяется повторно без падений.
- [x] Все добавленные тесты проходят локально.
