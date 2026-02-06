# bot_agent/conversation_memory.py
"""
Conversation Memory Module (Phase 4.2)
======================================

Долгосрочная память диалога с персистентным хранением.
Отслеживание интересов, вызовов и прорывов пользователя.
"""

import logging
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Один ход в диалоге"""
    timestamp: str
    user_input: str
    user_state: Optional[str] = None  # состояние пользователя
    bot_response: Optional[str] = None
    blocks_used: int = 0
    concepts: List[str] = field(default_factory=list)
    user_feedback: Optional[str] = None  # positive/negative/neutral
    user_rating: Optional[int] = None  # 1-5


class ConversationMemory:
    """
    Хранит и управляет историей диалога пользователя.
    Поддерживает персистентное хранилище.
    """
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.turns: List[ConversationTurn] = []
        self.metadata: Dict = {
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_turns": 0,
            "user_level": "beginner",
            "primary_interests": [],  # темы, которые интересуют пользователя
            "challenges": [],  # с чем борется пользователь
            "breakthroughs": []  # инсайты и прорывы
        }
        self.memory_dir = config.CACHE_DIR / "conversations"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
    
    def load_from_disk(self) -> bool:
        """
        Загрузить историю диалога с диска.
        
        Returns:
            True если загрузка успешна, False если файл не найден
        """
        filepath = self.memory_dir / f"{self.user_id}.json"
        
        if not filepath.exists():
            logger.debug(f"📋 Новая история диалога для пользователя {self.user_id}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.metadata = data.get("metadata", self.metadata)
            self.turns = [
                ConversationTurn(**turn_data)
                for turn_data in data.get("turns", [])
            ]
            
            logger.info(f"✅ Загружена история диалога: {len(self.turns)} оборотов")
            return True
        
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки истории: {e}")
            return False
    
    def save_to_disk(self) -> None:
        """
        Сохранить историю диалога на диск.
        """
        filepath = self.memory_dir / f"{self.user_id}.json"
        
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["total_turns"] = len(self.turns)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "metadata": self.metadata,
                    "turns": [asdict(turn) for turn in self.turns]
                }, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"💾 История сохранена ({len(self.turns)} оборотов)")
        
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения истории: {e}")
    
    def add_turn(
        self,
        user_input: str,
        bot_response: str,
        user_state: Optional[str] = None,
        blocks_used: int = 0,
        concepts: Optional[List[str]] = None
    ) -> ConversationTurn:
        """
        Добавить ход в историю.
        
        Args:
            user_input: Вопрос пользователя
            bot_response: Ответ бота
            user_state: Состояние пользователя (из StateClassifier)
            blocks_used: Количество использованных блоков
            concepts: Список концептов в ответе
            
        Returns:
            Созданный ConversationTurn
        """
        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            user_state=user_state,
            bot_response=bot_response,
            blocks_used=blocks_used,
            concepts=concepts or []
        )
        
        self.turns.append(turn)
        logger.debug(f"➕ Добавлен ход #{len(self.turns)}")

        # Ограничиваем общее число ходов (авторотация)
        max_turns = config.MAX_CONVERSATION_TURNS
        if max_turns and len(self.turns) > max_turns:
            overflow = len(self.turns) - max_turns
            self.turns = self.turns[overflow:]
        
        self.save_to_disk()
        return turn
    
    def add_feedback(
        self,
        turn_index: int,
        feedback: str,  # positive/negative/neutral
        rating: Optional[int] = None  # 1-5
    ) -> None:
        """
        Добавить обратную связь к ходу.
        
        Args:
            turn_index: Индекс хода (0-based) или -1 для последнего
            feedback: Тип обратной связи (positive/negative/neutral)
            rating: Рейтинг от 1 до 5
        """
        if turn_index == -1:
            turn_index = len(self.turns) - 1
            
        if 0 <= turn_index < len(self.turns):
            self.turns[turn_index].user_feedback = feedback
            self.turns[turn_index].user_rating = rating
            
            logger.debug(f"👍 Обратная связь добавлена: {feedback} (рейтинг: {rating})")
            self.save_to_disk()
        else:
            logger.warning(f"⚠️ Некорректный индекс хода: {turn_index}")
    
    def get_last_turns(self, n: int = 5) -> List[ConversationTurn]:
        """
        Получить последние N оборотов.
        
        Args:
            n: Количество последних ходов
            
        Returns:
            Список ConversationTurn
        """
        return self.turns[-n:] if self.turns else []
    
    def get_context_for_llm(self, n: int = 3, max_chars: Optional[int] = None) -> str:
        """
        Получить контекст последних оборотов для LLM.
        Используется для учета истории в ответе.
        
        Args:
            n: Количество последних ходов для контекста
            max_chars: Максимальный размер контекста (символы)
            
        Returns:
            Отформатированная строка с историей
        """
        last_turns = self.get_last_turns(n)
        
        if not last_turns:
            return ""

        if max_chars is None:
            max_chars = config.MAX_CONTEXT_SIZE
        
        context = "ИСТОРИЯ ДИАЛОГА (последние обороты):\n\n"

        # Добавляем последние ходы с учетом лимита
        entries: List[str] = []
        current_len = len(context)

        for i, turn in enumerate(reversed(last_turns), 1):
            turn_num = len(self.turns) - i + 1
            response_preview = (
                turn.bot_response[:200] + "..."
                if turn.bot_response and len(turn.bot_response) > 200
                else (turn.bot_response or "")
            )

            entry = (
                f"Обмен #{turn_num}:\n"
                f"  Пользователь: {turn.user_input}\n"
                f"  Бот: {response_preview}\n"
            )
            if turn.user_state:
                entry += f"  Состояние: {turn.user_state}\n"
            entry += "\n"

            # Проверяем лимит
            if max_chars and current_len + len(entry) > max_chars:
                if not entries:
                    # Если даже один ход слишком большой, обрежем его
                    allowed = max(0, max_chars - current_len)
                    entry = (entry[:max(0, allowed - 3)] + "...") if allowed > 0 else ""
                    if entry:
                        entries.append(entry)
                break

            entries.append(entry)
            current_len += len(entry)

        # Возвращаем в хронологическом порядке
        for entry in reversed(entries):
            context += entry

        return context

    def clear(self) -> None:
        """Очистить историю диалога и сохранить пустое состояние."""
        self.turns = []
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["total_turns"] = 0
        self.save_to_disk()
    
    def get_primary_interests(self) -> List[str]:
        """
        Получить основные интересы пользователя на основе истории.
        Сортировка по частоте упоминания концептов.
        
        Returns:
            Список топ-5 концептов
        """
        interests: Dict[str, int] = {}
        
        for turn in self.turns:
            for concept in turn.concepts:
                interests[concept] = interests.get(concept, 0) + 1
        
        # Сортируем по частоте
        sorted_interests = sorted(
            interests.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [concept for concept, _ in sorted_interests[:5]]
    
    def get_challenges(self) -> List[Dict]:
        """
        Получить основные вызовы пользователя (отрицательная обратная связь).
        
        Returns:
            Список ходов с негативной обратной связью
        """
        challenges = []
        
        for turn in self.turns:
            if turn.user_feedback == "negative":
                challenges.append({
                    "turn": turn.user_input,
                    "rating": turn.user_rating,
                    "concepts": turn.concepts,
                    "state": turn.user_state
                })
        
        return challenges
    
    def get_breakthroughs(self) -> List[Dict]:
        """
        Получить инсайты и прорывы (положительная обратная связь с высоким рейтингом).
        
        Returns:
            Список ходов с положительной обратной связью и рейтингом >= 4
        """
        breakthroughs = []
        
        for turn in self.turns:
            if turn.user_feedback == "positive" and turn.user_rating and turn.user_rating >= 4:
                breakthroughs.append({
                    "turn": turn.user_input,
                    "response": turn.bot_response[:300] if turn.bot_response else "",
                    "rating": turn.user_rating,
                    "concepts": turn.concepts,
                    "state": turn.user_state
                })
        
        return breakthroughs
    
    def get_summary(self) -> Dict:
        """
        Получить краткое резюме истории диалога.
        
        Returns:
            Dict с ключевыми метриками
        """
        interests = self.get_primary_interests()
        challenges = self.get_challenges()
        breakthroughs = self.get_breakthroughs()
        
        # Средний рейтинг
        avg_rating = 0.0
        if self.turns:
            ratings = [t.user_rating for t in self.turns if t.user_rating]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        return {
            "total_turns": len(self.turns),
            "primary_interests": interests,
            "num_challenges": len(challenges),
            "num_breakthroughs": len(breakthroughs),
            "average_rating": round(avg_rating, 2),
            "user_level": self.metadata.get("user_level", "beginner"),
            "last_interaction": self.turns[-1].timestamp if self.turns else None
        }
    
    def set_user_level(self, level: str) -> None:
        """
        Установить уровень пользователя.
        
        Args:
            level: beginner / intermediate / advanced
        """
        self.metadata["user_level"] = level
        self.save_to_disk()


# Глобальный кэш инстансов памяти
_memory_instances: Dict[str, ConversationMemory] = {}


def get_conversation_memory(user_id: str = "default") -> ConversationMemory:
    """
    Получить экземпляр памяти диалога для пользователя.
    Использует кэш для оптимизации.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        ConversationMemory для данного пользователя
    """
    if user_id not in _memory_instances:
        memory = ConversationMemory(user_id)
        memory.load_from_disk()
        _memory_instances[user_id] = memory
    
    return _memory_instances[user_id]


