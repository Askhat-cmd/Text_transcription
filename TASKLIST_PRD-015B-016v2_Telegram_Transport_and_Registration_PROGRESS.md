# TASKLIST PRD-015B-v2 + PRD-016-v2

## Scope
- PRD file: `PRD-015B-v2 + PRD-016-v2 — Пакетный документ (Revised).md`
- Goal: implement Telegram transport layer + registration/access/linking system with security hardening.

## Implementation Tasks

- [x] T1: Extend `api/telegram_adapter/config.py` to v2 settings (`polling/webhook`, backoff, secrets).
- [x] T2: Implement `api/telegram_adapter/outbound.py` with `TelegramOutboundSender`.
- [x] T3: Implement `api/telegram_adapter/transport.py` with polling loop + graceful stop + backoff.
- [x] T4: Implement `api/telegram_adapter/factory.py`.
- [x] T5: Implement `api/telegram_adapter/webhook_routes.py` with HMAC secret validation.
- [x] T6: Implement new package `api/registration/` (`models.py`, `repository.py`, `service.py`, `routes.py`, `security.py`, `guards.py`, `bootstrap.py`, `__init__.py`).
- [x] T7: Extend `api/identity/models.py` (`role`, `username`, `is_registered`) with defaults.
- [x] T8: Integrate registration dependencies/session resolving in `api/dependencies.py`.
- [x] T9: Migrate `api/auth.py` from in-memory keys to DB-backed keys (keep rate limiting behavior).
- [x] T10: Extend `api/telegram_adapter/service.py` with `/link <code>` flow via registration service.
- [x] T11: Integrate lifecycle startup/shutdown in `api/main.py`:
- [x] T11.1: `DatabaseBootstrap.run()` in startup.
- [x] T11.2: Polling transport task start/stop by flags.
- [x] T11.3: Conditional webhook router registration in webhook mode.
- [x] T12: Register new registration routes in API.
- [x] T13: Add tests for registration/security/guards/routes.
- [x] T14: Add tests for outbound/transport/webhook and link command.
- [x] T15: Update README/env docs with new settings and flow.

## Test Plan

- [x] `python -m pytest tests/registration tests/telegram_adapter/test_models.py tests/telegram_adapter/test_adapter.py tests/telegram_adapter/test_service.py tests/telegram_adapter/test_outbound.py tests/telegram_adapter/test_transport.py tests/telegram_adapter/test_webhook.py tests/telegram_adapter/test_link_command.py tests/api/test_auth_routes.py tests/api/test_telegram_mock_routes.py tests/api/test_routes_identity_integration.py tests/api/test_dependencies_conversation.py tests/api/test_conversation_routes.py -q`
- [x] `python -m pytest tests/api tests/identity tests/conversations -q`

## Quality Checks

- [x] No direct SQL in `telegram_adapter/transport.py` and `telegram_adapter/outbound.py`.
- [x] `registration/` does not import `api/identity/repository.py` directly.
- [x] `access_key` is stored only as argon2 hash.
- [x] `/confirm-link` requires internal key + HMAC and never accepts dev key.
- [x] `/link` attempt guard limits to 5 failures per 15 minutes.
- [x] `TELEGRAM_ENABLED=false` keeps runtime startup clean.
- [x] Polling transport stops gracefully.
- [x] Existing core tests still pass.

## Progress Log

- 2026-04-25: Tasklist created. Implementation started.
- 2026-04-25: Реализованы PRD-015B-v2 + PRD-016-v2 блоки (transport + registration + auth migration + bootstrap + tests + docs). Целевые тесты: `58 passed`, расширенный API/identity/conversations: `72 passed`.
