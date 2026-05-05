# TASKLIST PRD-038 — Tests Migration: Legacy Contracts to Multiagent Invariants

## Статус
- [x] PRD изучен
- [x] Инвентаризированы текущие inventory/legacy fixtures и тесты
- [x] Добавлен active fixture `multiagent_runtime_invariants_v1.json`
- [x] Добавлен тест `test_multiagent_runtime_invariants.py`
- [x] legacy runtime map tests переведены в archived-mode
- [x] runtime legacy touchpoints tests переведены в archived-mode
- [x] legacy fixtures помечены archived metadata
- [x] admin prompt fetch failure inventory переведен в archived-mode или active-quality mode
- [x] Прогнаны targeted и full inventory + regression наборы

## Задачи
- [x] `bot_psychologist/tests/fixtures/multiagent_runtime_invariants_v1.json`
- [x] `bot_psychologist/tests/inventory/test_multiagent_runtime_invariants.py`
- [ ] Переименовать и переписать:
  - [x] `test_legacy_runtime_map.py` -> `test_archived_legacy_runtime_map.py`
  - [x] `test_runtime_legacy_touchpoints_map.py` -> `test_archived_runtime_legacy_touchpoints_map.py`
- [ ] Обновить archived metadata:
  - [x] `tests/fixtures/legacy_runtime_map.json`
  - [x] `tests/fixtures/runtime_legacy_touchpoints_v102.json`
- [ ] Обновить admin broken-flow inventory:
  - [x] `tests/fixtures/admin_surface_inventory_v104_phase0.json`
  - [x] `tests/inventory/test_admin_prompt_fetch_failure_inventory.py`
- [x] Проверить связанные inventory тесты на совместимость

## Прогоны
- [x] `.venv\\Scripts\\python.exe -m pytest tests/inventory/test_multiagent_runtime_invariants.py -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/inventory/test_archived_legacy_runtime_map.py -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/inventory/test_archived_runtime_legacy_touchpoints_map.py -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/inventory/test_admin_prompt_fetch_failure_inventory.py -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/inventory -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/multiagent -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/api -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/test_llm_streaming.py -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/telegram_adapter -q`
- [x] `.venv\\Scripts\\python.exe -m pytest tests/test_admin_multiagent.py tests/test_admin_agent_llm_config.py tests/test_admin_runtime_contract.py -q`
