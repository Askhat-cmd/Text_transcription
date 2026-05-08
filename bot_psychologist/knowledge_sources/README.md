# Knowledge Sources

Эта папка предназначена для подготовки governed knowledge chunks перед подключением в runtime.

## Структура
- `source_registry.example.yaml` — безопасный пример реестра источников.
- `raw/` — локальные raw markdown материалы (не коммитятся).
- `local/` — локальные промежуточные файлы (не коммитятся).

## Почему raw-файлы не коммитятся
- исходники могут содержать частные/авторские формулировки;
- governance слой должен публиковать только контролируемые preview/metadata;
- PRD-046.0 не включает live-использование raw текстов в ответах пользователю.

## Dry-run запуск
```bash
python bot_psychologist/scripts/prepare_knowledge_base.py \
  --registry bot_psychologist/knowledge_sources/source_registry.example.yaml \
  --dry-run \
  --output TO_DO_LIST/reports/PRD-046.0_governed_chunks_preview.json \
  --markdown-report TO_DO_LIST/reports/PRD-046.0_KB_GOVERNANCE_DRY_RUN_REPORT.md
```

## Что делает dry-run
- читает манифесты источников;
- если raw-файлы отсутствуют, использует synthetic fixtures;
- строит governed chunks и policy metadata;
- формирует preview-отчёты без записи в production DB.
