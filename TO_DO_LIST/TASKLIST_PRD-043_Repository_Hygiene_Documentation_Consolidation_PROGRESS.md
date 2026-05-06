# TASKLIST PRD-043 — Repository Hygiene & Documentation Consolidation

## Scope
- [x] Изучить PRD-043
- [x] Выполнить cleanup временных/generated артефактов
- [x] Консолидировать docs после PRD-041/042
- [x] Добавить inventory guards для hygiene/docs consistency

## Cleanup
- [x] Удалить temp/cache директории (`__pycache__`, `.pytest_cache`, `.tmp_pytest*`, `_tmp_memory_*`)
- [x] Удалить временные db/log/report/snapshot файлы из PRD-043 списка
- [x] Очистить `bot_psychologist/data/threads` от runtime JSON, оставить `.gitkeep`

## Gitignore
- [x] Усилить root `.gitignore`
- [x] Исправить `bot_psychologist/.gitignore` для logs/data/runtime artifacts
- [x] Проверить наличие `.gitkeep` для log/data папок

## Docs
- [x] Создать `docs/archive/legacy_migration/`
- [x] Архивировать migration/audit документы
- [x] Перевести `migration_legacy_to_multiagent.md` в stub + ссылка на archive
- [x] Обновить `README.md` под текущее состояние
- [x] Создать/обновить `docs/README.md` (docs index)
- [x] Проверить и обновить active docs на consistency runtime=multiagent_adapter
- [x] Создать `docs/repository_hygiene_audit_prd043.md`
- [x] Создать `docs/repository_hygiene_review_prd043.md`

## Tests
- [x] Добавить `tests/inventory/test_repository_hygiene_prd043.py`
- [x] Добавить `tests/inventory/test_docs_current_runtime_consistency.py`

## Verification
- [x] `python -m pytest tests/inventory/test_repository_hygiene_prd043.py -q`
- [x] `python -m pytest tests/inventory/test_docs_current_runtime_consistency.py -q`
- [x] `python -m pytest tests/inventory -q`
- [x] `python -m pytest tests/api -q`
- [x] `python -m pytest tests/multiagent -q`
- [x] `python -m pytest tests/test_llm_streaming.py -q`
- [x] `python -m pytest tests/telegram_adapter -q`
- [x] `python -m pytest tests/test_admin_multiagent.py tests/test_admin_agent_llm_config.py tests/test_admin_runtime_contract.py -q`
- [x] `python -m pytest tests/test_feature_flags.py -q`
- [x] `python -m pytest tests/identity tests/conversations tests/registration -q`
- [x] `npm run build` (web_ui)
- [x] Import smoke (`import api.main`, `bot_agent`, `answer_adaptive`, `runtime_adapter`)
- [ ] Manual web chat smoke (не выполнялся в этой итерации)

## Notes
- Не удалять активные тестовые директории и REVIEW-модули.
- Не менять runtime adapter/prompt/model architecture.
- Не активировать Telegram как production канал.
- Для совместимости post-purge статуса обновлен один assert в `tests/test_admin_multiagent.py`:
  - `legacy.cascade_status` теперь допускает `physically_removed`.
