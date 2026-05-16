# Bot_data_base

`Bot_data_base` - ingestion/retrieval runtime для KB слоя проекта.
Текущий live режим: локальный API на `:8003`, focus-source only, строгая сверка blocks/Chroma.

## Live Run (ПК_2)
```powershell
cd C:\My_practice\Text_transcription\Bot_data_base
.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --reload --port 8003
```

## Runtime URLs
- `http://localhost:8003/`
- `http://localhost:8003/api/registry/`
- `http://localhost:8003/api/dashboard`
- `http://localhost:8003/api/dashboard/`
- `http://localhost:8003/api/status`

## Environment Baseline
- Python: `3.10` for `Bot_data_base`.
- Focus source: `123__кузница_духа` (`Кузница Духа`, `Саламат Сарсекенов`).
- Expected operational counts:
  - `sources = 1`
  - `blocks = 247`
  - `chroma = 247`
- Strict gate expectation: `247/247/247` for registry blocks, dashboard blocks, dashboard chroma.

## Legacy SD Status
- SD слой находится в `legacy/deprecated` режиме.
- По умолчанию legacy SD labeling отключен.
- SD не является authority слоем runtime/retrieval/readiness.
- `sd_level` / `sd_distribution` в старых артефактах сохраняются как backward-compatible metadata.
- Конфиг-файл хранит default-disabled состояние (`sd_labeling.enabled=false`), а env overrides применяются только в runtime и не должны перезаписывать `config.yaml`.

Legacy SD env vars (deprecated, disabled by default):
- `SD_LABELING_ENABLED=false`
- `SD_LABELING_EXPLICIT_LEGACY_MODE=false`
- `SD_LABELING_MODEL`
- `SD_LABELING_TEMPERATURE`
- `SD_LABELING_MAX_TOKENS`
- `SD_LABELING_MIN_CONFIDENCE`
- `SD_LABELING_BATCH_SIZE`
- `LEGACY_SD_LABELING_ENABLED=false`
- `LEGACY_SD_EXPLICIT_MODE=false`

## Core Env Vars
- `OPENAI_API_KEY`
- `PRIMARY_MODEL`
- `REFINE_MODEL`
- `OPENAI_API_TIMEOUT`
- `OPENAI_API_DELAY`
- `OPENAI_API_MAX_RETRIES`
- `OPENAI_API_RETRY_BACKOFF_BASE`
- `SENTENCE_TRANSFORMERS_MODEL`
- `SENTENCE_TRANSFORMERS_DEVICE`
- `API_HOST`
- `API_PORT`
- `YOUTUBE_API_KEY`
- `BOT_DB_DISABLE_EMBEDDINGS`
- `PIPELINE_SUBTITLES_DIR`
- `PIPELINE_BOOKS_UPLOADS_DIR`
- `PIPELINE_YOUTUBE_OUTPUT_DIR`
- `PIPELINE_BOOKS_OUTPUT_DIR`
- `CHUNKING_BOOK_TARGET_TOKENS`
- `CHUNKING_BOOK_MIN_TOKENS`
- `CHUNKING_BOOK_MAX_TOKENS`
- `CHUNKING_BOOK_OVERLAP_TOKENS`
- `CHUNKING_YOUTUBE_MIN_TOKENS`
- `CHROMA_DB_PATH`
- `CHROMA_COLLECTION_NAME`
- `JSON_EXPORT_DIR`
- `REGISTRY_PATH`
- `LOG_LEVEL`
- `LOG_FILE`

`.env` автоматически загружается при старте API/пайплайна. Шаблон: `.env.example`.

## Internal Docs
- `docs/README.md`
- `docs/ARCHITECTURE.md`
- `docs/RUNBOOK.md`
- `docs/API_CONTRACTS.md`
- `docs/DATA_CONTRACTS.md`
- `docs/CHROMA_RECOVERY.md`
- `docs/SOURCE_HYGIENE.md`
- `docs/LEGACY_SD.md`
- `docs/PROJECT_STATE.md`
