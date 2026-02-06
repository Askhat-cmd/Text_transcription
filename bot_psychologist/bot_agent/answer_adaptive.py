# bot_agent/answer_adaptive.py
"""
Adaptive Answer Module - Phase 4
================================

Главная функция Phase 4: answer_question_adaptive.

Расширяет Phase 3 полноценным сопровождением пользователя:
- Классификация состояния пользователя (10 состояний)
- Долгосрочная память диалога
- Построение персональных путей трансформации
- Адаптивные рекомендации по состоянию
- Запрос обратной связи
"""

import logging
from typing import Dict, Optional
from datetime import datetime

from .data_loader import data_loader
from .retriever import get_retriever
from .llm_answerer import LLMAnswerer
from .user_level_adapter import UserLevelAdapter, UserLevel
from .semantic_analyzer import SemanticAnalyzer
from .graph_client import graph_client
from .state_classifier import state_classifier, StateAnalysis, UserState
from .conversation_memory import get_conversation_memory
from .path_builder import path_builder
from .config import config

logger = logging.getLogger(__name__)


def answer_question_adaptive(
    query: str,
    user_id: str = "default",
    user_level: str = "beginner",
    include_path_recommendation: bool = True,
    include_feedback_prompt: bool = True,
    top_k: Optional[int] = None,
    debug: bool = False
) -> Dict:
    """
    Phase 4: Адаптивный QA с учетом состояния и истории пользователя.
    
    Этапы обработки:
        1. Загрузка данных и памяти пользователя
        2. Анализ состояния пользователя
        3. Поиск релевантных блоков
        4. Генерация ответа с контекстом состояния
        5. Построение рекомендации пути
        6. Подготовка запроса обратной связи
        7. Сохранение в память
    
    Args:
        query: Вопрос пользователя
        user_id: ID пользователя (для памяти)
        user_level: Уровень пользователя (beginner/intermediate/advanced)
        include_path_recommendation: Включать ли рекомендацию пути
        include_feedback_prompt: Запрашивать ли обратную связь
        top_k: Количество блоков для поиска
        debug: Отладочная информация
    
    Returns:
        Dict с расширенными полями Phase 4:
            - status: "success" | "error" | "partial"
            - answer: str — ответ
            - state_analysis: Dict — анализ состояния
            - path_recommendation: Optional[Dict] — рекомендуемый путь
            - conversation_context: str — контекст истории
            - feedback_prompt: str — запрос обратной связи
            - sources: List[Dict]
            - concepts: List[str]
            - metadata: Dict
            - timestamp: str
            - processing_time_seconds: float
            - debug: Optional[Dict]
    """
    
    logger.info(f"🎯 Phase 4: Адаптивный ответ для {user_id} | '{query[:50]}...'")
    
    top_k = top_k or config.TOP_K_BLOCKS
    start_time = datetime.now()
    debug_info = {} if debug else None
    
    try:
        # ================================================================
        # ЭТАП 1: Загрузка данных и памяти
        # ================================================================
        logger.debug("📚 Этап 1: Загрузка данных и памяти...")
        
        data_loader.load_all_data()
        memory = get_conversation_memory(user_id)
        conversation_context = memory.get_context_for_llm(
            n=config.CONVERSATION_HISTORY_DEPTH,
            max_chars=config.MAX_CONTEXT_SIZE
        )
        
        # Парсим уровень пользователя
        try:
            level_enum = UserLevel(user_level.lower())
        except ValueError:
            level_enum = UserLevel.BEGINNER
        
        level_adapter = UserLevelAdapter(user_level)
        
        if debug_info is not None:
            debug_info["user_id"] = user_id
            debug_info["memory_turns"] = len(memory.turns)
        
        # ================================================================
        # ЭТАП 2: Анализ состояния пользователя
        # ================================================================
        logger.debug("🎯 Этап 2: Анализ состояния...")
        
        # Получить историю для контекста анализа
        conversation_history = [
            {"role": "user", "content": turn.user_input}
            for turn in memory.get_last_turns(config.CONVERSATION_HISTORY_DEPTH)
        ]
        
        state_analysis = state_classifier.analyze_message(
            query,
            conversation_history=conversation_history
        )
        
        logger.info(f"✅ Состояние: {state_analysis.primary_state.value} "
                   f"(уверенность: {state_analysis.confidence:.2f})")
        
        if debug_info is not None:
            debug_info["state_analysis"] = {
                "primary": state_analysis.primary_state.value,
                "confidence": state_analysis.confidence,
                "secondary": [s.value for s in state_analysis.secondary_states],
                "emotional_tone": state_analysis.emotional_tone,
                "depth": state_analysis.depth
            }
        
        # ================================================================
        # ЭТАП 3: Поиск релевантных блоков
        # ================================================================
        logger.debug("🔍 Этап 3: Поиск блоков...")
        
        retriever = get_retriever()
        retrieved_blocks = retriever.retrieve(query, top_k=top_k)
        
        if not retrieved_blocks:
            response = _build_partial_response(
                "К сожалению, релевантный материал не найден. Попробуйте переформулировать вопрос.",
                state_analysis,
                memory,
                start_time
            )
            memory.add_turn(
                user_input=query,
                bot_response=response.get("answer", ""),
                user_state=state_analysis.primary_state.value if state_analysis else None,
                blocks_used=0,
                concepts=[]
            )
            return response
        
        blocks = [block for block, score in retrieved_blocks]
        adapted_blocks = level_adapter.filter_blocks_by_level(blocks)
        
        if not adapted_blocks:
            adapted_blocks = blocks[:3]  # fallback
        
        if debug_info is not None:
            debug_info["blocks_found"] = len(retrieved_blocks)
            debug_info["blocks_after_filter"] = len(adapted_blocks)
        
        # ================================================================
        # ЭТАП 4: Генерация ответа с контекстом состояния
        # ================================================================
        logger.debug("🤖 Этап 4: Генерация ответа...")
        
        answerer = LLMAnswerer()
        base_prompt = answerer.build_system_prompt()
        adapted_prompt = level_adapter.adapt_system_prompt(base_prompt)
        
        # Добавить контекст состояния
        state_context = f"""
КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:
- Текущее состояние: {state_analysis.primary_state.value}
- Эмоциональный тон: {state_analysis.emotional_tone}
- Глубина вовлечения: {state_analysis.depth}

РЕКОМЕНДАЦИЯ ПО ОТВЕТУ:
{state_analysis.recommendations[0] if state_analysis.recommendations else "Отвечай в своём обычном стиле"}

Адаптируй свой ответ к состоянию пользователя.
"""
        
        # Генерация ответа (с учётом истории диалога)
        final_system_prompt = f"{adapted_prompt}\n\n{state_context.strip()}"
        original_build_prompt = answerer.build_system_prompt
        answerer.build_system_prompt = lambda: final_system_prompt

        llm_result = answerer.generate_answer(
            query,
            adapted_blocks,
            conversation_history=conversation_context
        )
        answerer.build_system_prompt = original_build_prompt
        
        if llm_result.get("error") and llm_result["error"] not in ["no_blocks"]:
            logger.error(f"❌ Ошибка LLM: {llm_result['error']}")
            response = _build_error_response(
                f"Ошибка при генерации ответа: {llm_result['error']}",
                state_analysis,
                start_time
            )
            try:
                memory.add_turn(
                    user_input=query,
                    bot_response=response.get("answer", ""),
                    user_state=state_analysis.primary_state.value if state_analysis else None,
                    blocks_used=0,
                    concepts=[]
                )
            except Exception:
                pass
            return response
        
        answer = llm_result["answer"]
        
        # ================================================================
        # ЭТАП 5: Семантический анализ и извлечение концептов
        # ================================================================
        logger.debug("🔬 Этап 5: Семантический анализ...")
        
        semantic_analyzer = SemanticAnalyzer()
        semantic_data = semantic_analyzer.analyze_relations(adapted_blocks)
        concepts = semantic_data.get("primary_concepts", [])
        
        # ================================================================
        # ЭТАП 6: Рекомендация пути (опционально)
        # ================================================================
        logger.debug("🛤️ Этап 6: Рекомендация пути...")
        
        path_recommendation = None
        if include_path_recommendation and state_analysis.primary_state != UserState.INTEGRATED:
            try:
                personal_path = path_builder.build_path(
                    user_id=user_id,
                    state_analysis=state_analysis,
                    user_level=level_enum,
                    memory=memory
                )
                
                path_recommendation = {
                    "current_state": personal_path.current_state.value,
                    "target_state": personal_path.target_state.value,
                    "key_focus": personal_path.key_focus,
                    "steps_count": len(personal_path.path_steps),
                    "total_duration_weeks": personal_path.total_duration_weeks,
                    "adaptation_notes": personal_path.adaptation_notes,
                    "first_step": {
                        "title": personal_path.path_steps[0].title if personal_path.path_steps else "",
                        "duration_weeks": personal_path.path_steps[0].duration_weeks if personal_path.path_steps else 0,
                        "practices": personal_path.path_steps[0].practices[:3] if personal_path.path_steps else []
                    } if personal_path.path_steps else None
                }
            except Exception as e:
                logger.warning(f"⚠️ Ошибка построения пути: {e}")
                path_recommendation = None
        
        # ================================================================
        # ЭТАП 7: Подготовка запроса обратной связи
        # ================================================================
        logger.debug("📝 Этап 7: Подготовка обратной связи...")
        
        feedback_prompt = ""
        if include_feedback_prompt:
            feedback_prompt = _get_feedback_prompt_for_state(state_analysis.primary_state)
        
        # ================================================================
        # ЭТАП 8: Сохранение в память
        # ================================================================
        logger.debug("💾 Этап 8: Сохранение в память...")
        
        memory.add_turn(
            user_input=query,
            bot_response=answer,
            user_state=state_analysis.primary_state.value,
            blocks_used=len(adapted_blocks),
            concepts=concepts
        )
        
        # ================================================================
        # ФИНАЛЬНЫЙ РЕЗУЛЬТАТ
        # ================================================================
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        sources = [
            {
                "block_id": b.block_id,
                "title": b.title,
                "document_title": b.document_title,
                "youtube_link": b.youtube_link,
                "start": b.start,
                "end": b.end,
                "block_type": getattr(b, 'block_type', 'unknown'),
                "complexity_score": getattr(b, 'complexity_score', 0)
            }
            for b in adapted_blocks
        ]
        
        result = {
            "status": "success",
            "answer": answer,
            "state_analysis": {
                "primary_state": state_analysis.primary_state.value,
                "confidence": state_analysis.confidence,
                "secondary_states": [s.value for s in state_analysis.secondary_states],
                "emotional_tone": state_analysis.emotional_tone,
                "depth": state_analysis.depth,
                "recommendations": state_analysis.recommendations
            },
            "path_recommendation": path_recommendation,
            "conversation_context": memory.get_context_for_llm(
                n=config.CONVERSATION_HISTORY_DEPTH,
                max_chars=config.MAX_CONTEXT_SIZE
            ),
            "feedback_prompt": feedback_prompt,
            "sources": sources,
            "concepts": concepts,
            "metadata": {
                "user_id": user_id,
                "user_level": user_level,
                "blocks_used": len(adapted_blocks),
                "state": state_analysis.primary_state.value,
                "conversation_turns": len(memory.turns)
            },
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(elapsed_time, 2)
        }
        
        if debug_info is not None:
            debug_info["memory_summary"] = memory.get_summary()
            debug_info["total_time"] = elapsed_time
            debug_info["llm_tokens"] = llm_result.get("tokens_used", 0)
            result["debug"] = debug_info
        
        logger.info(f"✅ Адаптивный ответ готов за {elapsed_time:.2f}с")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}", exc_info=True)
        response = {
            "status": "error",
            "answer": f"Произошла ошибка при обработке запроса: {str(e)}",
            "state_analysis": None,
            "path_recommendation": None,
            "conversation_context": "",
            "feedback_prompt": "",
            "sources": [],
            "concepts": [],
            "metadata": {"user_id": user_id, "user_level": user_level},
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": (datetime.now() - start_time).total_seconds()
        }
        try:
            memory = get_conversation_memory(user_id)
            memory.add_turn(user_input=query, bot_response=response["answer"], blocks_used=0)
        except Exception:
            pass
        return response


def _get_feedback_prompt_for_state(state: UserState) -> str:
    """
    Получить запрос обратной связи в зависимости от состояния.
    """
    prompts = {
        UserState.UNAWARE: "Стало ли понятнее, о чём речь? Что осталось непонятным?",
        UserState.CURIOUS: "Хотите узнать что-то ещё по этой теме?",
        UserState.OVERWHELMED: "Не слишком ли много информации? Нужно ли упростить?",
        UserState.RESISTANT: "Есть ли что-то, с чем вы не согласны? Давайте обсудим.",
        UserState.CONFUSED: "Прояснилось ли объяснение? Если нет, какая часть всё ещё непонятна?",
        UserState.COMMITTED: "Готовы ли вы начать практику? Какая поддержка нужна?",
        UserState.PRACTICING: "Как идёт практика? Есть ли сложности?",
        UserState.STAGNANT: "Что, по-вашему, мешает продвижению? Попробуем найти новый подход?",
        UserState.BREAKTHROUGH: "Поздравляю с инсайтом! Как планируете применить это понимание?",
        UserState.INTEGRATED: "Как это знание проявляется в вашей жизни?"
    }
    
    return prompts.get(state, "Был ли этот ответ полезен? Оцените от 1 до 5.")


def _build_partial_response(
    message: str,
    state_analysis: StateAnalysis,
    memory,
    start_time: datetime
) -> Dict:
    """Построить частичный ответ (нет блоков)"""
    return {
        "status": "partial",
        "answer": message,
        "state_analysis": {
            "primary_state": state_analysis.primary_state.value,
            "confidence": state_analysis.confidence,
            "emotional_tone": state_analysis.emotional_tone,
            "recommendations": state_analysis.recommendations
        } if state_analysis else None,
        "path_recommendation": None,
        "conversation_context": memory.get_context_for_llm(
            n=config.CONVERSATION_HISTORY_DEPTH,
            max_chars=config.MAX_CONTEXT_SIZE
        ) if memory else "",
        "feedback_prompt": "Попробуйте переформулировать вопрос.",
        "sources": [],
        "concepts": [],
        "metadata": {"conversation_turns": len(memory.turns) if memory else 0},
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": (datetime.now() - start_time).total_seconds()
    }


def _build_error_response(
    message: str,
    state_analysis: StateAnalysis,
    start_time: datetime
) -> Dict:
    """Построить ответ с ошибкой"""
    return {
        "status": "error",
        "answer": message,
        "state_analysis": {
            "primary_state": state_analysis.primary_state.value if state_analysis else "unknown",
            "confidence": state_analysis.confidence if state_analysis else 0
        } if state_analysis else None,
        "path_recommendation": None,
        "conversation_context": "",
        "feedback_prompt": "",
        "sources": [],
        "concepts": [],
        "metadata": {},
        "timestamp": datetime.now().isoformat(),
        "processing_time_seconds": (datetime.now() - start_time).total_seconds()
    }


