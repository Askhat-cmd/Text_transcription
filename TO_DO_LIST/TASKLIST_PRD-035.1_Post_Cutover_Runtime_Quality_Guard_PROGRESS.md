# TASKLIST PRD-035.1 — Post-Cutover Runtime Quality & Model Guard

## Статус
- [x] PRD изучен
- [x] Текущие runtime/API/streaming/tests проверены
- [x] Добавлены runtime quality markers в multiagent adapter
- [x] Убран legacy-priority из `_resolve_multiagent_runtime`
- [x] Streaming default answer_fn переведен на multiagent adapter
- [x] Добавлены/обновлены тесты runtime markers и streaming default
- [x] Добавлен post-cutover model guard test
- [x] Добавлена видимость `state_analyzer_fallback_used` в debug/trace
- [x] Прогнаны целевые тесты PRD-035.1

## Задачи
- [x] `bot_psychologist/bot_agent/multiagent/runtime_adapter.py`
  - [x] metadata: `runtime_entrypoint`, `legacy_fallback_used`
  - [x] debug: `runtime_entrypoint`, `legacy_fallback_used`, `direct_multiagent_cutover`
  - [x] adapter log с model/api_mode метриками
- [x] `bot_psychologist/api/routes/chat.py`
  - [x] `_resolve_multiagent_runtime()` без fallback на `routes.answer_question_adaptive`
  - [x] trace-builder расширен полями runtime marker и state analyzer fallback
- [x] `bot_psychologist/bot_agent/llm_streaming.py`
  - [x] `_default_answer_fn()` -> `run_multiagent_adaptive_sync`
- [x] `bot_psychologist/bot_agent/multiagent/orchestrator.py`
  - [x] `state_analyzer_fallback_used` в debug payload

## Тесты
- [x] `bot_psychologist/tests/api/test_multiagent_runtime_cutover.py`
  - [x] runtime markers в metadata/debug(trace)
- [x] `bot_psychologist/tests/test_llm_streaming.py`
  - [x] default stream answer_fn не использует legacy `answer_adaptive`
- [x] `bot_psychologist/tests/multiagent/test_post_cutover_model_guard.py`
  - [x] writer model hot-swap + api_mode guard
- [x] `bot_psychologist/tests/api/test_routes_identity_integration.py`
  - [x] обновлен monkeypatch с `answer_question_adaptive` на `run_multiagent_adaptive_sync`

## Прогон
- [x] `.venv\Scripts\python.exe -m pytest tests/multiagent -q` → `181 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/api -q` → `31 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/test_admin_multiagent.py tests/test_admin_agent_llm_config.py -q` → `25 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/telegram_adapter -q` → `44 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/test_llm_streaming.py -q` → `7 passed`
- [x] `.venv\Scripts\python.exe -m pytest tests/inventory/test_runtime_cutover_no_legacy_entrypoints.py -q` → `4 passed`

## Model Profile For Manual Check
- [x] Рекомендуемый профиль:
  - `state_analyzer = gpt-4o-mini` или `gpt-5-nano`
  - `writer = gpt-5-mini` или `gpt-5`
  - `writer temperature = 0.7`
  - `thread_manager` сейчас heuristic, модель в Admin на ответ не влияет
