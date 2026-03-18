# PRD v2.0: Бот-Психолог — Завершение Миграции и Полная Реализация

**Версия:** 2.0
**Дата:** 18 марта 2026
**Статус:** Готов к реализации агентом IDE
**Репозиторий:** `Askhat-cmd/Text_transcription`
**Затрагиваемые подпроекты:** `bot_psychologist/` · `Bot_data_base/`

***

## 1. Контекст и цель документа

Данный PRD написан для **агента IDE (Cursor/Claude)** и полностью заменяет предыдущую версию PRD. Он описывает завершение незакрытого шага миграции и финальную доводку системы до 100% работоспособности согласно заложенным возможностям.

### 1.1 Текущее состояние системы

```
[Telegram Bot] ──► [bot_psychologist/bot_agent/] ──► РАЗРЫВ ──► [Bot_data_base/ HTTP API] ──► [ChromaDB]
                         ↓                                              ↓
                  (работает: TF-IDF,                          (работает: ingest, registry,
                   SD-фильтры, память,                         status, но НЕТ /api/query/)
                   graph_client, prompts)
```

**Корень проблемы:** `Bot_data_base/api/routes/` содержит только `youtube.py`, `books.py`, `registry.py`, `status.py` . Файл `query.py` с эндпоинтом `POST /api/query/` **не существует**. `bot_agent/retriever.py` и `chroma_loader.py` не имеют HTTP-клиента к `Bot_data_base`  — они либо обращаются к ChromaDB напрямую (устаревшая схема), либо работают только через TF-IDF fallback.

### 1.2 Что уже реализовано и трогать нельзя

| Компонент | Файл | Статус |
| :-- | :-- | :-- |
| TF-IDF индекс | `chroma_loader.py` | ✅ Работает |
| SD-классификатор пользователя | `sd_classifier.py` | ✅ Работает |
| SD-промпты (5 уровней) | `prompt_sd_*.md` | ✅ Работают |
| Граф концептов | `graph_client.py` | ✅ Работает |
| Память диалога | `conversation_memory.py`, `semantic_memory.py` | ✅ Работают |
| Построитель маршрутов | `path_builder.py` | ✅ Работает |
| Recommender практик | `practices_recommender.py` | ✅ Работает |
| State classifier | `state_classifier.py` | ✅ Работает |
| Ingest pipeline | `Bot_data_base/` | ✅ Работает |
| Voyage Rerank ключ | `.env` | ✅ Прописан, не подключён |

### 1.3 Что нужно реализовать (scope этого PRD)

1. **`POST /api/query/`** в `Bot_data_base` — семантический поиск по ChromaDB с SD-фильтром
2. **HTTP-клиент** в `bot_psychologist/bot_agent/` для вызова нового эндпоинта
3. **Voyage Rerank** — подключить в pipeline поиска
4. **Интеграция мульти-авторности** — фильтрация/смешивание по `author_id`
5. **Тесты** — покрыть всю новую и критическую существующую логику

***

## 2. Архитектура системы (целевое состояние)

```
[Telegram User]
      │
      ▼
[bot_psychologist/api/]          ← FastAPI бота (уже работает)
      │
      ▼
[bot_agent/retriever.py]         ← ИЗМЕНИТЬ: добавить режим HTTP-клиента
      │
      ├─► [TF-IDF fallback]      ← остаётся как резерв
      │
      └─► HTTP POST /api/query/  ─────────────────────────────────────────►
                                                                           │
                                                              [Bot_data_base/api/routes/query.py]  ← СОЗДАТЬ
                                                                           │
                                                              [Bot_data_base/storage/chroma_client.py]
                                                                           │
                                                              [ChromaDB collection: all_blocks]
                                                                           │
                                                              [Voyage Rerank API]  ← ПОДКЛЮЧИТЬ
                                                                           │
                                                              ◄────────────── ranked chunks
```

**Правило**: `bot_agent` **никогда** не обращается к ChromaDB напрямую. Только через HTTP к `Bot_data_base`.

***

## 3. Задача 1: `POST /api/query/` в Bot_data_base

### 3.1 Создать файл `Bot_data_base/api/routes/query.py`

**Полная спецификация эндпоинта:**

```python
# Bot_data_base/api/routes/query.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

router = APIRouter()

# ─── Request Schema ───────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000,
                       description="Текст запроса от пользователя")
    sd_level: int = Field(default=0, ge=0, le=8,
                          description="Уровень СД пользователя (0 = без фильтра, 1-8 = конкретный уровень)")
    top_k: int = Field(default=5, ge=1, le=50,
                       description="Количество итоговых чанков после rerank")
    pre_filter_k: int = Field(default=20, ge=5, le=100,
                              description="Количество кандидатов до rerank")
    author_id: Optional[str] = Field(default=None,
                                     description="Фильтр по конкретному автору (author_id из registry)")
    use_rerank: bool = Field(default=True,
                             description="Использовать Voyage Rerank (если False — вернуть raw ChromaDB результаты)")
    search_mode: Literal["semantic", "hybrid"] = Field(
        default="hybrid",
        description="semantic = только вектор, hybrid = вектор + TF-IDF с merge"
    )

# ─── Response Schema ──────────────────────────────────────────────────────────

class ChunkResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    sd_level: int
    author_id: str
    author_name: str
    source_type: Literal["youtube", "book"]
    youtube_url: Optional[str]          # с таймкодом, если youtube
    start_time: Optional[int]           # секунды
    end_time: Optional[int]
    block_title: Optional[str]
    keywords: List[str]

class QueryResponse(BaseModel):
    chunks: List[ChunkResult]
    total_found: int
    reranked: bool
    search_mode: str
    sd_filter_applied: bool
    query_time_ms: int
    debug: Optional[dict] = None        # только если LOG_LEVEL=DEBUG

# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=QueryResponse)
async def semantic_query(request: QueryRequest) -> QueryResponse:
    """
    Семантический поиск по ChromaDB с SD-фильтром и Voyage Rerank.
    Основной эндпоинт для bot_psychologist.
    """
    ...
```


### 3.2 Логика обработки запроса (пошагово)

Агент должен реализовать следующую последовательность **строго в этом порядке**:

**Шаг 1 — Формирование where-фильтра для ChromaDB:**

```python
where_filter = {}
if request.sd_level > 0:
    # Включаем запрошенный уровень и смежные (±1) для мягкого фильтра
    allowed_levels = [request.sd_level - 1, request.sd_level, request.sd_level + 1]
    allowed_levels = [l for l in allowed_levels if 1 <= l <= 8]
    where_filter["sd_level"] = {"$in": allowed_levels}

if request.author_id:
    where_filter["author_id"] = {"$eq": request.author_id}
```

**Шаг 2 — Поиск в ChromaDB (top pre_filter_k кандидатов):**

```python
results = chroma_collection.query(
    query_texts=[request.query],
    n_results=request.pre_filter_k,
    where=where_filter if where_filter else None,
    include=["documents", "metadatas", "distances"]
)
```

**Шаг 3 — Если `search_mode == "hybrid"`: дополнить результаты TF-IDF:**

```python
# Запустить TF-IDF поиск параллельно, взять top pre_filter_k
# Объединить с ChromaDB результатами по chunk_id (deduplicate)
# Пересчитать score: score = 0.7 * semantic_score + 0.3 * tfidf_score
```

**Шаг 4 — Если `use_rerank == True`: Voyage Rerank:**

```python
import voyageai
client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
reranking = client.rerank(
    query=request.query,
    documents=[chunk["content"] for chunk in candidates],
    model="rerank-2",
    top_k=request.top_k
)
# Пересобрать список чанков в новом порядке reranking.results
```

**Шаг 5 — Если `use_rerank == False`:** взять top `request.top_k` из кандидатов по score.

**Шаг 6 — Сформировать `QueryResponse` и вернуть.**

### 3.3 Обработка ошибок

| Ситуация | Поведение |
| :-- | :-- |
| ChromaDB недоступна | `raise HTTPException(status_code=503, detail="ChromaDB unavailable")` |
| Voyage API недоступен | Логировать WARNING, продолжить без rerank (`reranked=False`) |
| Коллекция пуста / 0 результатов | Вернуть `QueryResponse(chunks=[], total_found=0, ...)` — не ошибка |
| `sd_level` задан, но нет чанков этого уровня | Повторить запрос без SD-фильтра, установить флаг `sd_filter_applied=False` |

### 3.4 Зарегистрировать роутер в `main.py`

```python
# В Bot_data_base/api/main.py добавить:
from api.routes.query import router as query_router
app.include_router(query_router, prefix="/api/query", tags=["query"])
```


### 3.5 Добавить схемы в `schemas.py`

Перенести `QueryRequest`, `QueryResponse`, `ChunkResult` в `Bot_data_base/api/schemas.py` для единообразия.

***

## 4. Задача 2: HTTP-клиент в bot_agent

### 4.1 Создать `bot_psychologist/bot_agent/db_api_client.py`

```python
# bot_psychologist/bot_agent/db_api_client.py
"""
HTTP-клиент для обращения к Bot_data_base /api/query/.
Единственная точка взаимодействия bot_agent с базой данных.
"""

import httpx
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

BOT_DB_URL = os.getenv("BOT_DB_URL", "http://localhost:8001")
QUERY_TIMEOUT = float(os.getenv("BOT_DB_TIMEOUT", "10.0"))

@dataclass
class RetrievedChunk:
    chunk_id: str
    content: str
    score: float
    sd_level: int
    author_id: str
    author_name: str
    source_type: str
    youtube_url: Optional[str]
    start_time: Optional[int]
    end_time: Optional[int]
    block_title: Optional[str]
    keywords: List[str]

class DBApiClient:
    """
    Синхронный и асинхронный клиент к Bot_data_base API.
    При недоступности сервиса бросает DBApiUnavailableError.
    """

    def __init__(self, base_url: str = BOT_DB_URL, timeout: float = QUERY_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout

    def query(
        self,
        query: str,
        sd_level: int = 0,
        top_k: int = 5,
        author_id: Optional[str] = None,
        use_rerank: bool = True,
        search_mode: str = "hybrid"
    ) -> List[RetrievedChunk]:
        """Синхронный вызов. Возвращает список чанков или бросает исключение."""
        payload = {
            "query": query,
            "sd_level": sd_level,
            "top_k": top_k,
            "author_id": author_id,
            "use_rerank": use_rerank,
            "search_mode": search_mode
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}/api/query/", json=payload)
                response.raise_for_status()
                data = response.json()
                return [RetrievedChunk(**c) for c in data["chunks"]]
        except httpx.ConnectError:
            raise DBApiUnavailableError(f"Bot_data_base недоступен: {self.base_url}")
        except httpx.TimeoutException:
            raise DBApiUnavailableError(f"Таймаут запроса к Bot_data_base ({self.timeout}s)")

    async def aquery(self, **kwargs) -> List[RetrievedChunk]:
        """Асинхронная версия для FastAPI handlers."""
        ...  # реализация через httpx.AsyncClient

class DBApiUnavailableError(RuntimeError):
    pass
```


### 4.2 Изменить `bot_agent/retriever.py`

Добавить режим `"api"` в существующий `Retriever`. Логика выбора режима:

```python
class Retriever:
    def __init__(self, config):
        self.config = config
        self.db_client = DBApiClient()
        self.tfidf_engine = ...  # существующий TF-IDF

    def retrieve(self, query: str, sd_level: int = 0, top_k: int = 5,
                 author_id: str = None) -> List[RetrievedChunk]:
        """
        Стратегия выбора метода (cascading fallback):
        1. Попытаться через Bot_data_base HTTP API (semantic + rerank)
        2. При DBApiUnavailableError → WARNING лог → fallback на TF-IDF
        3. При полном провале TF-IDF → вернуть [] и залогировать ERROR
        """
        try:
            chunks = self.db_client.query(
                query=query,
                sd_level=sd_level,
                top_k=top_k,
                author_id=author_id,
                use_rerank=True,
                search_mode="hybrid"
            )
            if chunks:
                return chunks
            # Если 0 результатов с SD-фильтром — повторить без него
            if sd_level > 0:
                return self.db_client.query(query=query, sd_level=0, top_k=top_k)
            return []
        except DBApiUnavailableError as e:
            logger.warning(f"[Retriever] API недоступен, переключение на TF-IDF: {e}")
            return self._tfidf_fallback(query, top_k)

    def _tfidf_fallback(self, query: str, top_k: int) -> List[RetrievedChunk]:
        # существующая TF-IDF логика, обернуть результаты в RetrievedChunk
        ...
```


### 4.3 Переменные окружения

Добавить в `bot_psychologist/.env.example`:

```
# URL сервиса Bot_data_base
BOT_DB_URL=http://localhost:8001
BOT_DB_TIMEOUT=10.0
```


***

## 5. Задача 3: Подключение Voyage Rerank

Voyage Rerank уже имеет ключ в `.env`. Нужно создать обёртку в `Bot_data_base`:

### 5.1 Создать `Bot_data_base/utils/reranker.py`

```python
# Bot_data_base/utils/reranker.py

import os
import logging
from typing import List, Optional
import voyageai

logger = logging.getLogger(__name__)

class VoyageReranker:
    """
    Обёртка над Voyage AI rerank API.
    При недоступности API возвращает исходный порядок (graceful degradation).
    """
    MODEL = "rerank-2"

    def __init__(self):
        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            logger.warning("VOYAGE_API_KEY не задан, rerank отключён")
            self._client = None
        else:
            self._client = voyageai.Client(api_key=api_key)

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int,
        metadata: Optional[List[dict]] = None
    ) -> List[int]:
        """
        Возвращает список индексов documents в порядке убывания релевантности.
        При ошибке возвращает [0, 1, 2, ...top_k] (исходный порядок).
        """
        if not self._client or not documents:
            return list(range(min(top_k, len(documents))))

        try:
            result = self._client.rerank(
                query=query,
                documents=documents,
                model=self.MODEL,
                top_k=top_k
            )
            return [r.index for r in result.results]
        except Exception as e:
            logger.warning(f"[VoyageReranker] Ошибка API, используем исходный порядок: {e}")
            return list(range(min(top_k, len(documents))))
```


***

## 6. Задача 4: SD-фильтр как первоклассный компонент (интеграция)

SD-классификатор пользователя существует в `sd_classifier.py` . Нужно обеспечить сквозную передачу SD-уровня от Telegram-хэндлера до ChromaDB-запроса.

### 6.1 Схема передачи SD-уровня

```
[Telegram message]
       │
[bot_agent SD-классификатор]
       │ sd_level: int (1-8)
       │
[retriever.retrieve(query, sd_level=sd_level)]
       │
[DBApiClient.query(sd_level=sd_level)]
       │
[POST /api/query/ {sd_level: N}]
       │
[ChromaDB where: {sd_level: {$in: [N-1, N, N+1]}}]
```


### 6.2 Логика мягкого фильтра SD

Мягкий фильтр (уровень ±1) применяется всегда при `sd_level > 0`. Это обеспечивает связность ответов — пользователь уровня 4 (Green) видит материалы уровней 3, 4, 5.

**Если после мягкого фильтра найдено < 2 чанков** → повторить запрос **без фильтра**, добавить в ответ флаг `sd_filter_applied: false` и логировать. Это важно для новых пользователей с незаполненной БД конкретного уровня.

***

## 7. Задача 5: Мульти-авторность

`Bot_data_base` поддерживает нескольких авторов (у каждого чанка есть `author_id`). Для `bot_agent` нужно дать возможность:

- Поиска **по конкретному автору** (если пользователь явно спрашивает "что говорит Сарсенов о...")
- Поиска **по всем авторам** (по умолчанию)
- **Блендинга**: получить top-3 от каждого автора, смешать


### 7.1 Добавить в `bot_agent/config.py`

```python
# Стратегия мульти-авторного поиска
AUTHOR_BLEND_MODE: Literal["all", "single", "blend"] = "all"
# "all"    — поиск по всей БД без фильтра по автору
# "single" — фильтр по конкретному author_id (определяется из запроса)
# "blend"  — параллельный запрос к каждому автору, merge top-K
```


### 7.2 Детектор автора в запросе

Реализовать простую функцию `detect_author_intent(query: str, known_authors: List[str]) -> Optional[str]` в `bot_agent/semantic_analyzer.py`. Она использует LLM с коротким промптом для определения, упоминает ли пользователь конкретного автора.

***

## 8. Структура файлов (итоговая)

### Новые файлы для создания:

```
Bot_data_base/
└── api/
│   └── routes/
│       └── query.py                ← СОЗДАТЬ (Задача 1)
└── utils/
    └── reranker.py                 ← СОЗДАТЬ (Задача 3)

bot_psychologist/
└── bot_agent/
│   └── db_api_client.py            ← СОЗДАТЬ (Задача 2)
└── tests/
    ├── test_query_endpoint.py      ← СОЗДАТЬ (Раздел 9)
    ├── test_db_api_client.py       ← СОЗДАТЬ (Раздел 9)
    ├── test_retriever_fallback.py  ← СОЗДАТЬ (Раздел 9)
    ├── test_sd_filter.py           ← СОЗДАТЬ (Раздел 9)
    └── test_voyage_reranker.py     ← СОЗДАТЬ (Раздел 9)
```


### Файлы для изменения:

```
Bot_data_base/api/main.py           ← добавить query_router
Bot_data_base/api/schemas.py        ← добавить QueryRequest, QueryResponse, ChunkResult
bot_psychologist/bot_agent/retriever.py  ← добавить HTTP-режим + cascading fallback
bot_psychologist/bot_agent/config.py     ← добавить BOT_DB_URL, AUTHOR_BLEND_MODE
bot_psychologist/.env.example           ← добавить BOT_DB_URL, BOT_DB_TIMEOUT
```


***

## 9. Тесты (полный план)

### 9.1 `Bot_data_base/tests/test_query_endpoint.py`

```python
"""
Интеграционные тесты POST /api/query/
Используют TestClient FastAPI + мок ChromaDB
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.main import app

client = TestClient(app)

MOCK_CHUNKS = [
    {
        "chunk_id": "chunk_001",
        "content": "Осознанность — это способность наблюдать за своими мыслями",
        "sd_level": 4,
        "author_id": "sarsekanov",
        "author_name": "Сарсенов Саламат",
        "source_type": "youtube",
        "youtube_url": "https://youtube.com/watch?v=xxx&t=120",
        "start_time": 120,
        "end_time": 180,
        "block_title": "Введение в осознанность",
        "keywords": ["осознанность", "наблюдение", "мысли"]
    }
]

class TestQueryEndpointBasic:
    def test_returns_200_on_valid_request(self):
        with patch("api.routes.query.chroma_collection") as mock_chroma:
            mock_chroma.query.return_value = {"documents": [...], "metadatas": [...], "distances": [...]}
            response = client.post("/api/query/", json={"query": "что такое осознанность"})
        assert response.status_code == 200

    def test_response_schema_valid(self):
        """Проверяет, что ответ содержит все обязательные поля"""
        response = client.post("/api/query/", json={"query": "осознанность", "top_k": 3})
        data = response.json()
        assert "chunks" in data
        assert "total_found" in data
        assert "reranked" in data
        assert "search_mode" in data
        assert "query_time_ms" in data

    def test_empty_query_returns_422(self):
        response = client.post("/api/query/", json={"query": ""})
        assert response.status_code == 422

    def test_top_k_respected(self):
        response = client.post("/api/query/", json={"query": "практики", "top_k": 3})
        data = response.json()
        assert len(data["chunks"]) <= 3

    def test_returns_chunks_structure(self):
        response = client.post("/api/query/", json={"query": "осознанность"})
        if response.json()["chunks"]:
            chunk = response.json()["chunks"][0]
            assert "chunk_id" in chunk
            assert "content" in chunk
            assert "score" in chunk
            assert "sd_level" in chunk
            assert "author_id" in chunk

class TestQueryEndpointSDFilter:
    def test_sd_level_0_returns_all_levels(self):
        """sd_level=0 означает без фильтра"""
        response = client.post("/api/query/", json={"query": "практики", "sd_level": 0})
        assert response.json()["sd_filter_applied"] == False

    def test_sd_level_4_applies_filter(self):
        response = client.post("/api/query/", json={"query": "практики", "sd_level": 4})
        # Все возвращённые чанки должны быть уровня 3, 4 или 5
        for chunk in response.json()["chunks"]:
            assert chunk["sd_level"] in [3, 4, 5], \
                f"Чанк уровня {chunk['sd_level']} не должен быть в результате для sd_level=4"

    def test_fallback_when_no_sd_chunks(self):
        """Если нет чанков нужного SD-уровня — возвращает результаты без фильтра"""
        response = client.post("/api/query/", json={"query": "редкий запрос xyz", "sd_level": 8})
        # Не должно быть ошибки, sd_filter_applied может стать False
        assert response.status_code == 200

class TestQueryEndpointAuthorFilter:
    def test_author_filter_applied(self):
        response = client.post("/api/query/", json={
            "query": "осознанность",
            "author_id": "sarsekanov"
        })
        for chunk in response.json()["chunks"]:
            assert chunk["author_id"] == "sarsekanov"

    def test_unknown_author_returns_empty(self):
        response = client.post("/api/query/", json={
            "query": "осознанность",
            "author_id": "nonexistent_author_xyz"
        })
        assert response.status_code == 200
        assert response.json()["total_found"] == 0

class TestQueryEndpointRerank:
    def test_use_rerank_false_skips_voyage(self):
        with patch("api.routes.query.VoyageReranker.rerank") as mock_rerank:
            client.post("/api/query/", json={"query": "тест", "use_rerank": False})
            mock_rerank.assert_not_called()

    def test_voyage_failure_graceful_degradation(self):
        """При ошибке Voyage API — возвращает результаты без rerank"""
        with patch("utils.reranker.voyageai.Client") as mock_voyage:
            mock_voyage.return_value.rerank.side_effect = Exception("API Error")
            response = client.post("/api/query/", json={"query": "практики", "use_rerank": True})
        assert response.status_code == 200
        assert response.json()["reranked"] == False
```


### 9.2 `bot_psychologist/tests/test_db_api_client.py`

```python
"""
Юнит-тесты HTTP-клиента DBApiClient
"""
import pytest
import httpx
from unittest.mock import patch, MagicMock
from bot_agent.db_api_client import DBApiClient, DBApiUnavailableError, RetrievedChunk

MOCK_RESPONSE = {
    "chunks": [{
        "chunk_id": "c1", "content": "тест", "score": 0.9,
        "sd_level": 3, "author_id": "auth1", "author_name": "Автор",
        "source_type": "youtube", "youtube_url": None,
        "start_time": None, "end_time": None,
        "block_title": "Блок 1", "keywords": ["тест"]
    }],
    "total_found": 1, "reranked": True,
    "search_mode": "hybrid", "sd_filter_applied": True, "query_time_ms": 45
}

class TestDBApiClient:
    def test_successful_query_returns_chunks(self):
        with patch("httpx.Client") as mock_http:
            mock_http.return_value.__enter__.return_value.post.return_value = MagicMock(
                status_code=200, json=lambda: MOCK_RESPONSE
            )
            client = DBApiClient()
            result = client.query("осознанность", sd_level=3)
        assert len(result) == 1
        assert isinstance(result[0], RetrievedChunk)
        assert result[0].chunk_id == "c1"

    def test_connect_error_raises_unavailable(self):
        with patch("httpx.Client") as mock_http:
            mock_http.return_value.__enter__.return_value.post.side_effect = \
                httpx.ConnectError("Connection refused")
            client = DBApiClient()
            with pytest.raises(DBApiUnavailableError):
                client.query("тест")

    def test_timeout_raises_unavailable(self):
        with patch("httpx.Client") as mock_http:
            mock_http.return_value.__enter__.return_value.post.side_effect = \
                httpx.TimeoutException("Timeout")
            client = DBApiClient()
            with pytest.raises(DBApiUnavailableError):
                client.query("тест")

    def test_sd_level_passed_in_payload(self):
        with patch("httpx.Client") as mock_http:
            mock_post = MagicMock(status_code=200, json=lambda: MOCK_RESPONSE)
            mock_http.return_value.__enter__.return_value.post.return_value = mock_post
            client = DBApiClient()
            client.query("тест", sd_level=5)
            call_kwargs = mock_http.return_value.__enter__.return_value.post.call_args
            payload = call_kwargs[1]["json"]
            assert payload["sd_level"] == 5
```


### 9.3 `bot_psychologist/tests/test_retriever_fallback.py`

```python
"""
Тесты cascading fallback: API → TF-IDF
"""
import pytest
from unittest.mock import patch, MagicMock
from bot_agent.retriever import Retriever
from bot_agent.db_api_client import DBApiUnavailableError

class TestRetrieverFallback:
    def test_uses_api_when_available(self):
        with patch("bot_agent.db_api_client.DBApiClient.query") as mock_api:
            mock_api.return_value = [MagicMock()]
            retriever = Retriever(config={})
            result = retriever.retrieve("осознанность", sd_level=3)
        mock_api.assert_called_once()
        assert len(result) == 1

    def test_falls_back_to_tfidf_when_api_down(self):
        with patch("bot_agent.db_api_client.DBApiClient.query",
                   side_effect=DBApiUnavailableError("down")):
            with patch.object(Retriever, "_tfidf_fallback", return_value=[MagicMock()]) as mock_tfidf:
                retriever = Retriever(config={})
                result = retriever.retrieve("осознанность")
        mock_tfidf.assert_called_once()
        assert len(result) == 1

    def test_retries_without_sd_when_zero_results(self):
        """Если API вернул [], а sd_level > 0 — повторить без фильтра"""
        call_count = 0
        def mock_query(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("sd_level", 0) > 0:
                return []
            return [MagicMock()]

        with patch("bot_agent.db_api_client.DBApiClient.query", side_effect=mock_query):
            retriever = Retriever(config={})
            result = retriever.retrieve("практики", sd_level=7)
        assert call_count == 2
        assert len(result) == 1
```


### 9.4 `bot_psychologist/tests/test_sd_filter.py`

```python
"""
Тесты сквозного прохождения SD-уровня от классификатора до запроса
"""
import pytest
from unittest.mock import patch, MagicMock

class TestSDFilterPipeline:
    def test_sd_level_from_classifier_passed_to_retriever(self):
        """SD-уровень из sd_classifier должен попадать в retrieve()"""
        with patch("bot_agent.sd_classifier.SDClassifier.classify") as mock_clf:
            mock_clf.return_value = MagicMock(level=4)
            with patch("bot_agent.retriever.Retriever.retrieve") as mock_retrieve:
                mock_retrieve.return_value = []
                # Симулируем полный цикл обработки запроса
                from bot_agent.answer_adaptive import answer_adaptive
                answer_adaptive(query="я чувствую тревогу", user_id="u1")
            call_kwargs = mock_retrieve.call_args[1]
            assert call_kwargs.get("sd_level") == 4

    def test_sd_level_1_through_8_all_valid(self):
        """Все уровни 1-8 должны проходить без ошибок"""
        from bot_agent.db_api_client import DBApiClient
        client = DBApiClient()
        for level in range(1, 9):
            payload = {"query": "тест", "sd_level": level, "top_k": 1}
            # Проверяем формирование where_filter без реального вызова
            allowed = [l for l in [level-1, level, level+1] if 1 <= l <= 8]
            assert level in allowed
```


### 9.5 `Bot_data_base/tests/test_voyage_reranker.py`

```python
"""
Тесты VoyageReranker с graceful degradation
"""
import pytest
from unittest.mock import patch, MagicMock
from utils.reranker import VoyageReranker

DOCS = ["документ первый", "документ второй", "документ третий"]

class TestVoyageReranker:
    def test_returns_indices_list(self):
        with patch("voyageai.Client") as mock_client:
            mock_client.return_value.rerank.return_value = MagicMock(
                results=[MagicMock(index=2), MagicMock(index=0), MagicMock(index=1)]
            )
            reranker = VoyageReranker()
            indices = reranker.rerank("запрос", DOCS, top_k=3)
        assert indices == [2, 0, 1]

    def test_no_api_key_returns_original_order(self):
        with patch.dict("os.environ", {"VOYAGE_API_KEY": ""}):
            reranker = VoyageReranker()
            indices = reranker.rerank("запрос", DOCS, top_k=3)
        assert indices == [0, 1, 2]

    def test_api_exception_returns_original_order(self):
        with patch("voyageai.Client") as mock_client:
            mock_client.return_value.rerank.side_effect = Exception("Network error")
            reranker = VoyageReranker()
            indices = reranker.rerank("запрос", DOCS, top_k=2)
        assert indices == [0, 1]

    def test_empty_documents_returns_empty(self):
        reranker = VoyageReranker()
        indices = reranker.rerank("запрос", [], top_k=5)
        assert indices == []
```


***

## 10. Нефункциональные требования

### Безопасность

- Эндпоинт `/api/query/` не требует auth на первом этапе (внутренняя сеть), но должен иметь rate limiting: не более **60 запросов/мин** с одного IP.
- Ответы бота не содержат медицинских диагнозов. При детекции ключевых слов кризисного состояния (`суицид`, `не хочу жить`, `конец`) — обязательный дисклеймер с контактами помощи.


### Производительность

- `POST /api/query/` должен отвечать за **< 2 секунды** при включённом Voyage Rerank.
- ChromaDB инициализируется один раз при старте приложения (`@app.on_event("startup")`), не при каждом запросе.
- Кэшировать список авторов из registry — обновлять раз в 5 минут, не при каждом запросе.


### Логирование

- Каждый запрос к `/api/query/` логировать: `query_time_ms`, `total_found`, `reranked`, `sd_level`, `search_mode`.
- При fallback с SD-фильтра → без фильтра: обязательный `WARNING` с указанием `sd_level` и количества найденных чанков.

***

## 11. Порядок реализации (для агента)

Агент должен выполнять задачи **строго в этом порядке** — каждый шаг разблокирует следующий:

- **Шаг 1** — Создать `Bot_data_base/utils/reranker.py` + тесты `test_voyage_reranker.py`
- **Шаг 2** — Создать `Bot_data_base/api/routes/query.py` + обновить `schemas.py` + тесты `test_query_endpoint.py`
- **Шаг 3** — Зарегистрировать роутер в `Bot_data_base/api/main.py`
- **Шаг 4** — Запустить `Bot_data_base`, убедиться что `GET /docs` показывает `/api/query/`
- **Шаг 5** — Создать `bot_psychologist/bot_agent/db_api_client.py` + тесты `test_db_api_client.py`
- **Шаг 6** — Изменить `bot_agent/retriever.py` для HTTP-режима + тесты `test_retriever_fallback.py`
- **Шаг 7** — Написать `test_sd_filter.py`, убедиться что SD-уровень проходит сквозь всю цепочку
- **Шаг 8** — E2E smoke-тест: реальный запрос от Telegram → ответ с источниками

***

## 12. Definition of Done

Миграция считается **полностью завершённой**, когда выполнены все пункты:

- [ ] `POST /api/query/` отвечает `200 OK` с корректной схемой `QueryResponse`
- [ ] SD-фильтр работает: запрос с `sd_level=4` возвращает только чанки уровней 3, 4, 5
- [ ] Voyage Rerank применяется: `reranked: true` в ответе при `use_rerank=true`
- [ ] Fallback работает: при остановленном `Bot_data_base` бот отвечает через TF-IDF, не падает
- [ ] Фильтр по автору работает: `author_id=X` возвращает только чанки автора X
- [ ] Все 5 тест-файлов проходят без ошибок (`pytest -v`)
- [ ] `bot_agent` нигде не импортирует `chromadb` напрямую (только через `db_api_client`)
- [ ] E2E: вопрос через Telegram-бот возвращает ответ с `youtube_url` и таймкодом

