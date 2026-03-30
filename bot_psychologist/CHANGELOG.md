# Changelog

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
