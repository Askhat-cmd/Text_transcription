

# 🔧 МИНИ-PRD: Hotfix `CHUNKS: 0` — подключение `Bot_data_base` к боту

**Приоритет:** CRITICAL
**Файлы:** только `chroma_loader.py` и `.env`
**Задача:** бот загрузил книгу «Кузница Духа» (229 блоков) в `Bot_data_base`, но бот-психолог получает `CHUNKS: 0`. Исправить.

***

## ФАКТЫ О РЕАЛЬНОЙ СТРУКТУРЕ `Bot_data_base/data/`

```
Bot_data_base/data/
├── chroma_db/                          ← ChromaDB файлы (не трогать)
├── processed/
│   └── books/
│       ├── 123__кузница_духа_blocks.json   ← готовые блоки книги
│       └── all_blocks_merged.json          ← ВСЕ блоки из всех источников
├── uploads/
│   └── books/
│       └── КУЗНИЦА ДУХА v.2.md
└── registry.json                       ← реестр источников
```

**Ключевой факт:** файл `Bot_data_base/data/processed/books/all_blocks_merged.json` уже существует и содержит все 229 блоков. Его и нужно читать.

***

## ЗАДАЧА 1: Исправить `chroma_loader.py`

**Файл:** `bot_psychologist/bot_agent/chroma_loader.py`

### 1.1 — Исправить порт (строка в docstring и везде где упомянут 8003)

```python
# БЫЛО:
#   CHROMA_API_URL=http://localhost:8003

# СТАЛО:
#   CHROMA_API_URL=http://localhost:8004
```


### 1.2 — Полностью заменить метод `get_all_blocks()`

Проблема текущей реализации: при получении ответа от `/api/registry/export/merged` код пытается открыть файл через `open(file_path)` — но `file_path` это путь **на сервере**, не на машине бота. Это всегда падает с `FileNotFoundError`.

**Новая реализация — читать `all_blocks_merged.json` напрямую с диска:**

```python
def get_all_blocks(self) -> List[Block]:
    """
    Загрузить все блоки из Bot_data_base.

    СТРАТЕГИЯ (в порядке приоритета):
      1. Читать all_blocks_merged.json напрямую с диска
         (Bot_data_base/data/processed/books/all_blocks_merged.json)
      2. GET /api/registry/ + _load_source_blocks() через API — fallback
         если файл не найден (например, разные машины)

    Результат кэшируется в памяти.
    """
    if self._all_blocks_cache is not None:
        logger.info(f"[CHROMA] Используем кэш: {len(self._all_blocks_cache)} блоков")
        return self._all_blocks_cache

    logger.info(f"[CHROMA] Загрузка всех блоков...")
    blocks: List[Block] = []

    # ── Стратегия 1: читать merged JSON напрямую с диска ──────────────
    merged_path = config.ALL_BLOCKS_MERGED_PATH  # задаётся в config.py / .env
    if merged_path and Path(merged_path).exists():
        try:
            import json
            with open(merged_path, 'r', encoding='utf-8') as f:
                merged_data = json.load(f)

            # Поддержка двух форматов:
            # {"blocks": [...]}  или  [...]  или  {"sources": [{"blocks": [...]}]}
            if isinstance(merged_data, list):
                raw_blocks = merged_data
            elif isinstance(merged_data, dict):
                raw_blocks = merged_data.get("blocks", [])
                if not raw_blocks:
                    # Формат с вложенными sources
                    for src in merged_data.get("sources", []):
                        raw_blocks.extend(src.get("blocks", []))
            else:
                raw_blocks = []

            blocks = [self._parse_block(b, {}) for b in raw_blocks]
            logger.info(
                f"[CHROMA] ✅ Прочитано из merged JSON: "
                f"{len(blocks)} блоков из {merged_path}"
            )
            self._all_blocks_cache = blocks
            return blocks

        except Exception as e:
            logger.warning(
                f"[CHROMA] Не удалось прочитать merged JSON ({merged_path}): {e} "
                f"→ fallback на API"
            )

    # ── Стратегия 2: API fallback ─────────────────────────────────────
    logger.info(f"[CHROMA] Загрузка через API {self.api_url}")
    try:
        registry = self._get_registry()
    except Exception as e:
        logger.error(
            f"[CHROMA] ❌ Реестр недоступен: {e}. "
            f"Установите ALL_BLOCKS_MERGED_PATH в .env"
        )
        return blocks

    logger.info(f"[CHROMA] Реестр: {len(registry)} источников")
    for entry in registry:
        source_id = entry.get("source_id", "")
        if not source_id:
            continue
        try:
            source_blocks = self._load_source_blocks(source_id, entry)
            blocks.extend(source_blocks)
            logger.info(f"[CHROMA] '{source_id}': {len(source_blocks)} блоков")
        except Exception as e:
            logger.error(f"[CHROMA] Ошибка '{source_id}': {e}")

    self._all_blocks_cache = blocks
    logger.info(f"[CHROMA] Итого: {len(blocks)} блоков")
    return blocks
```


***

## ЗАДАЧА 2: Добавить `ALL_BLOCKS_MERGED_PATH` в `config.py`

**Файл:** `bot_psychologist/bot_agent/config.py`

В блок `# === Bot_data_base HTTP connection ===` добавить одну строку:

```python
# Абсолютный путь к all_blocks_merged.json (Bot_data_base/data/processed/books/)
# Если задан — блоки читаются напрямую с диска (быстрее, без HTTP)
# Если пустой — используется API fallback
ALL_BLOCKS_MERGED_PATH: str = os.getenv("ALL_BLOCKS_MERGED_PATH", "")
```


***

## ЗАДАЧА 3: Обновить `.env`

**Файл:** `bot_psychologist/.env`

```env
# Источник знаний
KNOWLEDGE_SOURCE=chromadb

# Bot_data_base API
CHROMA_API_URL=http://localhost:8004

# КРИТИЧНО: прямой путь к merged JSON с блоками всех книг
# Указать абсолютный путь к файлу на вашей машине:
ALL_BLOCKS_MERGED_PATH=C:/путь/к/проекту/Text_transcription/Bot_data_base/data/processed/books/all_blocks_merged.json
```

> ⚠️ **Агенту:** путь нужно определить автоматически — найти файл `all_blocks_merged.json` относительно корня репозитория `Text_transcription/`. Использовать `Path(__file__).resolve()` для построения относительного пути.

***

## ЗАДАЧА 4: Добавить авто-определение пути в `config.py`

В конце блока инициализации `ALL_BLOCKS_MERGED_PATH`, добавить авто-resolve если переменная пустая:

```python
# Авто-определение пути если не задан явно
if not ALL_BLOCKS_MERGED_PATH:
    _repo_root = Path(__file__).resolve().parents[^3]  # Text_transcription/
    _candidate = _repo_root / "Bot_data_base" / "data" / "processed" / "books" / "all_blocks_merged.json"
    if _candidate.exists():
        ALL_BLOCKS_MERGED_PATH = str(_candidate)
```


***

## ПРОВЕРКА ПОСЛЕ ИСПРАВЛЕНИЯ

Запустить в терминале (Bot_data_base должен быть запущен):

```bash
cd bot_psychologist
python -c "
from bot_agent.chroma_loader import chroma_loader
blocks = chroma_loader.get_all_blocks()
print(f'Загружено блоков: {len(blocks)}')
print(f'Первый блок: {blocks[^0].title if blocks else \"ПУСТО\"}')
"
```

**Ожидаемый результат:**

```
[CHROMA] ✅ Прочитано из merged JSON: 229 блоков из .../all_blocks_merged.json
Загружено блоков: 229
Первый блок: КУЗНИЦА ДУХА — ...
```

После этого перезапустить бота — `CHUNKS` перестанет быть 0.

***

**Конец мини-PRD. Агент — изменить только 3 файла: `chroma_loader.py`, `config.py`, `.env`. Остальное не трогать.**
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: image.jpg

