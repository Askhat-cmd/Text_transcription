# bot_agent/retriever.py
"""
Simple TF-IDF Retriever
=======================

Поиск релевантных блоков на основе TF-IDF + косинусного сходства.
"""

import hashlib
import logging
import time
from typing import List, Tuple, Optional

import joblib
import numpy as np

from .data_loader import data_loader, Block
from .config import config

logger = logging.getLogger(__name__)

CACHE_FORMAT_VERSION = "3.0.2"
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
        hasher = hashlib.md5()
        hasher.update(CACHE_FORMAT_VERSION.encode())
        for file_path in sorted(config.SAG_FINAL_DIR.glob("**/*.for_vector.json")):
            hasher.update(file_path.read_bytes())
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
    
    def retrieve(
        self, 
        query: str, 
        top_k: Optional[int] = None
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

        logger.info("[RETRIEVAL] cache_check hash=%s ts=%.6f", hash(query), time.time())
        logger.info("[RETRIEVAL] query='%s' top_k=%s", query, top_k)
        
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



