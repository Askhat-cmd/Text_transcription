# bot_agent/retriever.py
"""
Simple TF-IDF Retriever
=======================

Поиск релевантных блоков на основе TF-IDF + косинусного сходства.
"""

import hashlib
import logging
from time import sleep
from pathlib import Path
from typing import List, Tuple, Optional

import joblib
import numpy as np

from .data_loader import data_loader, Block
from .config import config
from .db_api_client import DBApiClient, DBApiUnavailableError, RetrievedChunk
from .embedding_provider import create_embedding_provider
from .feature_flags import feature_flags

logger = logging.getLogger(__name__)

CACHE_FORMAT_VERSION = "4.1.0"  # semantic fallback embeddings + model-aware cache
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
        self.semantic_matrix = None
        self.blocks: List[Block] = []
        self._embedding_provider = None
        self._semantic_ready = False
        self._is_built = False
        self.db_client = DBApiClient(
            base_url=config.BOT_DB_URL,
            timeout=float(getattr(config, "BOT_DB_TIMEOUT", 10.0)),
        )
    
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
        hasher.update(str(getattr(config, "EMBEDDING_MODEL", "")).encode())

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
                    cached_model = cached.get("embedding_model")
                    if cached_model == str(getattr(config, "EMBEDDING_MODEL", "")):
                        semantic = cached.get("semantic_matrix")
                        if semantic is not None:
                            self.semantic_matrix = np.asarray(semantic, dtype=np.float32)
                            self._semantic_ready = bool(self.semantic_matrix.size)
                    else:
                        self.semantic_matrix = None
                        self._semantic_ready = False
                    self._is_built = True
                    logger.info("[RETRIEVAL] TF-IDF loaded from cache (hash match)")
                    return
                except Exception as exc:
                    logger.warning("[RETRIEVAL] cache load failed: %s. Rebuilding.", exc)

        logger.info("[RETRIEVAL] building TF-IDF index")
        self._build_tfidf()
        self._build_semantic_index()

        if not self.blocks or self.tfidf_matrix is None:
            logger.warning("[RETRIEVAL] no blocks to cache; skipping TF-IDF cache save")
            return

        try:
            joblib.dump(
                {
                    "vectorizer": self.vectorizer,
                    "matrix": self.tfidf_matrix,
                    "blocks": self.blocks,
                    "semantic_matrix": self.semantic_matrix,
                    "embedding_model": str(getattr(config, "EMBEDDING_MODEL", "")),
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
    def _normalize_vectors(vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return vectors / norms

    def _get_embedding_provider(self):
        if self._embedding_provider is None:
            self._embedding_provider = create_embedding_provider(
                model_name=str(getattr(config, "EMBEDDING_MODEL", "")),
                device=str(getattr(config, "EMBEDDING_DEVICE", "auto")),
            )
        return self._embedding_provider

    def _build_semantic_index(self) -> None:
        self.semantic_matrix = None
        self._semantic_ready = False
        if not feature_flags.enabled("ENABLE_EMBEDDING_PROVIDER"):
            logger.info("[RETRIEVAL] semantic index disabled by feature flag")
            return
        if not self.blocks:
            return

        try:
            provider = self._get_embedding_provider()
            texts = [b.get_search_text() for b in self.blocks]
            vectors = provider.embed_passages(texts)
            matrix = np.asarray(vectors, dtype=np.float32)
            if matrix.ndim != 2 or matrix.shape[0] != len(self.blocks):
                logger.warning("[RETRIEVAL] semantic index skipped: invalid embedding shape=%s", getattr(matrix, "shape", None))
                return
            self.semantic_matrix = self._normalize_vectors(matrix)
            self._semantic_ready = True
            logger.info(
                "[RETRIEVAL] semantic index built: model=%s dim=%s blocks=%s",
                provider.model_name(),
                self.semantic_matrix.shape[1],
                self.semantic_matrix.shape[0],
            )
        except Exception as exc:
            logger.warning("[RETRIEVAL] semantic index unavailable, fallback to TF-IDF only: %s", exc)

    def _semantic_fallback(self, query: str, top_k: int) -> List[Tuple[Block, float]]:
        if not self._is_built:
            self.build_index()
        if not self._semantic_ready or self.semantic_matrix is None:
            return []
        try:
            provider = self._get_embedding_provider()
            query_vec = np.asarray(provider.embed_query(query), dtype=np.float32)
            if query_vec.ndim != 1:
                query_vec = query_vec.reshape(-1)
            norm = np.linalg.norm(query_vec)
            if norm == 0.0:
                return []
            query_vec = query_vec / norm
            similarities = self.semantic_matrix @ query_vec
            top_indices = np.argsort(-similarities)[: top_k * 2]
            results: List[Tuple[Block, float]] = []
            for idx in top_indices:
                score = float(similarities[idx])
                if score >= config.MIN_RELEVANCE_SCORE:
                    results.append((self.blocks[idx], score))
                if len(results) >= top_k:
                    break
            if results:
                logger.info("[RETRIEVAL] semantic fallback found %s blocks", len(results))
                for i, (block, score) in enumerate(results[:10], start=1):
                    title = (block.title or "")[:60]
                    logger.info(
                        "[RETRIEVAL]   [%s] score=%.4f block_id=%s title=%s",
                        i,
                        score,
                        block.block_id,
                        title,
                    )
            return results
        except Exception as exc:
            logger.warning("[RETRIEVAL] semantic fallback failed: %s", exc)
            return []

    @staticmethod
    def _sd_int_to_name(value: int) -> Optional[str]:
        # Legacy compatibility: Bot_data_base still может возвращать int SD.
        mapping = {
            1: "BEIGE",
            2: "PURPLE",
            3: "RED",
            4: "BLUE",
            5: "ORANGE",
            6: "GREEN",
            7: "YELLOW",
            8: "TURQUOISE",
        }
        return mapping.get(int(value))

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
        top_k: int,
        author_id: Optional[str] = None,
    ) -> List[Tuple[Block, float]]:
        chunks = self.db_client.query(
            query=query,
            top_k=top_k,
            author_id=author_id,
            use_rerank=True,
            search_mode="hybrid",
        )
        results: List[Tuple[Block, float]] = []
        for chunk in chunks:
            results.append((self._chunk_to_block(chunk), float(chunk.score)))
        return results

    def _api_retrieve_with_retry(
        self,
        query: str,
        top_k: int,
        author_id: Optional[str] = None,
    ) -> List[Tuple[Block, float]]:
        """
        Retry API retrieval for transient connectivity/timeout issues.
        """
        max_attempts = 2
        last_exc: Optional[DBApiUnavailableError] = None
        for attempt in range(1, max_attempts + 1):
            try:
                return self._api_retrieve(
                    query=query,
                    top_k=top_k,
                    author_id=author_id,
                )
            except DBApiUnavailableError as exc:
                last_exc = exc
                if exc.kind not in {"timeout", "connect", "http_status"} or attempt >= max_attempts:
                    raise
                logger.warning(
                    "[RETRIEVAL] API retry %s/%s after transient error kind=%s",
                    attempt,
                    max_attempts,
                    exc.kind,
                )
                sleep(0.2 * attempt)
        if last_exc is not None:
            raise last_exc
        return []
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        author_id: Optional[str] = None,
        **legacy_kwargs,
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
        sd_level = legacy_kwargs.pop("sd_level", None)
        if sd_level not in (None, 0):
            logger.info("[RETRIEVAL] legacy sd_level=%s ignored (v11.0 contract)", sd_level)
        if legacy_kwargs:
            logger.debug("[RETRIEVAL] ignored legacy kwargs in retrieve(): %s", sorted(legacy_kwargs.keys()))

        degraded_mode = bool(getattr(config, "DEGRADED_MODE", False))
        data_source = str(getattr(config, "DATA_SOURCE", "") or "").lower()
        if degraded_mode and data_source == "degraded":
            logger.warning(
                "[RETRIEVER] DEGRADED_MODE active. Retrieval returns 0 blocks. reason=no_data_source"
            )
            return []

        # ================================================================
        # Новый путь: Bot_data_base HTTP API (cascading fallback)
        # Активируется только для KNOWLEDGE_SOURCE=api|chromadb
        # ================================================================
        if config.KNOWLEDGE_SOURCE in ("api", "chromadb"):
            try:
                api_results = self._api_retrieve_with_retry(
                    query=query,
                    top_k=top_k,
                    author_id=author_id,
                )
                if api_results:
                    logger.info("[RETRIEVAL] API search: %d блоков", len(api_results))
                    return api_results
                logger.info("[RETRIEVAL] API search вернул 0 результатов → TF-IDF fallback")
            except DBApiUnavailableError as exc:
                if exc.kind == "http_status":
                    logger.warning(
                        "[RETRIEVAL] API fallback: kind=%s status=%s message=%s",
                        exc.kind,
                        exc.status_code,
                        exc,
                    )
                else:
                    logger.warning(
                        "[RETRIEVAL] API fallback: kind=%s message=%s",
                        exc.kind,
                        exc,
                    )
            if feature_flags.enabled("ENABLE_EMBEDDING_PROVIDER"):
                semantic_results = self._semantic_fallback(query, top_k)
                if semantic_results:
                    return semantic_results
            else:
                logger.info("[RETRIEVAL] semantic fallback disabled by feature flag")
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
