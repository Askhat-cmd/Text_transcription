# PRD TASKS v5.2 — LLM Payload Debug + Curious Mode Prompt

## 0) Подготовка
- [x] Прочитать `PRD v5.2 — LLM Payload Debug + Curious Mode Prompt.md`
- [x] Зафиксировать план работ

## 1) LLM Payload (Task 1)
- [x] Проверить текущий путь формирования `llm_calls` в `bot_psychologist/bot_agent/llm_answerer.py`
- [x] Добавить сохранение prompt-blob внутри `LLMAnswerer` с graceful fallback
- [x] Гарантировать заполнение `system_prompt_preview` / `user_prompt_preview` / `blob_error`
- [x] Обновить `answer_adaptive.py`, чтобы trace стабильно получал `llm_calls`
- [x] Обновить `answer_graph_powered.py`, чтобы trace/path payload работали в graph-ветке

## 2) Curious Mode Prompt (Task 2)
- [x] Создать `bot_psychologist/bot_agent/prompt_mode_informational.md`
- [x] Добавить `prompt_mode_informational` в editable prompts (`runtime_config.py`)
- [x] Добавить `MODE_PROMPT_MAP` и `resolve_mode_prompt()` в `answer_adaptive.py`
- [x] Встроить mode-override (для `curious`) в сборку финального системного промпта
- [x] Добавить в trace поля `informational_mode`, `user_state`, `applied_mode_prompt`

## 3) Проверка
- [x] Прогнать целевые unit/api тесты по debug/payload/prompt path
- [x] Проверить отсутствие регрессий в существующих тестах по retrieval/response/adaptive

## 4) Отчет
- [x] Обновить этот task-файл по фактическому статусу
