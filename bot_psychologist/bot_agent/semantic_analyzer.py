# bot_agent/semantic_analyzer.py
"""
Semantic Analyzer for Phase 2
=============================

Анализирует семантические отношения между концептами в найденных блоках.
Извлекает primary_concepts, related_concepts, conceptual_links.
"""

import logging
from typing import List, Dict
from collections import defaultdict

from .data_loader import Block

logger = logging.getLogger(__name__)


class SemanticAnalyzer:
    """
    Анализирует семантические отношения между концептами в найденных блоках.
    
    Phase 2: Используется для извлечения концептов и их связей
    на основе graph_entities из SAG v2.0.
    
    Usage:
        >>> analyzer = SemanticAnalyzer()
        >>> relations = analyzer.analyze_relations(blocks)
        >>> print(relations["primary_concepts"])
    """
    
    def analyze_relations(self, blocks: List[Block]) -> Dict:
        """
        Анализирует и возвращает структурированные отношения между концептами.
        
        Args:
            blocks: Список блоков для анализа
            
        Returns:
            Dict с ключами:
                - "primary_concepts": List[str] — основные концепты
                - "related_concepts": Dict[str, List[str]] — связанные концепты
                - "conceptual_links": List[Dict] — связи между концептами
                - "analysis_summary": str — текстовое резюме
        """
        if not blocks:
            return {
                "primary_concepts": [],
                "related_concepts": {},
                "conceptual_links": [],
                "analysis_summary": "Нет блоков для анализа."
            }
        
        logger.debug(f"🧠 Семантический анализ {len(blocks)} блоков...")
        
        # Собираем все концепты и их частоту
        concept_freq = defaultdict(int)
        block_concepts = []
        
        for block in blocks:
            entities = block.graph_entities or []
            block_concepts.append({
                "block_id": block.block_id,
                "entities": entities,
                "depth": block.conceptual_depth,
                "title": block.title
            })
            for entity in entities:
                concept_freq[entity] += 1
        
        # Основные концепты (с наибольшей частотой)
        primary_concepts = sorted(
            concept_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        primary_concept_names = [c[0] for c in primary_concepts]
        
        # Анализируем связи между концептами через блоки
        related_concepts = self._find_related_concepts(
            block_concepts,
            primary_concept_names
        )
        
        # Формируем отношения
        conceptual_links = self._extract_conceptual_links(
            blocks,
            primary_concept_names
        )
        
        # Генерируем резюме
        analysis_summary = self._generate_analysis_summary(
            primary_concept_names,
            len(blocks),
            concept_freq
        )
        
        result = {
            "primary_concepts": primary_concept_names,
            "related_concepts": related_concepts,
            "conceptual_links": conceptual_links,
            "analysis_summary": analysis_summary
        }
        
        logger.debug(f"✅ Анализ завершён: {len(primary_concept_names)} основных концептов, "
                    f"{len(conceptual_links)} связей")
        
        return result
    
    def _find_related_concepts(
        self,
        block_concepts: List[Dict],
        primary_concepts: List[str]
    ) -> Dict[str, List[str]]:
        """
        Находит концепты, связанные с основными через совместное появление в блоках.
        
        Args:
            block_concepts: Список словарей с концептами каждого блока
            primary_concepts: Список основных концептов
            
        Returns:
            Dict[str, List[str]] — для каждого основного концепта список связанных
        """
        related = {}
        
        for primary in primary_concepts:
            related_set = set()
            
            for block_data in block_concepts:
                if primary in block_data["entities"]:
                    # Добавляем все остальные концепты из этого блока
                    for other in block_data["entities"]:
                        if other != primary:
                            related_set.add(other)
            
            # Топ 5 связанных концептов
            related[primary] = list(related_set)[:5]
        
        return related
    
    def _extract_conceptual_links(
        self,
        blocks: List[Block],
        primary_concepts: List[str]
    ) -> List[Dict]:
        """
        Извлекает связи между концептами на основе совместного появления.
        
        Args:
            blocks: Список блоков
            primary_concepts: Список основных концептов
            
        Returns:
            List[Dict] — список связей с полями from, to, type, source_block, context
        """
        links = []
        seen_pairs = set()  # Избегаем дублирования
        
        for block in blocks:
            entities = block.graph_entities or []
            # Ищем блоки, содержащие несколько основных концептов
            main_in_block = [c for c in primary_concepts if c in entities]
            
            if len(main_in_block) >= 2:
                for i, concept1 in enumerate(main_in_block):
                    for concept2 in main_in_block[i+1:]:
                        # Создаём уникальный ключ пары
                        pair_key = tuple(sorted([concept1, concept2]))
                        
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            links.append({
                                "from": concept1,
                                "to": concept2,
                                "type": "co-occurs",
                                "source_block": block.block_id,
                                "context": block.title
                            })
        
        # Ограничиваем количество связей
        return links[:10]
    
    def _generate_analysis_summary(
        self,
        primary_concepts: List[str],
        block_count: int,
        concept_freq: Dict[str, int]
    ) -> str:
        """
        Генерирует текстовое резюме семантического анализа.
        
        Args:
            primary_concepts: Основные концепты
            block_count: Количество проанализированных блоков
            concept_freq: Частота появления концептов
            
        Returns:
            Строка с резюме анализа
        """
        if not primary_concepts:
            return "Анализ не выполнен: концепты не найдены."
        
        # Форматируем основные концепты с частотой
        concepts_str = " → ".join(primary_concepts[:3])
        total_concepts = len(concept_freq)
        
        return (
            f"Найдено {block_count} релевантных блоков. "
            f"Всего {total_concepts} уникальных концептов. "
            f"Основные темы: {concepts_str}."
        )
    
    def get_concept_frequency(self, blocks: List[Block]) -> Dict[str, int]:
        """
        Получить частоту всех концептов в блоках.
        
        Args:
            blocks: Список блоков
            
        Returns:
            Dict[str, int] — концепт -> количество появлений
        """
        freq = defaultdict(int)
        for block in blocks:
            for entity in (block.graph_entities or []):
                freq[entity] += 1
        return dict(freq)
    
    def get_blocks_by_concept(
        self,
        blocks: List[Block],
        concept: str
    ) -> List[Block]:
        """
        Получить все блоки, содержащие указанный концепт.
        
        Args:
            blocks: Список блоков
            concept: Искомый концепт
            
        Returns:
            Список блоков, содержащих концепт
        """
        return [
            b for b in blocks
            if concept in (b.graph_entities or [])
        ]
