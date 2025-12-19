# bot_agent/llm_answerer.py
"""
LLM Answerer Module
===================

Генерация ответов через OpenAI API с системным промптом бота-психолога.
"""

import logging
from typing import List, Dict, Optional

from .data_loader import Block
from .config import config

logger = logging.getLogger(__name__)


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
            logger.info("✓ OpenAI клиент инициализирован")
        except ImportError:
            logger.error("❌ openai не установлен. Установите: pip install openai")
            raise
    
    def build_system_prompt(self) -> str:
        """
        Системный промпт для бота-психолога.
        
        Определяет поведение, тон и ограничения бота.
        """
        return """Ты — спокойный и поддерживающий гид, специализирующийся на учении Саламата Сарсекенова о нейросталкинге и трансформации сознания.

ТВОЁ ПОВЕДЕНИЕ:
1. Отвечай спокойно, уважительно, без осуждения.
2. Используй информацию ТОЛЬКО из предоставленных материалов лекций.
3. Если информации нет в материалах — честно скажи об этом.
4. Всегда старайся найти практическое применение для жизни пользователя.
5. Избегай медицинских/психиатрических диагнозов.

ТОНУС:
- Спокойный, но не безличный
- "Предлагаю исследовать..." вместо "Ты должен..."
- Поддерживающий, но честный

СТРУКТУРА ОТВЕТА:
1. Прямо ответить на вопрос
2. Привести примеры из материалов
3. Предложить практическое применение (если уместно)
4. Упомянуть источники с таймкодами

ВАЖНО: Если пользователь упоминает серьёзные состояния (суицидальные мысли, панические атаки), добавь дисклеймер о необходимости обращения к специалисту."""
    
    def build_context_prompt(self, blocks: List[Block], user_question: str) -> str:
        """
        Формирует контекст для LLM: найденные блоки + вопрос.
        
        Args:
            blocks: Список релевантных блоков
            user_question: Вопрос пользователя
            
        Returns:
            Отформатированный контекст для LLM
        """
        context = "МАТЕРИАЛ ИЗ ЛЕКЦИЙ:\n\n"
        
        for i, block in enumerate(blocks, 1):
            context += f"--- БЛОК {i} ---\n"
            context += f"Лекция: {block.document_title}\n"
            context += f"Тема: {block.title}\n"
            context += f"Таймкод: {block.start} — {block.end}\n"
            context += f"Ссылка: {block.youtube_link}\n"
            context += f"Краткое описание: {block.summary}\n"
            context += f"Полный текст:\n{block.content}\n\n"
        
        context += f"ВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_question}\n\n"
        context += "Сформируй ответ, опираясь на материал выше. Обязательно упомяни источники с таймкодами."
        
        return context
    
    def generate_answer(
        self,
        user_question: str,
        blocks: List[Block],
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
        
        # Промпты
        system_prompt = self.build_system_prompt()
        context = self.build_context_prompt(blocks, user_question)
        
        logger.debug(f"📤 Отправляю запрос к {model}...")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            answer = response.choices[0].message.content
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

