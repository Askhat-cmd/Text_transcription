"""
ChromaLoader — HTTP-клиент к Bot_data_base API
===============================================

Конфигурация через .env:
  CHROMA_API_URL=http://localhost:8004
  CHROMA_COLLECTION=bot_knowledge
  ALL_BLOCKS_MERGED_PATH=C:/.../Bot_data_base/data/processed/all_blocks_merged.json

Подтверждённые эндпоинты Bot_data_base:
  GET  /api/registry/         → список всех источников
  GET  /api/registry/stats    → статистика и health check
  POST /api/ingest/book       → ингест книги
  GET  /api/status/{job_id}   → статус задачи

Эндпоинты для поиска и загрузки блоков:
  POST /api/query/            → семантический поиск
  GET  /api/blocks/{source_id} → блоки источника
  GET  /api/export/{source_id} → экспорт блоков

СТРАТЕГИЯ FALLBACK:
  Если /api/query/ недоступен (404) → retriever использует TF-IDF
  Если /api/blocks/ недоступен → пробуем /api/export/
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any

import requests

from .data_loader import Block, _detect_block_type
from .config import config
from .embedding_provider import create_embedding_provider

logger = logging.getLogger(__name__)


class ChromaLoader:
    """
    HTTP-клиент к Bot_data_base.

    Два режима:
      1. get_all_blocks()  — все блоки (для TF-IDF индекса в DataLoader)
      2. query_blocks()    — семантический поиск через ChromaDB эмбеддинги

    Оба возвращают объекты Block — совместимы со всеми модулями бота.
    """

    # Endpoints
    REGISTRY_URL = "/api/registry/"
    STATS_URL = "/api/registry/stats"
    EXPORT_MERGED_URL = "/api/registry/export/merged"  # Экспорт всех блоков
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
        self._query_endpoint_available: Optional[bool] = None
        self._blocks_endpoint_available: Optional[bool] = None

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def get_all_blocks(self) -> List[Block]:
        """
        Загрузить все блоки из Bot_data_base.

        СТРАТЕГИЯ (в порядке приоритета):
          1. Читать all_blocks_merged.json напрямую с диска
             (Bot_data_base/data/processed/all_blocks_merged.json)
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
        merged_path = config.ALL_BLOCKS_MERGED_PATH
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

    def rebuild_parallel_collection(
        self,
        *,
        confirm: bool = False,
        backup_tag: str = "pre-migration",
        collection_prefix: str = "psychologist",
        persist_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Безопасная переиндексация блоков в отдельную локальную Chroma-коллекцию.

        - Запуск только с confirm=True.
        - Проверяет, что в корне mono-репозитория есть backup с указанным тегом.
        - Создает новую коллекцию psychologist_<model_tag> (или *_timestamp, если имя занято).
        - Старые коллекции не удаляются.
        """
        if not confirm:
            raise ValueError(
                "Переиндексация заблокирована: сначала сделайте backup и затем повторите с --confirm."
            )

        repo_root = Path(__file__).resolve().parents[2]
        backups_dir = repo_root / "backups"
        backup_candidates = sorted(backups_dir.glob(f"chroma_{backup_tag}_*")) if backups_dir.exists() else []
        if not backup_candidates:
            raise ValueError(
                f"Не найден backup с тегом '{backup_tag}' в {backups_dir}. "
                "Без backup переиндексация запрещена."
            )

        blocks = self.get_all_blocks()
        if not blocks:
            raise RuntimeError("Нет блоков для переиндексации")

        provider = create_embedding_provider(
            model_name=str(getattr(config, "EMBEDDING_MODEL", "")),
            device=str(getattr(config, "EMBEDDING_DEVICE", "auto")),
        )
        model_tag = re.sub(r"[^a-zA-Z0-9_-]+", "-", provider.model_name().split("/")[-1]).strip("-").lower()
        if not model_tag:
            model_tag = "embedding"

        base_collection_name = f"{collection_prefix}_{model_tag}"
        chroma_path = Path(persist_path) if persist_path else (Path(config.PROJECT_ROOT) / "data" / "chroma_rebuild")
        chroma_path.mkdir(parents=True, exist_ok=True)

        try:
            import chromadb
            from chromadb.config import Settings
        except Exception as exc:
            raise RuntimeError("Для rebuild нужен пакет chromadb в окружении bot_psychologist") from exc

        client = chromadb.PersistentClient(path=str(chroma_path), settings=Settings(anonymized_telemetry=False))
        collection = client.get_or_create_collection(name=base_collection_name)
        collection_name = base_collection_name
        if collection.count() > 0:
            collection_name = f"{base_collection_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            collection = client.get_or_create_collection(name=collection_name)

        batch_size = 128
        indexed = 0
        seen_ids: set[str] = set()
        for start in range(0, len(blocks), batch_size):
            batch = blocks[start : start + batch_size]
            texts = [b.content or b.summary or b.title for b in batch]
            embeddings = provider.embed_passages(texts)
            ids: List[str] = []
            metadatas = []
            for i, b in enumerate(batch):
                block_id = b.block_id or f"{collection_name}:{start + i}"
                if block_id in seen_ids:
                    block_id = f"{block_id}:{start + i}"
                seen_ids.add(block_id)
                ids.append(block_id)
                metadatas.append(
                    {
                        "block_id": block_id,
                        "title": b.title,
                        "source_type": b.source_type,
                        "author_id": b.author_id,
                        "author": b.author,
                        "sd_level": b.sd_level,
                        "source_title": b.document_title,
                        "chunk_index": int(b.chunk_index or 0),
                        "language": b.language,
                    }
                )
            collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
            indexed += len(batch)

        result = {
            "collection_name": collection_name,
            "model_name": provider.model_name(),
            "indexed_blocks": indexed,
            "persist_path": str(chroma_path),
            "backup_used": str(backup_candidates[-1]),
        }
        logger.info("[CHROMA] rebuild complete: %s", result)
        return result

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
                    self._blocks_endpoint_available = False
                    logger.info("[CHROMA] /api/blocks/ не реализован → пробуем /api/export/")
            except requests.RequestException:
                pass

        try:
            url = f"{self.api_url}{self.EXPORT_URL.format(source_id=source_id)}"
            resp = self._session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                raw = data if isinstance(data, list) else data.get("blocks", [])
                return [self._parse_block(b, entry) for b in raw]
        except requests.RequestException:
            pass

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
