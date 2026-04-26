# NEO Multiagent System — Epoch 4

## Пайплайн

User Message → State Analyzer → Thread Manager → Memory+Retrieval → Writer → Validator → Answer

## Агенты

| Агент | Файл | Тип | PRD |
|---|---|---|---|
| State Analyzer | agents/state_analyzer.py | hybrid (det + nano LLM) | PRD-018 |
| Thread Manager | agents/thread_manager.py | deterministic | PRD-017 |
| Memory+Retrieval | agents/memory_retrieval.py | deterministic | PRD-019 |
| Writer / NEO | agents/writer_agent.py | LLM (gpt-5-mini) | PRD-020 |
| Validator | agents/validator_agent.py | deterministic | PRD-021 |

## Контракты

| Контракт | Описание |
|---|---|
| StateSnapshot | Результат State Analyzer: нервное состояние, интент, открытость |
| ThreadState | Активная нить разговора: фаза, режим ответа, петли |
| MemoryBundle | Сборка контекста: история, профиль, RAG-чанки |
| WriterContract | Входной контракт для Writer |
| ValidationResult | Результат Validator: заблокирован/чист/quality |

## Включение

Feature flag: `MULTIAGENT_ENABLED=True` в `.env` или через FeatureFlags.

## Тесты

`pytest bot_psychologist/tests/multiagent/ -q` → 159+ passed
