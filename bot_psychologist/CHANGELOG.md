# Changelog

## v0.13.0 - 2026-04-25

### Added
- Новый модуль `api/conversations/`:
  - `models.py` (`ConversationContext`, `ConversationSummary`, `StartConversationRequest`)
  - `repository.py` (CRUD + lifecycle + schema extension for `memory_items`)
  - `service.py` (create/resume/pause/close/list/touch)
- Новый API роутер `api/routes/conversation_routes.py`:
  - `GET /api/v1/conversations/`
  - `POST /api/v1/conversations/new`
  - `POST /api/v1/conversations/{conversation_id}/close`
- Добавлена SQL-миграция `scripts/migrations/014_conversation_layer.sql`.
- Новые тестовые наборы:
  - `tests/conversations/test_migration_014.py`
  - `tests/conversations/test_conversation_models.py`
  - `tests/conversations/test_conversation_repository.py`
  - `tests/conversations/test_conversation_service.py`
  - `tests/api/test_conversation_routes.py`
  - `tests/api/test_dependencies_conversation.py`
  - `tests/identity/test_dependencies.py`

### Fixed
- FINDING-01: при конфликте `(provider, external_id)` больше не перепривязывается `user_id` в `linked_identities`.
- FINDING-02: fallback identity-контекст теперь UUID-подобный (`anon_<32hex>` + fallback session/conversation ids), с логом `identity.resolve_failed`.
- FINDING-03: `upsert_session()` в identity repository упрощен до одной актуальной SQL-ветки.
- FINDING-04: fingerprint теперь учитывает `X-Forwarded-For` и `X-Real-IP` до `request.client.host`.
- FINDING-07: в `/api/v1/identity/me` `external_id` отдается в маскированном виде.
- Session metadata hardening: вместо сырого IP сохраняется `ip_hash`.

### Changed
- `IdentityContext.conversation_id` теперь резолвится через conversation layer (включая поддержку `X-Conversation-Id`).
- Chat routes обновляют `last_message_at` разговора через `ConversationService.touch_conversation()`.

## v0.12.1 - 2026-04-25

### Added
- PRD-013 Identity Layer:
  - `api/identity/` (`models.py`, `repository.py`, `service.py`, `middleware.py`)
  - `api/routes/identity_routes.py` (`/api/v1/identity/me`, stub endpoints for telegram linking)
  - SQL migration `scripts/migrations/013_identity_layer.sql`
  - Admin endpoint `GET /api/admin/users/{user_id}/identity` (+ `/api/v1/...`)

### Changed
- `api/dependencies.py`: added `get_identity_service()` and `get_identity_context()`.
- `api/routes/chat.py`, `api/routes/users.py`, `api/routes/feedback.py`: switched to canonical `IdentityContext`.
- `api/models.py`: `AskQuestionRequest.user_id` marked as deprecated-compatible optional field.
- `README.md`: added identity request headers section.

### Tests
- Added new test packs:
  - `tests/identity/test_migration_013.py`
  - `tests/identity/test_identity_models.py`
  - `tests/identity/test_identity_repository.py`
  - `tests/identity/test_identity_service.py`
  - `tests/identity/test_identity_middleware.py`
  - `tests/identity/test_legacy_user_id_bridge.py`
  - `tests/identity/test_link_telegram_stub.py`
  - `tests/identity/test_resolve_telegram.py`
  - `tests/identity/test_identity_logging.py`
  - `tests/api/test_routes_identity_integration.py`
  - `tests/api/test_admin_identity_endpoint.py`
- Full regression after integration: `538 passed, 13 skipped`.

## v0.7.1 - 2026-04-12

### Changed
- Trace contract aligned to `v2` across API debug and stream payloads.
- Runtime trace sanitization hardened to strip outdated fields on read.
- Web inline trace updated to Neo-only status chips and deep sections.
- Admin routing surface reduced to active Neo controls only.
- Runtime config editable surface cleaned from outdated routing keys.
- Retrieval evaluation scripts aligned to Neo retrieval signature.

### Added
- UI regression guard: `tests/ui/test_trace_statusbar_neo_contract.py`.

### Documentation
- Reworked `README.md` and core docs to Neo-only runtime description.
- Updated `.env.example` comments and removed outdated runtime flags from sample config.
- Added PRD-012 before/after cleanup report.

### Verification
- `pytest tests/contract tests/ui tests/inventory tests/regression/test_no_sd_runtime_metadata_fields.py tests/regression/test_trace_reflects_real_execution_only.py tests/regression/test_streaming_sd_runtime_disabled_contract.py tests/test_llm_payload_endpoint.py tests/test_sse_payload.py -q`
- `npm run lint` and `npm run build` in `web_ui/`

## v0.7.0 - 2026-03-31

### Added
- Новый task-файл реализации PRD v5.0: `PRD_TASKS_v5.0_smart_interlocutor.md`.
- Новые тесты:
  - `tests/test_llm_answerer.py`
  - `tests/test_path_builder.py`
  - `tests/test_routing_config.py`
  - `tests/test_admin_api.py`
- Новый backend router alias: `/api/v1/admin/*` (параллельно legacy `/api/admin/*`).
- Новые admin endpoints:
  - `GET /api/v1/admin/config/schema`
  - `GET /api/v1/admin/status`
  - `POST /api/v1/admin/reload-data`
- Автосоздание prompt snapshot-файлов `*.default.md` при старте API.
- Новый UI-компонент: `web_ui/src/components/admin/RoutingTab.tsx`.

### Changed
- `llm_answerer.py`:
  - добавлен единый builder API-параметров для chat/responses API;
  - логика токенов переведена на runtime-флаги:
    - `FREE_CONVERSATION_MODE`
    - `MAX_TOKENS`
    - `MAX_TOKENS_SOFT_CAP`
- `response_generator.py`:
  - добавлена FREE-ветка системного промпта;
  - добавлена иерархия приоритетов промптов через флаги:
    - `PROMPT_SD_OVERRIDES_BASE`
    - `PROMPT_MODE_OVERRIDES_SD`
  - фильтрация конфликтующих ограничивающих директив для расширяющих режимов.
- `runtime_config.py`/`config.py`:
  - добавлены routing-флаги и пороги:
    - `FAST_DETECTOR_ENABLED`
    - `FAST_DETECTOR_CONFIDENCE_THRESHOLD`
    - `STATE_CLASSIFIER_ENABLED`
    - `STATE_CLASSIFIER_CONFIDENCE_THRESHOLD`
    - `SD_CLASSIFIER_ENABLED`
    - `SD_CLASSIFIER_CONFIDENCE_THRESHOLD`
    - `DECISION_GATE_RULE_THRESHOLD`
    - `DECISION_GATE_LLM_ROUTER_ENABLED`
  - добавлены токенные параметры FREE-режима;
  - добавлены editable-поля для новых параметров в Admin config.
- `fast_detector.py`:
  - подключён глобальный runtime toggle `FAST_DETECTOR_ENABLED`;
  - добавлен runtime-порог `FAST_DETECTOR_CONFIDENCE_THRESHOLD`.
- `api/admin_routes.py`:
  - grouped payload для `POST /config`;
  - поддержка `MAX_TOKENS: null`;
  - prompt endpoints расширены alias-полем `content` и reset-роутом `POST /prompts/{name}/reset`.
- `web_ui`:
  - добавлена вкладка «Маршрутизация»;
  - runtime-вкладка дополнена статусом системы и кнопкой перезагрузки базы;
  - поддержка `int_or_null` в редакторе параметров (`MAX_TOKENS` как nullable).

### Tests
- `pytest tests --tb=short`: **168 passed, 11 skipped, 0 failed**.
- `npm run build` в `web_ui`: успешная сборка.

## v0.6.1-stability - 2026-03-30

### Fixed
- `bot_agent/data_loader.py`: добавлен thread-safe singleton guard (`load()`/`reload()`), устранена повторная загрузка при warmup.
- `bot_agent/data_loader.py`: реализована fallback-цепочка `api -> json_fallback -> degraded` с диагностикой источника данных.
- `bot_agent/retriever.py`: деградация включается только при реальном `data_source=degraded`; добавлен retry-wrapper для API retrieval.
- `api/routes.py`: `/api/v1/health` возвращает `status`, `data_source`, `blocks_loaded`, `bot_data_base_api`.
- `bot_agent/retrieval/confidence_scorer.py`: cap для уровней confidence переведён на runtime-конфиг (`high=7`, `medium=5`, `low=3`, `zero=0`) с логом применения.
- `bot_agent/runtime_config.py`: добавлен `reload()` для обратной совместимости тестов/утилит.

### Added
- Новые тесты: `tests/test_data_loader_singleton.py`, `tests/test_data_loader_fallback.py`, `tests/test_confidence_cap.py`.

### Tests
- Прогнаны целевые и регрессионные наборы тестов для bugfix v0.6.1.

## v0.6.1 - 2026-03-30

### Added
- `bot_agent/contradiction_detector.py`: детектор расхождений «всё нормально» vs маркеры напряжения.
- `bot_agent/progressive_rag.py`: SQLite-веса блоков (`block_weights`) + CLI-сброс `--reset-weights`.
- Cross-session summary слой: SQLite `session_summaries` + методы `save_session_summary()` и `load_cross_session_context()`.
- Новые тесты: `test_contradiction_detector.py`, `test_progressive_rag.py`, расширения в `test_conversation_memory_persistence.py` и `test_signal_detector.py`.

### Changed
- `answer_adaptive.py`: 
  - добавлен contradiction signal в `debug_trace` и `additional_system_context` без изменения routing;
  - добавлен cross-session context в системный контекст;
  - Progressive RAG применяется до reranker;
  - при позитивном сигнале (`это именно`, `в точку`, и т.п.) увеличиваются веса top-блоков.
- `decision/signal_detector.py`: добавлены сигналы `contradiction_*` и `positive_feedback_signal`.
- `storage/session_manager.py`: схема расширена таблицей `session_summaries` и методами загрузки/сохранения summary.

## v0.6.0 - 2026-03-25

### Changed
- Simplified retrieval pipeline: removed Stage/SD filters, flow is retrieval -> rerank -> cap -> LLM.
- Confidence scoring simplified (no voyage_confidence in formula).
- Fixed retrieval caps: `RETRIEVAL_TOP_K=5`, `VOYAGE_TOP_K=5`.
- Voyage rerank fallback keeps full candidate set (sorted by score).
- Increased adaptive request `query` limit to 2000 chars.
- Removed mirror-style opening from GREEN prompt to reduce reflective repeats in first sentence.
- Restored user level flow end-to-end: UI setting -> API payload `user_level` -> adaptive pipeline.
- Added active `USER_LEVEL` to trace `Config Snapshot`.
- Knowledge Graph made opt-in (`ENABLE_KNOWLEDGE_GRAPH=false` by default); warmup skips graph preload when disabled.
- Removed duplicate retrieval log line (`Final blocks to LLM`), оставлен единый `SOURCES`.
- API/app metadata bumped to `v0.6.0`.

### Added
- Runtime toggle `ENABLE_KNOWLEDGE_GRAPH` in config/.env.example.
- Debug endpoint `GET /api/debug/session/{session_id}/llm-payload`.
- Test `tests/test_graph_toggle.py` for graph enable/disable behavior.

### Tests
- Updated tests to match simplified retrieval pipeline.
- Added integration-style tests for simplified retrieval and confidence scorer.
