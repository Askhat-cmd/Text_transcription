
***

# 📋 PRD v4.0 — Миграция SD-разметки ChromaDB

**Скрипт:** `voice_bot_pipeline/scripts/migrate_add_sd_labels.py`
**Тип:** одноразовая идемпотентная миграция
**Зависимость от:** `sd_labeler.py` (уже существует ), коллекция `salamat_blocks`

***

## 1. Контекст проблемы

В ChromaDB существуют блоки, загруженные **до** внедрения SD-разметки (PRD v3.0). У них в metadata отсутствуют поля `sd_level`, `sd_secondary`, `emotional_tone`. `sd_filter.py` не может их фильтровать и падает в `fallback GREEN` для всех таких блоков — теряется весь смысл SD-адаптации .

**Решение:** пройтись по всей коллекции, найти блоки без `sd_level`, прогнать каждый через `SDLabeler.label_block()`, дозаписать metadata через ChromaDB API `collection.update()`.

***

## 2. Полный код скрипта

**Файл:** `voice_bot_pipeline/scripts/migrate_add_sd_labels.py`

```python
"""
Одноразовая миграция: добавляет SD-разметку к блокам ChromaDB,
у которых в metadata отсутствует поле sd_level.

Запуск:
    python -m scripts.migrate_add_sd_labels
    python -m scripts.migrate_add_sd_labels --collection salamat_blocks --batch-size 50 --dry-run

Идемпотентен: повторный запуск пропускает уже размеченные блоки.
"""

import argparse
import logging
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

# Путь к корню voice_bot_pipeline
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from text_processor.sd_labeler import SDLabeler  # noqa: E402

# ──────────────────────────────────────────────────────────────
# Логирование
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT_DIR / "logs" / "migrate_sd_labels.log", mode="a"),
    ],
)
logger = logging.getLogger("migrate_sd_labels")

# ──────────────────────────────────────────────────────────────
# Константы (переопределяются через аргументы CLI)
# ──────────────────────────────────────────────────────────────
DEFAULT_COLLECTION    = "salamat_blocks"
DEFAULT_BATCH_SIZE    = 50
DEFAULT_CHROMA_PATH   = str(ROOT_DIR / "data" / "chroma_db")
DEFAULT_LLM_MODEL     = "gpt-4o-mini"


# ══════════════════════════════════════════════════════════════
# CORE
# ══════════════════════════════════════════════════════════════

def get_chroma_collection(
    chroma_path: str,
    collection_name: str,
) -> chromadb.Collection:
    """
    Подключиться к ChromaDB и вернуть коллекцию.
    Использует PersistentClient — тот же способ, что в retriever.py проекта.
    """
    client = chromadb.PersistentClient(
        path=chroma_path,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_collection(name=collection_name)
    logger.info(
        f"[CHROMA] Подключено к коллекции '{collection_name}' "
        f"({chroma_path}), всего документов: {collection.count()}"
    )
    return collection


def fetch_unlabeled_ids(
    collection: chromadb.Collection,
    batch_size: int = 1000,
) -> list[str]:
    """
    Найти все document_id, у которых НЕТ поля sd_level в metadata.

    ChromaDB не поддерживает $not_exists — загружаем все документы
    страницами и фильтруем на Python стороне.
    Возвращает список id без SD-разметки.
    """
    unlabeled_ids: list[str] = []
    offset = 0
    total = collection.count()

    logger.info(f"[SCAN] Сканирование {total} документов...")

    while offset < total:
        result = collection.get(
            limit=batch_size,
            offset=offset,
            include=["metadatas"],
        )
        ids       = result["ids"]
        metadatas = result["metadatas"]

        for doc_id, meta in zip(ids, metadatas):
            if not meta or "sd_level" not in meta:
                unlabeled_ids.append(doc_id)

        offset += len(ids)
        logger.info(f"[SCAN] Прогресс: {min(offset, total)}/{total} проверено, "
                    f"найдено без разметки: {len(unlabeled_ids)}")

        # Безопасный выход если ChromaDB вернул пустой срез
        if not ids:
            break

    logger.info(f"[SCAN] ✅ Итого без SD-разметки: {len(unlabeled_ids)} блоков")
    return unlabeled_ids


def process_batch(
    collection: chromadb.Collection,
    labeler: SDLabeler,
    batch_ids: list[str],
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Прогнать один батч через SDLabeler и дозаписать metadata в ChromaDB.

    Алгоритм:
      1. Получить документы (тексты) из ChromaDB по ids
      2. Для каждого вызвать labeler.label_block()
      3. Смержить новые SD-поля с существующей metadata
      4. Вызвать collection.update() — документы и embeddings НЕ трогаются

    Returns:
        (success_count, error_count)
    """
    # Получаем тексты и текущую metadata для батча
    result = collection.get(
        ids=batch_ids,
        include=["documents", "metadatas"],
    )

    success = 0
    errors  = 0

    updated_ids:       list[str]  = []
    updated_metadatas: list[dict] = []

    for doc_id, document, current_meta in zip(
        result["ids"],
        result["documents"],
        result["metadatas"],
    ):
        try:
            sd_data = labeler.label_block(
                block_content=document or "",
                block_id=doc_id,
            )

            # Мержим: старые поля сохраняются, SD-поля добавляются
            new_meta = dict(current_meta or {})
            new_meta["sd_level"]        = sd_data.get("sd_level", "GREEN")
            new_meta["sd_secondary"]    = sd_data.get("sd_secondary") or ""
            new_meta["emotional_tone"]  = sd_data.get("emotional_tone", "neutral")
            new_meta["complexity_score"] = sd_data.get("complexity_score", 5)
            new_meta["sd_labeled_by"]   = "migrate_v4"
            new_meta["sd_labeled_at"]   = _now_iso()

            updated_ids.append(doc_id)
            updated_metadatas.append(new_meta)
            success += 1

        except Exception as exc:
            logger.error(f"[BATCH] Ошибка для block_id={doc_id}: {exc}")
            # Fallback: пишем GREEN, не останавливаемся
            fallback_meta = dict(current_meta or {})
            fallback_meta["sd_level"]       = "GREEN"
            fallback_meta["sd_secondary"]   = ""
            fallback_meta["emotional_tone"] = "neutral"
            fallback_meta["sd_labeled_by"]  = "migrate_v4_fallback"
            fallback_meta["sd_labeled_at"]  = _now_iso()

            updated_ids.append(doc_id)
            updated_metadatas.append(fallback_meta)
            errors += 1

    # Записываем в ChromaDB (только metadata, embeddings не трогаем)
    if updated_ids and not dry_run:
        collection.update(
            ids=updated_ids,
            metadatas=updated_metadatas,
        )
    elif dry_run:
        logger.info(f"[DRY-RUN] Пропускаем запись {len(updated_ids)} блоков")

    return success, errors


# ══════════════════════════════════════════════════════════════
# MAIN RUNNER
# ══════════════════════════════════════════════════════════════

def run_migration(
    collection_name: str = DEFAULT_COLLECTION,
    batch_size: int      = DEFAULT_BATCH_SIZE,
    chroma_path: str     = DEFAULT_CHROMA_PATH,
    llm_model: str       = DEFAULT_LLM_MODEL,
    dry_run: bool        = False,
    limit: Optional[int] = None,
) -> dict:
    """
    Главная функция миграции. Возвращает итоговую статистику.

    Args:
        collection_name: название коллекции в ChromaDB
        batch_size: сколько блоков обрабатывать за один LLM-запрос цикл
        chroma_path: путь к PersistentClient директории
        llm_model: модель OpenAI для SDLabeler
        dry_run: если True — только сканирует, не пишет в БД
        limit: ограничить число обрабатываемых блоков (для тестов)
    """
    logger.info("=" * 60)
    logger.info("🚀 СТАРТ МИГРАЦИИ SD-РАЗМЕТКИ")
    logger.info(f"   collection  : {collection_name}")
    logger.info(f"   chroma_path : {chroma_path}")
    logger.info(f"   batch_size  : {batch_size}")
    logger.info(f"   model       : {llm_model}")
    logger.info(f"   dry_run     : {dry_run}")
    logger.info("=" * 60)

    # 1. Подключение к ChromaDB
    collection = get_chroma_collection(chroma_path, collection_name)

    # 2. SDLabeler
    labeler = SDLabeler(model=llm_model, temperature=0.1)

    # 3. Найти все блоки без sd_level
    unlabeled_ids = fetch_unlabeled_ids(collection)

    if not unlabeled_ids:
        logger.info("✅ Все блоки уже размечены — миграция не нужна.")
        return {"total": 0, "processed": 0, "skipped": 0, "errors": 0, "distribution": {}}

    if limit:
        unlabeled_ids = unlabeled_ids[:limit]
        logger.info(f"[LIMIT] Обрабатываем только первые {limit} блоков")

    total_found     = len(unlabeled_ids)
    total_success   = 0
    total_errors    = 0
    processed_count = 0

    # 4. Обработка батчами
    for batch_start in range(0, total_found, batch_size):
        batch_ids = unlabeled_ids[batch_start : batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (total_found + batch_size - 1) // batch_size

        logger.info(
            f"\n[BATCH {batch_num}/{total_batches}] "
            f"Блоки {batch_start + 1}–{batch_start + len(batch_ids)} из {total_found}"
        )

        success, errors = process_batch(collection, labeler, batch_ids, dry_run=dry_run)
        total_success   += success
        total_errors    += errors
        processed_count += len(batch_ids)

        logger.info(
            f"[BATCH {batch_num}] ✅ {success} успешно, ❌ {errors} ошибок "
            f"| Всего обработано: {processed_count}/{total_found}"
        )

    # 5. Итоговая статистика по распределению SD-уровней
    distribution = _get_sd_distribution(collection, dry_run)
    _print_final_stats(total_found, total_success, total_errors, distribution)

    return {
        "total_found": total_found,
        "processed":   processed_count,
        "success":     total_success,
        "errors":      total_errors,
        "distribution": distribution,
    }


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _get_sd_distribution(
    collection: chromadb.Collection,
    dry_run: bool,
) -> dict[str, int]:
    """Подсчитать финальное распределение sd_level по всей коллекции."""
    if dry_run:
        return {}

    result = collection.get(include=["metadatas"])
    counts: Counter = Counter()
    for meta in result["metadatas"]:
        level = (meta or {}).get("sd_level", "UNKNOWN")
        counts[level] += 1
    return dict(counts)


def _print_final_stats(
    total_found: int,
    success: int,
    errors: int,
    distribution: dict[str, int],
) -> None:
    """Вывести итоговую статистику в лог."""
    logger.info("\n" + "=" * 60)
    logger.info("📊 ИТОГИ МИГРАЦИИ")
    logger.info(f"   Найдено без разметки : {total_found}")
    logger.info(f"   Успешно обработано   : {success}")
    logger.info(f"   Ошибок (fallback)    : {errors}")
    logger.info("-" * 40)
    if distribution:
        logger.info("   Распределение SD-уровней (вся коллекция):")
        for level, count in sorted(distribution.items(), key=lambda x: -x[^1]):
            bar = "█" * (count // max(1, max(distribution.values()) // 20))
            logger.info(f"   {level:<12} {count:>5}  {bar}")
    logger.info("=" * 60)


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Миграция: добавить SD-разметку к блокам ChromaDB без sd_level"
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help=f"Название коллекции ChromaDB (default: {DEFAULT_COLLECTION})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Размер батча (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--chroma-path",
        default=DEFAULT_CHROMA_PATH,
        help="Путь к директории PersistentClient ChromaDB",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_LLM_MODEL,
        help=f"OpenAI модель для SDLabeler (default: {DEFAULT_LLM_MODEL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только сканировать и логировать, не записывать в БД",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Обработать только N блоков (для тестового запуска)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    # Проверить что OPENAI_API_KEY есть
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY не задан. Установи переменную окружения.")
        sys.exit(1)

    stats = run_migration(
        collection_name=args.collection,
        batch_size=args.batch_size,
        chroma_path=args.chroma_path,
        llm_model=args.model,
        dry_run=args.dry_run,
        limit=args.limit,
    )

    exit_code = 0 if stats.get("errors", 0) == 0 else 1
    sys.exit(exit_code)
```


***

## 3. Команды запуска

```bash
# Тестовый прогон без записи в БД
python -m scripts.migrate_add_sd_labels --dry-run --limit 10

# Реальная миграция (все блоки)
python -m scripts.migrate_add_sd_labels

# Кастомные параметры
python -m scripts.migrate_add_sd_labels \
  --collection salamat_blocks \
  --batch-size 50 \
  --chroma-path ./data/chroma_db \
  --model gpt-4o-mini
```


***

## 4. Архитектурные решения

**Почему `collection.get()` а не `collection.query()`** — нужен полный скан всей коллекции для поиска блоков без `sd_level`. ChromaDB не поддерживает `$not_exists` в `where`-фильтрах, поэтому единственный корректный путь — загрузить все metadata и отфильтровать на Python-стороне.

**Почему `collection.update()` а не `collection.upsert()`** — `update()` гарантированно не перезаписывает документы и embeddings, обновляет только переданные metadata. `upsert()` мог бы затронуть векторы при некорректном вызове.

**Идемпотентность** достигается через `fetch_unlabeled_ids()`: при повторном запуске уже размеченные блоки (с полем `sd_level` в metadata) просто не попадают в список `unlabeled_ids`. Повторный прогон безопасен.

**Fallback-стратегия** — при любой ошибке LLM блок помечается `sd_level: "GREEN"` и скрипт продолжает работу. Поле `sd_labeled_by: "migrate_v4_fallback"` позволяет потом найти и перемаркировать именно эти блоки.

***

## 5. Карта изменений v4.0

```
voice_bot_pipeline/
└── scripts/
    └── migrate_add_sd_labels.py     ← СОЗДАТЬ (этот скрипт)

logs/
    └── migrate_sd_labels.log        ← создаётся автоматически
```

Никакие другие файлы не затрагиваются. `sd_labeler.py`, `sd_filter.py`, `sd_levels.yaml` — только читаются, не изменяются .

***

## 6. Пример вывода после успешной миграции

```
============================================================
📊 ИТОГИ МИГРАЦИИ
   Найдено без разметки : 843
   Успешно обработано   : 838
   Ошибок (fallback)    : 5
----------------------------------------
   Распределение SD-уровней (вся коллекция):
   GREEN        412  ████████████████████
   YELLOW       201  █████████
   ORANGE        98  ████
   BLUE          67  ███
   RED           35  █
   PURPLE        20  
   TURQUOISE      8  
   UNKNOWN        2  
============================================================
```

<div align="center">⁂</div>



