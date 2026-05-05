# TASKLIST PRD-039 — Trace & Metadata Multiagent-Only Cleanup

## Статус
- [x] PRD изучен
- [x] Инвентаризированы текущие trace/metadata touchpoints в runtime/API/tests
- [x] Введен active builder `_build_multiagent_metadata`
- [x] Введен active builder `_build_multiagent_trace_storage_payload`
- [x] Legacy sanitizer usage убран из active response/trace enrichment paths
- [x] DebugTrace явно помечен как compatibility view
- [x] Расширены trace-модели (`WriterLLMTrace`, `StateAnalyzerTrace`) под api_mode/error/fallback
- [x] Добавлены тесты PRD-039 (metadata + trace + inventory guard + endpoint smoke update)
- [x] Прогнаны targeted + regression наборы

## Реализация
- [x] `bot_psychologist/api/routes/common.py`
  - [x] Добавить `_COMPAT_ONLY_METADATA_KEYS`
  - [x] Добавить `_FORBIDDEN_LEGACY_METADATA_KEYS`, `_FORBIDDEN_LEGACY_TRACE_KEYS`
  - [x] Добавить `_build_multiagent_metadata(raw_metadata, debug_payload)`
  - [x] Добавить `_build_multiagent_trace_storage_payload(trace_payload)`
  - [x] Переименовать normalize helper в compat-имя + alias
  - [x] Перевести `_build_answer_response_from_adaptive` на multiagent metadata builder
  - [x] Перевести `_enrich_trace_for_storage` на multiagent trace storage builder
- [x] `bot_psychologist/api/routes/chat.py`
  - [x] Перевести metadata/trace сборку на новые helper-и
  - [x] Сохранить совместимость формы `DebugTrace`
- [x] `bot_psychologist/api/models.py`
  - [x] Документировать `DebugTrace` как compatibility
  - [x] `trace_contract_version` по умолчанию `multiagent_compat_v2`
  - [x] Расширить `WriterLLMTrace`: `api_mode`, `error`, `fallback_used`
  - [x] Расширить `StateAnalyzerTrace`: `model`, `api_mode`, `error`, `fallback_used`, `parse_error`
- [x] `bot_psychologist/api/debug_routes.py`
  - [x] Пробросить новые поля в `/multiagent-trace`
- [ ] Fixtures/inventory
  - [x] Проверить `tests/fixtures/multiagent_runtime_invariants_v1.json` на отсутствие legacy metadata keys

## Тесты
- [x] `bot_psychologist/tests/api/test_multiagent_metadata_contract.py`
- [x] `bot_psychologist/tests/api/test_multiagent_trace_contract.py`
- [x] `bot_psychologist/tests/inventory/test_no_active_legacy_trace_metadata_keys.py`
- [x] Обновить `bot_psychologist/tests/api/test_debug_trace_semantic_hits.py` под compat helper
- [x] Обновить/добавить smoke для `/api/debug/session/{session_id}/multiagent-trace`

## Прогоны
- [x] `.venv\\Scripts\\python.exe -m pytest tests/api/test_multiagent_metadata_contract.py -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/api/test_multiagent_trace_contract.py -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/inventory/test_no_active_legacy_trace_metadata_keys.py -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/api/test_debug_trace_semantic_hits.py -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/test_multiagent_trace.py -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/api -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/multiagent -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/inventory -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/test_llm_streaming.py -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/telegram_adapter -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/test_admin_multiagent.py tests/test_admin_agent_llm_config.py tests/test_admin_runtime_contract.py -q`
- [x] `cd bot_psychologist/web_ui && npm run build`
