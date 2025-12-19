<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# 🚀 Начало реализации Phase 3 в Cursor IDE

## Обзор Phase 3

**Phase 3** подключает Knowledge Graph:

- Загрузка и парсинг `*.knowledge_graph.json`
- Поиск узлов и связей в графе
- Рекомендация практик для концептов
- Построение цепочек связей между концептами
- Объяснение "почему так" через граф

**Результат:** Бот может не только находить информацию, но и объяснять архитектуру знаний.

***

## Шаг 1: Создание `bot_agent/graph_client.py`

Создай файл `voice_bot_pipeline/bot_agent/graph_client.py`:

```python
# bot_agent/graph_client.py

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, deque

from data_loader import data_loader
from config import config

logger = logging.getLogger(__name__)


class GraphNode:
    """Представление узла в Knowledge Graph"""
    
    def __init__(self, node_id: str, name: str, node_type: str, metadata: Dict = None):
        self.node_id = node_id
        self.name = name
        self.node_type = node_type  # CONCEPT, PRACTICE, TECHNIQUE, EXERCISE, PATTERN, PROCESS_STAGE
        self.metadata = metadata or {}


class GraphEdge:
    """Представление связи в Knowledge Graph"""
    
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
        self.confidence = confidence  # вес связи 0.0-1.0
        self.metadata = metadata or {}


class KnowledgeGraphClient:
    """
    Клиент для работы с Knowledge Graph из SAG v2.0.
    Загружает граф, предоставляет методы поиска и анализа.
    """
    
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency: Dict[str, List[GraphEdge]] = defaultdict(list)  # from_id -> edges
        self.reverse_adjacency: Dict[str, List[GraphEdge]] = defaultdict(list)  # to_id -> edges
        self.node_by_name: Dict[str, GraphNode] = {}  # для поиска по имени
        self._is_loaded = False
        self.metadata = {}
    
    def load_graphs_from_all_documents(self) -> None:
        """
        Загрузить Knowledge Graphs из всех документов.
        Объединить графы в единый полный граф.
        """
        if self._is_loaded:
            logger.info("✓ Графы уже загружены")
            return
        
        logger.info("📊 Загружаю Knowledge Graphs из всех документов...")
        
        documents = data_loader.get_all_documents()
        docs_with_graphs = 0
        
        for doc in documents:
            try:
                # Ищем соответствующий *.knowledge_graph.json файл
                # Предполагаем, что он лежит в той же папке что и *.for_vector.json
                # и имеет то же имя, но с расширением .knowledge_graph.json
                
                # Пока что граф может быть внутри for_vector.json в поле "knowledge_graph"
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
        Найти файл *.knowledge_graph.json для документа.
        """
        graph_files = list(config.SAG_FINAL_DIR.glob(f"**/*{video_id}.knowledge_graph.json"))
        
        if graph_files:
            return graph_files[0]
        
        # Если отдельного файла нет, пробуем загрузить из for_vector.json
        for_vector_files = list(config.SAG_FINAL_DIR.glob(f"**/*{video_id}.for_vector.json"))
        
        if for_vector_files:
            return for_vector_files[0]
        
        return None
    
    def _load_single_graph(self, graph_path: Path) -> None:
        """
        Загрузить граф из одного файла.
        """
        with open(graph_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Граф может быть:
        # 1. В поле "knowledge_graph" внутри for_vector.json
        # 2. В корне файла knowledge_graph.json
        
        if isinstance(data, dict) and "knowledge_graph" in data:
            graph_data = data["knowledge_graph"]
        else:
            graph_data = data
        
        # Загружаем узлы
        for node_data in graph_data.get("nodes", []):
            node_id = node_data.get("id")
            name = node_data.get("name")
            node_type = node_data.get("type", "CONCEPT")
            
            if node_id and name:
                node = GraphNode(node_id, name, node_type, node_data.get("metadata", {}))
                self.nodes[node_id] = node
                self.node_by_name[name.lower()] = node
        
        # Загружаем связи
        for edge_data in graph_data.get("edges", []):
            from_id = edge_data.get("from_id")
            to_id = edge_data.get("to_id")
            from_name = edge_data.get("from_name")
            to_name = edge_data.get("to_name")
            edge_type = edge_data.get("edge_type", "RELATED_TO")
            explanation = edge_data.get("explanation", "")
            confidence = float(edge_data.get("confidence", 1.0))
            
            if from_id and to_id:
                edge = GraphEdge(
                    from_id, to_id, from_name, to_name,
                    edge_type, explanation, confidence,
                    edge_data.get("metadata", {})
                )
                self.edges.append(edge)
                self.adjacency[from_id].append(edge)
                self.reverse_adjacency[to_id].append(edge)
        
        # Загружаем метаданные графа
        if "metadata" in graph_data:
            self.metadata.update(graph_data["metadata"])
        
        logger.debug(f"✓ Загруженo: {len(graph_data.get('nodes', []))} узлов, "
                    f"{len(graph_data.get('edges', []))} связей из {graph_path.name}")
    
    def find_node(self, name: str) -> Optional[GraphNode]:
        """
        Найти узел по имени (case-insensitive).
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
        
        logger.debug(f"⚠️ Узел '{name}' не найден")
        return None
    
    def find_node_by_id(self, node_id: str) -> Optional[GraphNode]:
        """Найти узел по ID"""
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        return self.nodes.get(node_id)
    
    def get_related(
        self,
        node_id: str,
        edge_types: List[str] = None,
        direction: str = "both"
    ) -> List[Tuple[GraphNode, GraphEdge]]:
        """
        Получить все связи узла.
        
        Аргументы:
            node_id: ID узла
            edge_types: Типы связей для фильтра (если None - все)
            direction: "outgoing" | "incoming" | "both"
        
        Возвращает:
            Список (узел, граница)
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        results = []
        
        # Исходящие связи
        if direction in ["outgoing", "both"]:
            for edge in self.adjacency.get(node_id, []):
                if edge_types is None or edge.edge_type in edge_types:
                    target_node = self.nodes.get(edge.to_id)
                    if target_node:
                        results.append((target_node, edge))
        
        # Входящие связи
        if direction in ["incoming", "both"]:
            for edge in self.reverse_adjacency.get(node_id, []):
                if edge_types is None or edge.edge_type in edge_types:
                    source_node = self.nodes.get(edge.from_id)
                    if source_node:
                        results.append((source_node, edge))
        
        # Сортируем по уверенности (confidence)
        results.sort(key=lambda x: x[1].confidence, reverse=True)
        
        logger.debug(f"🔗 Найдено {len(results)} связей для узла {node_id}")
        return results
    
    def get_practices_for_concept(self, concept_name: str) -> List[Dict]:
        """
        Найти практики для концепта.
        
        Возвращает:
            List[Dict] с ключами:
                - "practice_name": str
                - "type": "PRACTICE" | "TECHNIQUE" | "EXERCISE"
                - "edge_type": тип связи
                - "confidence": уверенность
                - "explanation": объяснение
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        concept_node = self.find_node(concept_name)
        if not concept_node:
            logger.warning(f"⚠️ Концепт '{concept_name}' не найден")
            return []
        
        # Ищем практики через IS_PRACTICE_FOR, IS_TECHNIQUE_FOR, IS_EXERCISE_FOR
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
        
        logger.info(f"✅ Найдено {len(practices)} практик для '{concept_name}'")
        return practices
    
    def get_chain(
        self,
        from_concept: str,
        to_concept: str,
        max_depth: int = 5
    ) -> Optional[List[Dict]]:
        """
        Найти цепочку связей от одного концепта к другому (BFS).
        
        Возвращает:
            List[Dict] или None если пути нет
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        from_node = self.find_node(from_concept)
        to_node = self.find_node(to_concept)
        
        if not from_node or not to_node:
            logger.warning(f"⚠️ Концепты не найдены")
            return None
        
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
                        step["relation"] = edges_list[i-1]
                    
                    chain.append(step)
                
                logger.info(f"✅ Найдена цепочка из {len(chain)} шагов: {from_concept} → {to_concept}")
                return chain
            
            # Развиваем поиск
            for neighbor, edge in self.get_related(current_id, direction="outgoing"):
                if neighbor.node_id not in visited:
                    visited.add(neighbor.node_id)
                    queue.append(
                        (neighbor.node_id, path + [neighbor.node_id], edges_list + [edge.edge_type])
                    )
        
        logger.warning(f"⚠️ Цепочка не найдена: {from_concept} → {to_concept}")
        return None
    
    def get_prerequisites_for_concept(self, concept_name: str) -> List[Dict]:
        """
        Получить предпосылки (что нужно изучить перед концептом).
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
                "explanation": edge.explanation
            })
        
        return prerequisites
    
    def get_concept_hierarchy(self, concept_name: str, depth: int = 3) -> Dict:
        """
        Получить иерархию концепта (что входит в него, что он входит).
        """
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        concept_node = self.find_node(concept_name)
        if not concept_node:
            return {"error": f"Концепт '{concept_name}' не найден"}
        
        return {
            "concept": concept_node.name,
            "type": concept_node.node_type,
            "parent_concepts": [
                {"name": n.name, "type": n.node_type, "confidence": e.confidence}
                for n, e in self.get_related(
                    concept_node.node_id,
                    edge_types=["IS_PART_OF", "IS_COMPONENT_OF"],
                    direction="incoming"
                )
            ],
            "child_concepts": [
                {"name": n.name, "type": n.node_type, "confidence": e.confidence}
                for n, e in self.get_related(
                    concept_node.node_id,
                    edge_types=["HAS_PART", "HAS_COMPONENT"],
                    direction="outgoing"
                )
            ],
            "related_concepts": [
                {"name": n.name, "type": n.node_type, "confidence": e.confidence}
                for n, e in self.get_related(
                    concept_node.node_id,
                    edge_types=["RELATED_TO"],
                    direction="both"
                )
            ]
        }
    
    def get_statistics(self) -> Dict:
        """Получить статистику графа"""
        if not self._is_loaded:
            self.load_graphs_from_all_documents()
        
        node_types = defaultdict(int)
        for node in self.nodes.values():
            node_types[node.node_type] += 1
        
        edge_types = defaultdict(int)
        for edge in self.edges:
            edge_types[edge.edge_type] += 1
        
        confidence_stats = {
            "min": min((e.confidence for e in self.edges), default=0),
            "max": max((e.confidence for e in self.edges), default=1),
            "avg": sum(e.confidence for e in self.edges) / len(self.edges) if self.edges else 0
        }
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": dict(node_types),
            "edge_types": dict(edge_types),
            "confidence_statistics": confidence_stats,
            "metadata": self.metadata
        }


# Глобальный инстанс
graph_client = KnowledgeGraphClient()
```


***

## Шаг 2: Создание `bot_agent/practices_recommender.py`

Создай файл `voice_bot_pipeline/bot_agent/practices_recommender.py`:

```python
# bot_agent/practices_recommender.py

import logging
from typing import List, Dict, Optional

from graph_client import graph_client
from data_loader import data_loader, Block

logger = logging.getLogger(__name__)


class PracticesRecommender:
    """
    Рекомендует практики, техники, упражнения на основе Knowledge Graph.
    """
    
    def __init__(self):
        graph_client.load_graphs_from_all_documents()
    
    def suggest_practices_for_concept(
        self,
        concept: str,
        limit: int = 5
    ) -> Dict:
        """
        Рекомендовать практики для концепта.
        
        Возвращает:
            {
                "concept": str,
                "practices": [
                    {
                        "name": str,
                        "type": str,
                        "confidence": float,
                        "explanation": str,
                        "source_blocks": List[Block]
                    }
                ]
            }
        """
        logger.info(f"🎯 Ищу практики для концепта: '{concept}'")
        
        practices_from_graph = graph_client.get_practices_for_concept(concept)
        
        if not practices_from_graph:
            logger.warning(f"⚠️ Практики не найдены в графе для '{concept}'")
            return {
                "concept": concept,
                "practices": [],
                "error": "no_practices_found"
            }
        
        # Сортируем по уверенности
        practices_from_graph.sort(key=lambda p: p["confidence"], reverse=True)
        practices_from_graph = practices_from_graph[:limit]
        
        # Находим блоки, где эти практики упоминаются
        all_blocks = data_loader.get_all_blocks()
        
        result_practices = []
        
        for practice_info in practices_from_graph:
            practice_name = practice_info["practice_name"]
            
            # Ищем блоки, содержащие эту практику
            relevant_blocks = [
                b for b in all_blocks
                if practice_name.lower() in [e.lower() for e in b.graph_entities]
            ]
            
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
                        "end": b.end
                    }
                    for b in relevant_blocks[:2]  # макс 2 блока на практику
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
        Построить путь обучения от стартового концепта к целевому.
        
        Возвращает:
            {
                "path": [
                    {
                        "step": int,
                        "concept": str,
                        "practices": List[str],
                        "duration": Optional[str]
                    }
                ]
            }
        """
        logger.info(f"🛤️ Строю путь обучения к '{target_concept}'")
        
        if start_concept:
            chain = graph_client.get_chain(start_concept, target_concept)
        else:
            # Если стартовой нет, просто получаем предпосылки
            chain = None
        
        if not chain:
            logger.warning("⚠️ Цепочка не найдена, строю на основе предпосылок")
            
            # Получаем предпосылки целевого концепта
            prerequisites = graph_client.get_prerequisites_for_concept(target_concept)
            
            if prerequisites:
                path = []
                for i, prereq in enumerate(prerequisites, 1):
                    practices = graph_client.get_practices_for_concept(prereq["prerequisite"])
                    path.append({
                        "step": i,
                        "concept": prereq["prerequisite"],
                        "practices": [p["practice_name"] for p in practices[:3]],
                        "required": True
                    })
                
                # Добавляем целевой концепт
                target_practices = graph_client.get_practices_for_concept(target_concept)
                path.append({
                    "step": len(path) + 1,
                    "concept": target_concept,
                    "practices": [p["practice_name"] for p in target_practices[:3]],
                    "required": False
                })
                
                return {"path": path}
        else:
            # Используем найденную цепочку
            path = []
            for i, step in enumerate(chain, 1):
                practices = graph_client.get_practices_for_concept(step["concept"])
                path.append({
                    "step": i,
                    "concept": step["concept"],
                    "type": step["type"],
                    "practices": [p["practice_name"] for p in practices[:2]]
                })
            
            return {"path": path}
        
        return {"path": [], "error": "no_path_found"}
    
    def get_practice_details(self, practice_name: str) -> Dict:
        """
        Получить полную информацию о практике.
        
        Возвращает:
            {
                "name": str,
                "description": str,
                "steps": List[str],
                "duration": str,
                "source_blocks": List[Dict]
            }
        """
        logger.info(f"📖 Получаю детали практики: '{practice_name}'")
        
        all_blocks = data_loader.get_all_blocks()
        
        # Ищем блоки, содержащие описание этой практики
        relevant_blocks = [
            b for b in all_blocks
            if practice_name.lower() in [e.lower() for e in b.graph_entities]
        ]
        
        if not relevant_blocks:
            return {"error": f"Информация о практике '{practice_name}' не найдена"}
        
        # Берем первый блок как основное описание
        main_block = relevant_blocks[0]
        
        return {
            "name": practice_name,
            "description": main_block.summary,
            "full_content": main_block.content,
            "source_blocks": [
                {
                    "title": b.title,
                    "youtube_link": b.youtube_link,
                    "start": b.start,
                    "end": b.end,
                    "block_id": b.block_id
                }
                for b in relevant_blocks
            ]
        }


# Глобальный инстанс
practices_recommender = PracticesRecommender()
```


***

## Шаг 3: Создание `bot_agent/answer_graph_powered.py`

Создай файл `voice_bot_pipeline/bot_agent/answer_graph_powered.py`:

```python
# bot_agent/answer_graph_powered.py

import logging
from typing import Dict, Optional
from datetime import datetime

from data_loader import data_loader
from retriever import get_retriever
from llm_answerer import LLMAnswerer
from user_level_adapter import UserLevelAdapter
from semantic_analyzer import SemanticAnalyzer
from graph_client import graph_client
from practices_recommender import practices_recommender
from config import config

logger = logging.getLogger(__name__)


def answer_question_graph_powered(
    query: str,
    user_level: str = "beginner",
    include_practices: bool = True,
    include_chain: bool = True,
    debug: bool = False
) -> Dict:
    """
    Phase 3: QA с полной поддержкой Knowledge Graph.
    
    Аргументы:
        query (str): Вопрос пользователя.
        user_level (str): Уровень пользователя.
        include_practices (bool): Включать ли рекомендации практик.
        include_chain (bool): Включать ли цепочки связей.
        debug (bool): Возвращать ли отладочную информацию.
    
    Возвращает:
        Dict с расширенными полями:
            - "status": "success" | "error" | "partial"
            - "answer": str
            - "sources": List[Dict]
            - "concepts": List[str]
            - "relations": List[Dict]
            - "practices": List[Dict] — рекомендованные практики
            - "concept_hierarchy": Dict — иерархия концептов
            - "learning_path": Optional[List] — путь обучения
            - "metadata": Dict
            - "debug": Optional[Dict]
    """
    
    logger.info(f"📊 Обработка запроса (Phase 3): '{query}'")
    
    start_time = datetime.now()
    debug_info = {} if debug else None
    
    try:
        # === ЭТАП 1: Базовая обработка (как в Phase 2) ===
        logger.debug("🔧 Этап 1: Инициализация...")
        
        data_loader.load_all_data()
        level_adapter = UserLevelAdapter(user_level)
        semantic_analyzer = SemanticAnalyzer()
        
        # === ЭТАП 2: Поиск блоков ===
        logger.debug("🔍 Этап 2: Поиск релевантных блоков...")
        retriever = get_retriever(use_chromadb=False)
        retrieved_blocks = retriever.retrieve(query, top_k=config.TOP_K_BLOCKS)
        
        if not retrieved_blocks:
            return {
                "status": "partial",
                "answer": "К сожалению, материал не найден.",
                "sources": [],
                "concepts": [],
                "relations": [],
                "practices": [],
                "concept_hierarchy": {},
                "learning_path": None,
                "metadata": {"blocks_used": 0},
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
                "debug": debug_info
            }
        
        blocks = [block for block, score in retrieved_blocks]
        adapted_blocks = level_adapter.filter_blocks_by_level(blocks)
        semantic_data = semantic_analyzer.analyze_relations(adapted_blocks)
        
        # === ЭТАП 3: Загрузка Knowledge Graph ===
        logger.debug("🧠 Этап 3: Загрузка Knowledge Graph...")
        graph_client.load_graphs_from_all_documents()
        
        if debug_info is not None:
            graph_stats = graph_client.get_statistics()
            debug_info["graph_stats"] = {
                "total_nodes": graph_stats["total_nodes"],
                "total_edges": graph_stats["total_edges"]
            }
        
        # === ЭТАП 4: Анализ концептов через граф ===
        logger.debug("🔗 Этап 4: Анализ концептов через граф...")
        
        primary_concepts = semantic_data["primary_concepts"]
        concept_hierarchies = {}
        
        for concept in primary_concepts:
            hierarchy = graph_client.get_concept_hierarchy(concept)
            if "error" not in hierarchy:
                concept_hierarchies[concept] = hierarchy
        
        if debug_info is not None:
            debug_info["graph_analysis"] = {
                "concepts_analyzed": len(concept_hierarchies),
                "hierarchies_found": len([h for h in concept_hierarchies.values() if "parent_concepts" in h])
            }
        
        # === ЭТАП 5: Формирование ответа ===
        logger.debug("🤖 Этап 5: Формирование ответа...")
        
        answerer = LLMAnswerer()
        base_prompt = answerer.build_system_prompt()
        adapted_prompt = level_adapter.adapt_system_prompt(base_prompt)
        
        # Обогащаем контекст информацией из графа
        context = answerer.build_context_prompt(adapted_blocks, query)
        
        if concept_hierarchies:
            context += "\n\n🧠 СТРУКТУРА КОНЦЕПТОВ (из Knowledge Graph):\n"
            for concept, hierarchy in list(concept_hierarchies.items())[:3]:
                if hierarchy.get("parent_concepts"):
                    context += f"\n{concept} требует: {', '.join(p['name'] for p in hierarchy['parent_concepts'][:3])}"
                if hierarchy.get("related_concepts"):
                    context += f"\n{concept} связан с: {', '.join(p['name'] for p in hierarchy['related_concepts'][:3])}"
        
        llm_result = answerer.generate_answer(query, adapted_blocks)
        
        if llm_result.get("error"):
            logger.error(f"❌ Ошибка LLM: {llm_result['error']}")
            return {
                "status": "error",
                "answer": llm_result.get("answer"),
                "sources": [],
                "concepts": primary_concepts,
                "relations": [],
                "practices": [],
                "concept_hierarchy": {},
                "learning_path": None,
                "metadata": {"error": llm_result.get("error")},
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
                "debug": debug_info
            }
        
        # === ЭТАП 6: Рекомендация практик ===
        logger.debug("🎯 Этап 6: Рекомендация практик...")
        
        practices = []
        if include_practices and primary_concepts:
            main_concept = primary_concepts[0]
            practices_rec = practices_recommender.suggest_practices_for_concept(main_concept, limit=3)
            practices = practices_rec.get("practices", [])
        
        # === ЭТАП 7: Цепочки связей ===
        logger.debug("⛓️ Этап 7: Анализ цепочек...")
        
        learning_path = None
        if include_chain and len(primary_concepts) >= 2:
            path_rec = practices_recommender.get_learning_path(
                primary_concepts[0],
                primary_concepts[1] if len(primary_concepts) > 1 else None
            )
            learning_path = path_rec.get("path")
        
        # === ЭТАП 8: Форматирование результата ===
        logger.debug("📝 Этап 8: Форматирование результата...")
        
        answer = llm_result["answer"]
        
        # Добавляем информацию о практиках
        if practices:
            answer += "\n\n💪 **Рекомендуемые практики:**\n"
            for practice in practices[:3]:
                answer += f"- {practice['name']} ({practice['type']}) — {practice['explanation']}\n"
        
        # Добавляем концепты
        concepts_section = level_adapter.format_concepts_for_output(primary_concepts)
        if concepts_section:
            answer += concepts_section
        
        sources = [
            {
                "block_id": b.block_id,
                "title": b.title,
                "document_title": b.document_title,
                "youtube_link": b.youtube_link,
                "start": b.start,
                "end": b.end,
                "video_id": b.video_id,
                "block_type": b.block_type,
                "complexity_score": b.complexity_score
            }
            for b in adapted_blocks
        ]
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            "status": "success",
            "answer": answer,
            "sources": sources,
            "concepts": primary_concepts,
            "relations": semantic_data["conceptual_links"],
            "practices": practices,
            "concept_hierarchy": concept_hierarchies,
            "learning_path": learning_path,
            "metadata": {
                "user_level": user_level,
                "blocks_used": len(adapted_blocks),
                "concepts_found": len(primary_concepts),
                "practices_recommended": len(practices),
                "chain_depth": len(learning_path) if learning_path else 0
            },
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(elapsed_time, 2)
        }
        
        if debug_info is not None:
            debug_info["total_time"] = elapsed_time
            result["debug"] = debug_info
        
        logger.info(f"✅ Запрос обработан за {elapsed_time:.2f}с (Phase 3)")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}", exc_info=True)
        return {
            "status": "error",
            "answer": f"Произошла ошибка: {str(e)}",
            "sources": [],
            "concepts": [],
            "relations": [],
            "practices": [],
            "concept_hierarchy": {},
            "learning_path": None,
            "metadata": {"error": str(e)},
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
            "debug": debug_info
        }
```


***

## Шаг 4: Обновить `bot_agent/__init__.py`

```python
# bot_agent/__init__.py

import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

LOG_DIR = Path(__file__).parent.parent / "logs" / "bot_agent"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "bot_agent.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("bot_agent")

# Phase 1
from answer_basic import answer_question_basic, ask

# Phase 2
from answer_sag_aware import answer_question_sag_aware

# Phase 3
from answer_graph_powered import answer_question_graph_powered

__all__ = [
    "answer_question_basic",
    "ask",
    "answer_question_sag_aware",
    "answer_question_graph_powered"
]

logger.info("🚀 Bot Agent инициализирован (Phase 1 + Phase 2 + Phase 3)")
```


***

## Шаг 5: Создание тестового скрипта `test_phase3.py`

```python
# test_phase3.py
"""
Тестирование Phase 3 - Graph Powered QA
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent / "bot_agent"))

from answer_graph_powered import answer_question_graph_powered

print("=" * 90)
print("🧪 ТЕСТИРОВАНИЕ PHASE 3 - KNOWLEDGE GRAPH POWERED QA БОТ")
print("=" * 90)

test_queries = [
    ("Что такое осознавание?", "beginner", True, True),
    ("Как работает разотождествление?", "intermediate", True, True),
    ("Какие практики помогают в трансформации сознания?", "advanced", True, True),
]

for i, (query, level, with_practices, with_chain) in enumerate(test_queries, 1):
    print(f"\n{'='*90}")
    print(f"ТЕСТ {i}/{len(test_queries)}")
    print(f"{'='*90}")
    print(f"\n📋 Вопрос: {query}")
    print(f"📊 Уровень: {level}\n")
    
    try:
        result = answer_question_graph_powered(
            query,
            user_level=level,
            include_practices=with_practices,
            include_chain=with_chain,
            debug=True
        )
        
        print(f"Status: {result['status']}")
        print(f"Processing time: {result['processing_time_seconds']}s")
        print(f"Metadata: {json.dumps(result['metadata'], indent=2)}")
        
        print(f"\n💬 ОТВЕТ:\n{result['answer']}")
        
        if result.get('concepts'):
            print(f"\n🔑 КОНЦЕПТЫ ({len(result['concepts'])}):")
            for concept in result['concepts']:
                print(f"  • {concept}")
        
        if result.get('practices'):
            print(f"\n💪 ПРАКТИКИ ({len(result['practices'])}):")
            for practice in result['practices'][:3]:
                print(f"  • {practice['name']} ({practice['type']})")
                if practice.get('source_blocks'):
                    print(f"    Источник: {practice['source_blocks'][0]['youtube_link']}")
        
        if result.get('learning_path'):
            print(f"\n🛤️ ПУТЬ ОБУЧЕНИЯ ({len(result['learning_path'])} шагов):")
            for step in result['learning_path'][:5]:
                print(f"  {step['step']}. {step['concept']}")
                if step.get('practices'):
                    print(f"     Практики: {', '.join(step['practices'][:2])}")
        
        if result.get('concept_hierarchy'):
            print(f"\n📊 ИЕРАРХИЯ КОНЦЕПТОВ:")
            for concept, hierarchy in list(result['concept_hierarchy'].items())[:2]:
                print(f"  {concept}:")
                if hierarchy.get('parent_concepts'):
                    parents = [p['name'] for p in hierarchy['parent_concepts'][:2]]
                    print(f"    ← {', '.join(parents)}")
                if hierarchy.get('related_concepts'):
                    related = [p['name'] for p in hierarchy['related_concepts'][:2]]
                    print(f"    ↔ {', '.join(related)}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 90)
print("✅ ТЕСТИРОВАНИЕ ФАЗЫ 3 ЗАВЕРШЕНО")
print("=" * 90)
```


***

## Шаг 6: Запуск Phase 3

```bash
# Убедись, что фазы 1 и 2 работают
python test_phase1.py
python test_phase2.py

# Запусти фазу 3
python test_phase3.py
```


***

## 🎯 Чек-лист Phase 3

- [ ] Создан `graph_client.py` с поддержкой Knowledge Graph
- [ ] Создан `practices_recommender.py` для рекомендаций практик
- [ ] Создан `answer_graph_powered.py` для Phase 3
- [ ] Обновлен `__init__.py` с новыми функциями
- [ ] Создан `test_phase3.py`
- [ ] Графы успешно загружаются
- [ ] Практики находятся и рекомендуются
- [ ] Цепочки связей строятся
- [ ] Иерархия концептов отображается правильно

***

## ✅ Результат Phase 3

✅ Полная поддержка Knowledge Graph
✅ Поиск практик для концептов
✅ Построение цепочек между концептами
✅ Рекомендации путей обучения
✅ Иерархия и связи концептов
✅ Объяснение "почему так" через граф

**Результат:** Бот превратился в **полнофункциональный ассистент трансформации** 🚀

