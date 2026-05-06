# TASKLIST PRD-043.1 — Encoding Hygiene Guard

## Scope
- [x] Исправить mojibake в root `.gitignore` (комментарии)
- [x] Проверить `bot_psychologist/.gitignore` и active docs на mojibake
- [x] Исправить обнаруженный mojibake в active API-файлах
- [x] Добавить inventory guard `test_no_mojibake_in_active_text_files.py`
- [x] Исключить `docs/archive` из guard (проверяются только `docs/*.md`)

## Additional fixes
- [x] Перекодировать `web_ui/src/components/debug/AnomalyList.tsx` из CP1251 в UTF-8

## Verification
- [x] `python -m pytest tests/inventory/test_no_mojibake_in_active_text_files.py -q`
- [x] `python -m pytest tests/inventory -q`
- [x] `python -m pytest tests/api -q`
