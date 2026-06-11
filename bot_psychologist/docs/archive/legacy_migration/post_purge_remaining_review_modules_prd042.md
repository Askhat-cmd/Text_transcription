# PRD-042 Remaining REVIEW Modules

Цель файла: зафиксировать модули, которые остались после physical purge PRD-041, чтобы исключить слепое удаление.

| Module | Why remains | Current importers/callers | Active or historical | Removable now | Separate PRD required |
|---|---|---|---|---|---|
| `bot_agent/state_classifier.py` | Используется вне удаленного cascade | `bot_agent/diagnostics_classifier.py`, `bot_agent/path_builder.py`, набор unit/integration тестов | Active helper surface | No | Yes |
| `bot_agent/route_resolver.py` | Используется тестами и legacy-compatible routing сценариями | `tests/golden/*`, `tests/integration/*`, `tests/unit/test_route_resolver_rules.py` | Mostly historical + test surface | No | Yes |
| `bot_agent/decision/` | Детерминированный decision слой еще покрывается тестами | `tests/test_decision_gate.py`, `tests/test_decision_table.py`, `tests/test_signal_detector.py` | Historical/supporting | No | Yes |
| `bot_agent/response/` | Используется response/formatting тестами и вспомогательными путями | `tests/test_response_*`, `tests/test_path_builder.py`, regression tests | Historical/supporting | No | Yes |
| `bot_agent/fast_detector.py` | Зависимость `state_classifier` | `bot_agent/state_classifier.py`, routing config tests | Active dependency | No | Yes |
| `bot_agent/user_level_types.py` | Используется `path_builder` и тестами типов | `bot_agent/path_builder.py`, `tests/unit/test_user_level_adapter_removed.py` | Active helper dependency | No | Yes |
| `bot_agent/memory_v12.py` | Активный контракт snapshot memory | `bot_agent/memory_context.py`, `bot_agent/memory_updater.py`, memory contract tests | Active dependency | No | Yes |

## Conclusion (Вывод)
- Эти модули не являются частью active multiagent runtime entrypoint (`multiagent_adapter`), но имеют текущие импортёры.
- Удаление возможно только после отдельного scoped-аудита и отдельного PRD на каждый кластер зависимостей.
