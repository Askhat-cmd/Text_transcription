# bot_agent/graph_client.py
"""
Knowledge Graph Client for Phase 3
==================================

Клиент для работы с Knowledge Graph из SAG v2.0.
Загружает графы из JSON, предоставляет методы поиска и анализа.

Типы узлов:
    - CONCEPT: Абстрактный концепт (осознавание, трансформация)
    - PRACTICE: Практика (медитация, дыхание)
    - TECHNIQUE: Техника (конкретный метод)
    - EXERCISE: Упражнение
    - PATTERN: Паттерн поведения
    - PROCESS_STAGE: Этап процесса

Типы связей:
    - IS_PRACTICE_FOR: практика для концепта
    - IS_TECHNIQUE_FOR: техника для концепта
    - IS_EXERCISE_FOR: упражнение для концепта
    - ENABLES: делает возможным
    - REQUIRES: требует
    - IS_PART_OF: является частью
    - HAS_PART: содержит
    - HAS_COMPONENT: содержит компонент
    - IS_COMPONENT_OF: является компонентом
    - RELATED_TO: связан с
    - NEEDS: нуждается в
    - PREREQUISITE: предпосылка
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, deque

from .config import config
from .data_loader import data_loader

logger = logging.getLogger(__name__)


class GraphNode:
    """
    Представление узла в Knowledge Graph.
    
    Атрибуты:
        node_id (str): Уникальный идентификатор узла
        name (str): Человекочитаемое имя узла
        node_type (str): Тип узла (CONCEPT, PRACTICE, TECHNIQUE, EXERCISE, PATTERN, PROCESS_STAGE)
        metadata (Dict): Дополнительные метаданные узла
    """
    
    def __init__(self, node_id: str, name: str, node_type: str, metadata: Dict = None):
        self.node_id = node_id
        self.name = name
        self.node_type = node_type
        self.metadata = metadata or {}
    
    def __repr__(self) -> str:
        return f"GraphNode(id={self.node_id}, name='{self.name}', type={self.node_type})"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, GraphNode):
            return False
        return self.node_id == other.node_id
    
    def __hash__(self) -> int:
        return hash(self.node_id)


class GraphEdge:
    """
    Представление связи в Knowledge Graph.
    
    Атрибуты:
        from_id (str): ID исходного узла
        to_id (str): ID целевого узла
        from_name (str): Имя исходного узла
        to_name (str): Имя целевого узла
        edge_type (str): Тип связи
        explanation (str): Пояснение связи
        confidence (float): Уверенность в связи (0.0-1.0)
        metadata (Dict): Дополнительные метаданные
    """
    
    def __init__(
        self,
        from_id: str,
        to_id: str,
        from_name: str,
        to_name: str,
        edge_type: str,
        explanation: str = "",
        confidence: float = 1.0,
        metadata: Dict = None
    ):
        self.from_id = from_id
        self.to_id = to_id
        self.from_name = from_name
        self.to_name = to_name
        self.edge_type = edge_type
        self.explanation = explanation
        self.confidence = max(0.0, min(1.0, confidence))  # Нормализация 0-1
        self.metadata = metadata or {}
    
    def __repr__(self) -> str:
        return f"GraphEdge({self.from_name} --[{self.edge_type}]--> {self.to_name})"


class KnowledgeGraphClient:
    """
    Клиент для работы с Knowledge Graph из SAG v2.0.
    
    Загружает графы из JSON файлов, объединяет их в единый граф,
    предоставляет методы поиска узлов, связей и навигации.
    
    Usage:
        >>> from graph_client import graph_client
        >>> graph_client.load_graphs_from_all_documents()
        >>> node = graph_client.find_node("осознавание")
        >>> practices = graph_client.get_practices_for_concept("осознавание")
    """
    
    def __init__(self):
        # Хранилище узлов и связей
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        
        # Индексы для быстрого поиска
        self.adjacency: Dict[str, List[GraphEdge]] = defaultdict(list)  # from_id -> edges
        self.reverse_adjacency: Dict[str, List[GraphEdge]] = defaultdict(list)  # to_id -> edges
        self.node_by_name: Dict[str, GraphNode] = {}  # lowercase name -> node
        
        # Метаданные и статус
        self._is_loaded = False
        self.metadata: Dict = {}
        self._loaded_files: List[str] = []
    
    def load_graphs_from_all_documents(self) -> None:
        """
        Загрузить Knowledge Graphs из всех документов.
        Объединяет графы в единый полный граф.
        
        Источники:
            1. Отдельные файлы *.knowledge_graph.json
            2. Поле "knowledge_graph" внутри *.for_vector.json
        """
        if self._is_loaded:
            logger.info("✓ Knowledge Graphs уже загружены")
            return
        
        logger.info("📊 Загружаю Knowledge Graphs из всех документов...")
        
        # Загружаем данные через data_loader
        documents = data_loader.get_all_documents()
        docs_with_graphs = 0
        
        for doc in documents:
            try:
                graph_path = self._find_graph_file_for_doc(doc.video_id)
                
                if graph_path:
                    self._load_single_graph(graph_path)
                    docs_with_graphs += 1
            
            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить граф для {doc.video_id}: {e}")
        
        self._is_loaded = True
        logger.info(f"✅ Загружено графов из {docs_with_graphs} документов")
        logger.info(f"   Всего узлов: {len(self.nodes)}, связей: {len(self.edges)}")
    
    def _find_graph_file_for_doc(self, video_id: str) -> Optional[Path]:
        """
        Найти файл Knowledge Graph для документа.
        
        Стратегия поиска:
            1. Ищем отдельный *.knowledge_graph.json файл
            2. Если нет — возвращаем *.for_vector.json (граф может быть внутри)
        
        Args:
            video_id: Идентификатор видео/документа
            
        Returns:
            Path к файлу или None
        """
        # Стратегия 1: Отдельный файл knowledge_graph.json
        graph_files = list(config.SAG_FINAL_DIR.glob(f"**/*{video_id}*.knowledge_graph.json"))
        
        if graph_files:
            return graph_files[0]
        
        # Стратегия 2: Внутри for_vector.json
        for_vector_files = list(config.SAG_FINAL_DIR.glob(f"**/*{video_id}*.for_vector.json"))
        
        if for_vector_files:
            return for_vector_files[0]
        
        return None
    
    def _load_single_graph(self, graph_path: Path) -> None:
        """
        Загрузить граф из одного файла.
        
        Поддерживает два формата:
            1. Корневой формат: {"nodes": [...], "edges": [...]}
            2. Вложенный формат: {"knowledge_graph": {"nodes": [...], "edges": [...]}}
        
        Args:
            graph_path: Путь к JSON файлу
        """
        if str(graph_path) in self._loaded_files:
            return  # Уже загружен
        
        with open(graph_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Определяем формат: вложенный или корневой
        if isinstance(data, dict) and "knowledge_graph" in data:
            graph_data = data["knowledge_graph"]
        elif isinstance(data, dict) and ("nodes" in data or "edges" in data):
            graph_data = data
        else:
            # Нет графа в этом файле
            return
        
        # Загружаем узлы
        nodes_loaded = 0
        for node_data in graph_data.get("nodes", []):
            node_id = node_data.get("id")
            name = node_data.get("name")
            node_type = node_data.get("type", "CONCEPT")
            
            if node_id and name:
                # Избегаем дубликатов узлов
                if node_id not in self.nodes:
                    node = GraphNode(
                        node_id=node_id,
                        name=name,
                        node_type=node_type,
                        metadata=node_data.get("metadata", {})
                    )
                    self.nodes[node_id] = node
                    self.node_by_name[name.lower()] = node
                    nodes_loaded += 1
        
        # Загружаем связи
        edges_loaded = 0
        for edge_data in graph_data.get("edges", []):
            from_id = edge_data.get("from_id")
            to_id = edge_data.get("to_id")
            from_name = edge_data.get("from_name", "")
            to_name = edge_data.get("to_name", "")
            edge_type = edge_data.get("edge_type", "RELATED_TO")
            explanation = edge_data.get("explanation", "")
            confidence = float(edge_data.get("confidence", 1.0))
            
            if from_id and to_id:
                edge = GraphEdge(
                    from_id=from_id,
                    to_id=to_id,
                    from_name=from_name,
                    to_name=to_name,
                    edge_type=edge_type,
                    explanation=explanation,
                    confidence=confidence,
                    metadata=edge_data.get("metadata", {})
                )
                self.edges.append(edge)
                self.adjacency[from_id].append(edge)
                self.reverse_adjacency[to_id].append(edge)
                edges_loaded += 1
        
        # Загружаем метаданные графа
        if "metadata" in graph_data:
            self.metadata.update(graph_data["metadata"])
        
        self._loaded_files.append(str(graph_path))
        
        if nodes_loaded > 0 or edges_loaded > 0:
            logger.debug(f"✓ Загружено: {nodes_loaded} узлов, {edges_loaded} связей из {graph_path.name}")
    
    def find_node(self, name: str) -> Optional[GraphNode]:
        """
        Найти узел по имени (case-insensitive).
        
        Args:
            name: Имя узла для поиска
            
        Returns:
            GraphNode или None если не найден
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        name_lower = name.lower()
        
        # Прямой поиск
        if name_lower in self.node_by_name:
            return self.node_by_name[name_lower]
        
        # Поиск по частичному совпадению
        for node_name, node in self.node_by_name.items():
            if name_lower in node_name or node_name in name_lower:
                return node
        
        logger.debug(f"⚠️ Узел '{name}' не найден в графе")
        return None
    
    def find_node_by_id(self, node_id: str) -> Optional[GraphNode]:
        """
        Найти узел по ID.
        
        Args:
            node_id: ID узла
            
        Returns:
            GraphNode или None
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        return self.nodes.get(node_id)
    
    def find_nodes_by_type(self, node_type: str) -> List[GraphNode]:
        """
        Найти все узлы определённого типа.
        
        Args:
            node_type: Тип узла (CONCEPT, PRACTICE, TECHNIQUE, etc.)
            
        Returns:
            Список узлов данного типа
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        return [node for node in self.nodes.values() if node.node_type == node_type]
    
    def get_related(
        self,
        node_id: str,
        edge_types: List[str] = None,
        direction: str = "both"
    ) -> List[Tuple[GraphNode, GraphEdge]]:
        """
        Получить все связи узла.
        
        Args:
            node_id: ID узла
            edge_types: Типы связей для фильтра (если None — все)
            direction: "outgoing" | "incoming" | "both"
        
        Returns:
            Список кортежей (узел, связь)
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        results = []
        
        # Исходящие связи (от node_id к другим)
        if direction in ["outgoing", "both"]:
            for edge in self.adjacency.get(node_id, []):
                if edge_types is None or edge.edge_type in edge_types:
                    target_node = self.nodes.get(edge.to_id)
                    if target_node:
                        results.append((target_node, edge))
        
        # Входящие связи (от других к node_id)
        if direction in ["incoming", "both"]:
            for edge in self.reverse_adjacency.get(node_id, []):
                if edge_types is None or edge.edge_type in edge_types:
                    source_node = self.nodes.get(edge.from_id)
                    if source_node:
                        results.append((source_node, edge))
        
        # Сортируем по уверенности (confidence)
        results.sort(key=lambda x: x[1].confidence, reverse=True)
        
        return results
    
    def get_practices_for_concept(self, concept_name: str) -> List[Dict]:
        """
        Найти практики, техники, упражнения для концепта.
        
        Args:
            concept_name: Имя концепта
            
        Returns:
            List[Dict] с ключами:
                - practice_name: str
                - type: "PRACTICE" | "TECHNIQUE" | "EXERCISE"
                - edge_type: тип связи
                - confidence: уверенность
                - explanation: объяснение
                - node_id: ID узла практики
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        concept_node = self.find_node(concept_name)
        if not concept_node:
            logger.debug(f"⚠️ Концепт '{concept_name}' не найден в графе")
            return []
        
        # Типы связей, указывающие на практики
        practice_edge_types = [
            "IS_PRACTICE_FOR",
            "IS_TECHNIQUE_FOR",
            "IS_EXERCISE_FOR",
            "ENABLES",
            "REQUIRES"
        ]
        
        practices = []
        related = self.get_related(concept_node.node_id, edge_types=practice_edge_types)
        
        for node, edge in related:
            if node.node_type in ["PRACTICE", "TECHNIQUE", "EXERCISE"]:
                practices.append({
                    "practice_name": node.name,
                    "type": node.node_type,
                    "edge_type": edge.edge_type,
                    "confidence": edge.confidence,
                    "explanation": edge.explanation,
                    "node_id": node.node_id
                })
        
        if practices:
            logger.debug(f"✓ Найдено {len(practices)} практик для '{concept_name}'")
        
        return practices
    
    def get_chain(
        self,
        from_concept: str,
        to_concept: str,
        max_depth: int = 5
    ) -> Optional[List[Dict]]:
        """
        Найти цепочку связей от одного концепта к другому (BFS).
        
        Args:
            from_concept: Имя начального концепта
            to_concept: Имя целевого концепта
            max_depth: Максимальная глубина поиска
            
        Returns:
            List[Dict] с шагами цепочки или None если путь не найден
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        from_node = self.find_node(from_concept)
        to_node = self.find_node(to_concept)
        
        if not from_node or not to_node:
            logger.debug(f"⚠️ Один из концептов не найден: {from_concept} -> {to_concept}")
            return None
        
        if from_node.node_id == to_node.node_id:
            return [{
                "step": 1,
                "concept": from_node.name,
                "type": from_node.node_type,
                "node_id": from_node.node_id
            }]
        
        # BFS поиск пути
        queue = deque([(from_node.node_id, [from_node.node_id], [])])
        visited = {from_node.node_id}
        
        while queue:
            current_id, path, edges_list = queue.popleft()
            
            if len(path) > max_depth:
                continue
            
            if current_id == to_node.node_id:
                # Нашли путь!
                chain = []
                for i, node_id in enumerate(path):
                    node = self.nodes[node_id]
                    step = {
                        "step": i + 1,
                        "concept": node.name,
                        "type": node.node_type,
                        "node_id": node_id
                    }
                    
                    if i > 0 and edges_list:
                        step["relation"] = edges_list[i - 1]
                    
                    chain.append(step)
                
                logger.debug(f"✓ Найдена цепочка из {len(chain)} шагов: {from_concept} → {to_concept}")
                return chain
            
            # Развиваем поиск (только исходящие связи)
            for neighbor, edge in self.get_related(current_id, direction="outgoing"):
                if neighbor.node_id not in visited:
                    visited.add(neighbor.node_id)
                    queue.append(
                        (neighbor.node_id, path + [neighbor.node_id], edges_list + [edge.edge_type])
                    )
        
        logger.debug(f"⚠️ Цепочка не найдена: {from_concept} → {to_concept}")
        return None
    
    def get_prerequisites_for_concept(self, concept_name: str) -> List[Dict]:
        """
        Получить предпосылки (что нужно изучить перед концептом).
        
        Args:
            concept_name: Имя концепта
            
        Returns:
            Список предпосылок с confidence и explanation
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        concept_node = self.find_node(concept_name)
        if not concept_node:
            return []
        
        prerequisites = []
        
        # Ищем входящие связи типа REQUIRES, NEEDS, PREREQUISITE
        related = self.get_related(
            concept_node.node_id,
            edge_types=["REQUIRES", "NEEDS", "PREREQUISITE"],
            direction="incoming"
        )
        
        for node, edge in related:
            prerequisites.append({
                "prerequisite": node.name,
                "type": node.node_type,
                "confidence": edge.confidence,
                "explanation": edge.explanation,
                "node_id": node.node_id
            })
        
        return prerequisites
    
    def get_concept_hierarchy(self, concept_name: str, depth: int = 3) -> Dict:
        """
        Получить иерархию концепта (родители, дети, связанные).
        
        Args:
            concept_name: Имя концепта
            depth: Глубина обхода (не используется пока)
            
        Returns:
            Dict с parent_concepts, child_concepts, related_concepts
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        concept_node = self.find_node(concept_name)
        if not concept_node:
            return {"error": f"Концепт '{concept_name}' не найден"}
        
        return {
            "concept": concept_node.name,
            "type": concept_node.node_type,
            "node_id": concept_node.node_id,
            
            # Родительские концепты (то, частью чего является этот концепт)
            "parent_concepts": [
                {
                    "name": n.name,
                    "type": n.node_type,
                    "confidence": e.confidence,
                    "relation": e.edge_type
                }
                for n, e in self.get_related(
                    concept_node.node_id,
                    edge_types=["IS_PART_OF", "IS_COMPONENT_OF"],
                    direction="outgoing"
                )
            ],
            
            # Дочерние концепты (части этого концепта)
            "child_concepts": [
                {
                    "name": n.name,
                    "type": n.node_type,
                    "confidence": e.confidence,
                    "relation": e.edge_type
                }
                for n, e in self.get_related(
                    concept_node.node_id,
                    edge_types=["HAS_PART", "HAS_COMPONENT"],
                    direction="outgoing"
                )
            ],
            
            # Связанные концепты
            "related_concepts": [
                {
                    "name": n.name,
                    "type": n.node_type,
                    "confidence": e.confidence,
                    "relation": e.edge_type
                }
                for n, e in self.get_related(
                    concept_node.node_id,
                    edge_types=["RELATED_TO"],
                    direction="both"
                )
            ]
        }
    
    def get_statistics(self) -> Dict:
        """
        Получить статистику графа.
        
        Returns:
            Dict со статистикой: узлы, связи, типы, confidence
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        # Подсчёт по типам узлов
        node_types = defaultdict(int)
        for node in self.nodes.values():
            node_types[node.node_type] += 1
        
        # Подсчёт по типам связей
        edge_types = defaultdict(int)
        for edge in self.edges:
            edge_types[edge.edge_type] += 1
        
        # Статистика confidence
        confidence_values = [e.confidence for e in self.edges]
        confidence_stats = {
            "min": min(confidence_values) if confidence_values else 0,
            "max": max(confidence_values) if confidence_values else 1,
            "avg": sum(confidence_values) / len(confidence_values) if confidence_values else 0
        }
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": dict(node_types),
            "edge_types": dict(edge_types),
            "confidence_statistics": confidence_stats,
            "loaded_files": len(self._loaded_files),
            "metadata": self.metadata
        }
    
    def reset(self) -> None:
        """Сбросить загруженные данные (для тестов или перезагрузки)"""
        self.nodes.clear()
        self.edges.clear()
        self.adjacency.clear()
        self.reverse_adjacency.clear()
        self.node_by_name.clear()
        self._loaded_files.clear()
        self.metadata.clear()
        self._is_loaded = False
        logger.info("🔄 Knowledge Graph сброшен")


# Глобальный синглтон
graph_client = KnowledgeGraphClient()
