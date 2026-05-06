# TASKLIST PRD-042 — Post-Purge Stabilization & Final Regression

## Scope
- [x] Изучить PRD-042
- [x] Проанализировать текущие runtime/API/Telegram/tests контракты
- [x] Реализовать post-purge стабилизацию без возврата legacy

## Backend Runtime / API
- [x] Стабилизировать `/api/debug/session/{session_id}/multiagent-trace` после PRD-041 purge
- [x] Добавить fallback lookup по доступным trace/debug ключам
- [x] Вернуть диагностический payload при отсутствии trace (вместо неинформативного 404)
- [x] Убедиться, что streaming/non-streaming путь консистентно сохраняют trace/debug

## Import Safety
- [x] Добавить PRD-042 сканер `scripts/post_purge_import_scan.py`
- [x] Добавить проверку forbidden active runtime imports (state_classifier/route_resolver/decision/response)
- [x] Подготовить читаемый отчёт сканера

## Tests
- [x] Добавить `tests/inventory/test_post_purge_no_broken_legacy_imports.py`
- [x] Добавить `tests/api/test_multiagent_trace_storage_consistency.py`
- [x] Добавить `tests/e2e/test_post_purge_runtime_smoke.py`
- [x] Обновить `tests/test_admin_runtime_contract.py` под physical purge статус
- [x] Проверить streaming smoke-контракт после purge

## Docs
- [x] Создать `docs/post_purge_stabilization_audit_prd042.md`
- [x] Создать `docs/post_purge_remaining_review_modules_prd042.md`
- [x] Обновить `README.md`
- [x] Обновить `docs/migration_legacy_to_multiagent.md`
- [x] Обновить `docs/testing_matrix.md`
- [x] Обновить `docs/legacy_physical_purge_audit_prd041.md` ссылкой на PRD-042 regression

## Test Run Log
- [x] `python -m pytest tests/inventory/test_post_purge_no_broken_legacy_imports.py -q`
- [x] `python -m pytest tests/api/test_multiagent_trace_storage_consistency.py -q`
- [x] `python -m pytest tests/e2e/test_post_purge_runtime_smoke.py -q`
- [x] `python -m pytest tests/inventory/test_physical_legacy_purge.py -q`
- [x] `python -m pytest tests/inventory/test_multiagent_runtime_invariants.py -q`
- [x] `python -m pytest tests/test_admin_runtime_contract.py -q`
- [x] `python -m pytest tests/test_llm_streaming.py -q`
- [x] `python scripts/post_purge_import_scan.py`

## Results Snapshot
- `tests/inventory/test_post_purge_no_broken_legacy_imports.py tests/api/test_multiagent_trace_storage_consistency.py tests/e2e/test_post_purge_runtime_smoke.py tests/test_admin_runtime_contract.py tests/test_multiagent_trace.py` → `23 passed`
- `tests/inventory/test_physical_legacy_purge.py tests/inventory/test_multiagent_runtime_invariants.py tests/test_llm_streaming.py` → `16 passed`
- `scripts/post_purge_import_scan.py` → `RESULT: PASS`

## Notes
- Не возвращать `adaptive_runtime` и legacy fallback.
- Не менять prompt-логику и model-adapter архитектуру.
- Telegram runtime не активировать.
