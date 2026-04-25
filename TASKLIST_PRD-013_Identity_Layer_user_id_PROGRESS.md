# TASKLIST PRD-013 Identity Layer user_id — Progress

## Scope
- PRD: `PRD-013_Identity_Layer_user_id.md`
- Target: implement stable identity layer (`users` + `linked_identities`) with backward compatibility for existing Web UI.

## Assumptions
- Existing API contract must remain backward compatible for current web client.
- Existing `sessions` table from `SessionManager` is reused and extended (non-breaking).
- Telegram runtime is out of active production flow, but identity stubs are required.

## Tasks

### 1) Migration and schema
- [x] Add SQL migration: `bot_psychologist/scripts/migrations/013_identity_layer.sql`
- [x] Ensure tables exist: `users`, `linked_identities`
- [x] Ensure `sessions` table has identity fields (`channel`, `device_fingerprint`, `last_seen_at`, `expires_at`, `metadata_json`)
- [x] Ensure indexes and unique constraints exist (`provider + external_id`)

### 2) Identity module
- [x] Create `api/identity/models.py`
- [x] Create `api/identity/repository.py`
- [x] Create `api/identity/service.py`
- [x] Create `api/identity/middleware.py` (identity helpers / fingerprint extraction)
- [x] Create `api/identity/__init__.py`

### 3) FastAPI dependencies
- [x] Add `get_identity_service()` singleton provider in `api/dependencies.py`
- [x] Add `get_identity_context()` dependency resolving:
  - headers: `X-Device-Fingerprint`, `X-Session-Id`
  - fallback fingerprint from request metadata
  - legacy bridge from body/path `user_id`

### 4) Route integration
- [x] Update `api/routes/chat.py` to use `IdentityContext`
- [x] Update `api/routes/users.py` to resolve canonical user through identity layer
- [x] Update `api/routes/feedback.py` to route feedback through canonical user
- [x] Add identity stub routes: `api/routes/identity_routes.py`
- [x] Register identity routes in `api/routes/__init__.py`

### 5) Admin identity endpoint
- [x] Add `GET /api/admin/users/{user_id}/identity`
- [x] Add `GET /api/v1/admin/users/{user_id}/identity`
- [x] Restrict by dev key (`require_dev_key`)
- [x] Mask external identifiers for web provider

### 6) Documentation and compatibility
- [x] Update API models (`AskQuestionRequest.user_id` deprecation-compatible)
- [x] Update README with identity headers (if needed for contract)
- [x] Keep legacy clients working without mandatory header changes

### 7) Tests
- [x] Add unit tests for identity models/repository/service
- [x] Add API tests for route integration and admin endpoint
- [x] Run targeted suite for changed areas

## Test plan
- [x] `pytest bot_psychologist/tests/identity -v`
- [x] `pytest bot_psychologist/tests/api -v` (if folder exists)
- [x] `pytest bot_psychologist/tests/smoke/test_pipeline_entrypoints.py -v`
- [x] `pytest bot_psychologist/tests/test_stream_dependencies.py -v`
- [x] `pytest bot_psychologist/tests/test_api.py -v` (local/API checks may skip)
- [x] Extended regression: `pytest tests --maxfail=1 -q` → `538 passed, 13 skipped`

## Acceptance checks
- [x] API keeps working for current web flow with body `user_id`
- [x] Same fingerprint resolves same canonical `user_id`
- [x] Legacy `user_id` is bridged to `linked_identities(provider='legacy')`
- [x] Admin identity endpoint returns linked identities and active sessions
- [x] No regressions in touched route entrypoints/signatures

## Progress log
- [x] PRD reviewed and implementation scope mapped to existing code.
- [x] Identity layer code integrated into API/dependencies/routes/admin.
- [x] Added migration + identity test pack + API integration tests.
- [x] Full test suite after changes: `538 passed, 13 skipped`.
- [x] PRD-013 scope completed.
