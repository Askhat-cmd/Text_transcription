# bot_agent/user_level_adapter.py
"""
User Level Adapter for Phase 2
==============================

Адаптирует ответы и выбор блоков в зависимости от уровня пользователя:
- beginner: простые объяснения, низкая сложность
- intermediate: средняя глубина, практика + теория
- advanced: полная глубина, философские основы
"""

import logging
from typing import List, Optional
from enum import Enum

from .data_loader import Block

logger = logging.getLogger(__name__)


class UserLevel(Enum):
    """Уровни подготовки пользователя"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class UserLevelAdapter:
    """
    Адаптирует ответы и выбор блоков в зависимости от уровня пользователя.
    
    Phase 2: Используется для фильтрации блоков, адаптации промптов,
    извлечения ключевых концептов.
    
    Usage:
        >>> adapter = UserLevelAdapter("beginner")
        >>> filtered_blocks = adapter.filter_blocks_by_level(blocks)
        >>> adapted_prompt = adapter.adapt_system_prompt(base_prompt)
    """
    
    def __init__(self, user_level: str = "beginner"):
        """
        Инициализация адаптера.
        
        Args:
            user_level: Уровень пользователя (beginner/intermediate/advanced)
        """
        try:
            self.level = UserLevel(user_level.lower())
        except ValueError:
            logger.warning(f"⚠️ Неизвестный уровень '{user_level}', используем beginner")
            self.level = UserLevel.BEGINNER
        
        logger.debug(f"🎯 UserLevelAdapter инициализирован: {self.level.value}")
    
    def filter_blocks_by_level(self, blocks: List[Block]) -> List[Block]:
        """
        Отфильтровать блоки по сложности в зависимости от уровня пользователя.
        
        Args:
            blocks: Список блоков для фильтрации
            
        Returns:
            Отфильтрованный список блоков
        """
        if not blocks:
            return blocks
        
        if self.level == UserLevel.BEGINNER:
            # Для начинающих: простые, низкая сложность, низкая глубина
            filtered = [
                b for b in blocks
                if b.complexity_score <= 5.0
                and b.conceptual_depth in ["low", "medium"]
                and b.block_type in ["theory", "practice"]
            ]
            logger.debug(f"🎯 BEGINNER: отфильтровано {len(filtered)}/{len(blocks)} блоков")
            return filtered if filtered else blocks[:3]  # fallback
        
        elif self.level == UserLevel.INTERMEDIATE:
            # Для промежуточных: средняя сложность, диалоги и практики
            filtered = [
                b for b in blocks
                if b.complexity_score <= 7.5
                and b.conceptual_depth in ["medium", "high"]
            ]
            logger.debug(f"🎯 INTERMEDIATE: отфильтровано {len(filtered)}/{len(blocks)} блоков")
            return filtered if filtered else blocks[:5]  # fallback
        
        else:  # ADVANCED
            # Для продвинутых: всё, включая сложное
            logger.debug(f"🎯 ADVANCED: используем все {len(blocks)} блоков")
            return blocks
    
    def adapt_system_prompt(self, base_prompt: str) -> str:
        """
        Адаптировать системный промпт под уровень пользователя.
        
        Args:
            base_prompt: Базовый системный промпт
            
        Returns:
            Адаптированный промпт с дополнительными инструкциями
        """
        if self.level == UserLevel.BEGINNER:
            addition = """

ДОПОЛНИТЕЛЬНО ДЛЯ BEGINNER:
- Избегай сложной терминологии, объясняй простыми словами.
- Используй аналогии из повседневной жизни.
- Сосредоточься на практическом применении, а не теории.
- Предлагай конкретные шаги, которые пользователь может начать прямо сейчас.
- Если используешь термин — сразу дай краткое пояснение."""
        
        elif self.level == UserLevel.INTERMEDIATE:
            addition = """

ДОПОЛНИТЕЛЬНО ДЛЯ INTERMEDIATE:
- Используй правильную терминологию, но объясняй новые термины.
- Показывай связи между концептами.
- Балансируй между теорией и практикой.
- Можешь упоминать более глубокие аспекты, но не углубляйся чрезмерно."""
        
        else:  # ADVANCED
            addition = """

ДОПОЛНИТЕЛЬНО ДЛЯ ADVANCED:
- Можешь использовать сложную терминологию и концепции.
- Углубляйся в философские и теоретические основы.
- Показывай взаимосвязи на уровне всей системы учения.
- Можешь обсуждать нюансы, парадоксы и тонкие различия."""
        
        return base_prompt + addition
    
    def extract_key_concepts(self, blocks: List[Block]) -> List[str]:
        """
        Извлечь ключевые концепты из блоков на основе graph_entities.
        
        Args:
            blocks: Список блоков для анализа
            
        Returns:
            Список ключевых концептов (отсортированных по частоте)
        """
        if not blocks:
            return []
        
        concepts_freq = {}
        
        for block in blocks:
            if block.graph_entities:
                for entity in block.graph_entities:
                    concepts_freq[entity] = concepts_freq.get(entity, 0) + 1
        
        # Сортируем по частоте
        sorted_concepts = sorted(
            concepts_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Возвращаем top концепты в зависимости от уровня
        if self.level == UserLevel.BEGINNER:
            max_concepts = 3
        elif self.level == UserLevel.INTERMEDIATE:
            max_concepts = 5
        else:  # ADVANCED
            max_concepts = 10
        
        result = [c[0] for c in sorted_concepts[:max_concepts]]
        logger.debug(f"🔑 Извлечено {len(result)} ключевых концептов для {self.level.value}")
        return result
    
    def get_answer_length_guidance(self) -> str:
        """
        Подсказка для LLM о длине и стиле ответа.
        
        Returns:
            Строка с рекомендациями по длине ответа
        """
        if self.level == UserLevel.BEGINNER:
            return "Напиши краткий ответ (2-3 абзаца). Избегай излишних деталей. Фокус на главном."
        elif self.level == UserLevel.INTERMEDIATE:
            return "Напиши подробный ответ (4-5 абзацев) с примерами и пояснениями."
        else:  # ADVANCED
            return "Напиши развернутый ответ (6+ абзацев) со всеми деталями, связями и нюансами."
    
    def format_concepts_for_output(self, concepts: List[str]) -> str:
        """
        Форматирование концептов для включения в конец ответа.
        
        Args:
            concepts: Список концептов для форматирования
            
        Returns:
            Отформатированная строка с концептами
        """
        if not concepts:
            return ""
        
        if self.level == UserLevel.BEGINNER:
            return f"\n\n🔑 **Ключевые термины:** {', '.join(concepts)}"
        
        elif self.level == UserLevel.INTERMEDIATE:
            return f"\n\n🔑 **Задействованные концепты:** {', '.join(concepts)}"
        
        else:  # ADVANCED
            return f"\n\n🧠 **Концептуальная основа:** {', '.join(concepts)}"
    
    def get_level_info(self) -> dict:
        """
        Вернуть информацию об уровне для метаданных.
        
        Returns:
            Словарь с информацией об уровне
        """
        level_descriptions = {
            UserLevel.BEGINNER: "Начинающий — простые объяснения, практические шаги",
            UserLevel.INTERMEDIATE: "Средний уровень — терминология, связи между концептами",
            UserLevel.ADVANCED: "Продвинутый — глубокая теория, философские основы"
        }
        
        return {
            "level": self.level.value,
            "description": level_descriptions.get(self.level, ""),
            "max_complexity": 5.0 if self.level == UserLevel.BEGINNER else 
                             7.5 if self.level == UserLevel.INTERMEDIATE else 10.0
        }
