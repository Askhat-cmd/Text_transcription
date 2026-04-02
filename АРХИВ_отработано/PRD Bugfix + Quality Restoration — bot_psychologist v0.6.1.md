# PRD: Bugfix + Quality Restoration — bot_psychologist v0.6.1

**Версия:** 3.0 · **Проект:** `Askhat-cmd/Text_transcription` · **Ветка:** `fix/v0.6.1-stability` · **Дата:** 2026-03-30
**Приоритет:** CRITICAL — бот отвечает без контекста из базы знаний

***

## 1. Контекст

После деплоя v0.6.0 выявлены три критических бага, подтверждённых логами (`bot.log`, `retrieval.log`, `bot_agent.log`). Баги не связаны с новым кодом фаз 2–5, а являются проблемами инициализации и конфигурации. Пользователи получают скупые ответы, так как LLM работает без контекста из базы знаний.

**Корневая причина (из логов 15:51:55–15:52:09):**

```
Bot_data_base :8003 → TIMEOUT при старте
→ DataLoader: "✅ Загружено: 0 документов, 0 блоков [source=api]"
→ Retriever: "no blocks available for indexing"
→ Первый запрос пользователя → 0 блоков в retrieval
→ LLM отвечает без контекста → скупой ответ
```

**Главный инвариант:** `answer_adaptive.py`, `working_state.py`, `path_builder.py`, `conversation_memory.py` — **не трогать**. Все изменения только в слое инициализации, retrieval и конфигурации.

***

## 2. Scope

### В рамках этого PRD (in scope)

- Устранение двойного вызова DataLoader при warmup
- Реализация fallback-цепочки при недоступном Bot_data_base API
- Увеличение `confidence_cap` с 3 до 5 блоков при `level=medium`
- Retry-логика для retriever при временном недоступном API
- Configurable параметры cap через `runtime_config.py`
- Полный набор тестов для каждого бага


### Вне рамок (out of scope)

- Изменение архитектуры retrieval pipeline
- Изменение embedding модели
- Изменение промптов и SD-логики
- Изменение `answer_adaptive.py`

***

## 3. Баг \#1 — Двойной вызов DataLoader при warmup

### 3.1 Описание

При старте сервера `api/main.py` вызывает `DataLoader._load_from_api()` **дважды** с интервалом 2 секунды. Оба вызова уходят в таймаут (10 сек каждый). Итог: старт тратит лишние 26 секунд, база не загружается.

**Доказательство из `bot.log`:**

```
15:51:55 | data_loader | [API] Загрузка всех блоков... ← вызов #1
15:51:57 | data_loader | [API] Загрузка всех блоков... ← вызов #2 (через 2 сек)
15:52:08 | data_loader | ❌ Ошибка: Read timed out (10.0s)
15:52:09 | data_loader | ❌ Ошибка: Read timed out (10.0s)
15:52:09 | data_loader | ✅ Загружено: 0 документов, 0 блоков
```


### 3.2 Требования к исправлению

**Файл:** `bot_agent/data_loader.py`

Добавить singleton-guard в класс `DataLoader`:

```python
class DataLoader:
    _initialized: bool = False
    _blocks: list = []

    def load(self):
        if self._initialized:
            logger.info("✓ Данные уже загружены, используем кэш")
            return self._blocks
        # ... логика загрузки
        self._initialized = True
        return self._blocks
```

**Требования:**

1. Метод `load()` при повторном вызове должен мгновенно возвращать кэш без HTTP-запроса.
2. Добавить в лог при cache_hit: `[DATA_LOADER] cache_hit blocks={len}` — для диагностики.
3. Метод `reload()` (принудительная перезагрузка) должен сбрасывать `_initialized = False` — для admin hot-reload.
4. `_initialized` должен быть thread-safe (использовать `threading.Lock`).

**Файл:** `api/main.py`

Найти все места, где при warmup инициализируется DataLoader/Retriever, и убедиться, что вызов происходит ровно один раз. Если retriever и data_loader инициализируются независимо — убедиться, что они оба используют одну и ту же инстанцию DataLoader (singleton).

### 3.3 Тесты

**Файл:** `tests/test_data_loader_singleton.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from bot_agent.data_loader import DataLoader

class TestDataLoaderSingleton:

    def test_load_called_once_on_double_init(self):
        """При двойном вызове load() HTTP-запрос идёт только один раз"""
        loader = DataLoader()
        with patch.object(loader, '_load_from_api', return_value=[]) as mock_api:
            loader.load()
            loader.load()
            assert mock_api.call_count == 1

    def test_cache_hit_returns_same_data(self):
        """При cache_hit возвращаются те же данные без нового запроса"""
        loader = DataLoader()
        fake_blocks = [{"id": "b1", "text": "test"}]
        with patch.object(loader, '_load_from_api', return_value=fake_blocks):
            result1 = loader.load()
            result2 = loader.load()
            assert result1 is result2  # тот же объект

    def test_reload_forces_refetch(self):
        """reload() сбрасывает кэш и вызывает API снова"""
        loader = DataLoader()
        with patch.object(loader, '_load_from_api', return_value=[]) as mock_api:
            loader.load()
            loader.reload()
            loader.load()
            assert mock_api.call_count == 2

    def test_thread_safety(self):
        """Параллельные вызовы load() не вызывают двойную загрузку"""
        import threading
        loader = DataLoader()
        call_count = []
        def mock_api():
            call_count.append(1)
            return []
        with patch.object(loader, '_load_from_api', side_effect=mock_api):
            threads = [threading.Thread(target=loader.load) for _ in range(10)]
            for t in threads: t.start()
            for t in threads: t.join()
            assert len(call_count) == 1

    def test_warmup_log_contains_single_load(self, caplog):
        """В логах при warmup ровно одна строка '[API] Загрузка'"""
        loader = DataLoader()
        with patch.object(loader, '_load_from_api', return_value=[]):
            loader.load()
            loader.load()
        api_logs = [r for r in caplog.records if '[API] Загрузка' in r.message]
        assert len(api_logs) == 1
```

**Acceptance criteria:**

- Все 5 тестов проходят.
- В логах при старте строка `[API] Загрузка всех блоков` появляется ровно 1 раз.
- Время старта сокращается с ~26 сек до ~13 сек (устранение одного лишнего таймаута).

***

## 4. Баг \#2 — Нет fallback при недоступном Bot_data_base на старте

### 4.1 Описание

При таймауте API на старте бот загружает 0 блоков и не предпринимает никаких действий. Retriever строит пустой TF-IDF индекс. Первый запрос пользователя получает `Initial retrieval: 0 blocks`. LLM отвечает без контекста.

**Доказательство из `retrieval.log`:**

```
15:53:44 | retriever | query='ВОПРОС-ЯКОРЬ: что такое Самоидентификация...' top_k=9
15:54:09 | retriever | API fallback: kind=timeout
15:54:09 | retriever | building TF-IDF index
15:54:09 | retriever | no blocks available for indexing   ← пустой индекс
15:54:09 | retriever | empty index
15:54:09 | answer_adaptive | Initial retrieval: 0 blocks   ← 0 блоков в промпт
```


### 4.2 Требования к исправлению

**Файл:** `bot_agent/data_loader.py` — метод `_load_from_api()`

Реализовать трёхуровневую fallback-цепочку:

```python
def load(self) -> list:
    """
    Уровень 1: API (Bot_data_base :8003)
    Уровень 2: all_blocks_merged.json (локальный файл)
    Уровень 3: DEGRADED_MODE (0 блоков, но без краша)
    """
    # Уровень 1
    try:
        blocks = self._load_from_api()
        if blocks:
            logger.info(f"[DATA_LOADER] source=api blocks={len(blocks)}")
            self._blocks = blocks
            self._initialized = True
            self._source = "api"
            return blocks
    except (ReadTimeout, ConnectionError) as e:
        logger.warning(f"[DATA_LOADER] API unavailable: {e}. Trying fallback.")

    # Уровень 2
    merged_path = config.ALL_BLOCKS_MERGED_PATH
    if merged_path and Path(merged_path).exists():
        try:
            blocks = self._load_from_json(merged_path)
            if blocks:
                logger.warning(f"[DATA_LOADER] source=json_fallback blocks={len(blocks)} path={merged_path}")
                self._blocks = blocks
                self._initialized = True
                self._source = "json_fallback"
                return blocks
        except Exception as e:
            logger.error(f"[DATA_LOADER] JSON fallback failed: {e}")

    # Уровень 3
    logger.critical("[DATA_LOADER] DEGRADED_MODE: no blocks loaded. Bot will answer without context.")
    self._blocks = []
    self._initialized = True
    self._source = "degraded"
    config.DEGRADED_MODE = True
    return []
```

**Файл:** `bot_agent/config.py` или `bot_agent/runtime_config.py`

Добавить:

```python
DEGRADED_MODE: bool = False          # True если база знаний недоступна
DATA_SOURCE: str = "unknown"         # api | json_fallback | degraded
ALL_BLOCKS_MERGED_PATH: str = ""     # путь к резервному JSON
```

**Файл:** `bot_agent/retriever.py` — метод `retrieve()`

При `DEGRADED_MODE=True` добавить в ответ метаданные:

```python
if config.DEGRADED_MODE:
    logger.warning("[RETRIEVER] DEGRADED_MODE active. Retrieval returns 0 blocks.")
    return RetrievalResult(blocks=[], degraded=True, reason="no_data_source")
```

**Файл:** `api/main.py` — health endpoint

Добавить в `/health` (или создать, если нет):

```json
{
  "status": "degraded",
  "data_source": "json_fallback",
  "blocks_loaded": 25,
  "bot_data_base_api": "unavailable"
}
```


### 4.3 Тесты

**Файл:** `tests/test_data_loader_fallback.py`

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json, tempfile
from bot_agent.data_loader import DataLoader
from bot_agent import config

class TestDataLoaderFallback:

    @pytest.fixture
    def fake_merged_json(self, tmp_path):
        data = [{"id": f"b{i}", "text": f"block {i}", "sd_level": "green"}
                for i in range(25)]
        p = tmp_path / "all_blocks_merged.json"
        p.write_text(json.dumps(data))
        return str(p)

    def test_api_success_no_fallback(self):
        """Если API отвечает — fallback не используется"""
        loader = DataLoader()
        fake_blocks = [{"id": "b1", "text": "test"}]
        with patch.object(loader, '_load_from_api', return_value=fake_blocks):
            result = loader.load()
            assert len(result) == 1
            assert loader._source == "api"

    def test_api_timeout_fallback_to_json(self, fake_merged_json):
        """При таймауте API → загрузка из JSON-файла"""
        import requests
        loader = DataLoader()
        config.ALL_BLOCKS_MERGED_PATH = fake_merged_json
        with patch.object(loader, '_load_from_api',
                          side_effect=requests.exceptions.ReadTimeout):
            result = loader.load()
            assert len(result) == 25
            assert loader._source == "json_fallback"

    def test_api_timeout_json_missing_degraded(self):
        """При таймауте API и отсутствии JSON → DEGRADED_MODE"""
        import requests
        loader = DataLoader()
        config.ALL_BLOCKS_MERGED_PATH = "/nonexistent/path.json"
        with patch.object(loader, '_load_from_api',
                          side_effect=requests.exceptions.ReadTimeout):
            result = loader.load()
            assert result == []
            assert config.DEGRADED_MODE is True
            assert loader._source == "degraded"

    def test_degraded_mode_does_not_crash(self):
        """В DEGRADED_MODE retriever возвращает пустой результат без исключения"""
        from bot_agent.retriever import Retriever
        config.DEGRADED_MODE = True
        retriever = Retriever(blocks=[])
        result = retriever.retrieve("тест запрос", top_k=5)
        assert result.blocks == []
        assert result.degraded is True

    def test_json_fallback_loads_correct_count(self, fake_merged_json):
        """JSON fallback загружает ровно столько блоков, сколько в файле"""
        import requests
        loader = DataLoader()
        config.ALL_BLOCKS_MERGED_PATH = fake_merged_json
        with patch.object(loader, '_load_from_api',
                          side_effect=requests.exceptions.ReadTimeout):
            result = loader.load()
            assert len(result) == 25

    def test_health_endpoint_reports_degraded(self, client):
        """GET /health возвращает status=degraded если DEGRADED_MODE=True"""
        config.DEGRADED_MODE = True
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"

    def test_health_endpoint_reports_ok_with_json_fallback(self, fake_merged_json, client):
        """GET /health возвращает status=degraded_fallback с source=json_fallback"""
        import requests
        loader = DataLoader()
        config.ALL_BLOCKS_MERGED_PATH = fake_merged_json
        with patch.object(loader, '_load_from_api',
                          side_effect=requests.exceptions.ReadTimeout):
            loader.load()
        response = client.get("/health")
        data = response.json()
        assert data["data_source"] == "json_fallback"
        assert data["blocks_loaded"] == 25
```

**Acceptance criteria:**

- Все 7 тестов проходят.
- При старте без Bot_data_base логи показывают `[DATA_LOADER] source=json_fallback blocks=25`.
- При старте без API и без JSON → `[DATA_LOADER] DEGRADED_MODE` в логах.
- В обоих случаях сервер не падает, `/health` отвечает корректно.
- Первый запрос пользователя при json_fallback получает ≥ 1 блока в retrieval.

***

## 5. Баг \#3 — `confidence_cap=3` режет контекст LLM

### 5.1 Описание

`confidence_cap` при `level=medium` всегда обрезает блоки до **3**. Это значение слишком мало: LLM получает недостаточно контекста и генерирует короткие, поверхностные ответы. До v0.6.0 в промпт попадало 5–7 блоков.

**Доказательство из `retrieval.log`:**

```
15:54:32 | retriever | API search: 9 блоков                    ← найдено 9
15:54:32 | retrieval.confidence_scorer | score=0.6294 level=medium
15:54:33 | answer_adaptive | confidence_cap=3 (before=3)        ← обрезано до 3
15:54:33 | answer_adaptive | After confidence cap: 3 blocks      ← только 3 в промпт
```


### 5.2 Требования к исправлению

**Файл:** `bot_agent/runtime_config.py` (или `config.py`)

Добавить конфигурируемые параметры cap:

```python
# Количество блоков, передаваемых в LLM по уровню уверенности retrieval
CONFIDENCE_CAP_HIGH: int = int(os.getenv("CONFIDENCE_CAP_HIGH", "7"))
CONFIDENCE_CAP_MEDIUM: int = int(os.getenv("CONFIDENCE_CAP_MEDIUM", "5"))
CONFIDENCE_CAP_LOW: int = int(os.getenv("CONFIDENCE_CAP_LOW", "3"))
CONFIDENCE_CAP_ZERO: int = int(os.getenv("CONFIDENCE_CAP_ZERO", "0"))
```

**Файл:** `bot_agent/retrieval/confidence_scorer.py` (или где расположен `confidence_cap`)

Заменить хардкод на configurable:

```python
# БЫЛО (хардкод):
CAP_BY_LEVEL = {"high": 5, "medium": 3, "low": 1, "zero": 0}

# СТАЛО (из config):
from bot_agent.runtime_config import (
    CONFIDENCE_CAP_HIGH, CONFIDENCE_CAP_MEDIUM,
    CONFIDENCE_CAP_LOW, CONFIDENCE_CAP_ZERO
)
CAP_BY_LEVEL = {
    "high":   CONFIDENCE_CAP_HIGH,    # 7
    "medium": CONFIDENCE_CAP_MEDIUM,  # 5
    "low":    CONFIDENCE_CAP_LOW,     # 3
    "zero":   CONFIDENCE_CAP_ZERO,    # 0
}
```

**Требования:**

1. Новые значения по умолчанию: `high=7`, `medium=5`, `low=3`, `zero=0`.
2. Все значения переопределяемы через `.env` без деплоя.
3. При применении cap логировать: `[CONFIDENCE] cap applied level={level} cap={cap} before={n} after={min(n, cap)}`.

### 5.3 Тесты

**Файл:** `tests/test_confidence_cap.py`

```python
import pytest
import os
from bot_agent.retrieval.confidence_scorer import ConfidenceScorer

class TestConfidenceCap:

    def make_blocks(self, n):
        return [{"id": f"b{i}", "score": 0.7 - i*0.01} for i in range(n)]

    def test_medium_level_returns_5_blocks(self):
        """При level=medium cap должен быть 5 (не 3)"""
        scorer = ConfidenceScorer()
        blocks = self.make_blocks(9)
        result = scorer.apply_cap(blocks, level="medium")
        assert len(result) == 5

    def test_high_level_returns_7_blocks(self):
        """При level=high cap должен быть 7"""
        scorer = ConfidenceScorer()
        blocks = self.make_blocks(9)
        result = scorer.apply_cap(blocks, level="high")
        assert len(result) == 7

    def test_low_level_returns_3_blocks(self):
        """При level=low cap должен быть 3"""
        scorer = ConfidenceScorer()
        blocks = self.make_blocks(9)
        result = scorer.apply_cap(blocks, level="low")
        assert len(result) == 3

    def test_zero_level_returns_0_blocks(self):
        """При level=zero cap=0 — нет контекста"""
        scorer = ConfidenceScorer()
        blocks = self.make_blocks(5)
        result = scorer.apply_cap(blocks, level="zero")
        assert len(result) == 0

    def test_cap_does_not_expand_blocks(self):
        """Если блоков меньше чем cap — все блоки сохраняются"""
        scorer = ConfidenceScorer()
        blocks = self.make_blocks(3)
        result = scorer.apply_cap(blocks, level="high")  # cap=7, blocks=3
        assert len(result) == 3

    def test_cap_configurable_via_env(self, monkeypatch):
        """Значение cap читается из env переменной"""
        monkeypatch.setenv("CONFIDENCE_CAP_MEDIUM", "6")
        # Перезагрузить модуль чтобы env применился
        import importlib
        import bot_agent.runtime_config as rc
        importlib.reload(rc)
        from bot_agent.retrieval.confidence_scorer import ConfidenceScorer as SC2
        scorer = SC2()
        blocks = self.make_blocks(9)
        result = scorer.apply_cap(blocks, level="medium")
        assert len(result) == 6

    def test_cap_log_message_format(self, caplog):
        """Лог содержит корректные данные о применённом cap"""
        scorer = ConfidenceScorer()
        blocks = self.make_blocks(9)
        scorer.apply_cap(blocks, level="medium")
        assert any("cap applied" in r.message and "medium" in r.message
                   for r in caplog.records)

    def test_integration_retrieval_returns_5_blocks_medium(self):
        """Интеграционный: полный pipeline возвращает 5 блоков при medium"""
        # Проверяет что answer_adaptive получает 5 блоков, а не 3
        from bot_agent.answer_adaptive import AdaptivePipeline
        from unittest.mock import patch, MagicMock
        pipeline = AdaptivePipeline()
        fake_blocks = [MagicMock(id=f"b{i}", score=0.65) for i in range(9)]
        with patch.object(pipeline.retriever, 'retrieve', return_value=fake_blocks):
            with patch.object(pipeline.confidence_scorer, 'score',
                              return_value=("medium", 0.63)):
                result = pipeline._apply_confidence_cap(fake_blocks, "medium", 0.63)
                assert len(result) == 5
```

**Acceptance criteria:**

- Все 8 тестов проходят.
- В `retrieval.log` строка `confidence_cap=5 (before=9)` (не `cap=3`).
- Длина ответа LLM в следующей сессии возрастает — субъективно ответы более развёрнуты.

***

## 6. Порядок выполнения и коммиты

Выполнять в строгом порядке, каждый баг — отдельный коммит:

```
[Fix #1] data_loader: singleton guard + thread-safe cache
[Fix #2] data_loader: 3-level fallback chain (api → json → degraded)
[Fix #3] confidence_cap: medium=5, high=7, configurable via env
[Test]   add tests for Fix #1, #2, #3
[Docs]   update CHANGELOG.md: v0.6.1 bugfix entry
```

**Ветка:** `fix/v0.6.1-stability` → PR в `main`.

***

## 7. Проверка после всех фиксов

### 7.1 Smoke-тест запуска (без Bot_data_base)

```bash
# Остановить Bot_data_base если запущен
# Запустить бот
cd bot_psychologist
python -m uvicorn api.main:app --port 8000

# Ожидаемые логи:
# [DATA_LOADER] API unavailable: Read timed out
# [DATA_LOADER] source=json_fallback blocks=25
# [WARMUP] completed
# (НЕ должно быть: "0 документов, 0 блоков")
```


### 7.2 Smoke-тест запроса

```bash
curl -X POST http://localhost:8000/api/v1/questions/adaptive-stream \
  -H "X-API-Key: dev-key-00" \
  -d '{"query": "что такое самоидентификация?", "user_id": "test_user_1"}'

# Ожидаемые логи в retrieval.log:
# [RETRIEVAL] Initial retrieval: 9 blocks      (не 0)
# [RETRIEVAL] confidence_cap=5 (before=9)      (не cap=3)
# [RETRIEVAL] After confidence cap: 5 blocks   (не 3)
```


### 7.3 Запуск всех тестов

```bash
pytest tests/test_data_loader_singleton.py -v
pytest tests/test_data_loader_fallback.py -v
pytest tests/test_confidence_cap.py -v

# Ожидаемый результат:
# 20 passed, 0 failed, 0 errors
```


### 7.4 Регрессионный тест

```bash
pytest tests/ -v --tb=short
# Ожидаемый результат: все тесты из v0.6.0 не сломаны
```


***

## 8. Definition of Done

| \# | Критерий | Как проверить |
| :-- | :-- | :-- |
| 1 | DataLoader при старте вызывает API ровно 1 раз | Лог: `[API] Загрузка` встречается 1 раз |
| 2 | При недоступном :8003 → загрузка из JSON | Лог: `source=json_fallback blocks=25` |
| 3 | При недоступном :8003 и JSON → DEGRADED\_MODE, не краш | Лог: `DEGRADED_MODE active` |
| 4 | `confidence_cap=medium` = 5, не 3 | Лог: `confidence_cap=5 (before=9)` |
| 5 | Все 20 новых тестов green | `pytest tests/test_data_loader_*.py tests/test_confidence_cap.py` |
| 6 | Все существующие тесты не сломаны | `pytest tests/ --tb=short` все green |
| 7 | CHANGELOG обновлён с v0.6.1 | Файл `bot_psychologist/CHANGELOG.md` |

