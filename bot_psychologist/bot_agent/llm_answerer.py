# bot_agent/llm_answerer.py
"""
LLM Answerer Module
===================

Генерация ответов через OpenAI API с системным промптом бота-психолога.
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path

from .data_loader import Block
from .config import config

logger = logging.getLogger(__name__)

_PROMPT_BASE_PATH = Path(__file__).resolve().parent / "prompt_system_base.md"


def _read_prompt_text(path: Path) -> str:
    """
    Read UTF-8 prompt text from disk.
    We allow BOM so the file can be edited in Windows tools comfortably.
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
        
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY не установлен. LLM ответы недоступны.")
        else:
            self._init_client()
    
    def _init_client(self):
        """Инициализация OpenAI клиента"""
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
            token_param = config.get_token_param_name()
            logger.info(
                "✓ OpenAI клиент инициализирован | модель: %s | параметр токенов: %s",
                config.LLM_MODEL,
                token_param,
            )
        except ImportError:
            logger.error("❌ openai не установлен. Установите: pip install openai")
            raise
    
    def build_system_prompt(self) -> str:
        """
        Системный промпт для бота-психолога.
        
        Определяет поведение, тон и ограничения бота.
        """
        try:
            return _read_prompt_text(_PROMPT_BASE_PATH)
        except FileNotFoundError:
            logger.warning(f"⚠️ System prompt file not found: {_PROMPT_BASE_PATH}. Falling back to встроенному промпту.")
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
        max_tokens: Optional[int] = None
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
        max_tokens = max_tokens or config.LLM_MAX_TOKENS
        token_param = config.get_token_param_name(model)
        
        # Промпты
        system_prompt = self.build_system_prompt()
        context = self.build_context_prompt(
            blocks,
            user_question,
            conversation_history=conversation_history
        )
        
        logger.debug(f"📤 Отправляю запрос к {model}...")
        
        try:
            logger.debug("Using token parameter: %s=%s for model %s", token_param, max_tokens, model)
            request_params = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context},
                ],
                token_param: max_tokens,
            }
            if config.supports_custom_temperature(model):
                request_params["temperature"] = temperature
            else:
                logger.debug("Skipping custom temperature for model %s", model)

            response = self.client.chat.completions.create(**request_params)
            
            raw_content = response.choices[0].message.content
            answer = (raw_content or "").strip()
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
            tokens = response.usage.total_tokens if response.usage else 0
            
            logger.debug(f"✅ Ответ получен ({tokens} токенов)")
            
            return {
                "answer": answer,
                "model_used": model,
                "tokens_used": tokens,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"❌ Ошибка при вызове OpenAI API: {e}")
            return {
                "answer": f"Ошибка при формировании ответа: {str(e)}",
                "model_used": model,
                "tokens_used": 0,
                "error": str(e)
            }



