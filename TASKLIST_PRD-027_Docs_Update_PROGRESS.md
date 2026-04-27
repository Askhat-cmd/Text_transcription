# TASKLIST — PRD-027 Docs Update

## Статус
- [x] Прочитать PRD-027 и зафиксировать scope
- [x] Сверить факты по мультиагенту с кодом (`state_analyzer`, `thread_manager`, `orchestrator`, контракты, feature flags)
- [x] Проверить актуальный тестовый статус `tests/multiagent`
- [x] Обновить `bot_psychologist/README.md`
- [x] Добавить `docs/multiagent_architecture.md`
- [x] Добавить `docs/multiagent_contracts.md`
- [x] Добавить `docs/thread_lifecycle.md`
- [x] Добавить `docs/safety_system.md`
- [x] Добавить `docs/migration_legacy_to_multiagent.md`
- [x] Добавить предупреждение в начало `docs/architecture.md`
- [x] Проверить взаимные ссылки между новыми docs
- [x] Финальная проверка diff по PRD-027
- [ ] Commit + push в `main`

## Тесты и проверки
- [x] `.venv\Scripts\python.exe -m pytest tests/multiagent -q` → `190 passed`
- [x] Проверка markdown-структуры новых файлов
- [x] Проверка README на отсутствие устаревшего пункта про PRD-017 в плане

## Примечания
- Факты в документации взяты только из актуального кода.
- В коммит PRD-027 включать только целевые файлы документации.
