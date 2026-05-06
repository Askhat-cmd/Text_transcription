# TASKLIST PRD-044 — Web UI Trace Cleanup (Remove Legacy DebugTrace Panel)

## Scope
- [x] Изучить PRD-044
- [x] Найти legacy trace UI и active multiagent trace UI
- [x] Убрать legacy DebugTrace panel из ChatMessage rendering
- [x] Изолировать/удалить legacy trace component из active UI
- [x] Обновить frontend types (compat note для DebugTrace)
- [x] Добавить source guard тест на отсутствие legacy trace в active UI
- [x] Прогнать web build + required backend regressions

## Inventory
- [x] Список legacy trace UI files
- [x] Список active multiagent trace UI files

legacy trace UI files:
- `bot_psychologist/web_ui/src/components/debug/compat/LegacyDebugTracePanel.compat.tsx`

active multiagent trace UI files:
- `bot_psychologist/web_ui/src/components/chat/Message.tsx`
- `bot_psychologist/web_ui/src/components/chat/MultiAgentTraceWidget.tsx`

## Implementation
- [x] `Message.tsx`: убрать рендер legacy `InlineDebugTrace`
- [x] Проверить `InlineDebugTrace` imports/usage; убрать из active chat path
- [x] Не ломать `MultiAgentTraceWidget` (Pipeline NEO | multiagent_v1)
- [x] Проверить пустые chips (MODE/STATE/RULE/CHUNKS cap) и не выводить бессмысленные значения

## Tests
- [x] Добавить `tests/inventory/test_web_ui_no_legacy_debug_trace_panel.py`
- [x] Убедиться, что active chat files не содержат: `Problems only`, `Роутинг и классификация`, `BLOCK CAP`
- [x] Убедиться, что active chat still has `Pipeline NEO` and `multiagent_v1`

## Verification
- [x] `cd bot_psychologist/web_ui && npm run build`
- [x] `cd bot_psychologist && .venv\Scripts\python.exe -m pytest tests/inventory -q` *(1 внешний фейл не по PRD-044: `test_threads_directory_contains_only_gitkeep`)*
- [x] `cd bot_psychologist && .venv\Scripts\python.exe -m pytest tests/api -q`
- [x] `cd bot_psychologist && .venv\Scripts\python.exe -m pytest tests/multiagent -q`
- [x] `cd bot_psychologist && .venv\Scripts\python.exe -m pytest tests/test_llm_streaming.py -q`
- [x] `cd bot_psychologist && .venv\Scripts\python.exe -m pytest tests/telegram_adapter -q`
- [x] `cd bot_psychologist && .venv\Scripts\python.exe -m pytest tests/test_admin_multiagent.py tests/test_admin_agent_llm_config.py tests/test_admin_runtime_contract.py -q`

## Notes
- Игнорировать посторонние изменения вне PRD-044 scope.
- Runtime/backend contracts не менять без крайней необходимости.
