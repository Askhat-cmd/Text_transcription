# TASKLIST_PRD-033_Per_Agent_LLM_Model_Selection_v3_FINAL_PROGRESS

Статус: DONE
Дата старта: 2026-05-01
Источник: TO_DO_LIST/PRD-033-Per-Agent-LLM-Model-Selection-v3-FINAL.md

## 1) План реализации
- [x] TASK-1: Создать `bot_psychologist/bot_agent/multiagent/agents/agent_llm_config.py`
- [x] TASK-2: Подключить источник модели в `state_analyzer.py`, `thread_manager.py`, `writer_agent.py`
- [x] TASK-3: Добавить backend endpoints для Agent LLM Config в `bot_psychologist/api/admin_routes.py`
- [x] TASK-4: Расширить типы в `bot_psychologist/web_ui/src/types/admin.types.ts`
- [x] TASK-5: Создать хук `bot_psychologist/web_ui/src/hooks/useAgentLLMConfig.ts`
- [x] TASK-6: Добавить UI-секцию в `bot_psychologist/web_ui/src/components/admin/AgentsTab.tsx`
- [x] TASK-7: Добавить unit-тесты `bot_psychologist/tests/multiagent/test_agent_llm_config.py`
- [x] TASK-8: Добавить API-тесты `bot_psychologist/tests/test_admin_agent_llm_config.py`

## 2) Проверки / тесты
- [x] `pytest bot_psychologist/tests/multiagent/test_agent_llm_config.py -q`
- [x] `pytest bot_psychologist/tests/test_admin_agent_llm_config.py -q`
- [x] `pytest bot_psychologist/tests/test_admin_multiagent.py -q`
- [x] `pytest bot_psychologist/tests/multiagent/test_writer_agent.py -q`
- [x] `pytest bot_psychologist/tests/multiagent/test_state_analyzer.py -q`

## 3) Acceptance checks
- [x] GET `/api/admin/agents/llm-config` возвращает 3 агента + allowed_models
- [x] PATCH `/api/admin/agents/{agent_id}/llm-config` валидирует модель/агента
- [x] POST `/api/admin/agents/{agent_id}/llm-config/reset` сбрасывает override
- [x] В AgentsTab есть секция «Модели агентов» с выбором и сбросом
- [x] Writer/State Analyzer используют модель из `agent_llm_config`

## 4) Notes
- Актуальные пути фронтенда отличаются от PRD: используется `web_ui/src/hooks`, а не `web-ui/src/admin/hooks`.
- В `thread_manager.py` прямого LLM-вызова нет; для унификации сохраняем per-agent model в инстансе.

