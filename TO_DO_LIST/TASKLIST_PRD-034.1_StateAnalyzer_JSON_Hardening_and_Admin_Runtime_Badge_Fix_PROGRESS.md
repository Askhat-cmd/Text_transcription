# TASKLIST PRD-034.1 — StateAnalyzer JSON hardening + Admin runtime badge fix

## Статус
- [x] PRD изучен и scope подтвержден
- [x] Усилен JSON parsing в `StateAnalyzerAgent._parse_json`
- [x] Усилена JSON-инструкция в `agent_llm_client` при `require_json=True`
- [x] Сохранены `raw_response`/`parse_error` в `last_debug` и ошибка не теряется в orchestrator
- [x] Исправлен runtime badge в Admin под фактический multiagent runtime
- [x] Добавлены/обновлены тесты
- [x] Прогнаны целевые тесты

## Технические задачи
- [x] `bot_psychologist/bot_agent/multiagent/agents/state_analyzer.py`
  - [x] Нормализация markdown fences
  - [x] Извлечение JSON между первой `{` и последней `}`
  - [x] Лог preview raw response на JSONDecodeError
  - [x] Сохранение `raw_response` и `parse_error` в `last_debug`
- [x] `bot_psychologist/bot_agent/multiagent/agents/agent_llm_client.py`
  - [x] Ужесточена JSON system instruction для `require_json=True`
- [x] `bot_psychologist/api/admin_routes.py`
  - [x] Нормализация bool-env (`on/true/1/yes/y`)
  - [x] Гарантия `active_runtime="multiagent"` для реального multiagent pipeline
- [x] UI/Admin
  - [x] `active_runtime` добавлен в типы и учитывается в Runtime Badge

## Тесты
- [x] `bot_psychologist/tests/multiagent/test_state_analyzer.py`
  - [x] pure JSON parse
  - [x] fenced JSON parse
  - [x] text + JSON + text parse
  - [x] invalid JSON сохраняет `parse_error`
- [x] `bot_psychologist/tests/multiagent/test_agent_llm_client.py`
  - [x] проверка строгой JSON-инструкции
- [x] `bot_psychologist/tests/test_admin_multiagent.py`
  - [x] `active_runtime` в status/config/overview
  - [x] truthy env (`true/1/...`) корректно определяет runtime

## Прогон
- [x] `.venv\Scripts\python.exe -m pytest bot_psychologist/tests/multiagent/test_state_analyzer.py bot_psychologist/tests/multiagent/test_agent_llm_client.py -q`
  - `19 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/test_admin_multiagent.py tests/test_admin_agent_llm_config.py -q` (из `bot_psychologist/`)
  - `25 passed`

## Definition of Done
- [x] StateAnalyzer устойчиво парсит JSON в типовых форматах
- [x] Ошибка parse не ломает пользовательский ответ и видна в debug
- [x] Admin показывает корректный runtime badge
- [x] Целевые тесты зеленые
