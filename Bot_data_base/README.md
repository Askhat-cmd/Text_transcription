# Bot_data_base

Минимальный запуск (3 команды):

```bash
cd Bot_data_base
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Запуск сервера:

```bash
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8003
```

Тесты:

```bash
.\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```

Переменные окружения:
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
- `CHUNKING_YOUTUBE_MAX_TOKENS`
- `SD_LABELING_ENABLED`
- `SD_LABELING_MODEL`
- `SD_LABELING_TEMPERATURE`
- `SD_LABELING_MAX_TOKENS`
- `SD_LABELING_MIN_CONFIDENCE`
- `SD_LABELING_BATCH_SIZE`
- `CHROMA_DB_PATH`
- `CHROMA_COLLECTION_NAME`
- `JSON_EXPORT_DIR`
- `REGISTRY_PATH`
- `LOG_LEVEL`
- `LOG_FILE`

Файл `.env` загружается автоматически при старте API и пайплайна. Пример — в `.env.example`.

Примечания:
- Для SD-разметки нужен `OPENAI_API_KEY`.
- Для ускорения тестов и локальной разработки можно отключить эмбеддинги:
  `set BOT_DB_DISABLE_EMBEDDINGS=1`
