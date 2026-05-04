# TASKLIST PRD-034 — Multiagent LLM Runtime Hot-Swap & OpenAI Adapter Fix

## Статус
- [x] Прочитан PRD-034 и зафиксирован scope
- [x] Реализован единый adapter `agent_llm_client.py`
- [x] WriterAgent переведен на adapter и dynamic runtime settings
- [x] StateAnalyzerAgent переведен на adapter и dynamic runtime settings
- [x] Orchestrator trace/metrics дополнены `api_mode` и ошибками агентов
- [x] Добавлены/обновлены тесты по adapter/hot-swap/trace-совместимости
- [x] Прогнаны целевые тесты PRD-034

## Технические задачи
- [x] Добавить `bot_psychologist/bot_agent/multiagent/agents/agent_llm_client.py`
- [x] Поддержать выбор API:
  - [x] `chat.completions` для моделей с `supports_custom_temperature=True`
  - [x] `responses.create` для моделей с `supports_custom_temperature=False`
- [x] Добавить извлечение usage для обоих API-режимов
- [x] Добавить `messages_to_input(...)` для Responses API
- [x] Обеспечить корректный возврат `api_mode` и токенов
- [x] Перевести WriterAgent на `_resolve_model()` + `_resolve_runtime_settings()` без кеша при `__init__`
- [x] Убрать прямой OpenAI вызов из WriterAgent, использовать adapter
- [x] Расширить `writer.last_debug` (model/api_mode/error/fallback_used/usage)
- [x] Перевести StateAnalyzerAgent на `_resolve_model()` без кеша
- [x] Убрать прямые OpenAI вызовы из StateAnalyzerAgent, использовать adapter
- [x] Добавить `state_analyzer.last_debug` (model/api_mode/error/usage)
- [x] В оркестраторе пробрасывать `writer_error/state_analyzer_error` и `writer_api_mode/state_analyzer_api_mode` в trace
- [x] Увеличивать `error_count` метрик при реальной ошибке writer/state
- [x] Не ломать существующий фикс `semantic_hits_detail` для DebugTrace

## Тесты
- [x] `python -m pytest tests/multiagent/test_agent_llm_client.py -q` (6 passed)
- [x] `python -m pytest tests/multiagent/test_agent_hot_swap.py -q` (2 passed)
- [x] `python -m pytest tests/multiagent/test_writer_agent.py -q` (14 passed)
- [x] `python -m pytest tests/multiagent/test_state_analyzer.py -q` (9 passed)
- [x] `python -m pytest tests/multiagent/test_orchestrator_e2e.py -q` (15 passed)
- [x] `python -m pytest tests/multiagent/test_safety_detection.py -q` (10 passed)
- [x] `python -m pytest tests/multiagent -q` (176 passed)
- [x] `python -m pytest tests/api -q` (26 passed)
- [x] `python -m pytest tests/test_admin_agent_llm_config.py -q` (12 passed)
- [x] `python -m pytest tests/test_admin_multiagent.py -q` (12 passed)

## Результат
- [x] Hot-swap моделей/параметров применяется на следующем запросе без рестарта.
- [x] Для `gpt-5*` adapter использует `responses.create` без неподдерживаемых параметров.
- [x] Для моделей с поддержкой температуры adapter использует `chat.completions.create`.
- [x] Trace/metrics оркестратора содержат `api_mode` и реальные ошибки writer/state_analyzer.

## Проверки DoD
- [ ] Writer: `gpt-5-mini` => `responses`
- [ ] Writer: `gpt-4o-mini` => `chat_completions`
- [ ] State Analyzer: `gpt-5-nano` => `responses`
- [ ] State Analyzer: `gpt-4o-mini` => `chat_completions`
- [ ] Hot-swap модели применяется на следующий запрос без рестарта
- [ ] Trace содержит `model/api_mode/error`
- [ ] Ошибки не скрываются полностью fallback-ответом
- [ ] DebugTrace не падает на `semantic_hits_detail`
