# bot_agent/answer_sag_aware.py
"""
SAG v2.0 Aware Answer Module - Phase 2
======================================

Главная функция Phase 2: answer_question_sag_aware.

Использует SAG v2.0 структуру для:
- Адаптации ответов под уровень пользователя
- Извлечения и отображения концептов
- Семантического анализа связей
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime

from .data_loader import data_loader, Block
from .retriever import get_retriever
from .llm_answerer import LLMAnswerer
from .user_level_adapter import UserLevelAdapter
from .semantic_analyzer import SemanticAnalyzer
from .config import config

logger = logging.getLogger(__name__)


def answer_question_sag_aware(
    query: str,
    user_level: str = "beginner",
    top_k: Optional[int] = None,
    debug: bool = False
) -> Dict:
    """
    Phase 2: QA с использованием SAG v2.0 структуры.
    
    Этапы обработки:
        1. Инициализация компонентов
        2. Поиск релевантных блоков
        3. Адаптация по уровню пользователя
        4. Семантический анализ
        5. Формирование ответа через LLM
        6. Форматирование вывода
    
    Args:
        query: Вопрос пользователя
        user_level: Уровень пользователя (beginner/intermediate/advanced)
        top_k: Количество блоков для поиска (по умолчанию из config)
        debug: Возвращать ли отладочную информацию
    
    Returns:
        Dict с ключами:
            - status: "success" | "error" | "partial"
            - answer: str — готовый ответ
            - sources: List[Dict] — использованные источники
            - concepts: List[str] — ключевые концепты
            - relations: List[Dict] — связи между концептами
            - user_level: str — уровень пользователя
            - metadata: Dict — дополнительная информация
            - timestamp: str — время обработки
            - processing_time_seconds: float
            - debug: Optional[Dict] — отладочная информация
    """
    
    logger.info(f"📋 Phase 2: Обработка запроса '{query[:50]}...' [Level: {user_level}]")
    
    top_k = top_k or config.TOP_K_BLOCKS
    start_time = datetime.now()
    debug_info = {} if debug else None
    
    try:
        # === ЭТАП 1: Инициализация компонентов ===
        logger.debug("🔧 Этап 1: Инициализация компонентов...")
        
        data_loader.load_all_data()
        level_adapter = UserLevelAdapter(user_level)
        semantic_analyzer = SemanticAnalyzer()
        
        if debug_info is not None:
            debug_info["user_level"] = user_level
            debug_info["top_k"] = top_k
        
        # === ЭТАП 2: Поиск блоков ===
        logger.debug("🔍 Этап 2: Поиск релевантных блоков...")
        
        retriever = get_retriever()
        retrieved_blocks = retriever.retrieve(query, top_k=top_k)
        
        if debug_info is not None:
            debug_info["blocks_retrieved"] = len(retrieved_blocks)
        
        if not retrieved_blocks:
            elapsed = (datetime.now() - start_time).total_seconds()
            return {
                "status": "partial",
                "answer": "К сожалению, я не нашёл релевантного материала для этого вопроса. "
                         "Попробуйте переформулировать или задать более конкретный вопрос.",
                "sources": [],
                "concepts": [],
                "relations": [],
                "user_level": user_level,
                "metadata": {"reason": "no_blocks_found"},
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": round(elapsed, 2),
                "debug": debug_info
            }
        
        # Извлекаем блоки из результатов (без скоров)
        blocks = [block for block, score in retrieved_blocks]
        
        if debug_info is not None:
            debug_info["block_scores"] = [
                {"block_id": b.block_id, "score": round(s, 3)} 
                for b, s in retrieved_blocks
            ]
        
        # === ЭТАП 3: Адаптация по уровню ===
        logger.debug("🎯 Этап 3: Адаптация блоков по уровню пользователя...")
        
        adapted_blocks = level_adapter.filter_blocks_by_level(blocks)
        
        if debug_info is not None:
            debug_info["blocks_after_level_filter"] = len(adapted_blocks)
        
        # === ЭТАП 4: Семантический анализ ===
        logger.debug("🧠 Этап 4: Семантический анализ...")
        
        semantic_data = semantic_analyzer.analyze_relations(adapted_blocks)
        
        if debug_info is not None:
            debug_info["semantic_analysis"] = {
                "primary_concepts": semantic_data["primary_concepts"],
                "relations_found": len(semantic_data["conceptual_links"])
            }
        
        # === ЭТАП 5: Формирование ответа через LLM ===
        logger.debug("🤖 Этап 5: Формирование ответа через LLM...")
        
        answerer = LLMAnswerer()
        
        # Адаптируем системный промпт под уровень
        base_system_prompt = answerer.build_system_prompt()
        adapted_system_prompt = level_adapter.adapt_system_prompt(base_system_prompt)
        
        # Добавляем guidance по длине ответа
        length_guidance = level_adapter.get_answer_length_guidance()
        
        # Формируем контекст с информацией о концептах
        context = answerer.build_context_prompt(adapted_blocks, query)
        context += f"\n\n{length_guidance}"
        
        if semantic_data["primary_concepts"]:
            concepts_hint = ", ".join(semantic_data["primary_concepts"])
            context += f"\n\n🔑 Основные концепты для этого ответа: {concepts_hint}"
        
        # Генерируем ответ с адаптированным промптом
        # Временно подменяем build_system_prompt для использования adapted версии
        original_build_prompt = answerer.build_system_prompt
        answerer.build_system_prompt = lambda: adapted_system_prompt
        
        llm_result = answerer.generate_answer(
            query,
            adapted_blocks,
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS
        )
        
        # Восстанавливаем оригинальный метод
        answerer.build_system_prompt = original_build_prompt
        
        if debug_info is not None:
            debug_info["llm_result"] = {
                "model_used": llm_result.get("model_used"),
                "tokens_used": llm_result.get("tokens_used"),
                "error": llm_result.get("error")
            }
        
        # Проверяем ошибки LLM
        if llm_result.get("error") and llm_result.get("error") not in ["no_blocks"]:
            elapsed = (datetime.now() - start_time).total_seconds()
            return {
                "status": "error",
                "answer": llm_result.get("answer", "Ошибка при формировании ответа"),
                "sources": _format_sources(adapted_blocks),
                "concepts": semantic_data["primary_concepts"],
                "relations": [],
                "user_level": user_level,
                "metadata": {"error": llm_result.get("error")},
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": round(elapsed, 2),
                "debug": debug_info
            }
        
        # === ЭТАП 6: Форматирование вывода ===
        logger.debug("📝 Этап 6: Форматирование вывода...")
        
        answer = llm_result["answer"]
        
        # Добавляем концепты в конец ответа (форматированные по уровню)
        concepts_section = level_adapter.format_concepts_for_output(
            semantic_data["primary_concepts"]
        )
        if concepts_section:
            answer += concepts_section
        
        # Формируем источники с SAG v2.0 полями
        sources = _format_sources(adapted_blocks)
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            "status": "success",
            "answer": answer,
            "sources": sources,
            "concepts": semantic_data["primary_concepts"],
            "relations": semantic_data["conceptual_links"],
            "user_level": user_level,
            "metadata": {
                "analysis_summary": semantic_data["analysis_summary"],
                "blocks_used": len(adapted_blocks),
                "semantic_links": len(semantic_data["conceptual_links"]),
                "model_used": llm_result.get("model_used"),
                "tokens_used": llm_result.get("tokens_used", 0)
            },
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(elapsed_time, 2)
        }
        
        if debug_info is not None:
            debug_info["total_time"] = elapsed_time
            result["debug"] = debug_info
        
        logger.info(f"✅ Phase 2: Запрос обработан за {elapsed_time:.2f}с "
                   f"[Level: {user_level}, Blocks: {len(adapted_blocks)}, "
                   f"Concepts: {len(semantic_data['primary_concepts'])}]")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Phase 2 Error: {e}", exc_info=True)
        elapsed = (datetime.now() - start_time).total_seconds()
        return {
            "status": "error",
            "answer": f"Произошла ошибка при обработке запроса: {str(e)}",
            "sources": [],
            "concepts": [],
            "relations": [],
            "user_level": user_level,
            "metadata": {"error": str(e)},
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(elapsed, 2),
            "debug": debug_info
        }


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


def ask_sag(query: str, user_level: str = "beginner") -> str:
    """
    Простой интерфейс Phase 2: вернуть только текст ответа.
    
    Args:
        query: Вопрос пользователя
        user_level: Уровень (beginner/intermediate/advanced)
        
    Returns:
        Текст ответа
    """
    result = answer_question_sag_aware(query, user_level=user_level)
    return result.get("answer", "Ошибка при формировании ответа")
