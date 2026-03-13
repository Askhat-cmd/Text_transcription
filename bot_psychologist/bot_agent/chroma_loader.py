"""
ChromaLoader — HTTP-клиент к Bot_data_base API
===============================================

Конфигурация через .env:
  CHROMA_API_URL=http://localhost:8003
  CHROMA_COLLECTION=bot_knowledge

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

        Стратегия:
          1. GET /api/registry/export/merged → читаем файл по пути
          2. POST /api/query/ с пустым запросом — fallback
          3. GET /api/registry/ + загрузка по источникам — последний fallback

        Результат кэшируется. Вызывать invalidate_cache() при добавлении источников.
        """
        if self._all_blocks_cache is not None:
            logger.info(f"[CHROMA] Используем кэш: {len(self._all_blocks_cache)} блоков")
            return self._all_blocks_cache

        logger.info(f"[CHROMA] Загрузка всех блоков из {self.api_url}")
        blocks: List[Block] = []

        # Попытка 1: /api/registry/export/merged → читаем файл напрямую
        try:
            resp = self._session.get(
                f"{self.api_url}{self.EXPORT_MERGED_URL}",
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                file_path = data.get("path")
                if file_path:
                    import json
                    with open(file_path, 'r', encoding='utf-8') as f:
                        merged_data = json.load(f)
                    raw_list = merged_data.get("blocks", []) if isinstance(merged_data, dict) else merged_data
                    blocks = [self._parse_block(b, {}) for b in raw_list]
                    logger.info(f"[CHROMA] Export merged: {len(blocks)} блоков из {file_path}")
                    self._all_blocks_cache = blocks
                    return blocks
                else:
                    logger.warning(f"[CHROMA] export/merged не вернул path")
            else:
                logger.info(f"[CHROMA] /api/registry/export/merged вернул {resp.status_code} → пробуем registry")
        except requests.RequestException as e:
            logger.warning(f"[CHROMA] export/merged ошибка: {e} → пробуем registry")
        except Exception as e:
            logger.warning(f"[CHROMA] export/merged file read error: {e} → пробуем registry")

        # Попытка 2: через registry
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
