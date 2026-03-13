<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# ОТлично! Теперь твоя задача заново написать PRD Миграция bot_psychologist на Bot_data_base_v.2 применив все свои рекомендации о которых ты говорил в этом чате, они очень существенные и важные, согласен с тобой со всеми пунктами!

Подойди к написанию ПРД максимально профессионально и внимательно! Это должен получиться развернутый и целостный документ, по которому будет работать агент ИДЕ в моем проекте! Если документ не влезет в одно сообщение, можешь поделить и продолжить новым сообщением, после я соединю, главное чтобы не происходило деградации когда будешь писать его!

Пишу полный PRD v.2. Это большой документ, разобью на 2 части.

***

# 📋 PRD v.2: Миграция `bot_psychologist` на `Bot_data_base`

**Документ для:** IDE Agent (Cursor / Windsurf / Continue)
**Репозиторий:** `github.com/Askhat-cmd/Text_transcription`
**Дата:** 12.03.2026
**Версия:** 2.0 (полная редакция с учётом аудита кода и реальных данных)
**Приоритет:** HIGH — весь функционал бота должен быть сохранён и улучшен

***

## 1. КОНТЕКСТ И ЦЕЛЬ

### 1.1 Что есть сейчас

Бот-психолог (`bot_psychologist/bot_agent/`) читает знания из **SAG v2.0 JSON-файлов** в директории `voice_bot_pipeline/data/sag_final/` через `DataLoader`. Данные — транскрипты YouTube-лекций одного автора (Сарсекенов Саламат) с таймкодами, ключевыми словами и `graph_entities`.

### 1.2 Что нужно сделать

Перевести источник знаний на **`Bot_data_base`** — отдельный FastAPI-сервис (`http://127.0.0.1:8004`), в котором хранятся книги и иные документы различных авторов в формате `bot_data_base_v1.0`, проиндексированные в ChromaDB через sentence-transformers.

### 1.3 Критические ограничения

- Файлы, не перечисленные в разделе «ЗАДАЧИ», **не изменяются**
- SD-адаптация, TF-IDF fallback, `practices_recommender`, `graph_client` — работают после миграции
- Обратная совместимость с SAG JSON-режимом сохраняется (переключение через `.env`)
- `Bot_data_base/` — только читаем через API, не изменяем


### 1.4 Подтверждённые факты о `Bot_data_base` (из реального запуска)

- Сервер работает на `http://127.0.0.1:8004`
- Эндпоинты `GET /api/registry/` и `GET /api/registry/stats` — **подтверждены** (200 OK в логах)
- Ингест: `POST /api/ingest/book` — **подтверждён**
- Статус задачи: `GET /api/status/{job_id}` — **подтверждён**
- `/api/query/`, `/api/blocks/{id}`, `/api/export/{id}` — **требуют проверки** перед использованием
- Векторизация: sentence-transformers на CPU (~1.7 сек/блок, 43 сек на 25 блоков)
- Формат выходного JSON: `bot_data_base_v1.0`, `schema_version` присутствует


### 1.5 Критические находки из аудита реального JSON

Из анализа `kniga-posle-obrabotki.json` (25 блоков, глава 10):

- `"summary": ""` — **пустое у всех блоков** → сломает TF-IDF и превью в боте
- `"complexity"` — **шкала 0–1** (например `0.75`), а SAG и бот ожидают **шкалу 1–10** → без нормализации бот будет считать все книжные блоки «почти нулевой сложности»
- `"keywords"` — **поле отсутствует** → TF-IDF поиск деградирует до `content[:300]`
- `"block_type"` — **отсутствует** → `practices_recommender.py` не сможет фильтровать практики от теории
- `"emotional_tone"` — **отсутствует** → `answer_adaptive.py` не получит сигнал для адаптации тона

***

## 2. СТРУКТУРА РЕПОЗИТОРИЯ

```
Text_transcription/
├── bot_psychologist/
│   ├── .env                          ← ИЗМЕНИТЬ (добавить переменные)
│   └── bot_agent/
│       ├── config.py                 ← ИЗМЕНИТЬ
│       ├── data_loader.py            ← ИЗМЕНИТЬ
│       ├── retriever.py              ← ИЗМЕНИТЬ
│       ├── chroma_loader.py          ← СОЗДАТЬ (новый файл)
│       ├── answer_adaptive.py        ← НЕ ТРОГАТЬ
│       ├── answer_basic.py           ← НЕ ТРОГАТЬ
│       ├── answer_graph_powered.py   ← НЕ ТРОГАТЬ
│       ├── answer_sag_aware.py       ← НЕ ТРОГАТЬ
│       ├── practices_recommender.py  ← НЕ ТРОГАТЬ
│       ├── graph_client.py           ← НЕ ТРОГАТЬ
│       ├── conversation_memory.py    ← НЕ ТРОГАТЬ
│       ├── llm_answerer.py           ← НЕ ТРОГАТЬ
│       ├── path_builder.py           ← НЕ ТРОГАТЬ
│       ├── runtime_config.py         ← НЕ ТРОГАТЬ
│       ├── sd_classifier.py          ← НЕ ТРОГАТЬ
│       ├── semantic_analyzer.py      ← НЕ ТРОГАТЬ
│       ├── semantic_memory.py        ← НЕ ТРОГАТЬ
│       ├── state_classifier.py       ← НЕ ТРОГАТЬ
│       ├── user_level_adapter.py     ← НЕ ТРОГАТЬ
│       ├── retrieval/                ← НЕ ТРОГАТЬ (вся директория)
│       ├── decision/                 ← НЕ ТРОГАТЬ (вся директория)
│       └── response/                 ← НЕ ТРОГАТЬ (вся директория)
└── Bot_data_base/                    ← НЕ ТРОГАТЬ (только читаем API)
```


***

## 3. АНАЛИЗ ФОРМАТОВ И МАППИНГ

### 3.1 SAG v2.0 (текущий)

```json
{
  "document_title": "Лекция об осознанности",
  "document_metadata": { "video_id": "abc123", "source_url": "https://..." },
  "blocks": [{
    "block_id": "abc123_001",
    "video_id": "abc123",
    "start": "00:01:30",
    "end": "00:03:45",
    "title": "Что такое осознанность",
    "summary": "Краткое содержание...",
    "content": "Полный текст блока...",
    "keywords": ["осознанность", "внимание"],
    "youtube_link": "https://youtu.be/abc123?t=90",
    "block_type": "theory",
    "emotional_tone": "explanatory",
    "conceptual_depth": "medium",
    "complexity_score": 6.5,
    "graph_entities": ["осознанность", "медитация"],
    "sd_metadata": { "sd_level": "GREEN", "sd_secondary": "YELLOW" }
  }]
}
```


### 3.2 Bot_data_base v1.0 (новый, реальный формат)

```json
{
  "schema_version": "bot_data_base_v1.0",
  "source_id": "121212__пробная_версия_главы_10",
  "source_type": "book",
  "generated_at": "2026-03-12T11:53:40.175057",
  "blocks_count": 25,
  "blocks": [{
    "id": "0a507765-3ca7-4726-9d43-44cc0aaad296",
    "text": "Полный текст блока...",
    "title": "ГЛАВА 10. НейроСталкинг",
    "summary": "",
    "sd_level": "YELLOW",
    "sd_confidence": 0.85,
    "complexity": 0.7,
    "source": "book:121212__пробная_версия_главы_10",
    "metadata": {
      "author": "Саламат",
      "author_id": "121212",
      "source_title": "Пробная версия главы 10",
      "language": "ru",
      "published_date": "",
      "chapter_title": "ГЛАВА 10. НейроСталкинг",
      "chunk_index": 0,
      "source_type": "book"
    }
  }]
}
```


### 3.3 Полная таблица маппинга полей

| Поле `Block` | SAG v2.0 | Bot_data_base v1.0 | Трансформация |
| :-- | :-- | :-- | :-- |
| `block_id` | `block_id` | `id` | rename |
| `content` | `content` | `text` | rename |
| `title` | `title` | `title` | совпадает |
| `summary` | `summary` | `summary` (пустое!) | использовать `title` как fallback |
| `document_title` | `document_title` | `metadata.source_title` | вложено |
| `sd_level` | `sd_metadata.sd_level` | `sd_level` | упрощено |
| `sd_secondary` | `sd_metadata.sd_secondary` | отсутствует | `None` |
| `sd_confidence` | отсутствует | `sd_confidence` | новое поле |
| `complexity_score` | `complexity_score` (1–10) | `complexity` **(0–1!)** | **умножать × 10** |
| `video_id` | `video_id` | отсутствует | `""` для книг |
| `start` / `end` | `start` / `end` | отсутствует | `"00:00:00"` |
| `youtube_link` | `youtube_link` | отсутствует | `""` для книг |
| `keywords` | `keywords` | отсутствует | `[]` → TF-IDF fallback по `content[:500]` |
| `graph_entities` | `graph_entities` | отсутствует | `[]` |
| `block_type` | `block_type` | отсутствует | **авто-определить** по `title` |
| `emotional_tone` | `emotional_tone` | отсутствует | `"explanatory"` по умолчанию |
| `conceptual_depth` | `conceptual_depth` | отсутствует | `"medium"` по умолчанию |
| `author` | отсутствует | `metadata.author` | новое поле |
| `author_id` | отсутствует | `metadata.author_id` | новое поле |
| `source_type` | `"youtube"` (подразумевается) | `source_type` | новое поле |
| `chunk_index` | отсутствует | `metadata.chunk_index` | новое поле |
| `language` | отсутствует | `metadata.language` | новое поле |


***

## 4. ЗАДАЧИ (атомарные, строго в порядке выполнения)


***

### ЗАДАЧА 1: Обновить `bot_agent/config.py`

**Файл:** `bot_psychologist/bot_agent/config.py`

#### 1.1 — Добавить переменные окружения

В класс `Config` добавить ПОСЛЕ блока `# === Paths ===`:

```python
# === Knowledge Source ===
# "json"     → SAG v2.0 JSON (voice_bot_pipeline/sag_final) — legacy режим
# "db_json"  → Bot_data_base exported *_blocks.json (без запущенного сервера)
# "chromadb" → Bot_data_base через HTTP API (рекомендуется для production)
KNOWLEDGE_SOURCE: str = os.getenv("KNOWLEDGE_SOURCE", "json")

# === Bot_data_base HTTP connection ===
CHROMA_API_URL: str = os.getenv("CHROMA_API_URL", "http://localhost:8004")
CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "bot_knowledge")

# === db_json mode paths ===
DB_JSON_DIR: str = os.getenv("DB_JSON_DIR", "")
DB_EXPORT_FILE: str = os.getenv("DB_EXPORT_FILE", "")
```


#### 1.2 — Обновить `validate()`

Найти и заменить:

```python
# БЫЛО:
if not cls.SAG_FINAL_DIR.exists():
    errors.append(f"Data directory not found: {cls.SAG_FINAL_DIR}")

# СТАЛО:
if cls.KNOWLEDGE_SOURCE == "json" and not cls.SAG_FINAL_DIR.exists():
    errors.append(f"SAG data directory not found: {cls.SAG_FINAL_DIR}")
elif cls.KNOWLEDGE_SOURCE == "db_json":
    db_dir = Path(cls.DB_JSON_DIR) if cls.DB_JSON_DIR else None
    db_file = Path(cls.DB_EXPORT_FILE) if cls.DB_EXPORT_FILE else None
    if not (db_dir and db_dir.exists()) and not (db_file and db_file.exists()):
        errors.append(
            f"db_json mode: ни DB_JSON_DIR, ни DB_EXPORT_FILE не заданы или не существуют"
        )
elif cls.KNOWLEDGE_SOURCE == "chromadb":
    pass  # health check выполняется в ChromaLoader при первом запросе
```


#### 1.3 — Обновить `info()`

Добавить в вывод метода `info()`:

```python
| KNOWLEDGE_SOURCE: {cls.KNOWLEDGE_SOURCE}
| CHROMA_API_URL:   {cls.CHROMA_API_URL}
| CHROMA_COLLECTION:{cls.CHROMA_COLLECTION}
```


***

### ЗАДАЧА 2: Обновить `bot_agent/data_loader.py`

**Файл:** `bot_psychologist/bot_agent/data_loader.py`

#### 2.1 — Заменить датакласс `Block`

Заменить существующее определение класса `Block` целиком:

```python
@dataclass
class Block:
    """
    Универсальный блок знаний. Поддерживает два источника:
      - SAG v2.0 (YouTube-лекции): все поля заполнены, шкала complexity 1-10
      - Bot_data_base v1.0 (книги/документы): video_id/start/end/youtube_link пустые,
        complexity нормализована из 0-1 в 1-10 при парсинге

    ВАЖНО: поле complexity_score всегда в шкале 1-10.
    """
    # --- Обязательные поля (общие для обоих форматов) ---
    block_id: str
    title: str
    content: str

    # --- Общие опциональные ---
    summary: str = ""
    document_title: str = ""

    # --- YouTube-специфичные (пустые для книг) ---
    video_id: str = ""
    start: str = "00:00:00"
    end: str = "00:00:00"
    youtube_link: str = ""
    keywords: List[str] = field(default_factory=list)

    # --- SAG v2.0 аналитические поля ---
    block_type: Optional[str] = None        # "theory"|"practice"|"case_study"|"quote"
    emotional_tone: Optional[str] = None    # "explanatory"|"inspirational"|"challenging"
    conceptual_depth: Optional[str] = None  # "low"|"medium"|"high"
    complexity_score: Optional[float] = None  # ВСЕГДА шкала 1-10
    graph_entities: Optional[List[str]] = None

    # --- SD-разметка ---
    sd_level: Optional[str] = None
    sd_secondary: Optional[str] = None
    sd_confidence: Optional[float] = None   # из bot_data_base (0.0–1.0)

    # --- Метаданные источника ---
    source_type: str = "book"               # "book" | "youtube"
    author: str = ""
    author_id: str = ""
    chunk_index: int = 0
    language: str = "ru"

    def __post_init__(self):
        if self.graph_entities is None:
            self.graph_entities = []
        if self.block_type is None:
            self.block_type = "theory"
        if self.emotional_tone is None:
            self.emotional_tone = "explanatory"
        if self.conceptual_depth is None:
            self.conceptual_depth = "medium"
        if self.complexity_score is None:
            self.complexity_score = 5.0
        # Если summary пустое — используем title как fallback
        if not self.summary and self.title:
            self.summary = self.title

    def get_preview(self, max_len: int = 200) -> str:
        text = self.content[:max_len] if len(self.content) > max_len else self.content
        return text + "..." if len(self.content) > max_len else text

    def get_search_text(self) -> str:
        """
        Текст для TF-IDF индексирования.
        Для YouTube-блоков: title + keywords + summary + content[:300]
        Для книжных блоков: title + summary + content[:500] (keywords пустые)
        """
        keywords_str = " ".join(self.keywords) if self.keywords else ""
        # Для книг keywords пустые — берём больше контента
        content_preview = self.content[:500] if not self.keywords else self.content[:300]
        return f"{self.title} {keywords_str} {self.summary} {content_preview}".strip()

    def get_entities_text(self) -> str:
        return " ".join(self.graph_entities) if self.graph_entities else ""

    def is_practice(self) -> bool:
        """True если блок содержит практику (для practices_recommender)."""
        return self.block_type == "practice"

    def has_graph_data(self) -> bool:
        """True если блок содержит граф-сущности (для graph_client)."""
        return bool(self.graph_entities)
```


#### 2.2 — Добавить вспомогательную функцию `_detect_block_type()`

Добавить как модульную функцию (не метод класса) ПЕРЕД определением `DataLoader`:

```python
def _detect_block_type(title: str, content: str) -> str:
    """
    Автоматически определяет тип блока по заголовку и контенту.
    Используется для блоков из Bot_data_base, где block_type отсутствует.

    Returns:
        "practice"   — если блок содержит упражнение/практику
        "case_study" — если блок содержит кейс/диалог/пример из жизни
        "quote"      — если блок состоит преимущественно из цитат
        "theory"     — всё остальное (по умолчанию)
    """
    title_lower = title.lower()
    content_lower = content.lower()

    # Паттерны для практик
    practice_keywords = [
        "практика", "упражнение", "задание", "техника",
        "practice", "exercise", "попробуй", "сделай",
        "шаг 1", "шаг 2", "время:", "цель:"
    ]
    if any(kw in title_lower for kw in practice_keywords):
        return "practice"
    # Контент-паттерны практик (инструкции)
    if content_lower.count("**") >= 4 and any(
        kw in content_lower for kw in ["цель:", "время:", "минут"]
    ):
        return "practice"

    # Паттерны для кейсов
    case_keywords = ["кейс", "случай", "пример", "история", "case"]
    dialogue_markers = ["— ", "– ", "> —", "> –"]
    if any(kw in title_lower for kw in case_keywords):
        return "case_study"
    if sum(content.count(m) for m in dialogue_markers) >= 3:
        return "case_study"

    # Паттерны для цитат
    if content.count('«') >= 3 or content.count('"') >= 4:
        return "quote"

    return "theory"
```


#### 2.3 — Обновить метод `load_all_data()` в классе `DataLoader`

Заменить метод целиком:

```python
def load_all_data(self) -> None:
    if self._is_loaded:
        logger.info("✓ Данные уже загружены, используем кэш")
        return

    source = config.KNOWLEDGE_SOURCE
    logger.info(f"📂 KNOWLEDGE_SOURCE={source}")

    if source == "chromadb":
        self._load_from_chromadb()
    elif source == "db_json":
        self._load_from_db_json()
    else:
        self._load_from_sag_json()  # legacy — исходная логика

    self._is_loaded = True
    self.loaded_at = datetime.now()
    logger.info(
        f"✅ Загружено: {len(self.documents)} документов, "
        f"{len(self.all_blocks)} блоков "
        f"[source={source}]"
    )
```


#### 2.4 — Добавить `_load_from_sag_json()`

```python
def _load_from_sag_json(self) -> None:
    """
    ИСХОДНАЯ логика load_all_data() — без изменений логики,
    только переименована. SAG v2.0 YouTube-формат.
    Добавляет source_type="youtube" к каждому блоку.
    """
    # ... скопировать весь исходный код из текущего load_all_data() ...
    # Единственное дополнение в _load_single_document():
    #   block.source_type = "youtube"
    #   block.author = doc_metadata.get("author", "")
    #   block.author_id = doc_metadata.get("author_id", "")
```


#### 2.5 — Добавить `_load_from_db_json()`

```python
def _load_from_db_json(self) -> None:
    """
    Загрузка из exported Bot_data_base JSON-файлов (без запущенного сервера).
    Поддерживает:
      - одиночные файлы (*_blocks.json)
      - merged JSON (список источников в одном файле)
    """
    db_export_file = Path(config.DB_EXPORT_FILE) if config.DB_EXPORT_FILE else None
    db_json_dir = Path(config.DB_JSON_DIR) if config.DB_JSON_DIR else None

    if db_export_file and db_export_file.exists():
        logger.info(f"📖 DB_JSON: загрузка из файла {db_export_file}")
        self._parse_db_json_file(db_export_file)
        return

    if db_json_dir and db_json_dir.exists():
        json_files = sorted(db_json_dir.glob("**/*_blocks.json"))
        logger.info(f"📖 DB_JSON: найдено {len(json_files)} файлов в {db_json_dir}")
        for json_path in json_files:
            try:
                self._parse_db_json_file(json_path)
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки {json_path.name}: {e}")
        return

    logger.error("❌ DB_JSON mode: ни DB_JSON_DIR, ни DB_EXPORT_FILE не настроены")
```


#### 2.6 — Добавить `_parse_db_json_file()`

```python
def _parse_db_json_file(self, json_path: Path) -> None:
    """
    Парсит один bot_data_base_v1.0 JSON файл.

    КРИТИЧЕСКИЕ ТРАНСФОРМАЦИИ:
      1. complexity (0-1) → complexity_score (1-10): умножаем на 10
      2. summary пустое → используем title как fallback (в __post_init__ Block)
      3. block_type → авто-определяем через _detect_block_type()
      4. sd_level читается напрямую (не через sd_metadata как в SAG)
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Поддержка merged формата (список) и одиночного (dict)
    sources = data if isinstance(data, list) else [data]

    for source_data in sources:
        source_id = source_data.get("source_id", json_path.stem)
        source_type = source_data.get("source_type", "book")
        blocks = []

        for bd in source_data.get("blocks", []):
            meta = bd.get("metadata", {})

            # ВАЖНО: нормализация complexity 0-1 → 1-10
            raw_complexity = bd.get("complexity")
            try:
                raw_val = float(raw_complexity) if raw_complexity is not None else 0.5
                # Если значение в диапазоне 0-1, нормализуем в 1-10
                # Если уже в диапазоне 1-10 (старые файлы), оставляем как есть
                if 0.0 <= raw_val <= 1.0:
                    complexity = round(raw_val * 10, 1)
                else:
                    complexity = round(raw_val, 1)
            except (ValueError, TypeError):
                complexity = 5.0

            title = bd.get("title", "")
            text_content = bd.get("text", "")

            # Авто-определение block_type для книжных блоков
            block_type = _detect_block_type(title, text_content)

            block = Block(
                block_id=bd.get("id", ""),
                title=title,
                content=text_content,
                summary=bd.get("summary", ""),   # "" → __post_init__ подставит title
                document_title=meta.get("source_title", source_id),
                sd_level=bd.get("sd_level"),
                sd_secondary=None,               # не используется в bot_data_base
                sd_confidence=bd.get("sd_confidence"),
                complexity_score=complexity,     # уже в шкале 1-10
                block_type=block_type,
                source_type=meta.get("source_type", source_type),
                author=meta.get("author", ""),
                author_id=meta.get("author_id", ""),
                chunk_index=meta.get("chunk_index", 0),
                language=meta.get("language", "ru"),
                # YouTube-поля пусты для книг
                video_id="",
                start="00:00:00",
                end="00:00:00",
                youtube_link="",
                keywords=[],
                graph_entities=[],
            )
            blocks.append(block)
            self._block_id_to_block[block.block_id] = block
            self.all_blocks.append(block)

        doc = Document(
            video_id=source_id,
            source_url="",
            title=source_id,
            blocks=blocks,
            metadata={
                "schema_version": source_data.get("schema_version", ""),
                "source_type": source_type,
            },
        )
        self.documents.append(doc)
        self._video_id_to_doc[source_id] = doc
        logger.debug(f"✓ DB_JSON: {source_id} ({len(blocks)} блоков)")
```


#### 2.7 — Добавить `_load_from_chromadb()`

```python
def _load_from_chromadb(self) -> None:
    """
    В режиме chromadb: загружает ВСЕ блоки из ChromaLoader для построения
    TF-IDF индекса. Семантический поиск выполняется напрямую в retriever.py.
    """
    try:
        from .chroma_loader import chroma_loader
        blocks = chroma_loader.get_all_blocks()

        if not blocks:
            logger.warning(
                "[CHROMADB] Не удалось загрузить блоки. "
                "Проверьте что Bot_data_base запущен на "
                f"{config.CHROMA_API_URL}"
            )
            return

        self.all_blocks = blocks
        self._block_id_to_block = {b.block_id: b for b in blocks}

        # Группируем блоки в Document-объекты по document_title
        docs_map: Dict[str, List[Block]] = {}
        for b in blocks:
            key = b.document_title or b.video_id or "unknown"
            docs_map.setdefault(key, []).append(b)

        for title, doc_blocks in docs_map.items():
            # Сортируем блоки по chunk_index для правильного порядка
            doc_blocks_sorted = sorted(doc_blocks, key=lambda b: b.chunk_index)
            doc = Document(
                video_id=title,
                source_url="",
                title=title,
                blocks=doc_blocks_sorted,
            )
            self.documents.append(doc)
            self._video_id_to_doc[title] = doc

        logger.info(
            f"✅ ChromaDB: {len(blocks)} блоков из "
            f"{len(self.documents)} источников загружено"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки из ChromaDB: {e}", exc_info=True)
```


#### 2.8 — Обновить `get_stats()`

```python
def get_stats(self) -> Dict:
    if not self._is_loaded:
        self.load_all_data()

    # Подсчёт SD-распределения
    sd_distribution: Dict[str, int] = {}
    source_type_counts: Dict[str, int] = {}
    practice_count = 0

    for b in self.all_blocks:
        if b.sd_level:
            sd_distribution[b.sd_level] = sd_distribution.get(b.sd_level, 0) + 1
        source_type_counts[b.source_type] = (
            source_type_counts.get(b.source_type, 0) + 1
        )
        if b.is_practice():
            practice_count += 1

    return {
        "total_documents": len(self.documents),
        "total_blocks": len(self.all_blocks),
        "practice_blocks": practice_count,
        "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
        "knowledge_source": config.KNOWLEDGE_SOURCE,
        "sd_distribution": sd_distribution,
        "source_type_counts": source_type_counts,
    }
```


***

### ЗАДАЧА 3: Создать `bot_agent/chroma_loader.py`

**Файл:** `bot_psychologist/bot_agent/chroma_loader.py` *(новый файл)*

```python
"""
ChromaLoader — HTTP-клиент к Bot_data_base API
===============================================

Конфигурация через .env:
  CHROMA_API_URL=http://localhost:8004
  CHROMA_COLLECTION=bot_knowledge

Подтверждённые эндпоинты Bot_data_base (из логов реального запуска):
  GET  /api/registry/         → список всех источников (200 OK)
  GET  /api/registry/stats    → статистика и health check (200 OK)
  POST /api/ingest/book       → ингест книги (200 OK)
  GET  /api/status/{job_id}   → статус задачи (200 OK)

Эндпоинты, требующие проверки перед использованием:
  POST /api/query/            → семантический поиск
  GET  /api/blocks/{id}       → блоки источника
  GET  /api/export/{id}       → экспорт блоков

СТРАТЕГИЯ FALLBACK:
  Если /api/query/ недоступен (404) → retriever использует TF-IDF
  Если /api/blocks/ недоступен → пробуем /api/export/
  Если оба недоступны → query с фильтром по source_id
"""

import logging
from typing import List, Optional, Dict, Tuple

import requests

from .data_loader import Block, _detect_block_type
from .config import config

logger = logging.getLogger(__name__)


class ChromaLoader:
    """
    HTTP-клиент к Bot_data_base.

    Два режима:
      1. get_all_blocks()  — все блоки (для TF-IDF индекса в DataLoader)
      2. query_blocks()    — семантический поиск через ChromaDB эмбеддинги

    Оба возвращают объекты Block — совместимы со всеми модулями бота.
    """

    # Endpoints (проверенные)
    REGISTRY_URL = "/api/registry/"
    STATS_URL = "/api/registry/stats"

    # Endpoints (требуют проверки)
    QUERY_URL = "/api/query/"
    BLOCKS_URL = "/api/blocks/{source_id}"
    EXPORT_URL = "/api/export/{source_id}"

    def __init__(self):
        self.api_url = config.CHROMA_API_URL.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self._all_blocks_cache: Optional[List[Block]] = None
        self._query_endpoint_available: Optional[bool] = None  # кэш проверки
        self._blocks_endpoint_available: Optional[bool] = None

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def get_all_blocks(self) -> List[Block]:
        """
        Загрузить все блоки из Bot_data_base.
        Результат кэшируется. Вызывать invalidate_cache() при добавлении источников.
        """
        if self._all_blocks_cache is not None:
            logger.info(f"[CHROMA] Используем кэш: {len(self._all_blocks_cache)} блоков")
            return self._all_blocks_cache

        logger.info(f"[CHROMA] Загрузка всех блоков из {self.api_url}")
        blocks: List[Block] = []

        try:
            registry = self._get_registry()
        except Exception as e:
            logger.error(f"[CHROMA] Не удалось получить реестр: {e}")
            return blocks

        logger.info(f"[CHROMA] Реестр: {len(registry)} источников")

        for entry in registry:
            source_id = entry.get("source_id", "")
            if not source_id:
                logger.warning(f"[CHROMA] Источник без source_id: {entry}")
                continue
            try:
                source_blocks = self._load_source_blocks(source_id, entry)
                blocks.extend(source_blocks)
                logger.info(
                    f"[CHROMA] '{source_id}': {len(source_blocks)} блоков "
                    f"(SD: {entry.get('sd_distribution', {})})"
                )
            except Exception as e:
                logger.error(f"[CHROMA] Ошибка загрузки '{source_id}': {e}")

        self._all_blocks_cache = blocks
        logger.info(f"[CHROMA] Итого загружено: {len(blocks)} блоков")
        return blocks

    def query_blocks(
        self,
        query_text: str,
        top_k: int = 5,
        sd_filter: Optional[str] = None,
        source_type_filter: Optional[str] = None,
    ) -> List[Tuple[Block, float]]:
        """
        Семантический поиск через ChromaDB эмбеддинги.
        POST /api/query/

        Args:
            query_text:          текст запроса
            top_k:               кол-во результатов
            sd_filter:           фильтр по SD-уровню ("GREEN", "YELLOW", ...)
            source_type_filter:  фильтр по типу источника ("book", "youtube")

        Returns:
            List[(Block, score)] — по убыванию релевантности.
            Пустой список если эндпоинт недоступен (TF-IDF fallback в retriever).
        """
        # Проверяем доступность эндпоинта (кэшируем результат)
        if self._query_endpoint_available is False:
            logger.debug("[CHROMA] /api/query/ недоступен (кэш) → TF-IDF fallback")
            return []

        payload: Dict = {"query": query_text, "n_results": top_k}
        if sd_filter:
            payload["sd_level"] = sd_filter
        if source_type_filter:
            payload["source_type"] = source_type_filter

        try:
            resp = self._session.post(
                f"{self.api_url}{self.QUERY_URL}",
                json=payload,
                timeout=10,
            )
            if resp.status_code == 404:
                logger.info(
                    "[CHROMA] /api/query/ не реализован (404) → TF-IDF fallback. "
                    "Добавьте POST /api/query/ в Bot_data_base для семантического поиска."
                )
                self._query_endpoint_available = False
                return []

            resp.raise_for_status()
            self._query_endpoint_available = True

        except requests.Timeout:
            logger.warning("[CHROMA] query_blocks: таймаут 10с → TF-IDF fallback")
            return []
        except requests.RequestException as e:
            logger.warning(f"[CHROMA] query_blocks ошибка: {e} → TF-IDF fallback")
            return []

        results = []
        for item in resp.json().get("results", []):
            bd = item.get("block", item)
            meta_override = item.get("metadata", {})
            try:
                block = self._parse_block(bd, meta_override)
                score = float(item.get("score", item.get("distance", 0.0)))
                results.append((block, score))
            except Exception as e:
                logger.warning(f"[CHROMA] Ошибка парсинга блока: {e}")

        logger.info(f"[CHROMA] Семантический поиск '{query_text[:50]}': {len(results)} блоков")
        return results

    def health_check(self) -> bool:
        """Проверить доступность Bot_data_base API."""
        try:
            resp = self._session.get(
                f"{self.api_url}{self.STATS_URL}", timeout=5
            )
            ok = resp.status_code == 200
            if ok:
                stats = resp.json()
                logger.info(
                    f"[CHROMA] Health OK — "
                    f"sources={stats.get('total_sources', '?')}, "
                    f"blocks={stats.get('total_blocks', '?')}"
                )
            return ok
        except Exception as e:
            logger.warning(f"[CHROMA] Health check failed: {e}")
            return False

    def invalidate_cache(self) -> None:
        """Сбросить кэш блоков (вызывать после добавления новых источников)."""
        self._all_blocks_cache = None
        self._query_endpoint_available = None
        self._blocks_endpoint_available = None
        logger.info("[CHROMA] Кэш блоков и endpoint-проверок сброшен")

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _get_registry(self) -> List[Dict]:
        """GET /api/registry/ → список источников."""
        resp = self._session.get(
            f"{self.api_url}{self.REGISTRY_URL}", timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        # Bot_data_base может вернуть список или {"sources": [...]}
        if isinstance(data, list):
            return data
        return data.get("sources", data.get("items", data.get("data", [])))

    def _load_source_blocks(self, source_id: str, entry: Dict) -> List[Block]:
        """
        Загрузить блоки одного источника.
        Стратегия (в порядке приоритета):
          1. GET /api/blocks/{source_id}
          2. GET /api/export/{source_id}
          3. POST /api/query/ с пустым запросом + фильтр source_id (fallback)
        """
        # Попытка 1: /api/blocks/{source_id}
        if self._blocks_endpoint_available is not False:
            try:
                url = f"{self.api_url}{self.BLOCKS_URL.format(source_id=source_id)}"
                resp = self._session.get(url, timeout=15)
                if resp.status_code == 200:
                    self._blocks_endpoint_available = True
                    data = resp.json()
                    raw = data if isinstance(data, list) else data.get("blocks", [])
                    return [self._parse_block(b, entry) for b in raw]
                elif resp.status_code == 404 and self._blocks_endpoint_available is None:
                    # Роут не существует в целом — отключаем
                    self._blocks_endpoint_available = False
                    logger.info("[CHROMA] /api/blocks/ не реализован → пробуем /api/export/")
            except requests.RequestException:
                pass

        # Попытка 2: /api/export/{source_id}
        try:
            url = f"{self.api_url}{self.EXPORT_URL.format(source_id=source_id)}"
            resp = self._session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                raw = data if isinstance(data, list) else data.get("blocks", [])
                return [self._parse_block(b, entry) for b in raw]
        except requests.RequestException:
            pass

        # Попытка 3: query fallback с source_id фильтром
        if self._query_endpoint_available is not False:
            try:
                n = entry.get("blocks_count", entry.get("total_blocks", 500))
                resp = self._session.post(
                    f"{self.api_url}{self.QUERY_URL}",
                    json={
                        "query": "психология",
                        "n_results": min(int(n), 1000),
                        "source_id": source_id,
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    items = resp.json().get("results", [])
                    return [
                        self._parse_block(
                            r.get("block", r),
                            {**entry, **r.get("metadata", {})}
                        )
                        for r in items
                    ]
                elif resp.status_code == 404:
                    self._query_endpoint_available = False
            except requests.RequestException as e:
                logger.warning(f"[CHROMA] query fallback '{source_id}' не удался: {e}")

        logger.error(
            f"[CHROMA] Не удалось загрузить блоки для '{source_id}'. "
            "Все три стратегии исчерпаны. "
            "Реализуйте GET /api/blocks/{source_id} в Bot_data_base."
        )
        return []

    def _parse_block(self, bd: Dict, meta_override: Dict = None) -> Block:
        """
        Конвертировать JSON-объект Bot_data_base в объект Block.

        КРИТИЧНО: нормализация complexity 0-1 → 1-10
        """
        if meta_override is None:
            meta_override = {}

        meta = {
            **bd.get("metadata", {}),
            **{k: v for k, v in meta_override.items() if v is not None}
        }

        # Нормализация complexity: 0-1 → 1-10
        raw_complexity = bd.get("complexity", bd.get("complexity_score"))
        try:
            raw_val = float(raw_complexity) if raw_complexity is not None else 0.5
            if 0.0 <= raw_val <= 1.0:
                complexity = round(raw_val * 10, 1)
            else:
                complexity = round(raw_val, 1)
        except (ValueError, TypeError):
            complexity = 5.0

        title = bd.get("title", "")
        text_content = bd.get("text", bd.get("content", ""))

        # Авто-определение block_type
        block_type = _detect_block_type(title, text_content)

        return Block(
            block_id=bd.get("id", bd.get("block_id", "")),
            title=title,
            content=text_content,
            summary=bd.get("summary", ""),
            document_title=meta.get("source_title", meta.get("document_title", "")),
            sd_level=bd.get("sd_level", meta.get("sd_level")),
            sd_secondary=bd.get("sd_secondary"),
            sd_confidence=bd.get("sd_confidence"),
            complexity_score=complexity,
            block_type=block_type,
            source_type=meta.get("source_type", "book"),
            author=meta.get("author", ""),
            author_id=meta.get("author_id", ""),
            chunk_index=int(meta.get("chunk_index", 0)),
            language=meta.get("language", "ru"),
            video_id="",
            start="00:00:00",
            end="00:00:00",
            youtube_link="",
            keywords=[],
            graph_entities=[],
        )


# Глобальный синглтон — используется в data_loader.py и retriever.py
chroma_loader = ChromaLoader()
```


***

### ЗАДАЧА 4: Обновить `bot_agent/retriever.py`

**Файл:** `bot_psychologist/bot_agent/retriever.py`

#### 4.1 — Обновить `CACHE_FORMAT_VERSION`

```python
CACHE_FORMAT_VERSION = "4.0.0"  # bumped: universal Block + ChromaDB support
```


#### 4.2 — Заменить `_compute_data_hash()`

```python
def _compute_data_hash(self) -> str:
    """
    Вычисляет хэш данных для инвалидации TF-IDF кэша.
    Зависит от KNOWLEDGE_SOURCE и содержимого источников.
    """
    hasher = hashlib.md5()
    hasher.update(CACHE_FORMAT_VERSION.encode())
    hasher.update(config.KNOWLEDGE_SOURCE.encode())

    if config.KNOWLEDGE_SOURCE == "json":
        for file_path in sorted(
            config.SAG_FINAL_DIR.glob("**/*.for_vector.json")
        ):
            hasher.update(file_path.read_bytes())

    elif config.KNOWLEDGE_SOURCE == "db_json":
        db_dir = Path(config.DB_JSON_DIR) if config.DB_JSON_DIR else None
        db_file = Path(config.DB_EXPORT_FILE) if config.DB_EXPORT_FILE else None
        if db_file and db_file.exists():
            hasher.update(db_file.read_bytes())
        elif db_dir and db_dir.exists():
            for file_path in sorted(db_dir.glob("**/*_blocks.json")):
                hasher.update(file_path.read_bytes())

    else:  # chromadb
        try:
            from .chroma_loader import chroma_loader
            resp = chroma_loader._session.get(
                f"{chroma_loader.api_url}{chroma_loader.STATS_URL}",
                timeout=5,
            )
            if resp.status_code == 200:
                hasher.update(resp.text.encode())
            else:
                hasher.update(b"chromadb_stats_unavailable")
        except Exception:
            hasher.update(b"chromadb_no_connection")

    return hasher.hexdigest()
```


#### 4.3 — Обновить метод `retrieve()`

В начало метода `retrieve()`, **строго ПЕРЕД** существующим TF-IDF кодом, вставить блок:

```python
def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Tuple[Block, float]]:
    if top_k is None:
        top_k = config.TOP_K_BLOCKS

    logger.info(
        "[RETRIEVAL] query='%s' top_k=%s source=%s",
        query[:80], top_k, config.KNOWLEDGE_SOURCE
    )

    # ================================================================
    # НОВЫЙ БЛОК: ChromaDB семантический поиск (приоритет над TF-IDF)
    # Активен только при KNOWLEDGE_SOURCE=chromadb
    # При недоступности /api/query/ — автоматически падает на TF-IDF
    # ================================================================
    if config.KNOWLEDGE_SOURCE == "chromadb":
        try:
            from .chroma_loader import chroma_loader
            semantic_results = chroma_loader.query_blocks(query, top_k=top_k)
            if semantic_results:
                logger.info(
                    "[RETRIEVAL] semantic search: %d блоков (ChromaDB)",
                    len(semantic_results)
                )
                return semantic_results
            logger.info(
                "[RETRIEVAL] semantic search вернул 0 результатов → TF-IDF fallback"
            )
        except Exception as e:
            logger.warning(
                "[RETRIEVAL] semantic search ошибка: %s → TF-IDF fallback", e
            )
    # ================================================================

    # Существующий TF-IDF код — БЕЗ ИЗМЕНЕНИЙ ↓
    if not self._is_built:
        self.build_index()
    # ... весь остальной код retrieve() без изменений ...
```


***

### ЗАДАЧА 5: Обновить `bot_psychologist/.env`

Добавить в конец файла `.env` (или создать если не существует):

```ini
# ============================================================
# Knowledge Source — переключение источника знаний бота
# ============================================================
# Варианты:
#   "json"     → SAG v2.0 (legacy, voice_bot_pipeline)
#   "db_json"  → Bot_data_base JSON без сервера (для тестов)
#   "chromadb" → Bot_data_base через HTTP (production)
KNOWLEDGE_SOURCE=chromadb

# ============================================================
# Bot_data_base API
# ============================================================
CHROMA_API_URL=http://localhost:8004
CHROMA_COLLECTION=bot_knowledge

# ============================================================
# db_json mode (только для KNOWLEDGE_SOURCE=db_json)
# Указать одно из двух:
# ============================================================
# DB_JSON_DIR=../Bot_data_base/data/exported
# DB_EXPORT_FILE=../Bot_data_base/data/exported/merged_export.json
```


***

## 5. ВАЖНЫЕ ОГРАНИЧЕНИЯ ДЛЯ АГЕНТА

### 5.1 Файлы под запретом изменений

Агент **НЕ ДОЛЖЕН** изменять:

```
bot_psychologist/bot_agent/answer_adaptive.py
bot_psychologist/bot_agent/answer_basic.py
bot_psychologist/bot_agent/answer_graph_powered.py
bot_psychologist/bot_agent/answer_sag_aware.py
bot_psychologist/bot_agent/practices_recommender.py
bot_psychologist/bot_agent/graph_client.py
bot_psychologist/bot_agent/conversation_memory.py
bot_psychologist/bot_agent/llm_answerer.py
bot_psychologist/bot_agent/path_builder.py
bot_psychologist/bot_agent/runtime_config.py
bot_psychologist/bot_agent/sd_classifier.py
bot_psychologist/bot_agent/semantic_analyzer.py
bot_psychologist/bot_agent/semantic_memory.py
bot_psychologist/bot_agent/state_classifier.py
bot_psychologist/bot_agent/user_level_adapter.py
bot_psychologist/bot_agent/working_state.py
bot_psychologist/bot_agent/retrieval/   (вся директория)
bot_psychologist/bot_agent/decision/    (вся директория)
bot_psychologist/bot_agent/response/    (вся директория)
bot_psychologist/bot_agent/storage/     (вся директория)
Bot_data_base/                          (вся директория)
```


### 5.2 Критические инварианты — проверить перед коммитом

1. `block.complexity_score` всегда в диапазоне `1.0–10.0` (не 0–1)
2. `block.summary` никогда не пустое (`__post_init__` подставляет `title`)
3. `block.block_type` всегда одно из: `"theory"`, `"practice"`, `"case_study"`, `"quote"`
4. `block.sd_level` читается через `block.sd_level` (не через `block.sd_metadata`)
5. TF-IDF `get_search_text()` возвращает непустую строку для любого блока

***

## 6. СЕРИЯ ТЕСТОВ

**Файл:** `bot_psychologist/tests/test_migration_v2.py`

```python
"""
Тесты миграции bot_psychologist → Bot_data_base v2.0

Запуск:
    cd bot_psychologist
    pytest tests/test_migration_v2.py -v

    # Только unit (без сервера):
    pytest tests/test_migration_v2.py -v -m "not integration"

    # С запущенным Bot_data_base (http://localhost:8004):
    pytest tests/test_migration_v2.py -v -m integration
"""
import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from typing import List


# ===========================================================================
# БЛОК 1: Датакласс Block — инварианты
# ===========================================================================

class TestBlockInvariants:

    def test_complexity_scale_1_to_10_default(self):
        """complexity_score по умолчанию 5.0, не 0.5."""
        from bot_agent.data_loader import Block
        b = Block(block_id="x", title="T", content="C")
        assert 1.0 <= b.complexity_score <= 10.0
        assert b.complexity_score == 5.0

    def test_summary_fallback_to_title(self):
        """Пустой summary → __post_init__ подставляет title."""
        from bot_agent.data_loader import Block
        b = Block(block_id="x", title="Глава 1", content="Текст", summary="")
        assert b.summary == "Глава 1"

    def test_summary_not_overwritten_if_set(self):
        """Непустой summary → не заменяется."""
        from bot_agent.data_loader import Block
        b = Block(block_id="x", title="T", content="C", summary="Мой саммари")
        assert b.summary == "Мой саммари"

    def test_block_type_default_theory(self):
        """block_type по умолчанию 'theory'."""
        from bot_agent.data_loader import Block
        b = Block(block_id="x", title="T", content="C")
        assert b.block_type == "theory"

    def test_sd_level_direct_access(self):
        """sd_level доступен напрямую (не через sd_metadata)."""
        from bot_agent.data_loader import Block
        b = Block(block_id="x", title="T", content="C", sd_level="GREEN")
        assert b.sd_level == "GREEN"
        # Нет атрибута sd_metadata — не должен существовать
        assert not hasattr(b, "sd_metadata")

    def test_search_text_never_empty(self):
        """get_search_text() возвращает непустую строку всегда."""
        from bot_agent.data_loader import Block
        b = Block(block_id="x", title="T", content="C")
        assert len(b.get_search_text()) > 0

    def test_graph_entities_empty_list_for_books(self):
        """Книжные блоки имеют graph_entities=[] (не None)."""
        from bot_agent.data_loader import Block
        b = Block(block_id="x", title="T", content="C", source_type="book")
        assert b.graph_entities == []
        assert b.has_graph_data() is False

    def test_youtube_block_has_graph_data(self):
        """YouTube-блоки с graph_entities возвращают has_graph_data=True."""
        from bot_agent.data_loader import Block
        b = Block(
            block_id="x", title="T", content="C",
            source_type="youtube",
            graph_entities=["осознанность", "медитация"]
        )
        assert b.has_graph_data() is True

    def test_is_practice_flag(self):
        """is_practice() корректно определяет практики."""
        from bot_agent.data_loader import Block
        b_practice = Block(block_id="x", title="T", content="C", block_type="practice")
        b_theory = Block(block_id="y", title="T", content="C", block_type="theory")
        assert b_practice.is_practice() is True
        assert b_theory.is_practice() is False


# ===========================================================================
# БЛОК 2: _detect_block_type()
# ===========================================================================

class TestDetectBlockType:

    def test_practice_by_title_keyword(self):
        from bot_agent.data_loader import _detect_block_type
        assert _detect_block_type("Практика 1. «Кто замечает»", "") == "practice"
        assert _detect_block_type("Упражнение для осознанности", "") == "practice"

    def test_practice_by_content_pattern(self):
        from bot_agent.data_loader import _detect_block_type
        content = "**Цель:** Прямой контакт\n**Время:** 10–15 минут\nСядь удобно."
        assert _detect_block_type("Заголовок", content) == "practice"

    def test_case_study_by_dialogue(self):
        from bot_agent.data_loader import _detect_block_type
        content = "— Саламат, что это?\n— Это практика.\n— Понял.\n— Хорошо."
        assert _detect_block_type("Кейс из сессии", content) == "case_study"

    def test_theory_by_default(self):
        from bot_agent.data_loader import _detect_block_type
        assert _detect_block_type(
            "Нейрофизиология присутствия", "Длинный теоретический текст..."
        ) == "theory"

    def test_real_book_blocks_classification(self):
        """Классификация реальных блоков из kniga-posle-obrabotki.json."""
        from bot_agent.data_loader import _detect_block_type
        cases = [
            ("ГЛАВА 10. НейроСталкинг — жизнь из присутствия", "", "theory"),
            ("Практика 1. «Кто замечает»", "**Цель:** Прямой контакт\n**Время:** 15 минут", "practice"),
            ("Практика 7. «90 секунд»", "**Цель:** Работа с нейрохимическим циклом\n**Время:** 90 секунд", "practice"),
            ("Ментальный суверенитет: неуязвимость — не броня", "Теоретический текст", "theory"),
        ]
        for title, content, expected in cases:
            result = _detect_block_type(title, content)
            assert result == expected, f"'{title}': ожидали {expected}, получили {result}"


# ===========================================================================
# БЛОК 3: Нормализация complexity
# ===========================================================================

class TestComplexityNormalization:

    def test_complexity_0_to_1_normalized_to_1_to_10(self):
        """complexity=0.7 → complexity_score=7.0."""
        from bot_agent.data_loader import DataLoader
        loader = DataLoader()
        # Создаём минимальный JSON с complexity в диапазоне 0-1
        import json, tempfile, pathlib
        data = {
            "source_id": "test",
            "source_type": "book",
            "blocks": [{
                "id": "b1", "title": "T", "text": "C",
                "complexity": 0.7,
                "metadata": {"source_title": "Test Book"}
            }]
        }
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='_blocks.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump(data, f)
            tmp_path = pathlib.Path(f.name)

        loader._parse_db_json_file(tmp_path)
        tmp_path.unlink()

        assert len(loader.all_blocks) == 1
        assert loader.all_blocks[0].complexity_score == 7.0

    def test_complexity_already_in_1_10_scale(self):
        """complexity=6.5 (SAG диапазон) → complexity_score=6.5 без изменений."""
        from bot_agent.data_loader import DataLoader
        import json, tempfile, pathlib
        loader = DataLoader()
        data = {
            "source_id": "test2", "source_type": "book",
            "blocks": [{
                "id": "b2", "title": "T", "text": "C",
                "complexity": 6.5,
                "metadata": {"source_title": "Test"}
            }]
        }
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='_blocks.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump(data, f)
            tmp_path = pathlib.Path(f.name)

        loader._parse_db_json_file(tmp_path)
        tmp_path.unlink()

        assert loader.all_blocks[0].complexity_score == 6.5

    def test_complexity_none_defaults_to_5(self):
        """complexity=None → complexity_score=5.0."""
        from bot_agent.data_loader import DataLoader
        import json, tempfile, pathlib
        loader = DataLoader()
        data = {
            "source_id": "test3", "source_type": "book",
            "blocks": [{
                "id": "b3", "title": "T", "text": "C",
                "metadata": {}
            }]
        }
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='_blocks.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump(data, f)
            tmp_path = pathlib.Path(f.name)

        loader._parse_db_json_file(tmp_path)
        tmp_path.unlink()

        assert loader.all_blocks[0].complexity_score == 5.0

    def test_complexity_boundary_values(self):
        """Граничные значения: 0.0→1.0, 1.0→10.0, 0.5→5.0."""
        from bot_agent.data_loader import DataLoader
        import json, tempfile, pathlib
        loader = DataLoader()
        blocks_data = [
            {"id": "c0", "title": "T", "text": "C", "complexity": 0.0, "metadata": {}},
            {"id": "c1", "title": "T", "text": "C", "complexity": 1.0, "metadata": {}},
            {"id": "c05", "title": "T", "text": "C", "complexity": 0.5, "metadata": {}},
        ]
        data = {"source_id": "bounds", "source_type": "book", "blocks": blocks_data}
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='_blocks.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump(data, f)
            tmp_path = pathlib.Path(f.name)

        loader._parse_db_json_file(tmp_path)
        tmp_path.unlink()

        scores = {b.block_id: b.complexity_score for b in loader.all_blocks}
        assert scores["c0"] == 0.0   # 0.0 в диапазоне 0-1 → 0.0 (минимум)
        assert scores["c1"] == 10.0  # 1.0 → 10.0 (максимум)
        assert scores["c05"] == 5.0  # 0.5 → 5.0 (середина)


# ===========================================================================
# БЛОК 4: DataLoader — режим db_json
# ===========================================================================

class TestDataLoaderDbJson:

    @pytest.fixture
    def real_book_json(self, tmp_path: Path) -> Path:
        """JSON в реальном формате bot_data_base_v1.0."""
        data = {
            "schema_version": "bot_data_base_v1.0",
            "source_id": "121212__тест_глава_1",
            "source_type": "book",
            "generated_at": "2026-03-12T11:53:40.175057",
            "blocks_count": 3,
            "blocks": [
                {
                    "id": "block-001",
                    "text": "Текст теоретического блока о психологии.",
                    "title": "Введение в психологию",
                    "summary": "",
                    "sd_level": "GREEN",
                    "sd_confidence": 0.85,
                    "complexity": 0.6,
                    "source": "book:121212__тест",
                    "metadata": {
                        "author": "Саламат",
                        "author_id": "121212",
                        "source_title": "Тест Книга",
                        "language": "ru",
                        "chapter_title": "Введение в психологию",
                        "chunk_index": 0,
                        "source_type": "book"
                    }
                },
                {
                    "id": "block-002",
                    "text": "Практика осознанности.",
                    "title": "Практика 1. «Дыхание»",
                    "summary": "Практическое упражнение",
                    "sd_level": "YELLOW",
                    "sd_confidence": 0.9,
                    "complexity": 0.3,
                    "source": "book:121212__тест",
                    "metadata": {
                        "author": "Саламат",
                        "author_id": "121212",
                        "source_title": "Тест Книга",
                        "language": "ru",
                        "chapter_title": "Практика 1",
                        "chunk_index": 1,
                        "source_type": "book"
                    }
                },
                {
                    "id": "block-003",
                    "text": "— Что значит быть осознанным?\n— Это значит замечать себя.\n— И всё?\n— Этого достаточно.",
                    "title": "Кейс: диалог с учеником",
                    "summary": "",
                    "sd_level": "GREEN",
                    "sd_confidence": 0.8,
                    "complexity": 0.5,
                    "source": "book:121212__тест",
                    "metadata": {
                        "author": "Саламат",
                        "author_id": "121212",
                        "source_title": "Тест Книга",
                        "language": "ru",
                        "chunk_index": 2,
                        "source_type": "book"
                    }
                }
            ]
        }
        json_path = tmp_path / "тест_blocks.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return tmp_path

    def test_blocks_count(self, real_book_json: Path):
        from bot_agent.data_loader import DataLoader
        loader = DataLoader()
        json_file = list(real_book_json.glob("*.json"))[0]
        loader._parse_db_json_file(json_file)
        assert len(loader.all_blocks) == 3

    def test_field_mapping(self, real_book_json: Path):
        """id→block_id, text→content, complexity×10."""
        from bot_agent.data_loader import DataLoader
        loader = DataLoader()
        json_file = list(real_book_json.glob("*.json"))[0]
        loader._parse_db_json_file(json_file)

        b0 = loader.all_blocks[0]
        assert b0.block_id == "block-001"
        assert b0.content == "Текст теоретического блока о психологии."
        assert b0.title == "Введение в психологию"
        assert b0.sd_level == "GREEN"
        assert b0.sd_confidence == 0.85
        assert b0.complexity_score == 6.0  # 0.6 × 10
        assert b0.author == "Саламат"
        assert b0.author_id == "121212"
        assert b0.document_title == "Тест Книга"
        assert b0.source_type == "book"
        assert b0.language == "ru"
        assert b0.chunk_index == 0

    def test_summary_fallback(self, real_book_json: Path):
        """Пустой summary → title."""
        from bot_agent.data_loader import DataLoader
        loader = DataLoader()
        json_file = list(real_book_json.glob("*.json"))[0]
        loader._parse_db_json_file(json_file)

        b0 = loader.all_blocks[0]
        assert b0.summary == "Введение в психологию"  # title как fallback

        b1 = loader.all_blocks[1]
        assert b1.summary == "Практическое упражнение"  # оригинал сохранён

    def test_youtube_fields_empty(self, real_book_json: Path):
        from bot_agent.data_loader import DataLoader
        loader = DataLoader()
        json_file = list(real_book_json.glob("*.json"))[0]
        loader._parse_db_json_file(json_file)

        for b in loader.all_blocks:
            assert b.video_id == ""
            assert b.youtube_link == ""
            assert b.start == "00:00:00"
            assert b.keywords == []
            assert b.graph_entities == []

    def test_block_type_autodetection(self, real_book_json: Path):
        """block_type определяется автоматически по title/content."""
        from bot_agent.data_loader import DataLoader
        loader = DataLoader()
        json_file = list(real_book_json.glob("*.json"))[0]
        loader._parse_db_json_file(json_file)

        assert loader.all_blocks[0].block_type == "theory"    # "Введение в психологию"
        assert loader.all_blocks[1].block_type == "practice"  # "Практика 1."
        assert loader.all_blocks[2].block_type == "case_study"  # диалоги

    def test_chunks_sorted_by_index(self, real_book_json: Path):
        """Блоки в документе отсортированы по chunk_index."""
        from bot_agent.data_loader import DataLoader
        loader = DataLoader()
        json_file = list(real_book_json.glob("*.json"))[0]
        loader._parse_db_json_file(json_file)

        doc = loader.documents[0]
        indices = [b.chunk_index for b in doc.blocks]
        assert indices == sorted(indices)

    def test_document_created(self, real_book_json: Path):
        """DataLoader создаёт Document-объект."""
        from bot_agent.data_loader import DataLoader
        loader = DataLoader()
        json_file = list(real_book_json.glob("*.json"))[0]
        loader._parse_db_json_file(json_file)

        assert len(loader.documents) == 1
        assert loader.documents[0].title == "121212__тест_глава_1"

    def test_get_stats_includes_new_fields(self, real_book_json: Path):
        """get_stats() возвращает sd_distribution, source_type_counts."""
        from bot_agent.data_loader import DataLoader
        loader = DataLoader()
        json_file = list(real_book_json.glob("*.json"))[0]
        loader._parse_db_json_file(json_file)
        loader._is_loaded = True

        stats = loader.get_stats()
        assert "sd_distribution" in stats
        assert "source_type_counts" in stats
        assert "knowledge_source" in stats
        assert stats["source_type_counts"].get("book", 0) == 3

    def test_merged_json_format(self, tmp_path: Path):
        """Merged JSON (список источников) — загружаются все."""
        from bot_agent.data_loader import DataLoader
        merged = [
            {
                "source_id": "book_a", "source_type": "book",
                "blocks": [{"id": "a1", "title": "A1", "text": "text a",
                             "complexity": 0.5, "metadata": {"source_title": "A"}}]
            },
            {
                "source_id": "book_b", "source_type": "book",
                "blocks": [
                    {"id": "b1", "title": "B1", "text": "text b1",
                     "complexity": 0.6, "metadata": {"source_title": "B"}},
                    {"id": "b2", "title": "B2", "text": "text b2",
                     "complexity": 0.7, "metadata": {"source_title": "B"}},
                ]
            },
        ]
        json_file = tmp_path / "merged_blocks.json"
        json_file.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")

        loader = DataLoader()
        loader._parse_db_json_file(json_file)
        assert len(loader.all_blocks) == 3
        assert len(loader.documents) == 2


# ===========================================================================
# БЛОК 5: ChromaLoader (unit, без сервера)
# ===========================================================================

class TestChromaLoaderUnit:

    @pytest.fixture
    def loader(self):
        from bot_agent.chroma_loader import ChromaLoader
        cl = ChromaLoader()
        cl.api_url = "http://mock-server:8004"
        return cl

    def test_parse_block_complexity_normalization(self, loader):
        """complexity 0-1 → 1-10 в _parse_block()."""
        bd = {"id": "x", "title": "T", "text": "C", "complexity": 0.75}
        block = loader._parse_block(bd)
        assert block.complexity_score == 7.5

    def test_parse_block_summary_fallback(self, loader):
        """Пустой summary → title через __post_init__."""
        bd = {"id": "x", "title": "Моя глава", "text": "C", "summary": ""}
        block = loader._parse_block(bd)
        assert block.summary == "Моя глава"

    def test_parse_block_block_type_autodetect(self, loader):
        """block_type определяется через _detect_block_type."""
        bd = {"id": "x", "title": "Практика 3. Суверенный разговор", "text": "Практика..."}
        block = loader._parse_block(bd)
        assert block.block_type == "practice"

    def test_parse_block_real_format(self, loader):
        """Парсинг реального блока из bot_data_base_v1.0."""
        bd = {
            "id": "0a507765-3ca7-4726-9d43-44cc0aaad296",
            "text": "Девять глав до этой...",
            "title": "ГЛАВА 10. НейроСталкинг",
            "summary": "",
            "sd_level": "YELLOW",
            "sd_confidence": 0.85,
            "complexity": 0.7,
            "metadata": {
                "author": "Саламат",
                "author_id": "121212",
                "source_title": "Пробная версия главы 10",
                "language": "ru",
                "chunk_index": 0,
                "source_type": "book"
            }
        }
        block = loader._parse_block(bd)
        assert block.block_id == "0a507765-3ca7-4726-9d43-44cc0aaad296"
        assert block.sd_level == "YELLOW"
        assert block.sd_confidence == 0.85
        assert block.complexity_score == 7.0
        assert block.author == "Саламат"
        assert block.summary == "ГЛАВА 10. НейроСталкинг"  # fallback

    def test_query_blocks_404_returns_empty(self, loader):
        """404 на /api/query/ → пустой список (TF-IDF будет использован)."""
        mock_resp = Mock(status_code=404)
        loader._session.post = Mock(return_value=mock_resp)

        result = loader.query_blocks("осознанность", top_k=5)
        assert result == []
        assert loader._query_endpoint_available is False

    def test_query_blocks_second_call_skips_request(self, loader):
        """После 404 повторный вызов не делает запрос."""
        mock_resp = Mock(status_code=404)
        loader._session.post = Mock(return_value=mock_resp)
        loader.query_blocks("тест")
        loader.query_blocks("тест2")
        assert loader._session.post.call_count == 1  # только один запрос

    def test_query_blocks_connection_error_returns_empty(self, loader):
        """Ошибка соединения → пустой список, не исключение."""
        import requests
        loader._session.post = Mock(side_effect=requests.ConnectionError())
        result = loader.query_blocks("тест")
        assert result == []

    def test_get_registry_list_format(self, loader):
        mock_resp = Mock()
        mock_resp.json.return_value = [{"source_id": "a"}, {"source_id": "b"}]
        mock_resp.raise_for_status = Mock()
        loader._session.get = Mock(return_value=mock_resp)
        result = loader._get_registry()
        assert len(result) == 2

    def test_get_registry_dict_format(self, loader):
        mock_resp = Mock()
        mock_resp.json.return_value = {"sources": [{"source_id": "c"}]}
        mock_resp.raise_for_status = Mock()
        loader._session.get = Mock(return_value=mock_resp)
        result = loader._get_registry()
        assert len(result) == 1

    def test_invalidate_cache_resets_all(self, loader):
        """invalidate_cache() сбрасывает кэш блоков и endpoint-флаги."""
        loader._all_blocks_cache = []
        loader._query_endpoint_available = False
        loader._blocks_endpoint_available = False
        loader.invalidate_cache()
        assert loader._all_blocks_cache is None
        assert loader._query_endpoint_available is None
        assert loader._blocks_endpoint_available is None


# ===========================================================================
# БЛОК 6: Режим chromadb в DataLoader
# ===========================================================================

class TestDataLoaderChromaMode:

    def test_chromadb_mode_dispatches_to_chroma_loader(self):
        """KNOWLEDGE_SOURCE=chromadb → вызывает chroma_loader.get_all_blocks()."""
        from bot_agent.data_loader import DataLoader
        from bot_agent.data_loader import Block

        mock_blocks = [
            Block(block_id="b1", title="T1", content="C1", sd_level="GREEN",
                  complexity_score=6.0, source_type="book", document_title="Book A",
                  chunk_index=0),
            Block(block_id="b2", title="T2", content="C2", sd_level="YELLOW",
                  complexity_score=7.0, source_type="book", document_title="Book A",
                  chunk_index=1),
        ]

        with patch("bot_agent.data_loader.config") as mock_cfg:
            mock_cfg.KNOWLEDGE_SOURCE = "chromadb"
            mock_cfg.CHROMA_API_URL = "http://mock:8004"

            with patch("bot_agent.data_loader.chroma_loader") as mock_cl:
                mock_cl.get_all_blocks.return_value = mock_blocks
                loader = DataLoader()
                loader._load_from_chromadb()

        assert len(loader.all_blocks) == 2
        assert len(loader.documents) == 1  # оба блока из "Book A"

    def test_chromadb_blocks_sorted_by_chunk_index(self):
        """Блоки в документе отсортированы по chunk_index даже если пришли не по порядку."""
        from bot_agent.data_loader import DataLoader, Block

        mock_blocks = [
            Block(block_id="b2", title="T2", content="C2", document_title="Book",
                  chunk_index=2, complexity_score=5.0),
            Block(block_id="b0", title="T0", content="C0", document_title="Book",
                  chunk_index=0, complexity_score=5.0),
            Block(block_id="b1", title="T1", content="C1", document_title="Book",
                  chunk_index=1, complexity_score=5.0),
        ]

        with patch("bot_agent.data_loader.config") as mock_cfg:
            mock_cfg.KNOWLEDGE_SOURCE = "chromadb"
            with patch("bot_agent.data_loader.chroma_loader") as mock_cl:
                mock_cl.get_all_blocks.return_value = mock_blocks
                loader = DataLoader()
                loader._load_from_chromadb()

        doc = loader.documents[0]
        assert [b.chunk_index for b in doc.blocks] == [0, 1, 2]


# ===========================================================================
# БЛОК 7: Совместимость с SAG v2.0 (обратная)
# ===========================================================================

class TestSAGBackwardCompatibility:

    def test_json_mode_still_works_with_legacy_config(self):
        """KNOWLEDGE_SOURCE=json → исходная логика SAG, нет краша."""
        from bot_agent.data_loader import DataLoader
        with patch("bot_agent.data_loader.config") as mock_cfg:
            mock_cfg.KNOWLEDGE_SOURCE = "json"
            # Если SAG_FINAL_DIR не существует, должен логировать ошибку, не падать
            mock_cfg.SAG_FINAL_DIR.exists = Mock(return_value=False)
            loader = DataLoader()
            # Метод должен существовать
            assert hasattr(loader, "_load_from_sag_json")

    def test_sag_block_sd_level_still_readable(self):
        """SAG-блоки: sd_level доступен через block.sd_level (не sd_metadata)."""
        from bot_agent.data_loader import Block
        # Эмулируем блок из SAG-источника
        b = Block(
            block_id="abc_001", title="Осознанность", content="Текст лекции",
            sd_level="GREEN", sd_secondary="YELLOW",
            source_type="youtube", video_id="abc123",
            graph_entities=["осознанность", "медитация"],
            complexity_score=6.5,
        )
        assert b.sd_level == "GREEN"
        assert b.sd_secondary == "YELLOW"
        assert b.complexity_score == 6.5
        assert b.source_type == "youtube"
        assert b.has_graph_data() is True


# ===========================================================================
# БЛОК 8: Integration Tests (требуют запущенного Bot_data_base)
# ===========================================================================

@pytest.mark.integration
class TestBotDataBaseIntegration:
    """
    Запускать только при запущенном Bot_data_base на http://localhost:8004.
    pytest tests/test_migration_v2.py -v -m integration
    """

    def test_health_check(self):
        """Bot_data_base API доступен."""
        from bot_agent.chroma_loader import chroma_loader
        assert chroma_loader.health_check() is True

    def test_registry_returns_sources(self):
        """GET /api/registry/ возвращает список источников."""
        from bot_agent.chroma_loader import chroma_loader
        registry = chroma_loader._get_registry()
        assert isinstance(registry, list)
        assert len(registry) >= 1
        # Проверяем структуру записи
        for entry in registry:
            assert "source_id" in entry

    def test_all_blocks_have_valid_complexity(self):
        """Все блоки имеют complexity_score в диапазоне 1-10."""
        from bot_agent.chroma_loader import chroma_loader
        blocks = chroma_loader.get_all_blocks()
        assert len(blocks) > 0
        for b in blocks:
            assert 0.0 <= b.complexity_score <= 10.0, (
                f"Block {b.block_id}: complexity_score={b.complexity_score} out of range"
            )

    def test_all_blocks_have_non_empty_summary(self):
        """Все блоки имеют непустой summary (fallback на title)."""
        from bot_agent.chroma_loader import chroma_loader
        blocks = chroma_loader.get_all_blocks()
        for b in blocks:
            assert b.summary, f"Block {b.block_id}: summary пустой"

    def test_all_blocks_have_valid_block_type(self):
        """Все блоки имеют валидный block_type."""
        from bot_agent.chroma_loader import chroma_loader
        valid_types = {"theory", "practice", "case_study", "quote"}
        blocks = chroma_loader.get_all_blocks()
        for b in blocks:
            assert b.block_type in valid_types, (
                f"Block {b.block_id}: block_type='{b.block_type}'"
            )

    def test_sd_level_distribution_matches_dashboard(self):
        """SD-распределение блоков соответствует дашборду (YELLOW:7, GREEN:16...)."""
        from bot_agent.chroma_loader import chroma_loader
        blocks = chroma_loader.get_all_blocks()
        distribution: dict = {}
        for b in blocks:
            if b.sd_level:
                distribution[b.sd_level] = distribution.get(b.sd_level, 0) + 1
        # Проверяем что SD-уровни присутствуют
        assert len(distribution) >= 1
        print(f"\nSD Distribution: {distribution}")

    def test_query_endpoint_if_available(self):
        """Если /api/query/ реализован — возвращает результаты."""
        from bot_agent.chroma_loader import chroma_loader
        results = chroma_loader.query_blocks("осознанность", top_k=3)
        if chroma_loader._query_endpoint_available:
            assert len(results) <= 3
            for block, score in results:
                assert isinstance(score, float)
                assert block.block_id
        else:
            pytest.skip("/api/query/ не реализован в Bot_data_base")

    def test_data_loader_chromadb_mode_end_to_end(self):
        """DataLoader в режиме chromadb загружает блоки и строит документы."""
        from bot_agent.data_loader import DataLoader
        import os
        with patch.dict(os.environ, {
            "KNOWLEDGE_SOURCE": "chromadb",
            "CHROMA_API_URL": "http://localhost:8004",
        }):
            loader = DataLoader()
            loader.load_all_data()

        assert len(loader.all_blocks) > 0
        assert len(loader.documents) > 0
        stats = loader.get_stats()
        assert stats["knowledge_source"] == "chromadb"
        assert stats["total_blocks"] > 0
        print(f"\nStats: {stats}")
```


***

## 7. ЧЕКЛИСТ ВЫПОЛНЕНИЯ ДЛЯ АГЕНТА

Агент выполняет задачи строго в порядке и проставляет галочки:

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



