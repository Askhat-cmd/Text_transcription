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

import asyncio
import concurrent.futures
import logging
import json
import re
from typing import Dict, Optional, List, Tuple
from datetime import datetime

from .data_loader import Block, data_loader
from .retriever import get_retriever
from .user_level_adapter import UserLevelAdapter, UserLevel
from .semantic_analyzer import SemanticAnalyzer
from .graph_client import graph_client
from .state_classifier import state_classifier, StateAnalysis, UserState
from .conversation_memory import get_conversation_memory
from .working_state import WorkingState
from .path_builder import path_builder
from .config import config
from .decision import (
    DecisionGate,
    build_mode_directive,
    detect_routing_signals,
    resolve_user_stage,
)
from .retrieval import HybridQueryBuilder, VoyageReranker, filter_by_sd_level
from .response import ResponseFormatter, ResponseGenerator
from .sd_classifier import SDClassificationResult, get_sd_settings, sd_classifier

logger = logging.getLogger(__name__)


def _run_coroutine_sync(coro):
    """
    Run coroutine from sync context.
    If an event loop is already running, run it in a separate thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()


def _fallback_state_analysis() -> StateAnalysis:
    fallback_state = UserState.CURIOUS
    return StateAnalysis(
        primary_state=fallback_state,
        confidence=0.3,
        secondary_states=[],
        indicators=[],
        emotional_tone="neutral",
        depth="intermediate",
        recommendations=state_classifier._get_recommendations_for_state(fallback_state),
    )


def _fallback_sd_result(reason: str = "fallback_on_error") -> SDClassificationResult:
    return SDClassificationResult(
        primary="GREEN",
        secondary=None,
        confidence=0.5,
        indicator=reason,
        method="fallback",
    )


async def _classify_parallel(
    user_message: str,
    history_state: List[Dict],
    history_sd: List[Dict],
    user_sd_profile: Optional[dict],
) -> Tuple[StateAnalysis, SDClassificationResult]:
    if sd_classifier is None:
        state_result = await state_classifier.classify(
            user_message,
            conversation_history=history_state,
        )
        return state_result, _fallback_sd_result("sd_classifier_unavailable")

    results = await asyncio.gather(
        state_classifier.classify(user_message, conversation_history=history_state),
        sd_classifier.classify_user(
            message=user_message,
            conversation_history=history_sd,
            user_sd_profile=user_sd_profile,
        ),
        return_exceptions=True,
    )

    state_result = results[0]
    sd_result = results[1]

    if isinstance(state_result, Exception):
        logger.warning(
            "[CLASSIFY_PARALLEL] StateClassifier failed: %s. Using fallback.",
            state_result,
        )
        state_result = _fallback_state_analysis()

    if isinstance(sd_result, Exception):
        logger.warning(
            "[CLASSIFY_PARALLEL] SDClassifier failed: %s. Using GREEN fallback.",
            sd_result,
        )
        sd_result = _fallback_sd_result("fallback_on_error")

    return state_result, sd_result


def _log_retrieval_pairs(stage: str, pairs, limit: int = 5) -> None:
    logger.info(f"[RETRIEVAL] {stage}: {len(pairs)} blocks")
    for i, (block, score) in enumerate(pairs[:limit], start=1):
        title = (block.title or "")[:60]
        logger.info(
            f"[RETRIEVAL]   [{i}] block_id={block.block_id} score={float(score):.4f} title={title}"
        )


def _log_blocks(stage: str, blocks, limit: int = 5) -> None:
    logger.info(f"[RETRIEVAL] {stage}: {len(blocks)} blocks")
    for i, block in enumerate(blocks[:limit], start=1):
        title = (block.title or "")[:60]
        logger.info(f"[RETRIEVAL]   [{i}] block_id={block.block_id} title={title}")


def _truncate_preview(text: Optional[str], max_len: int = 300) -> str:
    value = str(text or "")
    return value[:max_len]


def _extract_block_sd(block, default_sd_level: str = "UNKNOWN") -> Tuple[str, str, str]:
    metadata = getattr(block, "metadata", {}) or {}
    sd_level = getattr(block, "sd_level", None) or metadata.get("sd_level")
    sd_secondary = getattr(block, "sd_secondary", None) or metadata.get("sd_secondary")
    emotional_tone = getattr(block, "emotional_tone", None) or metadata.get("emotional_tone")
    return (
        str(sd_level or default_sd_level).upper(),
        str(sd_secondary or ""),
        str(emotional_tone or ""),
    )


def _build_chunk_trace_item(
    *,
    block,
    score_initial: float,
    score_final: float,
    passed_sd_filter: bool,
    filter_reason: str,
    default_sd_level: str = "UNKNOWN",
) -> Dict:
    sd_level, sd_secondary, emotional_tone = _extract_block_sd(block, default_sd_level=default_sd_level)
    preview_source = getattr(block, "content", None) or getattr(block, "summary", None) or ""
    return {
        "block_id": str(getattr(block, "block_id", "")),
        "title": str(getattr(block, "title", "")),
        "sd_level": sd_level,
        "sd_secondary": sd_secondary,
        "emotional_tone": emotional_tone,
        "score_initial": float(score_initial),
        "score_final": float(score_final),
        "passed_sd_filter": bool(passed_sd_filter),
        "filter_reason": str(filter_reason or ""),
        "preview": _truncate_preview(preview_source, 120),
    }


def _build_chunk_trace_lists(
    *,
    initial_retrieved: List[Tuple],
    sd_filtered: List[Tuple],
    reranked: List[Tuple],
    allowed_levels: List[str],
) -> Tuple[List[Dict], List[Dict]]:
    allowed_norm = [str(level).upper() for level in (allowed_levels or [])]
    passed_ids = {str(getattr(block, "block_id", "")) for block, _ in sd_filtered}
    reranked_scores = {
        str(getattr(block, "block_id", "")): float(score)
        for block, score in reranked
    }

    chunks_retrieved: List[Dict] = []
    chunks_after_filter: List[Dict] = []

    for block, initial_score in initial_retrieved:
        block_id = str(getattr(block, "block_id", ""))
        raw_metadata = getattr(block, "metadata", {}) or {}
        raw_sd = getattr(block, "sd_level", None) or raw_metadata.get("sd_level")
        passed = block_id in passed_ids

        filter_reason = ""
        if not passed:
            if not raw_sd:
                filter_reason = "sd_level_missing"
            elif allowed_norm and str(raw_sd).upper() not in allowed_norm:
                filter_reason = f"sd_level_{str(raw_sd).upper()}_not_allowed"
            else:
                filter_reason = "filtered_by_sd"

        item = _build_chunk_trace_item(
            block=block,
            score_initial=float(initial_score),
            score_final=reranked_scores.get(block_id, float(initial_score)),
            passed_sd_filter=passed,
            filter_reason=filter_reason,
        )
        chunks_retrieved.append(item)
        if passed:
            chunks_after_filter.append(item)

    return chunks_retrieved, chunks_after_filter


def _get_memory_trace_metrics(memory, context_turns: int) -> Dict[str, object]:
    summary_used = bool(
        config.ENABLE_CONVERSATION_SUMMARY
        and memory.summary
        and context_turns > 20
    )
    if config.ENABLE_SEMANTIC_MEMORY and memory.semantic_memory and context_turns > 5:
        semantic_hits = int(getattr(memory.semantic_memory, "last_hits_count", 0) or 0)
    else:
        semantic_hits = 0
    return {
        "summary_used": summary_used,
        "semantic_hits": semantic_hits,
    }


def _build_retrieval_detail(block, score: float, stage: str) -> Dict:
    source = str(getattr(block, "document_title", "") or getattr(block, "title", "") or getattr(block, "block_id", ""))
    start = str(getattr(block, "start", "") or "")
    end = str(getattr(block, "end", "") or "")
    if start and end:
        source = f"{source} [{start}-{end}]"
    return {
        "block_id": str(getattr(block, "block_id", "")),
        "score": float(score),
        "title": str(getattr(block, "title", "")),
        "text": str(getattr(block, "content", "")),
        "source": source,
        "stage": stage,
    }


def _build_llm_prompt_previews(
    *,
    response_generator: ResponseGenerator,
    query: str,
    blocks: List[Block],
    conversation_context: str,
    user_level_adapter,
    sd_level: str,
    mode_prompt: str,
    additional_system_context: str,
) -> Tuple[str, str]:
    try:
        answerer = response_generator.answerer
        system_prompt = answerer.build_system_prompt()

        if user_level_adapter is not None:
            try:
                system_prompt = user_level_adapter.adapt_system_prompt(system_prompt)
            except Exception:
                pass

        sd_overlay = response_generator._load_sd_prompt(sd_level)
        if sd_overlay:
            system_prompt = f"{system_prompt}\n\n{sd_overlay}"

        system_chunks = [system_prompt, f"MODE DIRECTIVE:\n{mode_prompt}"]
        if additional_system_context:
            system_chunks.append(additional_system_context.strip())

        final_system_prompt = "\n\n".join(chunk for chunk in system_chunks if chunk).strip()
        user_prompt = answerer.build_context_prompt(
            blocks,
            query,
            conversation_history=conversation_context,
        )
        return _truncate_preview(final_system_prompt, 300), _truncate_preview(user_prompt, 300)
    except Exception as exc:
        logger.debug(f"[DEBUG_TRACE] Failed to build prompt previews: {exc}")
        return "", ""


def _build_llm_call_trace(
    *,
    llm_result: Dict,
    step: str,
    system_prompt_preview: str,
    user_prompt_preview: str,
    fallback_error: Optional[str],
    duration_ms: int,
) -> Dict:
    call_info = {}
    if isinstance(llm_result, dict):
        raw_info = llm_result.get("llm_call_info")
        if isinstance(raw_info, dict):
            call_info.update(raw_info)

    model_used = (
        call_info.get("model")
        or (llm_result.get("model_used") if isinstance(llm_result, dict) else None)
        or config.LLM_MODEL
    )
    response_preview = (
        call_info.get("response_preview")
        or _truncate_preview(
            (llm_result.get("answer") if isinstance(llm_result, dict) else fallback_error) or "",
            300,
        )
    )
    return {
        "step": call_info.get("step") or step,
        "model": str(model_used),
        "system_prompt_preview": call_info.get("system_prompt_preview") or system_prompt_preview,
        "user_prompt_preview": call_info.get("user_prompt_preview") or user_prompt_preview,
        "response_preview": response_preview,
        "tokens_prompt": call_info.get("tokens_prompt"),
        "tokens_completion": call_info.get("tokens_completion"),
        "tokens_total": call_info.get("tokens_total"),
        "tokens_used": llm_result.get("tokens_used") if isinstance(llm_result, dict) else None,
        "duration_ms": call_info.get("duration_ms") or duration_ms,
    }


def _update_session_token_metrics(
    *,
    memory,
    tokens_prompt: Optional[int],
    tokens_completion: Optional[int],
    tokens_total: Optional[int],
    model_name: str,
) -> Dict[str, Optional[float]]:
    previous_total = int(memory.metadata.get("session_tokens_total") or 0)
    previous_turns = int(memory.metadata.get("session_turns") or 0)
    previous_cost = memory.metadata.get("session_cost_usd")
    previous_cost = float(previous_cost) if isinstance(previous_cost, (int, float, str)) else 0.0

    new_total = previous_total + (int(tokens_total) if isinstance(tokens_total, (int, float)) else 0)
    new_turns = previous_turns + 1

    cost_per_1m = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
        "gpt-5-mini": {"input": 0.25, "output": 2.00},
        "gpt-5-mini-2025-08-07": {"input": 0.25, "output": 2.00},
        "gpt-5": {"input": 1.25, "output": 10.00},
        "gpt-5-2025-08-07": {"input": 1.25, "output": 10.00},
    }

    model_key = (model_name or "").lower()
    session_cost = None
    if model_key in cost_per_1m and tokens_prompt is not None and tokens_completion is not None:
        rates = cost_per_1m[model_key]
        cost = (
            (tokens_prompt / 1_000_000 * rates["input"])
            + (tokens_completion / 1_000_000 * rates["output"])
        )
        session_cost = round(previous_cost + cost, 6)

    memory.metadata["session_tokens_total"] = new_total
    memory.metadata["session_turns"] = new_turns
    if session_cost is not None:
        memory.metadata["session_cost_usd"] = session_cost

    return {
        "session_tokens_total": new_total,
        "session_turns": new_turns,
        "session_cost_usd": session_cost,
    }


def _build_memory_context_snapshot(memory) -> str:
    try:
        if not memory.turns:
            return ""
        turn = memory.turns[-1]
        payload = {
            "timestamp": turn.timestamp,
            "user_input": turn.user_input,
            "bot_response": turn.bot_response,
            "user_state": turn.user_state,
            "blocks_used": turn.blocks_used,
            "concepts": turn.concepts,
        }
        return _truncate_preview(json.dumps(payload, ensure_ascii=False), 1200)
    except Exception:
        return ""


def _build_state_context(
    state_analysis: StateAnalysis,
    mode_prompt: str,
    sd_level: str = "GREEN",
) -> str:
    recommendation = (
        state_analysis.recommendations[0]
        if state_analysis and state_analysis.recommendations
        else "Respond in a clear and grounded way."
    )
    return f"""
КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:
- Текущее состояние: {state_analysis.primary_state.value}
- Эмоциональный тон: {state_analysis.emotional_tone}
- Глубина вовлечения: {state_analysis.depth}
- Уровень развития (СД): {sd_level}

РЕКОМЕНДАЦИЯ ПО ОТВЕТУ:
{recommendation}

Адаптируй стиль ответа к уровню СД пользователя.
SD-оверлей применяется автоматически через системный промт.

РЕЖИМНАЯ ДИРЕКТИВА:
{mode_prompt}
"""


def _depth_to_phase(depth: str) -> str:
    normalized = (depth or "").lower()
    if "deep" in normalized:
        return "работа"
    if "intermediate" in normalized or "medium" in normalized:
        return "осмысление"
    return "начало контакта"


def _mode_to_direction(mode: str) -> str:
    mapping = {
        "CLARIFICATION": "уточнение",
        "VALIDATION": "поддержка",
        "THINKING": "рефлексия",
        "INTERVENTION": "действие",
        "INTEGRATION": "интеграция",
        "PRESENCE": "диагностика",
    }
    return mapping.get((mode or "PRESENCE").upper(), "диагностика")


def _derive_defense(state_value: str) -> Optional[str]:
    state = (state_value or "").lower()
    if state == "resistant":
        return "сопротивление"
    if state == "overwhelmed":
        return "перегрузка"
    if state == "confused":
        return "неясность"
    return None


def _build_working_state(
    *,
    state_analysis: StateAnalysis,
    routing_result,
    memory,
) -> WorkingState:
    return WorkingState(
        dominant_state=state_analysis.primary_state.value,
        emotion=state_analysis.emotional_tone or "neutral",
        defense=_derive_defense(state_analysis.primary_state.value),
        phase=_depth_to_phase(state_analysis.depth),
        direction=_mode_to_direction(routing_result.mode),
        last_updated_turn=len(memory.turns) + 1,
        confidence_level=routing_result.confidence_level,
    )


def _looks_like_greeting(query: str) -> bool:
    q = (query or "").strip().lower()
    greetings = {
        "привет",
        "здравствуй",
        "здравствуйте",
        "добрый день",
        "добрый вечер",
        "доброе утро",
        "hi",
        "hello",
    }
    return q in greetings


def _looks_like_name_intro(query: str) -> bool:
    q = (query or "").strip().lower()
    return bool(re.search(r"\b(меня зовут|my name is)\b", q))


def _should_use_fast_path(query: str, routing_result) -> bool:
    if _looks_like_greeting(query) or _looks_like_name_intro(query):
        return True
    tokens = [token for token in re.split(r"\s+", query.strip()) if token]
    if len(tokens) <= 3 and routing_result.mode in {"PRESENCE", "CLARIFICATION"}:
        return True
    return False


def _build_fast_path_block(
    *,
    query: str,
    conversation_context: str,
    state_analysis: StateAnalysis,
) -> Block:
    return Block(
        block_id="fast-path-runtime-context",
        video_id="runtime",
        start="00:00:00",
        end="00:00:00",
        title="Runtime conversational context",
        summary="Use dialogue context and user message only. No lecture citation required.",
        content=(
            "FAST PATH CONTEXT\n"
            "This user turn should be handled without lecture retrieval.\n\n"
            f"USER MESSAGE:\n{query}\n\n"
            f"DIALOGUE CONTEXT:\n{conversation_context[:1500]}\n\n"
            f"USER STATE:\n{state_analysis.primary_state.value}, "
            f"{state_analysis.emotional_tone}, depth={state_analysis.depth}\n"
        ),
        keywords=["fast-path", "context"],
        youtube_link="",
        document_title="Runtime",
        block_type="dialogue",
        emotional_tone=state_analysis.emotional_tone or "neutral",
        conceptual_depth="low",
        complexity_score=0.1,
        graph_entities=[],
    )


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
    
    logger.info(f"[ADAPTIVE] new request user_id={user_id} query='{query[:50]}...'")
    
    top_k = top_k or config.TOP_K_BLOCKS
    start_time = datetime.now()
    debug_info = {} if debug else None
    debug_trace = (
        {
            "sd_classification": {
                "method": "fallback",
                "primary": "GREEN",
                "secondary": None,
                "confidence": 0.0,
                "indicator": "not_set",
                "allowed_levels": [],
            },
            "chunks_retrieved": [],
            "chunks_after_filter": [],
            "llm_calls": [],
            "context_written": "",
            "total_duration_ms": 0,
        }
        if debug
        else None
    )
    
    try:
        # ================================================================
        # ЭТАП 1: Загрузка данных и памяти
        # ================================================================
        logger.debug("📚 Этап 1: Загрузка данных и памяти...")
        
        data_loader.load_all_data()
        memory = get_conversation_memory(user_id)
        conversation_context = memory.get_adaptive_context_text(query)
        context_turns = len(memory.turns)
        memory_trace_metrics = _get_memory_trace_metrics(memory, context_turns)
        
        # Парсим уровень пользователя
        try:
            level_enum = UserLevel(user_level.lower())
        except ValueError:
            level_enum = UserLevel.BEGINNER
        
        level_adapter = UserLevelAdapter(user_level)
        
        if debug_info is not None:
            debug_info["user_id"] = user_id
            debug_info["memory_turns"] = len(memory.turns)
        sd_settings = get_sd_settings()
        sd_profile_update_every_n = max(1, int(sd_settings.get("update_profile_every_n_messages", 5)))
        
        # ================================================================
        # ЭТАП 2: Анализ состояния пользователя
        # ================================================================
        logger.debug("🎯 Этап 2: Анализ состояния...")
        
        # Получить историю для контекста анализа
        conversation_history = [
            {"role": "user", "content": turn.user_input}
            for turn in memory.get_last_turns(config.CONVERSATION_HISTORY_DEPTH)
        ]
        
        conversation_history_for_sd = [
            {"role": "user", "content": turn.user_input}
            for turn in memory.get_last_turns(10)
        ]

        state_analysis, sd_result = _run_coroutine_sync(
            _classify_parallel(
                query,
                conversation_history,
                conversation_history_for_sd,
                memory.get_user_sd_profile(),
            )
        )
        user_stage = resolve_user_stage(memory, state_analysis)

        logger.info(
            f"✅ Состояние: {state_analysis.primary_state.value} "
            f"(уверенность: {state_analysis.confidence:.2f})"
        )
        logger.info(
            f"✅ SD уровень: {sd_result.primary} "
            f"(conf={sd_result.confidence:.2f}, method={sd_result.method})"
        )

        if len(memory.turns) % sd_profile_update_every_n == 0:
            try:
                memory.update_sd_profile(
                    level=sd_result.primary,
                    confidence=sd_result.confidence,
                )
            except Exception:
                pass

        if debug_info is not None:
            debug_info["state_analysis"] = {
                "primary": state_analysis.primary_state.value,
                "confidence": state_analysis.confidence,
                "secondary": [s.value for s in state_analysis.secondary_states],
                "emotional_tone": state_analysis.emotional_tone,
                "depth": state_analysis.depth,
                "user_stage": user_stage,
            }

        if debug_info is not None:
            debug_info["sd_classification"] = {
                "primary": sd_result.primary,
                "secondary": sd_result.secondary,
                "confidence": sd_result.confidence,
                "indicator": sd_result.indicator,
                "method": sd_result.method,
                "allowed_blocks": sd_result.allowed_blocks,
                "allowed_levels": sd_result.allowed_blocks,
            }
        if debug_trace is not None:
            debug_trace["sd_classification"] = {
                "method": sd_result.method,
                "primary": sd_result.primary,
                "secondary": sd_result.secondary,
                "confidence": float(sd_result.confidence),
                "indicator": sd_result.indicator,
                "allowed_levels": [str(level) for level in (sd_result.allowed_blocks or [])],
            }

        decision_gate = DecisionGate()
        pre_routing_signals = detect_routing_signals(query, [], state_analysis)
        pre_routing_result = decision_gate.route(pre_routing_signals, user_stage=user_stage)

        if _should_use_fast_path(query, pre_routing_result):
            logger.info(
                "[FAST_PATH] enabled mode=%s reason=%s",
                pre_routing_result.mode,
                pre_routing_result.decision.reason,
            )
            mode_directive = build_mode_directive(
                mode=pre_routing_result.mode,
                confidence_level=pre_routing_result.confidence_level,
                reason=pre_routing_result.decision.reason,
                forbid=pre_routing_result.decision.forbid,
            )
            fast_block = _build_fast_path_block(
                query=query,
                conversation_context=conversation_context,
                state_analysis=state_analysis,
            )
            state_context = _build_state_context(
                state_analysis,
                mode_directive.prompt,
                sd_level=sd_result.primary,
            )
            response_generator = ResponseGenerator()
            llm_system_preview = ""
            llm_user_preview = ""
            if debug_trace is not None:
                llm_system_preview, llm_user_preview = _build_llm_prompt_previews(
                    response_generator=response_generator,
                    query=query,
                    blocks=[fast_block],
                    conversation_context=conversation_context,
                    user_level_adapter=level_adapter,
                    sd_level=sd_result.primary,
                    mode_prompt=mode_directive.prompt,
                    additional_system_context=state_context,
                )

            llm_started = datetime.now()
            llm_result = {}
            llm_error = None
            try:
                llm_result = response_generator.generate(
                    query,
                    [fast_block],
                    conversation_context=conversation_context,
                    mode=pre_routing_result.mode,
                    confidence_level=pre_routing_result.confidence_level,
                    forbid=pre_routing_result.decision.forbid,
                    user_level_adapter=level_adapter,
                    additional_system_context=state_context,
                    sd_level=sd_result.primary,
                    model=config.LLM_MODEL,
                    temperature=config.LLM_TEMPERATURE,
                    max_tokens=config.get_mode_max_tokens(pre_routing_result.mode),
                )
            except Exception as llm_exc:
                llm_error = str(llm_exc)
                raise
            finally:
                if debug_trace is not None:
                    debug_trace["llm_calls"].append(
                        _build_llm_call_trace(
                            llm_result=llm_result if isinstance(llm_result, dict) else {},
                            step="answer",
                            system_prompt_preview=llm_system_preview,
                            user_prompt_preview=llm_user_preview,
                            fallback_error=llm_error,
                            duration_ms=int((datetime.now() - llm_started).total_seconds() * 1000),
                        )
                    )
            answer = llm_result.get("answer", "")
            formatter = ResponseFormatter()
            answer = formatter.format_answer(
                answer,
                mode=pre_routing_result.mode,
                confidence_level=pre_routing_result.confidence_level,
            )

            try:
                memory.set_working_state(
                    _build_working_state(
                        state_analysis=state_analysis,
                        routing_result=pre_routing_result,
                        memory=memory,
                    )
                )
            except Exception as exc:
                logger.warning(f"[FAST_PATH] working_state update failed: {exc}")

            tokens_prompt = llm_result.get("tokens_prompt") if isinstance(llm_result, dict) else None
            tokens_completion = llm_result.get("tokens_completion") if isinstance(llm_result, dict) else None
            tokens_total = llm_result.get("tokens_total") if isinstance(llm_result, dict) else None
            model_used = llm_result.get("model_used") if isinstance(llm_result, dict) else config.LLM_MODEL
            session_metrics = _update_session_token_metrics(
                memory=memory,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                tokens_total=tokens_total,
                model_name=str(model_used),
            )

            memory.add_turn(
                user_input=query,
                bot_response=answer,
                user_state=state_analysis.primary_state.value,
                blocks_used=0,
                concepts=[],
            )

            memory_turns = len(memory.turns)
            summary_length = len(memory.summary) if memory.summary else 0
            summary_last_turn = memory.summary_updated_at
            elapsed_time = (datetime.now() - start_time).total_seconds()
            feedback_prompt = ""
            if include_feedback_prompt:
                feedback_prompt = _get_feedback_prompt_for_state(state_analysis.primary_state)

            result = {
                "status": "success",
                "answer": answer,
                "state_analysis": {
                    "primary_state": state_analysis.primary_state.value,
                    "confidence": state_analysis.confidence,
                    "secondary_states": [s.value for s in state_analysis.secondary_states],
                    "emotional_tone": state_analysis.emotional_tone,
                    "depth": state_analysis.depth,
                    "recommendations": state_analysis.recommendations,
                },
                "path_recommendation": None,
                "conversation_context": memory.get_adaptive_context_text(query),
                "feedback_prompt": feedback_prompt,
                "sources": [],
                "concepts": [],
                "metadata": {
                    "user_id": user_id,
                    "user_level": user_level,
                    "blocks_used": 0,
                    "state": state_analysis.primary_state.value,
                    "conversation_turns": len(memory.turns),
                    "recommended_mode": pre_routing_result.mode,
                    "decision_rule_id": pre_routing_result.decision.rule_id,
                    "confidence_score": pre_routing_result.confidence_score,
                    "confidence_level": pre_routing_result.confidence_level,
                    "mode_reason": mode_directive.reason,
                    "retrieval_block_cap": 0,
                    "fast_path": True,
                    "sd_level": sd_result.primary,
                    "sd_secondary": sd_result.secondary,
                    "sd_confidence": round(sd_result.confidence, 3),
                    "sd_method": sd_result.method,
                    "sd_allowed_blocks": sd_result.allowed_blocks,
                    "summary_used": memory_trace_metrics["summary_used"],
                    "summary_length": summary_length,
                    "summary_last_turn": summary_last_turn,
                    "semantic_hits": memory_trace_metrics["semantic_hits"],
                    "memory_turns": memory_turns,
                    "tokens_prompt": tokens_prompt,
                    "tokens_completion": tokens_completion,
                    "tokens_total": tokens_total,
                    "session_tokens_total": session_metrics.get("session_tokens_total"),
                    "session_cost_usd": session_metrics.get("session_cost_usd"),
                    "session_turns": session_metrics.get("session_turns"),
                },
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": round(elapsed_time, 2),
            }
            if debug_info is not None:
                debug_info["fast_path"] = True
                debug_info["routing"] = {
                    "mode": pre_routing_result.mode,
                    "rule_id": pre_routing_result.decision.rule_id,
                    "reason": pre_routing_result.decision.reason,
                    "confidence_score": pre_routing_result.confidence_score,
                    "confidence_level": pre_routing_result.confidence_level,
                    "adjusted_by_stage": pre_routing_result.adjusted_by_stage,
                }
                debug_info["memory_summary"] = memory.get_summary()
                debug_info["total_time"] = elapsed_time
                debug_info["llm_tokens"] = llm_result.get("tokens_used", 0)
                result["debug"] = debug_info
            if debug_trace is not None:
                debug_trace["context_written"] = _build_memory_context_snapshot(memory)
                debug_trace["total_duration_ms"] = int(elapsed_time * 1000)
                debug_trace["primary_model"] = config.LLM_MODEL
                debug_trace["classifier_model"] = config.CLASSIFIER_MODEL
                debug_trace["embedding_model"] = config.EMBEDDING_MODEL
                debug_trace["reranker_model"] = config.VOYAGE_MODEL if config.VOYAGE_ENABLED else None
                debug_trace["reranker_enabled"] = bool(config.VOYAGE_ENABLED)
                debug_trace["tokens_prompt"] = tokens_prompt
                debug_trace["tokens_completion"] = tokens_completion
                debug_trace["tokens_total"] = tokens_total
                debug_trace["session_tokens_total"] = session_metrics.get("session_tokens_total")
                debug_trace["session_cost_usd"] = session_metrics.get("session_cost_usd")
                debug_trace["session_turns"] = session_metrics.get("session_turns")
                result["debug_trace"] = debug_trace

            logger.info(f"[ADAPTIVE] fast-path response ready in {elapsed_time:.2f}s")
            return result
        
        # ================================================================
        # ЭТАП 3: Поиск релевантных блоков
        # ================================================================
        logger.debug("🔍 Этап 3: Поиск блоков...")

        query_builder = HybridQueryBuilder(max_chars=config.MAX_CONTEXT_SIZE + 1200)
        hybrid_query = query_builder.build_query(
            current_question=query,
            conversation_summary=memory.summary or "",
            working_state=memory.working_state,
            short_term_context=conversation_context,
        )
        logger.info(
            "[RETRIEVAL] built hybrid_query len=%s (orig_query len=%s)",
            len(hybrid_query),
            len(query),
        )

        retriever = get_retriever()
        raw_retrieved_blocks = retriever.retrieve(hybrid_query, top_k=top_k)
        _log_retrieval_pairs("Initial retrieval", raw_retrieved_blocks, limit=10)
        retrieved_blocks = filter_by_sd_level(
            blocks_with_scores=raw_retrieved_blocks,
            user_sd_level=sd_result.primary,
            user_state=state_analysis.primary_state.value,
            sd_secondary=sd_result.secondary,
            sd_confidence=sd_result.confidence,
            is_first_session=(len(memory.turns) == 0),
            min_blocks=3,
        )
        _log_retrieval_pairs("After SD filter", retrieved_blocks, limit=10)
        initial_retrieved_blocks = list(raw_retrieved_blocks)
        sd_filtered_blocks = list(retrieved_blocks)
        reranker = VoyageReranker(
            model=config.VOYAGE_MODEL,
            enabled=config.VOYAGE_ENABLED,
        )
        rerank_k = min(len(retrieved_blocks), max(1, min(top_k, config.VOYAGE_TOP_K)))
        if rerank_k > 0:
            reranked = reranker.rerank_pairs(query, retrieved_blocks, top_k=rerank_k)
            if reranked:
                retrieved_blocks = reranked
                voyage_active = bool(config.VOYAGE_ENABLED and config.VOYAGE_API_KEY)
                logger.info("[RETRIEVAL] reranked top_k=%s (voyage_active=%s)", rerank_k, voyage_active)
        reranked_blocks_for_trace = list(retrieved_blocks)

        routing_signals = detect_routing_signals(query, retrieved_blocks, state_analysis)
        routing_result = decision_gate.route(routing_signals, user_stage=user_stage)
        stage_filtered_blocks = decision_gate.stage_filter.filter_retrieval_pairs(
            user_stage,
            retrieved_blocks,
        )
        _log_retrieval_pairs("After stage filter", stage_filtered_blocks, limit=10)
        block_cap = decision_gate.scorer.suggest_block_cap(
            len(stage_filtered_blocks),
            routing_result.confidence_level,
        )
        stage_count_before_cap = len(stage_filtered_blocks)
        retrieved_blocks = stage_filtered_blocks[:block_cap]
        capped_retrieved_blocks = list(retrieved_blocks)
        logger.info(
            f"[RETRIEVAL] confidence_cap={block_cap} (before={stage_count_before_cap})"
        )
        _log_retrieval_pairs("After confidence cap", retrieved_blocks, limit=10)
        mode_directive = build_mode_directive(
            mode=routing_result.mode,
            confidence_level=routing_result.confidence_level,
            reason=routing_result.decision.reason,
            forbid=routing_result.decision.forbid,
        )

        if not retrieved_blocks:
            response = _build_partial_response(
                "К сожалению, релевантный материал не найден. Попробуйте переформулировать вопрос.",
                state_analysis,
                memory,
                start_time,
                query
            )
            try:
                memory.set_working_state(
                    _build_working_state(
                        state_analysis=state_analysis,
                        routing_result=routing_result,
                        memory=memory,
                    )
                )
            except Exception as exc:
                logger.warning(f"[ADAPTIVE] working_state update failed (partial): {exc}")
            memory.add_turn(
                user_input=query,
                bot_response=response.get("answer", ""),
                user_state=state_analysis.primary_state.value if state_analysis else None,
                blocks_used=0,
                concepts=[]
            )
            if debug_info is not None:
                debug_info["memory_summary"] = memory.get_summary()
                debug_info["total_time"] = (datetime.now() - start_time).total_seconds()
                response["debug"] = debug_info
            if debug_trace is not None:
                chunks_retrieved, chunks_after_filter = _build_chunk_trace_lists(
                    initial_retrieved=initial_retrieved_blocks,
                    sd_filtered=sd_filtered_blocks,
                    reranked=reranked_blocks_for_trace,
                    allowed_levels=sd_result.allowed_blocks,
                )
                debug_trace["chunks_retrieved"] = chunks_retrieved
                debug_trace["chunks_after_filter"] = chunks_after_filter
                debug_trace["context_written"] = _build_memory_context_snapshot(memory)
                debug_trace["total_duration_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)
                response["debug_trace"] = debug_trace
            return response
        
        blocks = [block for block, score in retrieved_blocks]
        _log_blocks("Final blocks to LLM", blocks, limit=10)
        adapted_blocks = level_adapter.filter_blocks_by_level(blocks)
        
        if not adapted_blocks:
            adapted_blocks = blocks[:3]  # fallback
        
        if debug_info is not None:
            debug_info["blocks_found"] = len(retrieved_blocks)
            debug_info["blocks_after_filter"] = len(adapted_blocks)
            debug_info["hybrid_query"] = hybrid_query
            stage_filtered_ids = {str(block.block_id) for block, _ in stage_filtered_blocks}
            capped_ids = {str(block.block_id) for block, _ in capped_retrieved_blocks}
            stage_filtered_out = [
                (block, score)
                for block, score in initial_retrieved_blocks
                if str(block.block_id) not in stage_filtered_ids
            ]
            confidence_capped_out = [
                (block, score)
                for block, score in stage_filtered_blocks
                if str(block.block_id) not in capped_ids
            ]
            final_score_map = {str(block.block_id): float(score) for block, score in capped_retrieved_blocks}
            debug_info["retrieval_details"] = {
                "initial_retrieval": [
                    _build_retrieval_detail(block, score, "initial")
                    for block, score in initial_retrieved_blocks
                ],
                "after_stage_filter": [
                    _build_retrieval_detail(block, score, "stage_filter")
                    for block, score in stage_filtered_blocks
                ],
                "after_sd_filter": [
                    _build_retrieval_detail(block, score, "sd_filter")
                    for block, score in sd_filtered_blocks
                ],
                "after_confidence_cap": [
                    _build_retrieval_detail(block, score, "confidence_cap")
                    for block, score in capped_retrieved_blocks
                ],
                "stage_filtered": [
                    _build_retrieval_detail(block, score, "stage_filter")
                    for block, score in stage_filtered_out
                ],
                "confidence_capped": [
                    _build_retrieval_detail(block, score, "confidence_cap")
                    for block, score in confidence_capped_out
                ],
                "final_blocks": [
                    _build_retrieval_detail(
                        block,
                        final_score_map.get(str(block.block_id), 0.0),
                        "final",
                    )
                    for block in adapted_blocks
                ],
            }
            debug_info["voyage_rerank"] = {
                "enabled": bool(config.VOYAGE_ENABLED),
                "top_k": rerank_k,
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
        if debug_trace is not None:
            chunks_retrieved, chunks_after_filter = _build_chunk_trace_lists(
                initial_retrieved=initial_retrieved_blocks,
                sd_filtered=sd_filtered_blocks,
                reranked=reranked_blocks_for_trace,
                allowed_levels=sd_result.allowed_blocks,
            )
            debug_trace["chunks_retrieved"] = chunks_retrieved
            debug_trace["chunks_after_filter"] = chunks_after_filter
        
        # ================================================================
        # ЭТАП 4: Генерация ответа с контекстом состояния
        # ================================================================
        logger.debug("🤖 Этап 4: Генерация ответа...")
        
        # Добавить контекст состояния
        state_context = _build_state_context(
            state_analysis,
            mode_directive.prompt,
            sd_level=sd_result.primary,
        )

        # Генерация ответа (с учётом истории диалога)
        response_generator = ResponseGenerator()
        llm_system_preview = ""
        llm_user_preview = ""
        if debug_trace is not None:
            llm_system_preview, llm_user_preview = _build_llm_prompt_previews(
                response_generator=response_generator,
                query=query,
                blocks=adapted_blocks,
                conversation_context=conversation_context,
                user_level_adapter=level_adapter,
                sd_level=sd_result.primary,
                mode_prompt=mode_directive.prompt,
                additional_system_context=state_context,
            )

        llm_started = datetime.now()
        llm_result = {}
        llm_error = None
        try:
            llm_result = response_generator.generate(
                query,
                adapted_blocks,
                conversation_context=conversation_context,
                mode=routing_result.mode,
                confidence_level=routing_result.confidence_level,
                forbid=routing_result.decision.forbid,
                user_level_adapter=level_adapter,
                additional_system_context=state_context,
                sd_level=sd_result.primary,
                model=config.LLM_MODEL,
                temperature=config.LLM_TEMPERATURE,
                max_tokens=config.get_mode_max_tokens(routing_result.mode),
            )
        except Exception as llm_exc:
            llm_error = str(llm_exc)
            raise
        finally:
            if debug_trace is not None:
                debug_trace["llm_calls"].append(
                    _build_llm_call_trace(
                        llm_result=llm_result if isinstance(llm_result, dict) else {},
                        step="answer",
                        system_prompt_preview=llm_system_preview,
                        user_prompt_preview=llm_user_preview,
                        fallback_error=llm_error,
                        duration_ms=int((datetime.now() - llm_started).total_seconds() * 1000),
                    )
                )
        
        if llm_result.get("error") and llm_result["error"] not in ["no_blocks"]:
            logger.error(f"[ADAPTIVE] LLM error: {llm_result['error']}")
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
            if debug_info is not None:
                debug_info["memory_summary"] = memory.get_summary()
                debug_info["total_time"] = (datetime.now() - start_time).total_seconds()
                response["debug"] = debug_info
            if debug_trace is not None:
                chunks_retrieved, chunks_after_filter = _build_chunk_trace_lists(
                    initial_retrieved=initial_retrieved_blocks,
                    sd_filtered=sd_filtered_blocks,
                    reranked=reranked_blocks_for_trace,
                    allowed_levels=sd_result.allowed_blocks,
                )
                debug_trace["chunks_retrieved"] = chunks_retrieved
                debug_trace["chunks_after_filter"] = chunks_after_filter
                debug_trace["context_written"] = _build_memory_context_snapshot(memory)
                debug_trace["total_duration_ms"] = int((datetime.now() - start_time).total_seconds() * 1000)
                response["debug_trace"] = debug_trace
            return response
        
        answer = llm_result["answer"]
        formatter = ResponseFormatter()
        answer = formatter.format_answer(
            answer,
            mode=routing_result.mode,
            confidence_level=routing_result.confidence_level,
        )
        
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
        
        try:
            memory.set_working_state(
                _build_working_state(
                    state_analysis=state_analysis,
                    routing_result=routing_result,
                    memory=memory,
                )
            )
        except Exception as exc:
            logger.warning(f"[ADAPTIVE] working_state update failed: {exc}")

        tokens_prompt = llm_result.get("tokens_prompt") if isinstance(llm_result, dict) else None
        tokens_completion = llm_result.get("tokens_completion") if isinstance(llm_result, dict) else None
        tokens_total = llm_result.get("tokens_total") if isinstance(llm_result, dict) else None
        model_used = llm_result.get("model_used") if isinstance(llm_result, dict) else config.LLM_MODEL
        session_metrics = _update_session_token_metrics(
            memory=memory,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_total,
            model_name=str(model_used),
        )

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
        _log_blocks("SOURCES", adapted_blocks, limit=10)
        
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
            "conversation_context": memory.get_adaptive_context_text(query),
            "feedback_prompt": feedback_prompt,
            "sources": sources,
            "concepts": concepts,
            "metadata": {
                "user_id": user_id,
                "user_level": user_level,
                "blocks_used": len(adapted_blocks),
                "state": state_analysis.primary_state.value,
                "conversation_turns": len(memory.turns),
                "recommended_mode": routing_result.mode,
                "decision_rule_id": routing_result.decision.rule_id,
                "confidence_score": routing_result.confidence_score,
                "confidence_level": routing_result.confidence_level,
                "mode_reason": mode_directive.reason,
                "retrieval_block_cap": block_cap,
                "sd_level": sd_result.primary,
                "sd_secondary": sd_result.secondary,
                "sd_confidence": round(sd_result.confidence, 3),
                "sd_method": sd_result.method,
                "sd_allowed_blocks": sd_result.allowed_blocks,
                "summary_used": memory_trace_metrics["summary_used"],
                "summary_length": len(memory.summary) if memory.summary else 0,
                "summary_last_turn": memory.summary_updated_at,
                "semantic_hits": memory_trace_metrics["semantic_hits"],
                "memory_turns": len(memory.turns),
                "tokens_prompt": tokens_prompt,
                "tokens_completion": tokens_completion,
                "tokens_total": tokens_total,
                "session_tokens_total": session_metrics.get("session_tokens_total"),
                "session_cost_usd": session_metrics.get("session_cost_usd"),
                "session_turns": session_metrics.get("session_turns"),
            },
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(elapsed_time, 2)
        }
        
        if debug_info is not None:
            debug_info["memory_summary"] = memory.get_summary()
            debug_info["total_time"] = elapsed_time
            debug_info["llm_tokens"] = llm_result.get("tokens_used", 0)
            result["metadata"]["retrieval_details"] = debug_info.get("retrieval_details", {})
            result["metadata"]["sources"] = sources
            result["debug"] = debug_info
        if debug_trace is not None:
            debug_trace["context_written"] = _build_memory_context_snapshot(memory)
            debug_trace["total_duration_ms"] = int(elapsed_time * 1000)
            debug_trace["primary_model"] = config.LLM_MODEL
            debug_trace["classifier_model"] = config.CLASSIFIER_MODEL
            debug_trace["embedding_model"] = config.EMBEDDING_MODEL
            debug_trace["reranker_model"] = config.VOYAGE_MODEL if config.VOYAGE_ENABLED else None
            debug_trace["reranker_enabled"] = bool(config.VOYAGE_ENABLED)
            debug_trace["tokens_prompt"] = tokens_prompt
            debug_trace["tokens_completion"] = tokens_completion
            debug_trace["tokens_total"] = tokens_total
            debug_trace["session_tokens_total"] = session_metrics.get("session_tokens_total")
            debug_trace["session_cost_usd"] = session_metrics.get("session_cost_usd")
            debug_trace["session_turns"] = session_metrics.get("session_turns")
            result["debug_trace"] = debug_trace
        
        logger.info(f"[ADAPTIVE] response ready in {elapsed_time:.2f}s")
        
        return result
    
    except Exception as e:
        logger.error(f"[ADAPTIVE] unhandled error: {e}", exc_info=True)
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
    start_time: datetime,
    query: str
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
        "conversation_context": memory.get_adaptive_context_text(query) if memory else "",
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





