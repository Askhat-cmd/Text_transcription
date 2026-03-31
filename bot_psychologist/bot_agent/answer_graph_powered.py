# bot_agent/answer_graph_powered.py
"""
Graph-Powered Answer Module - Phase 3
=====================================

Главная функция Phase 3: answer_question_graph_powered.

Расширяет Phase 2 поддержкой Knowledge Graph:
- Загрузка и анализ графа знаний
- Рекомендация практик для концептов
- Построение путей обучения
- Иерархия концептов
- Объяснение связей через граф
"""

import logging
from typing import Any, Dict, Optional, List
from datetime import datetime

from .data_loader import data_loader, Block
from .retriever import get_retriever
from .user_level_adapter import UserLevelAdapter
from .semantic_analyzer import SemanticAnalyzer
from .graph_client import graph_client
from .practices_recommender import practices_recommender
from .config import config
from .conversation_memory import get_conversation_memory
from .decision import DecisionGate, detect_routing_signals, resolve_user_stage
from .retrieval import HybridQueryBuilder, VoyageReranker
from .response import ResponseFormatter, ResponseGenerator

logger = logging.getLogger(__name__)


def answer_question_graph_powered(
    query: str,
    user_id: str = "default",
    user_level: str = "beginner",
    include_practices: bool = True,
    include_chain: bool = True,
    top_k: Optional[int] = None,
    debug: bool = False,
    session_store: Optional[Any] = None,
) -> Dict:
    """
    Phase 3: QA с полной поддержкой Knowledge Graph.
    
    Этапы обработки:
        1. Инициализация компонентов
        2. Поиск релевантных блоков
        3. Загрузка Knowledge Graph
        4. Анализ концептов через граф
        5. Формирование ответа через LLM
        6. Рекомендация практик
        7. Анализ цепочек (learning path)
        8. Форматирование результата
    
    Args:
        query: Вопрос пользователя
        user_level: Уровень пользователя (beginner/intermediate/advanced)
        include_practices: Включать ли рекомендации практик
        include_chain: Включать ли цепочки связей / learning path
        top_k: Количество блоков для поиска
        debug: Возвращать ли отладочную информацию
    
    Returns:
        Dict с расширенными полями Phase 3:
            - status: "success" | "error" | "partial"
            - answer: str — готовый ответ
            - sources: List[Dict] — использованные источники
            - concepts: List[str] — ключевые концепты
            - relations: List[Dict] — связи между концептами
            - practices: List[Dict] — рекомендованные практики
            - concept_hierarchy: Dict — иерархия концептов
            - learning_path: Optional[List] — путь обучения
            - metadata: Dict — дополнительная информация
            - timestamp: str — время обработки
            - processing_time_seconds: float
            - debug: Optional[Dict] — отладочная информация
    """
    
    logger.info(f"📊 Phase 3: Обработка запроса '{query[:50]}...' [Level: {user_level}, user: {user_id}]")
    
    top_k = top_k or config.TOP_K_BLOCKS
    start_time = datetime.now()
    debug_info = {} if debug else None
    
    try:
        # === ЭТАП 0: Загрузка памяти диалога ===
        memory = get_conversation_memory(user_id)
        conversation_context = memory.get_adaptive_context_text(query)
        user_stage = resolve_user_stage(memory)

        # === ЭТАП 1: Инициализация компонентов ===
        logger.debug("🔧 Этап 1: Инициализация компонентов...")
        
        data_loader.load_all_data()
        level_adapter = UserLevelAdapter(user_level)
        semantic_analyzer = SemanticAnalyzer()
        
        if debug_info is not None:
            debug_info["user_level"] = user_level
            debug_info["top_k"] = top_k
            debug_info["include_practices"] = include_practices
            debug_info["include_chain"] = include_chain
        
        # === ЭТАП 2: Поиск блоков ===
        logger.debug("🔍 Этап 2: Поиск релевантных блоков...")
        query_builder = HybridQueryBuilder(max_chars=config.MAX_CONTEXT_SIZE + 1200)
        hybrid_query = query_builder.build_query(
            current_question=query,
            conversation_summary=memory.summary or "",
            working_state=memory.working_state,
            short_term_context=conversation_context,
        )

        retriever = get_retriever()
        retrieved_blocks = retriever.retrieve(hybrid_query, top_k=top_k)
        reranker = VoyageReranker(
            model=config.VOYAGE_MODEL,
            enabled=config.VOYAGE_ENABLED,
        )
        rerank_k = min(len(retrieved_blocks), max(1, min(top_k, config.VOYAGE_TOP_K)))
        if rerank_k > 0:
            reranked = reranker.rerank_pairs(query, retrieved_blocks, top_k=rerank_k)
            if reranked:
                retrieved_blocks = reranked

        decision_gate = DecisionGate()
        routing_signals = detect_routing_signals(query, retrieved_blocks)
        routing_result = decision_gate.route(routing_signals, user_stage=user_stage)

        block_cap = decision_gate.scorer.suggest_block_cap(
            len(retrieved_blocks),
            routing_result.confidence_level,
        )
        retrieved_blocks = retrieved_blocks[:block_cap]
        
        if debug_info is not None:
            debug_info["blocks_retrieved"] = len(retrieved_blocks)
        
        if not retrieved_blocks:
            elapsed = (datetime.now() - start_time).total_seconds()
            response = _build_empty_response(
                query=query,
                user_level=user_level,
                reason="no_blocks_found",
                elapsed=elapsed,
                debug_info=debug_info
            )
            memory.add_turn(user_input=query, bot_response=response["answer"], blocks_used=0)
            return response
        
        # Извлекаем блоки из результатов
        blocks = [block for block, score in retrieved_blocks]
        
        if debug_info is not None:
            debug_info["block_scores"] = [
                {"block_id": b.block_id, "score": round(s, 3)} 
                for b, s in retrieved_blocks
            ]
            debug_info["hybrid_query"] = hybrid_query
            debug_info["voyage_rerank"] = {
                "enabled": bool(config.VOYAGE_ENABLED),
                "top_k": rerank_k,
                "confidence_block_cap": block_cap,
            }
            debug_info["routing"] = {
                "mode": routing_result.mode,
                "rule_id": routing_result.decision.rule_id,
                "reason": routing_result.decision.reason,
                "confidence_score": routing_result.confidence_score,
                "confidence_level": routing_result.confidence_level,
            }
        
        # Адаптация по уровню
        adapted_blocks = level_adapter.filter_blocks_by_level(blocks)
        
        # Семантический анализ (Phase 2)
        semantic_data = semantic_analyzer.analyze_relations(adapted_blocks)
        primary_concepts = semantic_data["primary_concepts"]
        
        if debug_info is not None:
            debug_info["blocks_after_level_filter"] = len(adapted_blocks)
            debug_info["primary_concepts"] = primary_concepts
        
        # === ЭТАП 3: Загрузка Knowledge Graph ===
        logger.debug("🧠 Этап 3: Загрузка Knowledge Graph...")
        
        graph_client.load_graphs_from_all_documents()
        
        if debug_info is not None:
            graph_stats = graph_client.get_statistics()
            debug_info["graph_stats"] = {
                "total_nodes": graph_stats["total_nodes"],
                "total_edges": graph_stats["total_edges"],
                "loaded_files": graph_stats["loaded_files"]
            }
        
        # === ЭТАП 4: Анализ концептов через граф ===
        logger.debug("🔗 Этап 4: Анализ концептов через Knowledge Graph...")
        
        concept_hierarchies = {}
        
        for concept in primary_concepts[:3]:  # Ограничиваем топ-3 концептами
            hierarchy = graph_client.get_concept_hierarchy(concept)
            if "error" not in hierarchy:
                concept_hierarchies[concept] = hierarchy
        
        if debug_info is not None:
            debug_info["graph_analysis"] = {
                "concepts_analyzed": len(concept_hierarchies),
                "hierarchies_found": len([
                    h for h in concept_hierarchies.values() 
                    if h.get("parent_concepts") or h.get("related_concepts")
                ])
            }
        
        # === ЭТАП 5: Формирование ответа через LLM ===
        logger.debug("🤖 Этап 5: Формирование ответа через LLM...")
        
        graph_context = _build_graph_context(concept_hierarchies)
        response_generator = ResponseGenerator()
        llm_result = response_generator.generate(
            query,
            adapted_blocks,
            conversation_context=conversation_context,
            mode=routing_result.mode,
            confidence_level=routing_result.confidence_level,
            forbid=routing_result.decision.forbid,
            user_level_adapter=level_adapter,
            additional_system_context=graph_context,
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.get_mode_max_tokens(routing_result.mode),
            session_store=session_store,
            session_id=user_id,
        )
        
        if debug_info is not None:
            debug_info["llm_result"] = {
                "model_used": llm_result.get("model_used"),
                "tokens_used": llm_result.get("tokens_used"),
                "error": llm_result.get("error"),
                "llm_call_info": llm_result.get("llm_call_info"),
            }
        
        # Проверяем ошибки LLM
        if llm_result.get("error") and llm_result.get("error") not in ["no_blocks"]:
            elapsed = (datetime.now() - start_time).total_seconds()
            response = {
                "status": "error",
                "answer": llm_result.get("answer", "Ошибка при формировании ответа"),
                "sources": _format_sources(adapted_blocks),
                "concepts": primary_concepts,
                "relations": [],
                "practices": [],
                "concept_hierarchy": {},
                "learning_path": None,
                "metadata": {"error": llm_result.get("error")},
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": round(elapsed, 2),
                "debug": debug_info
            }
            memory.add_turn(user_input=query, bot_response=response["answer"], blocks_used=len(adapted_blocks))
            return response
        
        # === ЭТАП 6: Рекомендация практик ===
        logger.debug("🎯 Этап 6: Рекомендация практик...")
        
        practices = []
        if include_practices and primary_concepts:
            main_concept = primary_concepts[0]
            practices_rec = practices_recommender.suggest_practices_for_concept(
                main_concept, 
                limit=3
            )
            practices = practices_rec.get("practices", [])
        
        if debug_info is not None:
            debug_info["practices_found"] = len(practices)
        
        # === ЭТАП 7: Анализ цепочек (Learning Path) ===
        logger.debug("⛓️ Этап 7: Анализ цепочек...")
        
        learning_path = None
        if include_chain and primary_concepts:
            main_concept = primary_concepts[0]
            path_rec = practices_recommender.get_learning_path(main_concept)
            learning_path = path_rec.get("path")
        
        if debug_info is not None:
            debug_info["learning_path_steps"] = len(learning_path) if learning_path else 0
        
        # === ЭТАП 8: Форматирование результата ===
        logger.debug("📝 Этап 8: Форматирование результата...")
        
        answer = llm_result["answer"]
        
        # Добавляем раздел с практиками
        if practices:
            answer += "\n\n💪 **Рекомендуемые практики:**\n"
            for practice in practices[:3]:
                explanation = practice.get("explanation", "")
                if explanation:
                    answer += f"- **{practice['name']}** ({practice['type']}) — {explanation}\n"
                else:
                    answer += f"- **{practice['name']}** ({practice['type']})\n"
        
        # Добавляем концепты (форматированные по уровню)
        concepts_section = level_adapter.format_concepts_for_output(primary_concepts)
        if concepts_section:
            answer += concepts_section
        formatter = ResponseFormatter()
        answer = formatter.format_answer(
            answer,
            mode=routing_result.mode,
            confidence_level=routing_result.confidence_level,
        )
        
        # Формируем источники
        sources = _format_sources(adapted_blocks)
        
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
                "chain_depth": len(learning_path) if learning_path else 0,
                "model_used": llm_result.get("model_used"),
                "tokens_used": llm_result.get("tokens_used", 0),
                "graph_nodes": graph_client.get_statistics()["total_nodes"],
                "graph_edges": graph_client.get_statistics()["total_edges"],
                "recommended_mode": routing_result.mode,
                "decision_rule_id": routing_result.decision.rule_id,
                "confidence_score": routing_result.confidence_score,
                "confidence_level": routing_result.confidence_level,
                "mode_reason": routing_result.decision.reason,
                "retrieval_block_cap": block_cap,
            },
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(elapsed_time, 2)
        }

        if debug_info is not None:
            llm_call = llm_result.get("llm_call_info") if isinstance(llm_result, dict) else None
            if not isinstance(llm_call, dict):
                llm_call = {}
            result["debug_trace"] = {
                "turn_number": len(memory.turns) + 1,
                "recommended_mode": routing_result.mode,
                "sd_level": None,
                "user_state": None,
                "hybrid_query_preview": hybrid_query[:400],
                "chunks_after_filter": [],
                "llm_calls": [llm_call] if llm_call else [],
            }

        memory.add_turn(
            user_input=query,
            bot_response=answer,
            blocks_used=len(adapted_blocks),
            concepts=[b.title for b in adapted_blocks]
        )
        
        if debug_info is not None:
            debug_info["total_time"] = elapsed_time
            result["debug"] = debug_info
        
        logger.info(
            f"✅ Phase 3: Запрос обработан за {elapsed_time:.2f}с "
            f"[Level: {user_level}, Blocks: {len(adapted_blocks)}, "
            f"Concepts: {len(primary_concepts)}, Practices: {len(practices)}]"
        )
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Phase 3 Error: {e}", exc_info=True)
        elapsed = (datetime.now() - start_time).total_seconds()
        response = {
            "status": "error",
            "answer": f"Произошла ошибка при обработке запроса: {str(e)}",
            "sources": [],
            "concepts": [],
            "relations": [],
            "practices": [],
            "concept_hierarchy": {},
            "learning_path": None,
            "metadata": {"error": str(e)},
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(elapsed, 2),
            "debug": debug_info
        }
        try:
            memory = get_conversation_memory(user_id)
            memory.add_turn(user_input=query, bot_response=response["answer"], blocks_used=0)
        except Exception:
            pass
        return response


def _build_empty_response(
    query: str,
    user_level: str,
    reason: str,
    elapsed: float,
    debug_info: Optional[Dict]
) -> Dict:
    """Построить пустой ответ при отсутствии данных"""
    return {
        "status": "partial",
        "answer": "К сожалению, я не нашёл релевантного материала для этого вопроса. "
                 "Попробуйте переформулировать или задать более конкретный вопрос.",
        "sources": [],
        "concepts": [],
        "relations": [],
        "practices": [],
        "concept_hierarchy": {},
        "learning_path": None,
        "metadata": {"reason": reason, "user_level": user_level},
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": round(elapsed, 2),
        "debug": debug_info
    }


def _build_graph_context(concept_hierarchies: Dict) -> str:
    """
    Построить контекст из иерархии концептов для LLM.
    
    Args:
        concept_hierarchies: Dict концепт -> иерархия
        
    Returns:
        Строка с контекстом для добавления в промпт
    """
    if not concept_hierarchies:
        return ""
    
    context_lines = ["\n\n🧠 СТРУКТУРА КОНЦЕПТОВ (из Knowledge Graph):"]
    
    for concept, hierarchy in list(concept_hierarchies.items())[:3]:
        context_lines.append(f"\n**{concept}** ({hierarchy.get('type', 'CONCEPT')}):")
        
        # Родительские концепты
        if hierarchy.get("parent_concepts"):
            parents = [p["name"] for p in hierarchy["parent_concepts"][:3]]
            context_lines.append(f"  ← Часть: {', '.join(parents)}")
        
        # Дочерние концепты
        if hierarchy.get("child_concepts"):
            children = [c["name"] for c in hierarchy["child_concepts"][:3]]
            context_lines.append(f"  → Содержит: {', '.join(children)}")
        
        # Связанные концепты
        if hierarchy.get("related_concepts"):
            related = [r["name"] for r in hierarchy["related_concepts"][:3]]
            context_lines.append(f"  ↔ Связан с: {', '.join(related)}")
    
    return "\n".join(context_lines)


def _format_sources(blocks: List[Block]) -> List[Dict]:
    """
    Форматирует блоки в источники с SAG v2.0 полями.
    
    Args:
        blocks: Список блоков
        
    Returns:
        List[Dict] — отформатированные источники
    """
    sources = []
    for block in blocks:
        sources.append({
            "block_id": block.block_id,
            "title": block.title,
            "summary": block.summary,
            "document_title": block.document_title,
            "youtube_link": block.youtube_link,
            "start": block.start,
            "end": block.end,
            "video_id": block.video_id,
            # SAG v2.0 поля
            "block_type": block.block_type,
            "emotional_tone": block.emotional_tone,
            "complexity_score": block.complexity_score,
            "conceptual_depth": block.conceptual_depth
        })
    return sources


def ask_graph(
    query: str,
    user_level: str = "beginner",
    include_practices: bool = True
) -> str:
    """
    Простой интерфейс Phase 3: вернуть только текст ответа.
    
    Args:
        query: Вопрос пользователя
        user_level: Уровень (beginner/intermediate/advanced)
        include_practices: Включать ли практики в ответ
        
    Returns:
        Текст ответа
    """
    result = answer_question_graph_powered(
        query,
        user_level=user_level,
        include_practices=include_practices
    )
    return result.get("answer", "Ошибка при формировании ответа")


