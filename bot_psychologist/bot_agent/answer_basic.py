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
from .llm_answerer import LLMAnswerer
from .config import config
from .conversation_memory import get_conversation_memory

logger = logging.getLogger(__name__)


def answer_question_basic(
    query: str,
    user_id: str = "default",
    top_k: Optional[int] = None,
    debug: bool = False
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
        conversation_context = memory.get_context_for_llm(
            n=config.CONVERSATION_HISTORY_DEPTH,
            max_chars=config.MAX_CONTEXT_SIZE
        )

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
        retriever = get_retriever()
        retrieved_blocks = retriever.retrieve(query, top_k=top_k)
        
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
                "blocks_found": len(blocks),
                "scores": [float(score) for block, score in retrieved_blocks]
            }
        
        logger.info(f"✅ Найдено {len(blocks)} релевантных блоков")
        
        # === ЭТАП 3: Формирование ответа через LLM ===
        logger.debug("🤖 Этап 3: Формирование ответа через LLM...")
        answerer = LLMAnswerer()
        llm_result = answerer.generate_answer(
            query,
            blocks,
            conversation_history=conversation_context
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
        
        result = {
            "status": "success",
            "answer": llm_result["answer"],
            "sources": sources,
            "blocks_used": len(blocks),
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(elapsed_time, 2)
        }

        memory.add_turn(
            user_input=query,
            bot_response=llm_result["answer"],
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



