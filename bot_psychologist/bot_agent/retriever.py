# bot_agent/retriever.py
"""
Simple TF-IDF Retriever
=======================

Поиск релевантных блоков на основе TF-IDF + косинусного сходства.
"""

import hashlib
import logging
import time
from pathlib import Path
from typing import List, Tuple, Optional

import joblib
import numpy as np

from .data_loader import data_loader, Block
from .config import config
from .db_api_client import DBApiClient, DBApiUnavailableError, RetrievedChunk
from .sd_classifier import SD_LEVELS_ORDER

logger = logging.getLogger(__name__)

CACHE_FORMAT_VERSION = "4.0.0"  # bumped: universal Block + ChromaDB support
CACHE_DIR = config.CACHE_DIR
TFIDF_CACHE_PATH = CACHE_DIR / "tfidf_cache.joblib"
TFIDF_HASH_PATH = CACHE_DIR / "tfidf_cache.hash"


class SimpleRetriever:
    """
    Простой retriever на основе TF-IDF + косинусного сходства.
    
    Используется для Phase 1 как fallback если нет ChromaDB.
    
    Usage:
        >>> retriever = SimpleRetriever()
        >>> retriever.build_index()
        >>> results = retriever.retrieve("Что такое осознавание?")
        >>> for block, score in results:
        ...     print(f"{block.title}: {score:.2f}")
    """
    
    def __init__(self):
        self.vectorizer = None
        self.tfidf_matrix = None
        self.blocks: List[Block] = []
        self._is_built = False
        self.db_client = DBApiClient()
    
    def build_index(self) -> None:
        """
        Построить TF-IDF индекс на основе всех блоков.
        
        Использует символьные n-граммы для лучшей работы с русским языком.
        """
        if self._is_built:
            logger.info("[RETRIEVAL] index already built")
            return
        self._build_or_load_tfidf()

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

        else:  # chromadb/api
            try:
                merged_path = Path(getattr(config, "ALL_BLOCKS_MERGED_PATH", "") or "")
                if merged_path and merged_path.exists():
                    hasher.update(merged_path.read_bytes())
                    return hasher.hexdigest()

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

    def _build_or_load_tfidf(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        current_hash = self._compute_data_hash()

        if TFIDF_CACHE_PATH.exists() and TFIDF_HASH_PATH.exists():
            saved_hash = TFIDF_HASH_PATH.read_text(encoding="utf-8").strip()
            if saved_hash == current_hash:
                try:
                    cached = joblib.load(TFIDF_CACHE_PATH)
                    self.vectorizer = cached.get("vectorizer")
                    self.tfidf_matrix = cached.get("matrix")
                    self.blocks = cached.get("blocks", [])
                    self._is_built = True
                    logger.info("[RETRIEVAL] TF-IDF loaded from cache (hash match)")
                    return
                except Exception as exc:
                    logger.warning("[RETRIEVAL] cache load failed: %s. Rebuilding.", exc)

        logger.info("[RETRIEVAL] building TF-IDF index")
        self._build_tfidf()

        if not self.blocks or self.tfidf_matrix is None:
            logger.warning("[RETRIEVAL] no blocks to cache; skipping TF-IDF cache save")
            return

        try:
            joblib.dump(
                {
                    "vectorizer": self.vectorizer,
                    "matrix": self.tfidf_matrix,
                    "blocks": self.blocks,
                    "cache_version": CACHE_FORMAT_VERSION,
                },
                TFIDF_CACHE_PATH,
                compress=3,
            )
            TFIDF_HASH_PATH.write_text(current_hash, encoding="utf-8")
            logger.info("[RETRIEVER] TF-IDF matrix cached successfully")
        except Exception as exc:
            logger.warning("[RETRIEVER] Could not save cache: %s", exc)

    def _build_tfidf(self) -> None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            logger.error("[RETRIEVAL] scikit-learn is not installed", exc_info=True)
            raise

        self.blocks = data_loader.get_all_blocks()

        if not self.blocks:
            logger.warning("[RETRIEVAL] no blocks available for indexing")
            return

        texts = [block.get_search_text() for block in self.blocks]

        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 4),
            max_features=10000,
            lowercase=True,
            strip_accents='unicode'
        )

        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        self._is_built = True
        logger.info("[RETRIEVAL] index built for %s blocks", len(self.blocks))

    @staticmethod
    def _sd_int_to_name(value: int) -> Optional[str]:
        if 1 <= int(value) <= len(SD_LEVELS_ORDER):
            return SD_LEVELS_ORDER[int(value) - 1]
        return None

    @staticmethod
    def _format_seconds(value: Optional[int]) -> str:
        if value is None:
            return "00:00:00"
        try:
            total = int(value)
            hours = total // 3600
            minutes = (total % 3600) // 60
            seconds = total % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except Exception:
            return "00:00:00"

    def _chunk_to_block(self, chunk: RetrievedChunk) -> Block:
        title = chunk.block_title or (chunk.content[:60] if chunk.content else "Фрагмент")
        sd_name = self._sd_int_to_name(chunk.sd_level)
        return Block(
            block_id=chunk.chunk_id,
            title=title,
            content=chunk.content or "",
            summary=title,
            video_id="",
            start=self._format_seconds(chunk.start_time),
            end=self._format_seconds(chunk.end_time),
            youtube_link=chunk.youtube_url or "",
            keywords=chunk.keywords or [],
            block_type=None,
            emotional_tone=None,
            conceptual_depth=None,
            complexity_score=5.0,
            graph_entities=[],
            sd_level=sd_name,
            sd_secondary=None,
            sd_confidence=None,
            source_type=chunk.source_type or "book",
            author=chunk.author_name or "",
            author_id=chunk.author_id or "",
            chunk_index=0,
            language="ru",
        )

    def _api_retrieve(
        self,
        query: str,
        sd_level: int,
        top_k: int,
        author_id: Optional[str] = None,
    ) -> List[Tuple[Block, float]]:
        chunks = self.db_client.query(
            query=query,
            sd_level=sd_level,
            top_k=top_k,
            author_id=author_id,
            use_rerank=True,
            search_mode="hybrid",
        )
        results: List[Tuple[Block, float]] = []
        for chunk in chunks:
            results.append((self._chunk_to_block(chunk), float(chunk.score)))
        return results
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        sd_level: int = 0,
        author_id: Optional[str] = None,
    ) -> List[Tuple[Block, float]]:
        """
        Найти top_k релевантных блоков для запроса.

        Args:
            query: Текст запроса на русском языке
            top_k: Количество результатов (по умолчанию из config)

        Returns:
            Список кортежей (Block, score), отсортированный по убыванию score
        """
        if top_k is None:
            top_k = config.TOP_K_BLOCKS

        logger.info(
            "[RETRIEVAL] query='%s' top_k=%s source=%s",
            query[:80], top_k, config.KNOWLEDGE_SOURCE
        )

        # ================================================================
        # Новый путь: Bot_data_base HTTP API (cascading fallback)
        # Активируется только для KNOWLEDGE_SOURCE=api|chromadb
        # ================================================================
        if config.KNOWLEDGE_SOURCE in ("api", "chromadb"):
            try:
                api_results = self._api_retrieve(
                    query=query,
                    sd_level=sd_level,
                    top_k=top_k,
                    author_id=author_id,
                )
                if api_results:
                    logger.info("[RETRIEVAL] API search: %d блоков", len(api_results))
                    return api_results
                if sd_level > 0:
                    logger.warning(
                        "[RETRIEVAL] API 0 результатов с sd_level=%s → повтор без фильтра",
                        sd_level,
                    )
                    api_results = self._api_retrieve(
                        query=query,
                        sd_level=0,
                        top_k=top_k,
                        author_id=author_id,
                    )
                    return api_results
                logger.info("[RETRIEVAL] API search вернул 0 результатов → TF-IDF fallback")
            except DBApiUnavailableError as exc:
                logger.warning("[RETRIEVAL] API недоступен → TF-IDF fallback: %s", exc)
        # ================================================================

        return self._tfidf_fallback(query, top_k)

    def _tfidf_fallback(self, query: str, top_k: int) -> List[Tuple[Block, float]]:
        if not self._is_built:
            self.build_index()

        if not self.blocks or self.tfidf_matrix is None:
            logger.warning("[RETRIEVAL] empty index")
            return []

        from sklearn.metrics.pairwise import cosine_similarity

        # Трансформируем запрос в TF-IDF вектор
        query_vec = self.vectorizer.transform([query])

        # Считаем косинусное сходство с каждым блоком
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Берём top_k индексов с наибольшим сходством
        top_indices = np.argsort(-similarities)[:top_k * 2]  # берём больше для фильтрации

        # Фильтруем по минимальному порогу релевантности
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= config.MIN_RELEVANCE_SCORE:
                results.append((self.blocks[idx], score))
                if len(results) >= top_k:
                    break

        logger.info("[RETRIEVAL] tfidf found %s blocks", len(results))
        for i, (block, score) in enumerate(results[:10], start=1):
            title = (block.title or "")[:60]
            logger.info("[RETRIEVAL]   [%s] score=%.4f block_id=%s title=%s", i, score, block.block_id, title)
        return results


# Глобальный инстанс
_retriever_instance: Optional[SimpleRetriever] = None


def get_retriever() -> SimpleRetriever:
    """
    Получить экземпляр retriever'а (синглтон).
    
    Returns:
        SimpleRetriever: Инстанс retriever'а
    """
    global _retriever_instance
    
    if _retriever_instance is None:
        logger.debug("📦 Создаю SimpleRetriever")
        _retriever_instance = SimpleRetriever()
    
    return _retriever_instance
