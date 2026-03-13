

```
[ ] ЗАДАЧА 1: config.py — добавлены KNOWLEDGE_SOURCE, CHROMA_API_URL, CHROMA_COLLECTION,
              DB_JSON_DIR, DB_EXPORT_FILE; validate() обновлён; info() обновлён
[ ] ЗАДАЧА 2: data_loader.py — Block обновлён (новые поля: author_id, chunk_index, language,
              sd_confidence, source_type, author); _detect_block_type() добавлена;
              load_all_data() диспетчеризирует по source; _load_from_sag_json(),
              _load_from_db_json(), _parse_db_json_file(), _load_from_chromadb() добавлены;
              get_search_text() расширен для книг; get_stats() обновлён
[ ] ЗАДАЧА 3: chroma_loader.py — файл создан; ChromaLoader полностью реализован;
              синглтон chroma_loader экспортирован в конце файла
[ ] ЗАДАЧА 4: retriever.py — CACHE_FORMAT_VERSION → "4.0.0";
              _compute_data_hash() заменён; в начало retrieve() добавлен ChromaDB-блок
              с автоматическим fallback на TF-IDF
[ ] ЗАДАЧА 5: .env — добавлены переменные; KNOWLEDGE_SOURCE=chromadb по умолчанию
[ ] ТЕСТЫ: tests/test_migration_v2.py — файл создан; все 8 блоков тестов присутствуют
[ ] ПРОВЕРКА ИНВАРИАНТОВ (см. раздел 5.2) — выполнить вручную после написания кода
```


***

## 8. ПОРЯДОК РУЧНОЙ ПРОВЕРКИ ПОСЛЕ ВЫПОЛНЕНИЯ

Выполнить последовательно в терминале:

### Шаг 8.1 — Запустить unit-тесты (без сервера)

```bash
cd bot_psychologist
pip install pytest
pytest tests/test_migration_v2.py -v -m "not integration"
```

**Ожидаемый результат:** все тесты зелёные. Если падает — чинить прежде чем идти дальше.

### Шаг 8.2 — Запустить Bot_data_base

```bash
cd ../Bot_data_base
.\.venv\Scripts\activate       # Windows
# или: source .venv/bin/activate  (Linux/Mac)
python -m uvicorn api.main:app --reload --port 8004
```

Убедиться что в логах появилось:

```
INFO: Application startup complete.
```


### Шаг 8.3 — Проверить API вручную

```bash
# Health check
curl http://localhost:8004/api/registry/stats

# Реестр источников
curl http://localhost:8004/api/registry/

# ВАЖНО: проверить наличие /api/query/ и /api/blocks/
curl -X POST http://localhost:8004/api/query/ \
     -H "Content-Type: application/json" \
     -d '{"query": "осознанность", "n_results": 3}'

curl http://localhost:8004/api/blocks/121212__пробная_версия_главы_10
curl http://localhost:8004/api/export/121212__пробная_версия_главы_10
```

По результатам этих запросов заполнить таблицу:


| Эндпоинт | Статус | Структура ответа |
| :-- | :-- | :-- |
| `GET /api/registry/stats` | ✅ 200 | `{"total_sources":1,"total_blocks":25}` |
| `GET /api/registry/` | ✅ 200 | `[{"source_id":"..."}]` |
| `POST /api/query/` | ❓ | — |
| `GET /api/blocks/{id}` | ❓ | — |
| `GET /api/export/{id}` | ❓ | — |

Если `/api/query/` возвращает 404 — `ChromaLoader` автоматически переключится на `TF-IDF` (это нормально, бот продолжит работать). Если `/api/blocks/` и `/api/export/` оба 404 — нужно добавить хотя бы один из них в `Bot_data_base` (см. раздел 9).

### Шаг 8.4 — Запустить integration-тесты

```bash
# В отдельном терминале — Bot_data_base должен быть запущен
pytest tests/test_migration_v2.py -v -m integration -s
```

Обратить особое внимание на вывод:

- `SD Distribution: {...}` — должно совпасть с дашбордом (`YELLOW:7, GREEN:16, ORANGE:1, BLUE:1`)
- `Stats: {...}` — `total_blocks` должно быть `25`


### Шаг 8.5 — Запустить бота целиком

```bash
cd bot_psychologist
python -m bot_agent.main  # или как запускается ваш бот
```

Отправить тестовые запросы:


| Тестовый запрос | Что проверяем |
| :-- | :-- |
| `"Что такое НейроСталкинг?"` | SD-адаптация + блоки из книги |
| `"Дай практику на осознанность"` | `practices_recommender` фильтрует `block_type=practice` |
| `"Расскажи про ментальный суверенитет"` | Поиск по семантике/TF-IDF |
| `"Кто автор книги?"` | `block.author` = "Саламат" присутствует в контексте |


***

## 9. ДЕЙСТВИЯ ПРИ ОТСУТСТВИИ ЭНДПОИНТОВ В `Bot_data_base`

Если `POST /api/query/`, `GET /api/blocks/`, `GET /api/export/` не реализованы, добавить в `Bot_data_base/api/` следующее (это НЕ часть основной задачи агента, выполняется отдельно):

### 9.1 — `GET /api/blocks/{source_id}`

```python
# Bot_data_base/api/routes/blocks.py
from fastapi import APIRouter, HTTPException
from ..services.registry import RegistryService

router = APIRouter()

@router.get("/api/blocks/{source_id}")
async def get_blocks(source_id: str):
    """Вернуть все блоки указанного источника."""
    service = RegistryService()
    blocks = await service.get_blocks_by_source(source_id)
    if not blocks:
        raise HTTPException(
            status_code=404,
            detail=f"Source '{source_id}' not found or has no blocks"
        )
    return {"source_id": source_id, "blocks": blocks, "count": len(blocks)}
```


### 9.2 — `POST /api/query/`

```python
# Bot_data_base/api/routes/query.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..services.chroma_service import ChromaService

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    n_results: int = 5
    sd_level: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None

@router.post("/api/query/")
async def semantic_query(request: QueryRequest):
    """
    Семантический поиск по ChromaDB.
    Возвращает список блоков с cosine similarity score.
    """
    service = ChromaService()
    where_filter = {}
    if request.sd_level:
        where_filter["sd_level"] = request.sd_level
    if request.source_type:
        where_filter["source_type"] = request.source_type
    if request.source_id:
        where_filter["source_id"] = request.source_id

    results = await service.query(
        query_text=request.query,
        n_results=request.n_results,
        where=where_filter if where_filter else None,
    )
    return {"query": request.query, "results": results, "count": len(results)}
```


***

## 10. ДЕРЕВО ЗАВИСИМОСТЕЙ МОДУЛЕЙ

```
bot_agent/main.py
    └── bot_agent/config.py          ← ИЗМЕНЁН (ЗАДАЧА 1)
        └── .env                     ← ИЗМЕНЁН (ЗАДАЧА 5)

bot_agent/retriever.py               ← ИЗМЕНЁН (ЗАДАЧА 4)
    ├── bot_agent/data_loader.py     ← ИЗМЕНЁН (ЗАДАЧА 2)
    │   └── bot_agent/chroma_loader.py  ← СОЗДАН (ЗАДАЧА 3)
    │       └── bot_agent/config.py
    └── bot_agent/config.py

bot_agent/answer_adaptive.py         ← НЕ ТРОГАТЬ
    └── bot_agent/data_loader.Block  ← совместим (новые поля не ломают)

bot_agent/practices_recommender.py   ← НЕ ТРОГАТЬ
    └── Block.is_practice()          ← метод добавлен в ЗАДАЧА 2.1

bot_agent/graph_client.py            ← НЕ ТРОГАТЬ
    └── Block.has_graph_data()       ← метод добавлен в ЗАДАЧА 2.1

bot_agent/answer_sag_aware.py        ← НЕ ТРОГАТЬ
    └── Block.summary                ← никогда не пустой (ЗАДАЧА 2.1 __post_init__)
```


***

## 11. МАТРИЦА РИСКОВ

| Риск | Вероятность | Влияние | Митигация |
| :-- | :-- | :-- | :-- |
| `/api/query/` не реализован | Высокая | Низкое | Авто-fallback на TF-IDF в `ChromaLoader.query_blocks()` |
| `/api/blocks/` и `/api/export/` не реализованы | Средняя | Высокое | Реализовать по разделу 9; fallback через query с source_id |
| `complexity_score` вне диапазона 1–10 | Низкая (если код верен) | Высокое | Тест `test_complexity_0_to_1_normalized_to_1_to_10` |
| `summary` остаётся пустым | Низкая (если `__post_init__` верен) | Среднее | Тест `test_summary_fallback_to_title` |
| Bot_data_base недоступен при старте бота | Средняя | Среднее | `health_check()` логирует WARNING, бот стартует; используется TF-IDF |
| SAG JSON-режим сломан после миграции | Низкая | Высокое | `TestSAGBackwardCompatibility` + `KNOWLEDGE_SOURCE=json` в `.env` |
| TF-IDF кэш устарел (новые книги добавлены) | Средняя | Среднее | `invalidate_cache()` + `CACHE_FORMAT_VERSION="4.0.0"` |


***

## 12. ГЛОССАРИЙ

| Термин | Определение |
| :-- | :-- |
| `SAG v2.0` | Существующий формат JSON-файлов с транскриптами YouTube-лекций |
| `bot_data_base_v1.0` | Новый формат JSON для книг, создаётся сервисом `Bot_data_base` |
| `Block` | Универсальный датакласс — единица знаний в `bot_psychologist` |
| `ChromaDB` | Векторная база данных, используемая `Bot_data_base` |
| `sd_level` | Уровень спиральной динамики блока (`BEIGE`, `PURPLE`, `RED`, `BLUE`, `ORANGE`, `GREEN`, `YELLOW`, `TURQUOISE`) |
| `complexity_score` | Оценка сложности блока **в шкале 1–10** (не 0–1!) |
| `KNOWLEDGE_SOURCE` | Env-переменная: `json` / `db_json` / `chromadb` |
| `TF-IDF fallback` | Резервный поиск по ключевым словам, если ChromaDB недоступен |
| `_detect_block_type()` | Функция авто-классификации: `theory` / `practice` / `case_study` / `quote` |
| `chroma_loader` | Глобальный синглтон `ChromaLoader`, импортируется где нужен |


***

**Конец документа PRD v.2**
*Версия: 2.0 | 12.03.2026 | Готов к исполнению IDE-агентом*

