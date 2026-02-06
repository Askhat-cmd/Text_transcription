# bot_agent/practices_recommender.py
"""
Practices Recommender for Phase 3
=================================

Рекомендует практики, техники, упражнения на основе Knowledge Graph.
Строит пути обучения между концептами.

Использует:
    - graph_client для навигации по Knowledge Graph
    - data_loader для связи с блоками контента
"""

import logging
from typing import List, Dict, Optional

from .graph_client import graph_client
from .data_loader import data_loader, Block

logger = logging.getLogger(__name__)


class PracticesRecommender:
    """
    Рекомендатор практик на основе Knowledge Graph.
    
    Находит практики для концептов, строит пути обучения,
    связывает практики с блоками контента.
    
    Usage:
        >>> from practices_recommender import practices_recommender
        >>> result = practices_recommender.suggest_practices_for_concept("осознавание")
        >>> path = practices_recommender.get_learning_path("осознавание")
    """
    
    def __init__(self):
        self._is_initialized = False
    
    def _ensure_initialized(self) -> None:
        """Ленивая инициализация: загрузить графы при первом использовании"""
        if not self._is_initialized:
            graph_client.load_graphs_from_all_documents()
            self._is_initialized = True
    
    def suggest_practices_for_concept(
        self,
        concept: str,
        limit: int = 5
    ) -> Dict:
        """
        Рекомендовать практики для концепта.
        
        Находит практики через Knowledge Graph и связывает их
        с блоками контента для получения источников.
        
        Args:
            concept: Имя концепта
            limit: Максимальное количество практик
            
        Returns:
            Dict:
                - concept: str — имя концепта
                - practices: List[Dict] — список практик
                - error: Optional[str] — ошибка если нет практик
        """
        self._ensure_initialized()
        
        logger.info(f"🎯 Ищу практики для концепта: '{concept}'")
        
        # Получаем практики из графа
        practices_from_graph = graph_client.get_practices_for_concept(concept)
        
        if not practices_from_graph:
            logger.debug(f"⚠️ Практики не найдены в графе для '{concept}'")
            return {
                "concept": concept,
                "practices": [],
                "error": "no_practices_found"
            }
        
        # Сортируем по уверенности и берём топ-N
        practices_from_graph.sort(key=lambda p: p["confidence"], reverse=True)
        practices_from_graph = practices_from_graph[:limit]
        
        # Находим блоки, где эти практики упоминаются
        all_blocks = data_loader.get_all_blocks()
        
        result_practices = []
        
        for practice_info in practices_from_graph:
            practice_name = practice_info["practice_name"]
            
            # Ищем блоки, содержащие эту практику в graph_entities
            relevant_blocks = self._find_blocks_for_entity(practice_name, all_blocks)
            
            result_practices.append({
                "name": practice_name,
                "type": practice_info["type"],
                "confidence": practice_info["confidence"],
                "explanation": practice_info["explanation"],
                "source_blocks": [
                    {
                        "block_id": b.block_id,
                        "title": b.title,
                        "youtube_link": b.youtube_link,
                        "start": b.start,
                        "end": b.end,
                        "document_title": b.document_title
                    }
                    for b in relevant_blocks[:2]  # Максимум 2 блока на практику
                ]
            })
        
        logger.info(f"✅ Рекомендовано {len(result_practices)} практик для '{concept}'")
        
        return {
            "concept": concept,
            "practices": result_practices
        }
    
    def get_learning_path(
        self,
        target_concept: str,
        start_concept: Optional[str] = None
    ) -> Dict:
        """
        Построить путь обучения к целевому концепту.
        
        Если указан start_concept — строит цепочку от него к target_concept.
        Если не указан — строит путь на основе предпосылок target_concept.
        
        Args:
            target_concept: Целевой концепт (куда идём)
            start_concept: Начальный концепт (откуда идём), опционально
            
        Returns:
            Dict:
                - path: List[Dict] — шаги пути обучения
                - error: Optional[str] — ошибка если путь не найден
        """
        self._ensure_initialized()
        
        logger.info(f"🛤️ Строю путь обучения к '{target_concept}'")
        
        # Если указан стартовый концепт — ищем цепочку через граф
        if start_concept:
            chain = graph_client.get_chain(start_concept, target_concept)
            
            if chain:
                path = self._chain_to_learning_path(chain)
                return {"path": path}
        
        # Если цепочка не найдена или стартовый не указан — строим на основе предпосылок
        logger.debug("⚠️ Строю путь на основе предпосылок")
        
        prerequisites = graph_client.get_prerequisites_for_concept(target_concept)
        
        if prerequisites:
            path = []
            
            # Добавляем предпосылки как первые шаги
            for i, prereq in enumerate(prerequisites, 1):
                practices = graph_client.get_practices_for_concept(prereq["prerequisite"])
                path.append({
                    "step": i,
                    "concept": prereq["prerequisite"],
                    "type": prereq["type"],
                    "practices": [p["practice_name"] for p in practices[:3]],
                    "required": True
                })
            
            # Добавляем целевой концепт
            target_practices = graph_client.get_practices_for_concept(target_concept)
            path.append({
                "step": len(path) + 1,
                "concept": target_concept,
                "type": "CONCEPT",
                "practices": [p["practice_name"] for p in target_practices[:3]],
                "required": False
            })
            
            return {"path": path}
        
        # Если и предпосылок нет — возвращаем только целевой концепт
        target_practices = graph_client.get_practices_for_concept(target_concept)
        
        return {
            "path": [{
                "step": 1,
                "concept": target_concept,
                "type": "CONCEPT",
                "practices": [p["practice_name"] for p in target_practices[:3]],
                "required": False
            }]
        }
    
    def _chain_to_learning_path(self, chain: List[Dict]) -> List[Dict]:
        """
        Преобразовать цепочку из графа в путь обучения.
        
        Args:
            chain: Цепочка от graph_client.get_chain()
            
        Returns:
            List[Dict] — шаги пути обучения с практиками
        """
        path = []
        
        for step in chain:
            practices = graph_client.get_practices_for_concept(step["concept"])
            path.append({
                "step": step["step"],
                "concept": step["concept"],
                "type": step["type"],
                "practices": [p["practice_name"] for p in practices[:2]],
                "relation": step.get("relation")
            })
        
        return path
    
    def get_practice_details(self, practice_name: str) -> Dict:
        """
        Получить полную информацию о практике.
        
        Находит блоки, где практика упоминается, и возвращает
        описание, контент и источники.
        
        Args:
            practice_name: Имя практики
            
        Returns:
            Dict:
                - name: str — имя практики
                - description: str — краткое описание (summary)
                - full_content: str — полный контент блока
                - source_blocks: List[Dict] — источники
                - error: Optional[str] — ошибка если не найдено
        """
        self._ensure_initialized()
        
        logger.info(f"📖 Получаю детали практики: '{practice_name}'")
        
        all_blocks = data_loader.get_all_blocks()
        
        # Ищем блоки, содержащие эту практику
        relevant_blocks = self._find_blocks_for_entity(practice_name, all_blocks)
        
        if not relevant_blocks:
            return {"error": f"Информация о практике '{practice_name}' не найдена"}
        
        # Берём первый блок как основное описание
        main_block = relevant_blocks[0]
        
        return {
            "name": practice_name,
            "description": main_block.summary,
            "full_content": main_block.content,
            "block_type": main_block.block_type,
            "complexity_score": main_block.complexity_score,
            "source_blocks": [
                {
                    "title": b.title,
                    "youtube_link": b.youtube_link,
                    "start": b.start,
                    "end": b.end,
                    "block_id": b.block_id,
                    "document_title": b.document_title
                }
                for b in relevant_blocks
            ]
        }
    
    def _find_blocks_for_entity(
        self,
        entity_name: str,
        blocks: List[Block]
    ) -> List[Block]:
        """
        Найти блоки, содержащие сущность в graph_entities.
        
        Args:
            entity_name: Имя сущности для поиска
            blocks: Список блоков для поиска
            
        Returns:
            Список блоков, содержащих сущность
        """
        entity_lower = entity_name.lower()
        
        relevant = []
        for block in blocks:
            if block.graph_entities:
                # Проверяем точное и частичное совпадение
                entities_lower = [e.lower() for e in block.graph_entities]
                
                if entity_lower in entities_lower:
                    relevant.append(block)
                elif any(entity_lower in e or e in entity_lower for e in entities_lower):
                    relevant.append(block)
        
        return relevant
    
    def get_related_practices(
        self,
        practice_name: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Найти практики, связанные с данной практикой.
        
        Args:
            practice_name: Имя практики
            limit: Максимальное количество
            
        Returns:
            Список связанных практик
        """
        self._ensure_initialized()
        
        # Находим узел практики в графе
        practice_node = graph_client.find_node(practice_name)
        
        if not practice_node:
            return []
        
        # Получаем связанные узлы
        related = graph_client.get_related(
            practice_node.node_id,
            direction="both"
        )
        
        # Фильтруем только практики/техники/упражнения
        related_practices = [
            {
                "name": node.name,
                "type": node.node_type,
                "relation": edge.edge_type,
                "confidence": edge.confidence
            }
            for node, edge in related
            if node.node_type in ["PRACTICE", "TECHNIQUE", "EXERCISE"]
        ]
        
        return related_practices[:limit]
    
    def get_concepts_for_practice(self, practice_name: str) -> List[Dict]:
        """
        Найти концепты, для которых эта практика полезна.
        
        Args:
            practice_name: Имя практики
            
        Returns:
            Список концептов
        """
        self._ensure_initialized()
        
        practice_node = graph_client.find_node(practice_name)
        
        if not practice_node:
            return []
        
        # Ищем входящие связи к практике
        related = graph_client.get_related(
            practice_node.node_id,
            edge_types=[
                "IS_PRACTICE_FOR",
                "IS_TECHNIQUE_FOR",
                "IS_EXERCISE_FOR",
                "ENABLES"
            ],
            direction="incoming"
        )
        
        concepts = [
            {
                "concept": node.name,
                "type": node.node_type,
                "relation": edge.edge_type,
                "confidence": edge.confidence
            }
            for node, edge in related
            if node.node_type == "CONCEPT"
        ]
        
        return concepts


# Глобальный синглтон
practices_recommender = PracticesRecommender()


