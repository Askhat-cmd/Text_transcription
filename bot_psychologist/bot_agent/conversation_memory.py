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
from typing import Any

from .config import config
from .semantic_memory import get_semantic_memory, SemanticMemory, TurnEmbedding
from .storage import SessionManager
from .working_state import WorkingState

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

        # === НОВОЕ: Semantic Memory ===
        self.semantic_memory: Optional[SemanticMemory] = None
        if config.ENABLE_SEMANTIC_MEMORY:
            self.semantic_memory = get_semantic_memory(user_id)

        # === НОВОЕ: Conversation Summary ===
        self.summary: Optional[str] = None
        self.summary_updated_at: Optional[int] = None  # turn index
        self.working_state: Optional[WorkingState] = None

        # === PRD v2.0 bootstrap: SQLite Session Storage ===
        self.session_manager: Optional[SessionManager] = None
        if config.ENABLE_SESSION_STORAGE:
            try:
                self.session_manager = SessionManager(str(config.BOT_DB_PATH))
                self.session_manager.create_session(
                    session_id=self.user_id,
                    user_id=self.user_id,
                    metadata={"source": "conversation_memory"},
                )
            except Exception as exc:
                logger.error(f"❌ Ошибка инициализации SessionManager: {exc}")
    
    def load_from_disk(self) -> bool:
        """
        Загрузить историю диалога с диска.
        
        Returns:
            True если загрузка успешна, False если файл не найден
        """
        if self._load_from_session_storage():
            return True

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

            # === НОВОЕ: Загрузить summary ===
            self.summary = data.get("summary")
            self.summary_updated_at = data.get("summary_updated_at")
            raw_working_state = data.get("working_state")
            if isinstance(raw_working_state, dict):
                self.working_state = WorkingState.from_dict(raw_working_state)
            
            logger.info(f"✅ Загружена история диалога: {len(self.turns)} оборотов")
            return True
        
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки истории: {e}")
            return False

    def _load_from_session_storage(self) -> bool:
        """Загрузить состояние из SQLite SessionManager."""
        if not self.session_manager:
            return False

        try:
            payload = self.session_manager.load_session(self.user_id)
            if not payload:
                return False

            turns_data = payload.get("conversation_turns", [])
            session_info = payload.get("session_info", {})

            if not turns_data and not session_info.get("conversation_summary"):
                return False

            metadata = session_info.get("metadata")
            if isinstance(metadata, dict):
                self.metadata.update(metadata)

            restored_turns: List[ConversationTurn] = []
            for turn in turns_data:
                concepts = turn.get("chunks_used") or []
                restored_turns.append(
                    ConversationTurn(
                        timestamp=turn["timestamp"],
                        user_input=turn["user_input"],
                        user_state=turn.get("user_state"),
                        bot_response=turn["bot_response"],
                        blocks_used=len(concepts),
                        concepts=concepts,
                        user_feedback=turn.get("user_feedback"),
                        user_rating=turn.get("user_rating"),
                    )
                )

            self.turns = restored_turns
            self.summary = session_info.get("conversation_summary")
            self.summary_updated_at = len(self.turns) if self.summary else None
            raw_working_state = session_info.get("working_state")
            if isinstance(raw_working_state, dict):
                self.working_state = WorkingState.from_dict(raw_working_state)
            self.metadata["last_updated"] = datetime.now().isoformat()
            self.metadata["total_turns"] = len(self.turns)

            self._restore_semantic_embeddings_from_session(payload)

            logger.info(
                f"✅ Загружена история из SQLite: {len(self.turns)} оборотов для {self.user_id}"
            )
            return True
        except Exception as exc:
            logger.error(f"❌ Ошибка загрузки из SessionManager: {exc}")
            return False

    def _restore_semantic_embeddings_from_session(self, payload: Dict[str, Any]) -> None:
        """Восстановить semantic embeddings из SQLite в runtime-кеш."""
        if not self.semantic_memory:
            return

        embeddings = payload.get("semantic_embeddings", [])
        if not embeddings:
            return

        turns_by_number = {
            idx: turn for idx, turn in enumerate(payload.get("conversation_turns", []), start=1)
        }

        restored: List[TurnEmbedding] = []
        for item in embeddings:
            turn_number = item.get("turn_number")
            turn_data = turns_by_number.get(turn_number)
            if not turn_data:
                continue

            bot_response = turn_data.get("bot_response") or ""
            restored.append(
                TurnEmbedding(
                    turn_index=turn_number,
                    user_input=turn_data.get("user_input", ""),
                    bot_response_preview=bot_response[:200],
                    user_state=None,
                    concepts=turn_data.get("chunks_used", []),
                    timestamp=turn_data.get("timestamp", ""),
                    embedding=item["embedding"],
                )
            )

        if restored:
            self.semantic_memory.turn_embeddings = restored
    
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
                    "turns": [asdict(turn) for turn in self.turns],
                    # === НОВОЕ: Сохранить summary ===
                    "summary": self.summary,
                    "summary_updated_at": self.summary_updated_at,
                    "working_state": (
                        self.working_state.to_dict() if self.working_state else None
                    ),
                }, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"💾 История сохранена ({len(self.turns)} оборотов)")
        
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения истории: {e}")

        if self.session_manager:
            try:
                self.session_manager.create_session(
                    session_id=self.user_id,
                    user_id=self.user_id,
                    metadata=self.metadata,
                )
                if self.summary:
                    self.session_manager.update_summary(self.user_id, self.summary)
                if self.working_state:
                    self.session_manager.update_working_state(
                        self.user_id,
                        self.working_state.to_dict(),
                    )
            except Exception as exc:
                logger.error(f"❌ Ошибка синхронизации metadata в SessionManager: {exc}")

    def set_working_state(self, working_state: WorkingState) -> None:
        """Обновить рабочее состояние пользователя и синхронизировать хранение."""
        self.working_state = working_state
        if self.session_manager:
            try:
                self.session_manager.update_working_state(
                    self.user_id,
                    working_state.to_dict(),
                )
            except Exception as exc:
                logger.error(f"❌ Ошибка сохранения working_state в SessionManager: {exc}")
        self.save_to_disk()
    
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
        turn_index = len(self.turns)
        logger.debug(f"➕ Добавлен ход #{len(self.turns)}")

        embedding_to_store = None

        # Ограничиваем общее число ходов (авторотация)
        # === НОВОЕ: Добавить эмбеддинг в semantic memory ===
        if self.semantic_memory and config.ENABLE_SEMANTIC_MEMORY:
            try:
                self.semantic_memory.add_turn_embedding(
                    turn_index=turn_index,
                    user_input=user_input,
                    bot_response=bot_response,
                    user_state=user_state,
                    concepts=concepts or [],
                    timestamp=turn.timestamp
                )
                self.semantic_memory.save_to_disk()
                if self.semantic_memory.turn_embeddings:
                    embedding_to_store = self.semantic_memory.turn_embeddings[-1].embedding
            except Exception as e:
                logger.error(f"❌ Ошибка добавления эмбеддинга: {e}")

        self._persist_turn_to_session_storage(
            turn_index=turn_index,
            turn=turn,
            embedding=embedding_to_store,
        )

        # === НОВОЕ: Обновить summary каждые N ходов ===
        if config.ENABLE_CONVERSATION_SUMMARY and config.SUMMARY_UPDATE_INTERVAL > 0:
            if turn_index % config.SUMMARY_UPDATE_INTERVAL == 0:
                self._update_summary()

        max_turns = config.MAX_CONVERSATION_TURNS
        if max_turns and len(self.turns) > max_turns:
            overflow = len(self.turns) - max_turns
            self.turns = self.turns[overflow:]
        
        self.save_to_disk()
        return turn

    def _persist_turn_to_session_storage(
        self,
        turn_index: int,
        turn: ConversationTurn,
        embedding: Optional[object] = None,
    ) -> None:
        """Сохранить ход в SQLite, если SessionManager включён."""
        if not self.session_manager:
            return

        try:
            self.session_manager.save_turn(
                session_id=self.user_id,
                turn_number=turn_index,
                user_input=turn.user_input,
                bot_response=turn.bot_response or "",
                mode="ADAPTIVE",
                timestamp=turn.timestamp,
                chunks_used=turn.concepts,
                user_state=turn.user_state,
                user_feedback=turn.user_feedback,
                user_rating=turn.user_rating,
                embedding=embedding,
            )
        except Exception as exc:
            logger.error(f"❌ Ошибка сохранения хода в SessionManager: {exc}")
    
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
            self._sync_feedback_to_session_storage(turn_index)
            self.save_to_disk()
        else:
            logger.warning(f"⚠️ Некорректный индекс хода: {turn_index}")

    def _sync_feedback_to_session_storage(self, turn_index: int) -> None:
        """Обновить feedback/rating в SQLite для уже сохранённого хода."""
        if not self.session_manager:
            return
        if not (0 <= turn_index < len(self.turns)):
            return

        turn = self.turns[turn_index]
        try:
            self.session_manager.save_turn(
                session_id=self.user_id,
                turn_number=turn_index + 1,
                user_input=turn.user_input,
                bot_response=turn.bot_response or "",
                mode="ADAPTIVE",
                timestamp=turn.timestamp,
                chunks_used=turn.concepts,
                user_state=turn.user_state,
                user_feedback=turn.user_feedback,
                user_rating=turn.user_rating,
            )
        except Exception as exc:
            logger.error(f"❌ Ошибка обновления feedback в SessionManager: {exc}")
    
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

    def get_full_context_for_llm(
        self,
        current_question: str,
        include_semantic: bool = True,
        include_summary: bool = True
    ) -> Dict[str, str]:
        """
        Получить полный контекст для LLM со всеми типами памяти.
        """
        context = {"short_term": "", "semantic": "", "summary": ""}

        context["short_term"] = self.get_context_for_llm(
            n=config.CONVERSATION_HISTORY_DEPTH,
            max_chars=config.MAX_CONTEXT_SIZE
        )

        if include_semantic and self.semantic_memory and config.ENABLE_SEMANTIC_MEMORY:
            try:
                context["semantic"] = self.semantic_memory.get_context_for_llm(
                    query=current_question,
                    max_chars=config.SEMANTIC_MAX_CHARS,
                    top_k=config.SEMANTIC_SEARCH_TOP_K,
                    min_similarity=config.SEMANTIC_MIN_SIMILARITY
                )
            except Exception as e:
                logger.error(f"❌ Ошибка semantic search: {e}")

        if include_summary and config.ENABLE_CONVERSATION_SUMMARY and self.summary:
            context["summary"] = self.summary

        return context

    def get_adaptive_context_for_llm(self, current_question: str) -> Dict[str, str]:
        """
        Адаптивная загрузка контекста в зависимости от длины диалога.
        """
        total_turns = len(self.turns)

        if total_turns <= 5:
            return {
                "short_term": self.get_context_for_llm(n=total_turns),
                "semantic": "",
                "summary": ""
            }
        if total_turns <= 20:
            return self.get_full_context_for_llm(
                current_question,
                include_semantic=True,
                include_summary=False
            )
        return self.get_full_context_for_llm(
            current_question,
            include_semantic=True,
            include_summary=True
        )

    def format_context_for_llm(self, context: Dict[str, str]) -> str:
        """Сформировать единый текстовый контекст для LLM."""
        parts: List[str] = []

        if context.get("summary"):
            parts.append(
                "КРАТКОЕ РЕЗЮМЕ ДИАЛОГА:\n"
                f"{context['summary']}\n\n---\n"
            )

        if context.get("semantic"):
            parts.append(context["semantic"].strip() + "\n---\n")

        if context.get("short_term"):
            parts.append(context["short_term"].strip() + "\n---\n")

        return "".join(parts).strip()

    def get_adaptive_context_text(self, current_question: str) -> str:
        """Получить готовый текст контекста (short-term + semantic + summary)."""
        context = self.get_adaptive_context_for_llm(current_question)
        return self.format_context_for_llm(context)

    def _update_summary(self) -> None:
        """
        Обновить резюме диалога через LLM.
        """
        if len(self.turns) < 5:
            return
        if not config.OPENAI_API_KEY:
            logger.warning("⚠️ OPENAI_API_KEY не установлен — summary не обновляется")
            return

        logger.info(f"📝 Обновляю резюме диалога (ход #{len(self.turns)})...")

        try:
            recent_turns = self.turns[-10:]
            turns_text = ""
            for i, turn in enumerate(recent_turns, 1):
                turns_text += f"\nХод {i}:\n"
                turns_text += f"Пользователь: {turn.user_input}\n"
                response = turn.bot_response or ""
                if len(response) > 200:
                    response = response[:200] + "..."
                turns_text += f"Бот: {response}\n"
                if turn.user_state:
                    turns_text += f"Состояние: {turn.user_state}\n"

            summary_prompt = f"""Создай КРАТКОЕ резюме диалога (максимум {config.SUMMARY_MAX_CHARS} символов, по-русски).

Включи:
- Ключевые темы, которые обсуждались
- Прогресс пользователя в понимании
- Важные инсайты или прорывы (если были)
- Текущий фокус диалога

ДИАЛОГ (последние 10 ходов):
{turns_text}

РЕЗЮМЕ (кратко, одним параграфом, без заголовков):"""

            from .llm_answerer import LLMAnswerer

            answerer = LLMAnswerer()
            if not answerer.client:
                logger.warning("⚠️ LLM клиент недоступен — summary не обновляется")
                return

            response = answerer.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3,
                max_tokens=200
            )

            summary_text = response.choices[0].message.content.strip()
            if len(summary_text) > config.SUMMARY_MAX_CHARS:
                summary_text = summary_text[:config.SUMMARY_MAX_CHARS].rstrip()

            self.summary = summary_text
            self.summary_updated_at = len(self.turns)

            logger.info(f"✅ Резюме обновлено: {len(self.summary)} символов")
            if self.session_manager and self.summary:
                self.session_manager.update_summary(self.user_id, self.summary)
            self.save_to_disk()
        except Exception as e:
            logger.error(f"❌ Ошибка обновления резюме: {e}")

    def clear(self) -> None:
        """Очистить историю диалога и сохранить пустое состояние."""
        self.turns = []
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["total_turns"] = 0

        # === НОВОЕ: Очистить summary ===
        self.summary = None
        self.summary_updated_at = None
        self.working_state = None

        # === НОВОЕ: Очистить semantic memory ===
        if self.semantic_memory:
            self.semantic_memory.clear()

        if self.session_manager:
            self.session_manager.delete_session_data(self.user_id)
            self.session_manager.create_session(
                session_id=self.user_id,
                user_id=self.user_id,
                metadata={"source": "conversation_memory", "reset": True},
            )

        self.save_to_disk()

    def purge_user_data(self) -> None:
        """
        Полностью удалить данные пользователя (GDPR):
        JSON, semantic cache и SQLite-сессию без авто-воссоздания.
        """
        self.turns = []
        self.summary = None
        self.summary_updated_at = None
        self.working_state = None
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["total_turns"] = 0

        if self.semantic_memory:
            self.semantic_memory.clear()

        if self.session_manager:
            self.session_manager.delete_session_data(self.user_id)

        filepath = self.memory_dir / f"{self.user_id}.json"
        if filepath.exists():
            filepath.unlink()
    
    def rebuild_semantic_memory(self) -> None:
        """
        Пересоздать semantic memory на основе текущей истории.
        """
        if not self.semantic_memory:
            logger.warning("⚠️ Semantic memory не включена")
            return
        if not self.turns:
            logger.warning("⚠️ Нет ходов для создания эмбеддингов")
            return

        logger.info(f"🔨 Пересоздаю semantic memory для {len(self.turns)} ходов...")
        turns_data = [
            {
                "user_input": turn.user_input,
                "bot_response": turn.bot_response,
                "user_state": turn.user_state,
                "concepts": turn.concepts,
                "timestamp": turn.timestamp
            }
            for turn in self.turns
        ]
        self.semantic_memory.rebuild_all_embeddings(turns_data)
        logger.info("✅ Semantic memory пересоздана")

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
        
        result = {
            "total_turns": len(self.turns),
            "primary_interests": interests,
            "num_challenges": len(challenges),
            "num_breakthroughs": len(breakthroughs),
            "average_rating": round(avg_rating, 2),
            "user_level": self.metadata.get("user_level", "beginner"),
            "last_interaction": self.turns[-1].timestamp if self.turns else None,
            # === НОВОЕ: Summary данные ===
            "conversation_summary": self.summary,
            "summary_updated_at_turn": self.summary_updated_at,
            "working_state": (
                self.working_state.to_dict() if self.working_state else None
            ),
        }

        if self.semantic_memory:
            result["semantic_memory"] = self.semantic_memory.get_stats()

        return result
    
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
        logger.info(f"[CONV_MEMORY] cache_miss user_id={user_id}")
        memory = ConversationMemory(user_id)
        memory.load_from_disk()
        _memory_instances[user_id] = memory
    else:
        logger.info(
            f"[CONV_MEMORY] cache_hit user_id={user_id} turns={len(_memory_instances[user_id].turns)}"
        )
    
    return _memory_instances[user_id]


