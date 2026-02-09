# bot_agent/answer_basic.py
"""
Basic QA Module - Phase 1
=========================

Основная функция ответа на вопросы: поиск блоков + генерация ответа через LLM.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from .data_loader import data_loader, Block
from .retriever import get_retriever
from .config import config
from .conversation_memory import get_conversation_memory
from .decision import DecisionGate, detect_routing_signals, resolve_user_stage
from .retrieval import HybridQueryBuilder, VoyageReranker
from .response import ResponseFormatter, ResponseGenerator

logger = logging.getLogger(__name__)


def answer_question_basic(
    query: str,
    user_id: str = "default",
    top_k: Optional[int] = None,
    debug: bool = False,
    use_semantic_memory: bool = True
) -> Dict:
    """
    Основная функция Phase 1: QA по лекциям.
    
    Принимает вопрос пользователя, находит релевантные блоки,
    и генерирует ответ через LLM.
    
    Args:
        query: Вопрос пользователя на русском языке
        top_k: Сколько релевантных блоков использовать (по умолчанию из config)
        debug: Если True, возвращает отладочную информацию
    
    Returns:
        Dict с ключами:
            - status: "success", "partial", или "error"
            - answer: str — готовый ответ пользователю
            - sources: List[Dict] — список блоков-источников
            - blocks_used: int — сколько блоков использовано
            - timestamp: str — когда был сформирован ответ
            - processing_time_seconds: float
            - debug: Optional[Dict] — отладочная информация
    
    Example:
        >>> result = answer_question_basic("Что такое осознавание?")
        >>> print(result["answer"])
        >>> for src in result["sources"]:
        ...     print(f"  - {src['title']} ({src['youtube_link']})")
    """
    
    logger.info(f"📋 Обработка запроса: '{query[:50]}...' (user: {user_id})")
    
    top_k = top_k or config.TOP_K_BLOCKS
    start_time = datetime.now()
    debug_info = {} if debug else None
    
    try:
        # === ЭТАП 0: Загрузка памяти диалога ===
        memory = get_conversation_memory(user_id)

        if use_semantic_memory and (
            config.ENABLE_SEMANTIC_MEMORY or config.ENABLE_CONVERSATION_SUMMARY
        ):
            memory_context = memory.get_adaptive_context_for_llm(query)
            conversation_context = memory.format_context_for_llm(memory_context)
        else:
            conversation_context = memory.get_context_for_llm(
                n=config.CONVERSATION_HISTORY_DEPTH,
                max_chars=config.MAX_CONTEXT_SIZE
            )
            memory_context = {
                "short_term": conversation_context,
                "semantic": "",
                "summary": ""
            }

        if debug_info is not None:
            debug_info["memory_context_used"] = {
                "short_term_chars": len(memory_context.get("short_term", "")),
                "semantic_chars": len(memory_context.get("semantic", "")),
                "summary_chars": len(memory_context.get("summary", "")),
                "semantic_enabled": bool(use_semantic_memory and config.ENABLE_SEMANTIC_MEMORY),
                "summary_enabled": bool(use_semantic_memory and config.ENABLE_CONVERSATION_SUMMARY)
            }

        user_stage = resolve_user_stage(memory)

        # === ЭТАП 1: Загрузка данных ===
        logger.debug("📂 Этап 1: Загрузка данных...")
        data_loader.load_all_data()
        
        if not data_loader.get_all_blocks():
            response = {
                "status": "error",
                "answer": f"❌ Не удалось загрузить данные лекций. Проверьте наличие файлов в {config.SAG_FINAL_DIR}",
                "sources": [],
                "blocks_used": 0,
                "error": "no_data",
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": 0.0,
                "debug": {"error_detail": "data_loader returned empty blocks"} if debug else None
            }
            memory.add_turn(user_input=query, bot_response=response["answer"], blocks_used=0)
            return response
        
        if debug_info is not None:
            debug_info["data_loaded"] = {
                "total_documents": len(data_loader.get_all_documents()),
                "total_blocks": len(data_loader.get_all_blocks())
            }
        
        # === ЭТАП 2: Поиск релевантных блоков ===
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

        stage_filtered_blocks = decision_gate.stage_filter.filter_retrieval_pairs(
            user_stage,
            retrieved_blocks,
        )
        block_cap = decision_gate.scorer.suggest_block_cap(
            len(stage_filtered_blocks),
            routing_result.confidence_level,
        )
        retrieved_blocks = stage_filtered_blocks[:block_cap]
        
        if not retrieved_blocks:
            logger.warning(f"⚠️ Не найдено релевантных блоков для: '{query}'")
            response = {
                "status": "partial",
                "answer": "К сожалению, я не нашёл релевантного материала для этого вопроса. Попробуйте переформулировать или спросить что-то более конкретное.",
                "sources": [],
                "blocks_used": 0,
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
                "debug": debug_info
            }
            memory.add_turn(user_input=query, bot_response=response["answer"], blocks_used=0)
            return response
        
        blocks = [block for block, score in retrieved_blocks]
        
        if debug_info is not None:
            debug_info["retrieval"] = {
                "query": query,
                "hybrid_query": hybrid_query,
                "blocks_found": len(blocks),
                "scores": [float(score) for block, score in retrieved_blocks],
                "voyage_enabled": bool(config.VOYAGE_ENABLED),
                "voyage_top_k": rerank_k,
                "stage_filter_applied": True,
                "confidence_block_cap": block_cap,
            }
            debug_info["routing"] = {
                "mode": routing_result.mode,
                "rule_id": routing_result.decision.rule_id,
                "reason": routing_result.decision.reason,
                "confidence_score": routing_result.confidence_score,
                "confidence_level": routing_result.confidence_level,
                "adjusted_by_stage": routing_result.adjusted_by_stage,
            }
        
        logger.info(f"✅ Найдено {len(blocks)} релевантных блоков")
        
        # === ЭТАП 3: Формирование ответа через LLM ===
        logger.debug("🤖 Этап 3: Формирование ответа через LLM...")
        response_generator = ResponseGenerator()
        llm_result = response_generator.generate(
            query,
            blocks,
            conversation_context=conversation_context,
            mode=routing_result.mode,
            confidence_level=routing_result.confidence_level,
            forbid=routing_result.decision.forbid,
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
        )
        
        if llm_result.get("error"):
            logger.error(f"❌ Ошибка LLM: {llm_result['error']}")
            response = {
                "status": "error",
                "answer": llm_result.get("answer", "Произошла ошибка при формировании ответа."),
                "sources": [],
                "blocks_used": 0,
                "error": llm_result.get("error"),
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
                "debug": debug_info
            }
            memory.add_turn(user_input=query, bot_response=response["answer"], blocks_used=0)
            return response
        
        if debug_info is not None:
            debug_info["llm"] = {
                "model": llm_result.get("model_used"),
                "tokens_used": llm_result.get("tokens_used")
            }
        
        # === ЭТАП 4: Формирование источников ===
        logger.debug("📝 Этап 4: Формирование информации об источниках...")
        sources = [
            {
                "block_id": b.block_id,
                "title": b.title,
                "summary": b.summary,
                "document_title": b.document_title,
                "youtube_link": b.youtube_link,
                "start": b.start,
                "end": b.end,
                "video_id": b.video_id
            }
            for b in blocks
        ]
        
        # === ФИНАЛЬНЫЙ РЕЗУЛЬТАТ ===
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        formatter = ResponseFormatter()
        formatted_answer = formatter.format_answer(
            llm_result["answer"],
            mode=routing_result.mode,
            confidence_level=routing_result.confidence_level,
        )

        result = {
            "status": "success",
            "answer": formatted_answer,
            "sources": sources,
            "blocks_used": len(blocks),
            "metadata": {
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

        memory.add_turn(
            user_input=query,
            bot_response=formatted_answer,
            blocks_used=len(blocks),
            concepts=[b.title for b in blocks]
        )
        
        if debug_info is not None:
            debug_info["total_time"] = elapsed_time
            result["debug"] = debug_info
        
        logger.info(f"✅ Запрос обработан за {elapsed_time:.2f}с")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Непредвиденная ошибка: {e}", exc_info=True)
        response = {
            "status": "error",
            "answer": f"❌ Произошла непредвиденная ошибка: {str(e)}",
            "sources": [],
            "blocks_used": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
            "debug": debug_info
        }
        try:
            memory = get_conversation_memory(user_id)
            memory.add_turn(user_input=query, bot_response=response["answer"], blocks_used=0)
        except Exception:
            pass
        return response


# === ПРОСТОЙ ИНТЕРФЕЙС ДЛЯ БЫСТРОГО ИСПОЛЬЗОВАНИЯ ===

def ask(query: str, verbose: bool = False) -> str:
    """
    Простой интерфейс: вопрос -> ответ (только текст).
    
    Используется когда нужен только текст ответа:
    
    Example:
        >>> print(ask("Что такое разотождествление?"))
        
        >>> # С выводом источников:
        >>> print(ask("Что такое осознавание?", verbose=True))
    """
    result = answer_question_basic(query, debug=verbose)
    
    if verbose and result.get("sources"):
        print(f"\n[📚 Источники ({len(result['sources'])} блоков)]")
        for src in result['sources']:
            print(f"  • {src['document_title']} ({src['start']}—{src['end']})")
            print(f"    → {src['youtube_link']}")
    
    return result["answer"]



