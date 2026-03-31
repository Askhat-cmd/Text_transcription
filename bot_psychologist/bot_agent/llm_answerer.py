# bot_agent/llm_answerer.py
"""
LLM Answerer Module
===================

Генерация ответов через OpenAI API с системным промптом бота-психолога.
"""

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncGenerator, List, Dict, Optional, Tuple
from pathlib import Path

from .data_loader import Block
from .config import config

logger = logging.getLogger(__name__)


def _read_prompt_text(path: Path) -> str:
    """
    Read UTF-8 prompt text from disk.
    We allow BOM so the file can be edited in Windows tools comfortably.
    TODO(admin-panel): чтение промта на уровне модуля — не hot-reloadable.
    Для горячей замены перенести в функцию и использовать config.get_prompt().
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8-sig")
    return text.lstrip("\ufeff").strip()


class LLMAnswerer:
    """
    Формирует ответ на основе найденных блоков, используя OpenAI API.
    
    Usage:
        >>> answerer = LLMAnswerer()
        >>> result = answerer.generate_answer("Что такое осознавание?", blocks)
        >>> print(result["answer"])
    """
    
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.client = None
        self.async_client = None
        
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY не установлен. LLM ответы недоступны.")
        else:
            self._init_client()
    
    def _init_client(self):
        """Инициализация OpenAI клиента"""
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
            self.async_client = openai.AsyncOpenAI(api_key=self.api_key)
            token_param = config.get_token_param_name()
            logger.info(
                "✓ OpenAI клиент инициализирован | модель: %s | параметр токенов: %s",
                config.LLM_MODEL,
                token_param,
            )
        except ImportError:
            logger.error("❌ openai не установлен. Установите: pip install openai")
            raise

    @staticmethod
    def _messages_to_input(messages: List[Dict]) -> str:
        """Convert chat messages into a plain text payload for Responses API."""
        chunks = []
        for msg in messages or []:
            role = str(msg.get("role", "user")).upper()
            content = str(msg.get("content", ""))
            if content:
                chunks.append(f"{role}:\n{content}")
        return "\n\n".join(chunks).strip()

    def _resolve_max_tokens(self, model: str, explicit_max_tokens: Optional[int]) -> Optional[int]:
        """
        Resolve token budget with FREE mode priority.

        Priority:
        1) FREE_CONVERSATION_MODE -> MAX_TOKENS_SOFT_CAP
        2) explicit max_tokens argument
        3) config.MAX_TOKENS (can be None)
        """
        if config.FREE_CONVERSATION_MODE:
            return int(config.MAX_TOKENS_SOFT_CAP)
        if explicit_max_tokens is not None:
            return int(explicit_max_tokens)
        configured = getattr(config, "MAX_TOKENS", None)
        if configured is None:
            return None
        return int(configured)

    def _build_api_params(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict:
        """Build OpenAI request params for either chat-completions or responses API."""
        model_name = model or config.LLM_MODEL
        resolved_max_tokens = self._resolve_max_tokens(model_name, max_tokens)
        token_param = config.get_token_param_name(model_name)

        if not config.supports_custom_temperature(model_name):
            request_params: Dict = {
                "model": model_name,
                "input": self._messages_to_input(messages),
            }
            if resolved_max_tokens is not None:
                request_params["max_output_tokens"] = resolved_max_tokens
            if stream:
                request_params["stream"] = True
            reasoning_effort = config.get_reasoning_effort(model_name)
            if reasoning_effort:
                request_params["reasoning"] = {"effort": reasoning_effort}
            return request_params

        final_temperature = (
            temperature if temperature is not None else config.LLM_TEMPERATURE
        )
        request_params = {
            "model": model_name,
            "messages": messages,
            "temperature": final_temperature,
        }
        if resolved_max_tokens is not None:
            request_params[token_param] = resolved_max_tokens
        if stream:
            request_params["stream"] = True
        return request_params

    @staticmethod
    def _save_blob_compat(
        session_store: Any,
        *,
        text: str,
        session_id: Optional[str],
    ) -> Optional[str]:
        """
        Save prompt text to session storage and return blob id.

        Supports both APIs:
        - save_blob(text, session_id=...)
        - set_blob(blob_id, text)
        """
        if not session_store or not text:
            return None

        save_blob = getattr(session_store, "save_blob", None)
        if callable(save_blob):
            return str(save_blob(text, session_id=session_id))

        set_blob = getattr(session_store, "set_blob", None)
        if callable(set_blob):
            prefix = (session_id or "blob").strip() or "blob"
            blob_id = f"{prefix}:{uuid.uuid4().hex[:8]}"
            set_blob(blob_id, text, ttl_seconds=1800)
            return blob_id

        return None
    
    def build_system_prompt(self) -> str:
        """
        Системный промпт для бота-психолога.

        Определяет поведение, тон и ограничения бота.
        """
        try:
            # Используем config.get_prompt() для горячей замены (admin-panel)
            return config.get_prompt("prompt_system_base")["text"]
        except (FileNotFoundError, ValueError):
            logger.warning("⚠️ prompt_system_base.md not found. Falling back to встроенному промпту.")
            return (
                "Ты — спокойный и точный помощник.\n"
                "Отвечай по-русски. Опирайся на материалы, переданные в контексте. "
                "Если в материалах нет ответа — честно скажи об этом и попроси уточнение."
            )
    
    def build_context_prompt(
        self,
        blocks: List[Block],
        user_question: str,
        conversation_history: Optional[str] = None
    ) -> str:
        """
        Формирует контекст для LLM: найденные блоки + вопрос.
        
        Args:
            blocks: Список релевантных блоков
            user_question: Вопрос пользователя
            conversation_history: История последних N обменов (если есть)
            
        Returns:
            Отформатированный контекст для LLM
        """
        context = ""

        if conversation_history:
            context += conversation_history.strip() + "\n\n"

        context += "МАТЕРИАЛ ИЗ ЛЕКЦИЙ:\n\n"
        
        for i, block in enumerate(blocks, 1):
            context += f"--- БЛОК {i} ---\n"
            context += f"Лекция: {block.document_title}\n"
            context += f"Тема: {block.title}\n"
            context += f"Таймкод: {block.start} — {block.end}\n"
            context += f"Ссылка: {block.youtube_link}\n"
            context += f"Краткое описание: {block.summary}\n"
            context += f"Полный текст:\n{block.content}\n\n"
        
        context += f"ВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_question}\n\n"
        context += "Сформируй ответ, опираясь на материал выше."
        
        return context
    
    def generate_answer(
        self,
        user_question: str,
        blocks: List[Block],
        conversation_history: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        step_name: str = "answer",
        system_prompt_blob_id: Optional[str] = None,
        user_prompt_blob_id: Optional[str] = None,
        session_store: Optional[Any] = None,
        session_id: Optional[str] = None,
    ) -> Dict:
        """
        Формирует ответ через OpenAI API.
        
        Args:
            user_question: Вопрос пользователя
            blocks: Список релевантных блоков
            model: Модель LLM (по умолчанию из config)
            temperature: Температура генерации
            max_tokens: Максимальная длина ответа
            
        Returns:
            Dict с ключами:
                - answer: str — готовый ответ
                - model_used: str — какую модель использовали
                - tokens_used: int — количество токенов
                - error: Optional[str] — если была ошибка
        """
        # Обработка случая без блоков
        if not blocks:
            logger.warning("⚠️ Нет блоков для контекста!")
            return {
                "answer": "К сожалению, я не нашёл релевантного материала для этого вопроса. Попробуйте переформулировать.",
                "model_used": None,
                "tokens_used": 0,
                "error": "no_blocks"
            }
        
        # Проверка клиента
        if not self.client:
            return {
                "answer": "❌ OpenAI API недоступен. Проверьте OPENAI_API_KEY в .env",
                "model_used": None,
                "tokens_used": 0,
                "error": "no_api_key"
            }
        
        # Параметры
        model = model or config.LLM_MODEL
        temperature = temperature if temperature is not None else config.LLM_TEMPERATURE
        resolved_max_tokens = self._resolve_max_tokens(model, max_tokens)
        token_param = config.get_token_param_name(model)
        
        # Промпты
        system_prompt = self.build_system_prompt()
        context = self.build_context_prompt(
            blocks,
            user_question,
            conversation_history=conversation_history
        )

        blob_error = None
        if session_store is not None:
            try:
                system_prompt_blob_id = self._save_blob_compat(
                    session_store,
                    text=system_prompt,
                    session_id=session_id,
                )
                user_prompt_blob_id = self._save_blob_compat(
                    session_store,
                    text=context,
                    session_id=session_id,
                )
            except Exception as exc:
                blob_error = f"blob_save_failed: {exc}"
                system_prompt_blob_id = None
                user_prompt_blob_id = None

        llm_call_info = {
            "step": step_name,
            "model": str(model),
            "tokens_prompt": None,
            "tokens_completion": None,
            "tokens_total": None,
            "duration_ms": 0,
            "system_prompt_preview": (system_prompt or "")[:300],
            "user_prompt_preview": (context or "")[:300],
            "response_preview": "",
            "system_prompt_blob_id": system_prompt_blob_id,
            "user_prompt_blob_id": user_prompt_blob_id,
            "blob_error": blob_error,
        }

        logger.debug("[LLM_ANSWERER] sending request to %s", model)

        try:
            logger.debug(
                "Using token parameter: %s=%s for model %s (free_mode=%s)",
                token_param,
                resolved_max_tokens,
                model,
                config.FREE_CONVERSATION_MODE,
            )
            start_time = time.perf_counter()
            tokens_prompt = None
            tokens_completion = None
            tokens_total = None
            model_used = model
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ]
            if not config.supports_custom_temperature(model):
                request_params = self._build_api_params(
                    messages=messages,
                    model=model,
                    max_tokens=max_tokens,
                )
                response = self.client.responses.create(**request_params)
                answer = (getattr(response, "output_text", "") or "").strip()
                usage = getattr(response, "usage", None)
                model_used = str(getattr(response, "model", model))
                if usage is not None:
                    _tp = getattr(usage, "prompt_tokens", None)
                    tokens_prompt = _tp if _tp is not None else getattr(usage, "input_tokens", None)

                    _tc = getattr(usage, "completion_tokens", None)
                    tokens_completion = _tc if _tc is not None else getattr(usage, "output_tokens", None)

                    tokens_total = getattr(usage, "total_tokens", None)
                    if tokens_total is None and tokens_prompt is not None and tokens_completion is not None:
                        tokens_total = int(tokens_prompt) + int(tokens_completion)
            else:
                request_params = self._build_api_params(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                response = self.client.chat.completions.create(**request_params)
                raw_content = response.choices[0].message.content
                answer = (raw_content or "").strip()
                model_used = str(getattr(response, "model", model))
                if response.usage:
                    tokens_prompt = getattr(response.usage, "prompt_tokens", None)
                    tokens_completion = getattr(response.usage, "completion_tokens", None)
                    tokens_total = getattr(response.usage, "total_tokens", None)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            tokens = tokens_total if tokens_total is not None else 0
            logger.debug(
                "[LLM_ANSWERER] raw content length=%s model=%s",
                len(answer),
                model,
            )
            if not answer:
                logger.warning(
                    "[LLM_ANSWERER] ⚠️ Empty content returned by model %s, using fallback",
                    model,
                )
                answer = (
                    "Расскажите подробнее о своём вопросе — я готов помочь разобраться."
                )
            
            logger.debug(f"✅ Ответ получен ({tokens} токенов)")
            
            llm_call_info.update(
                {
                    "model": model_used,
                    "tokens_prompt": int(tokens_prompt) if isinstance(tokens_prompt, (int, float)) else None,
                    "tokens_completion": int(tokens_completion) if isinstance(tokens_completion, (int, float)) else None,
                    "tokens_total": int(tokens_total) if isinstance(tokens_total, (int, float)) else None,
                    "duration_ms": duration_ms,
                    "response_preview": (answer or "")[:300],
                }
            )

            return {
                "answer": answer,
                "model_used": model_used,
                "tokens_used": tokens,
                "tokens_prompt": llm_call_info["tokens_prompt"],
                "tokens_completion": llm_call_info["tokens_completion"],
                "tokens_total": llm_call_info["tokens_total"],
                "duration_ms": llm_call_info["duration_ms"],
                "llm_call_info": llm_call_info,
                "error": None,
            }
        
        except Exception as e:
            logger.error("[LLM_ANSWERER] OpenAI API error: %s", e)
            llm_call_info["duration_ms"] = int((time.perf_counter() - start_time) * 1000) if "start_time" in locals() else 0
            llm_call_info["response_preview"] = ""
            return {
                "answer": f"Ошибка при формировании ответа: {str(e)}",
                "model_used": model,
                "tokens_used": 0,
                "llm_call_info": llm_call_info,
                "error": str(e)
            }

    async def answer_stream(
        self,
        user_question: str,
        blocks: List[Block],
        conversation_history: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt_override: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream answer tokens from OpenAI."""
        if not blocks:
            yield (
                "К сожалению, я не нашёл релевантного материала для этого вопроса. "
                "Попробуйте переформулировать."
            )
            return

        if not self.async_client:
            yield "❌ OpenAI API недоступен. Проверьте OPENAI_API_KEY в .env"
            return

        model = model or config.LLM_MODEL
        temperature = temperature if temperature is not None else config.LLM_TEMPERATURE
        resolved_max_tokens = self._resolve_max_tokens(model, max_tokens)

        system_prompt = system_prompt_override or self.build_system_prompt()
        context = self.build_context_prompt(
            blocks,
            user_question,
            conversation_history=conversation_history,
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ]

        if not config.supports_custom_temperature(model):
            try:
                request_params = self._build_api_params(
                    messages=messages,
                    model=model,
                    max_tokens=max_tokens,
                    stream=True,
                )

                stream = await self.async_client.responses.create(**request_params)
                async for event in stream:
                    token = ""
                    if hasattr(event, "delta") and event.delta:
                        token = event.delta
                    elif hasattr(event, "output_text") and event.output_text:
                        token = event.output_text
                    elif isinstance(event, dict):
                        token = event.get("delta") or event.get("output_text") or ""
                    if token:
                        yield token
                return
            except Exception as exc:
                logger.warning("[LLM_ANSWERER] reasoning stream failed: %s", exc)
                # Fallback to non-streaming generation
                result = await asyncio.to_thread(
                    self.generate_answer,
                    user_question,
                    blocks,
                    conversation_history,
                    model,
                    temperature,
                    resolved_max_tokens,
                )
                answer = (result.get("answer") or "").strip()
                if answer:
                    yield answer
                return

        request_params = self._build_api_params(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        stream = await self.async_client.chat.completions.create(**request_params)
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            token = getattr(delta, "content", None) if delta else None
            if token:
                yield token



