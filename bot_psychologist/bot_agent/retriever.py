# bot_agent/retriever.py
"""
Simple TF-IDF Retriever
=======================

Поиск релевантных блоков на основе TF-IDF + косинусного сходства.
"""

import logging
from typing import List, Tuple, Optional
import numpy as np

from .data_loader import data_loader, Block
from .config import config

logger = logging.getLogger(__name__)


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
            logger.info("✓ Индекс уже построен")
            return
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            logger.error("❌ scikit-learn не установлен. Установите: pip install scikit-learn")
            raise
        
        logger.info("🔨 Строю TF-IDF индекс...")
        self.blocks = data_loader.get_all_blocks()
        
        if not self.blocks:
            logger.warning("⚠️ Нет блоков для индексирования!")
            return
        
        # Формируем текст для каждого блока: title + keywords + summary
        texts = [block.get_search_text() for block in self.blocks]
        
        # TF-IDF с символьными n-граммами (лучше для русского языка)
        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',      # символьный анализ с word boundaries
            ngram_range=(2, 4),      # 2-4 символьные n-граммы
            max_features=10000,      # ограничение размера словаря
            lowercase=True,
            strip_accents='unicode'
        )
        
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        self._is_built = True
        
        logger.info(f"✅ Индекс построен для {len(self.blocks)} блоков")
    
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
        
        if not self._is_built:
            self.build_index()
        
        if not self.blocks or self.tfidf_matrix is None:
            logger.warning("⚠️ Индекс пуст!")
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
        
        logger.debug(f"🔍 Найдено {len(results)} релевантных блоков для: '{query[:50]}...'")
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

