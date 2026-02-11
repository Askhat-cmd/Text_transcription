# bot_agent/conversation_memory.py
"""
Conversation Memory Module (Phase 4.2)
======================================

Р”РѕР»РіРѕСЃСЂРѕС‡РЅР°СЏ РїР°РјСЏС‚СЊ РґРёР°Р»РѕРіР° СЃ РїРµСЂСЃРёСЃС‚РµРЅС‚РЅС‹Рј С…СЂР°РЅРµРЅРёРµРј.
РћС‚СЃР»РµР¶РёРІР°РЅРёРµ РёРЅС‚РµСЂРµСЃРѕРІ, РІС‹Р·РѕРІРѕРІ Рё РїСЂРѕСЂС‹РІРѕРІ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
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
    """РћРґРёРЅ С…РѕРґ РІ РґРёР°Р»РѕРіРµ"""
    timestamp: str
    user_input: str
    user_state: Optional[str] = None  # СЃРѕСЃС‚РѕСЏРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
    bot_response: Optional[str] = None
    blocks_used: int = 0
    concepts: List[str] = field(default_factory=list)
    user_feedback: Optional[str] = None  # positive/negative/neutral
    user_rating: Optional[int] = None  # 1-5


class ConversationMemory:
    """
    РҐСЂР°РЅРёС‚ Рё СѓРїСЂР°РІР»СЏРµС‚ РёСЃС‚РѕСЂРёРµР№ РґРёР°Р»РѕРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
    РџРѕРґРґРµСЂР¶РёРІР°РµС‚ РїРµСЂСЃРёСЃС‚РµРЅС‚РЅРѕРµ С…СЂР°РЅРёР»РёС‰Рµ.
    """
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.turns: List[ConversationTurn] = []
        self.metadata: Dict = {
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_turns": 0,
            "user_level": "beginner",
            "primary_interests": [],  # С‚РµРјС‹, РєРѕС‚РѕСЂС‹Рµ РёРЅС‚РµСЂРµСЃСѓСЋС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
            "challenges": [],  # СЃ С‡РµРј Р±РѕСЂРµС‚СЃСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ
            "breakthroughs": []  # РёРЅСЃР°Р№С‚С‹ Рё РїСЂРѕСЂС‹РІС‹
        }
        self.memory_dir = config.CACHE_DIR / "conversations"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # === РќРћР’РћР•: Semantic Memory ===
        self.semantic_memory: Optional[SemanticMemory] = None
        if config.ENABLE_SEMANTIC_MEMORY:
            self.semantic_memory = get_semantic_memory(user_id)

        # === РќРћР’РћР•: Conversation Summary ===
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
                logger.error(f"SessionManager init error: {exc}")
    
    def load_from_disk(self) -> bool:
        """
        Р—Р°РіСЂСѓР·РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° СЃ РґРёСЃРєР°.
        
        Returns:
            True РµСЃР»Рё Р·Р°РіСЂСѓР·РєР° СѓСЃРїРµС€РЅР°, False РµСЃР»Рё С„Р°Р№Р» РЅРµ РЅР°Р№РґРµРЅ
        """
        logger.info(f"[MEMORY] load_history start user_id={self.user_id}")
        if self._load_from_session_storage():
            return True

        filepath = self.memory_dir / f"{self.user_id}.json"
        
        if not filepath.exists():
            logger.debug(f"рџ“‹ РќРѕРІР°СЏ РёСЃС‚РѕСЂРёСЏ РґРёР°Р»РѕРіР° РґР»СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ {self.user_id}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.metadata = data.get("metadata", self.metadata)
            self.turns = [
                ConversationTurn(**turn_data)
                for turn_data in data.get("turns", [])
            ]

            # === РќРћР’РћР•: Р—Р°РіСЂСѓР·РёС‚СЊ summary ===
            self.summary = data.get("summary")
            self.summary_updated_at = data.get("summary_updated_at")
            raw_working_state = data.get("working_state")
            if isinstance(raw_working_state, dict):
                self.working_state = WorkingState.from_dict(raw_working_state)
            
            logger.info(f"[MEMORY] loaded from json turns={len(self.turns)} user_id={self.user_id}")
            return True
        
        except Exception as e:
            logger.error(f"[MEMORY] load_history failed user_id={self.user_id}: {e}", exc_info=True)
            return False

    def _load_from_session_storage(self) -> bool:
        """Р—Р°РіСЂСѓР·РёС‚СЊ СЃРѕСЃС‚РѕСЏРЅРёРµ РёР· SQLite SessionManager."""
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
                f"[MEMORY] loaded from sqlite turns={len(self.turns)} user_id={self.user_id}"
            )
            return True
        except Exception as exc:
            logger.error(f"[MEMORY] sqlite load failed user_id={self.user_id}: {exc}", exc_info=True)
            return False

    def _restore_semantic_embeddings_from_session(self, payload: Dict[str, Any]) -> None:
        """Р’РѕСЃСЃС‚Р°РЅРѕРІРёС‚СЊ semantic embeddings РёР· SQLite РІ runtime-РєРµС€."""
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
        РЎРѕС…СЂР°РЅРёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° РЅР° РґРёСЃРє.
        """
        filepath = self.memory_dir / f"{self.user_id}.json"
        
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["total_turns"] = len(self.turns)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "metadata": self.metadata,
                    "turns": [asdict(turn) for turn in self.turns],
                    # === РќРћР’РћР•: РЎРѕС…СЂР°РЅРёС‚СЊ summary ===
                    "summary": self.summary,
                    "summary_updated_at": self.summary_updated_at,
                    "working_state": (
                        self.working_state.to_dict() if self.working_state else None
                    ),
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[MEMORY] saved turns={len(self.turns)} user_id={self.user_id}")
        
        except Exception as e:
            logger.error(f"[MEMORY] save failed user_id={self.user_id}: {e}", exc_info=True)

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
                logger.error(f"SessionManager metadata sync error: {exc}")

    def set_working_state(self, working_state: WorkingState) -> None:
        """РћР±РЅРѕРІРёС‚СЊ СЂР°Р±РѕС‡РµРµ СЃРѕСЃС‚РѕСЏРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ Рё СЃРёРЅС…СЂРѕРЅРёР·РёСЂРѕРІР°С‚СЊ С…СЂР°РЅРµРЅРёРµ."""
        self.working_state = working_state
        if self.session_manager:
            try:
                self.session_manager.update_working_state(
                    self.user_id,
                    working_state.to_dict(),
                )
            except Exception as exc:
                logger.error(f"SessionManager working_state save error: {exc}")
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
        Р”РѕР±Р°РІРёС‚СЊ С…РѕРґ РІ РёСЃС‚РѕСЂРёСЋ.
        
        Args:
            user_input: Р’РѕРїСЂРѕСЃ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
            bot_response: РћС‚РІРµС‚ Р±РѕС‚Р°
            user_state: РЎРѕСЃС‚РѕСЏРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (РёР· StateClassifier)
            blocks_used: РљРѕР»РёС‡РµСЃС‚РІРѕ РёСЃРїРѕР»СЊР·РѕРІР°РЅРЅС‹С… Р±Р»РѕРєРѕРІ
            concepts: РЎРїРёСЃРѕРє РєРѕРЅС†РµРїС‚РѕРІ РІ РѕС‚РІРµС‚Рµ
            
        Returns:
            РЎРѕР·РґР°РЅРЅС‹Р№ ConversationTurn
        """
        logger.info(f"[MEMORY] add_turn user_id={self.user_id} turns_before={len(self.turns)}")
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
        logger.info(f"[MEMORY] turn_added user_id={self.user_id} turn_index={turn_index}")

        embedding_to_store = None

        # РћРіСЂР°РЅРёС‡РёРІР°РµРј РѕР±С‰РµРµ С‡РёСЃР»Рѕ С…РѕРґРѕРІ (Р°РІС‚РѕСЂРѕС‚Р°С†РёСЏ)
        # === РќРћР’РћР•: Р”РѕР±Р°РІРёС‚СЊ СЌРјР±РµРґРґРёРЅРі РІ semantic memory ===
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
                logger.error(f"[MEMORY] semantic embedding add failed user_id={self.user_id}: {e}", exc_info=True)

        self._persist_turn_to_session_storage(
            turn_index=turn_index,
            turn=turn,
            embedding=embedding_to_store,
        )

        # === РќРћР’РћР•: РћР±РЅРѕРІРёС‚СЊ summary РєР°Р¶РґС‹Рµ N С…РѕРґРѕРІ ===
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
        """РЎРѕС…СЂР°РЅРёС‚СЊ С…РѕРґ РІ SQLite, РµСЃР»Рё SessionManager РІРєР»СЋС‡С‘РЅ."""
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
            logger.error(f"[MEMORY] sqlite save_turn failed user_id={self.user_id}: {exc}", exc_info=True)
    
    def add_feedback(
        self,
        turn_index: int,
        feedback: str,  # positive/negative/neutral
        rating: Optional[int] = None  # 1-5
    ) -> None:
        """
        Р”РѕР±Р°РІРёС‚СЊ РѕР±СЂР°С‚РЅСѓСЋ СЃРІСЏР·СЊ Рє С…РѕРґСѓ.
        
        Args:
            turn_index: РРЅРґРµРєСЃ С…РѕРґР° (0-based) РёР»Рё -1 РґР»СЏ РїРѕСЃР»РµРґРЅРµРіРѕ
            feedback: РўРёРї РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·Рё (positive/negative/neutral)
            rating: Р РµР№С‚РёРЅРі РѕС‚ 1 РґРѕ 5
        """
        if turn_index == -1:
            turn_index = len(self.turns) - 1
            
        if 0 <= turn_index < len(self.turns):
            self.turns[turn_index].user_feedback = feedback
            self.turns[turn_index].user_rating = rating
            
            logger.debug(f"рџ‘Ќ РћР±СЂР°С‚РЅР°СЏ СЃРІСЏР·СЊ РґРѕР±Р°РІР»РµРЅР°: {feedback} (СЂРµР№С‚РёРЅРі: {rating})")
            self._sync_feedback_to_session_storage(turn_index)
            self.save_to_disk()
        else:
            logger.warning(f"вљ пёЏ РќРµРєРѕСЂСЂРµРєС‚РЅС‹Р№ РёРЅРґРµРєСЃ С…РѕРґР°: {turn_index}")

    def _sync_feedback_to_session_storage(self, turn_index: int) -> None:
        """РћР±РЅРѕРІРёС‚СЊ feedback/rating РІ SQLite РґР»СЏ СѓР¶Рµ СЃРѕС…СЂР°РЅС‘РЅРЅРѕРіРѕ С…РѕРґР°."""
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
            logger.error(f"SessionManager feedback update error: {exc}")
    
    def get_last_turns(self, n: int = 5) -> List[ConversationTurn]:
        """
        РџРѕР»СѓС‡РёС‚СЊ РїРѕСЃР»РµРґРЅРёРµ N РѕР±РѕСЂРѕС‚РѕРІ.
        
        Args:
            n: РљРѕР»РёС‡РµСЃС‚РІРѕ РїРѕСЃР»РµРґРЅРёС… С…РѕРґРѕРІ
            
        Returns:
            РЎРїРёСЃРѕРє ConversationTurn
        """
        return self.turns[-n:] if self.turns else []
    
    def get_context_for_llm(self, n: int = 3, max_chars: Optional[int] = None) -> str:
        """
        РџРѕР»СѓС‡РёС‚СЊ РєРѕРЅС‚РµРєСЃС‚ РїРѕСЃР»РµРґРЅРёС… РѕР±РѕСЂРѕС‚РѕРІ РґР»СЏ LLM.
        РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РґР»СЏ СѓС‡РµС‚Р° РёСЃС‚РѕСЂРёРё РІ РѕС‚РІРµС‚Рµ.
        
        Args:
            n: РљРѕР»РёС‡РµСЃС‚РІРѕ РїРѕСЃР»РµРґРЅРёС… С…РѕРґРѕРІ РґР»СЏ РєРѕРЅС‚РµРєСЃС‚Р°
            max_chars: РњР°РєСЃРёРјР°Р»СЊРЅС‹Р№ СЂР°Р·РјРµСЂ РєРѕРЅС‚РµРєСЃС‚Р° (СЃРёРјРІРѕР»С‹)
            
        Returns:
            РћС‚С„РѕСЂРјР°С‚РёСЂРѕРІР°РЅРЅР°СЏ СЃС‚СЂРѕРєР° СЃ РёСЃС‚РѕСЂРёРµР№
        """
        last_turns = self.get_last_turns(n)
        
        if not last_turns:
            return ""

        if max_chars is None:
            max_chars = config.MAX_CONTEXT_SIZE
        
        context = "РРЎРўРћР РРЇ Р”РРђР›РћР“Рђ (РїРѕСЃР»РµРґРЅРёРµ РѕР±РѕСЂРѕС‚С‹):\n\n"

        # Р”РѕР±Р°РІР»СЏРµРј РїРѕСЃР»РµРґРЅРёРµ С…РѕРґС‹ СЃ СѓС‡РµС‚РѕРј Р»РёРјРёС‚Р°
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
                f"РћР±РјРµРЅ #{turn_num}:\n"
                f"  РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ: {turn.user_input}\n"
                f"  Р‘РѕС‚: {response_preview}\n"
            )
            if turn.user_state:
                entry += f"  РЎРѕСЃС‚РѕСЏРЅРёРµ: {turn.user_state}\n"
            entry += "\n"

            # РџСЂРѕРІРµСЂСЏРµРј Р»РёРјРёС‚
            if max_chars and current_len + len(entry) > max_chars:
                if not entries:
                    # Р•СЃР»Рё РґР°Р¶Рµ РѕРґРёРЅ С…РѕРґ СЃР»РёС€РєРѕРј Р±РѕР»СЊС€РѕР№, РѕР±СЂРµР¶РµРј РµРіРѕ
                    allowed = max(0, max_chars - current_len)
                    entry = (entry[:max(0, allowed - 3)] + "...") if allowed > 0 else ""
                    if entry:
                        entries.append(entry)
                break

            entries.append(entry)
            current_len += len(entry)

        # Р’РѕР·РІСЂР°С‰Р°РµРј РІ С…СЂРѕРЅРѕР»РѕРіРёС‡РµСЃРєРѕРј РїРѕСЂСЏРґРєРµ
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
        РџРѕР»СѓС‡РёС‚СЊ РїРѕР»РЅС‹Р№ РєРѕРЅС‚РµРєСЃС‚ РґР»СЏ LLM СЃРѕ РІСЃРµРјРё С‚РёРїР°РјРё РїР°РјСЏС‚Рё.
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
                logger.error(f"Semantic search error: {e}")

        if include_summary and config.ENABLE_CONVERSATION_SUMMARY and self.summary:
            context["summary"] = self.summary

        return context

    def get_adaptive_context_for_llm(self, current_question: str) -> Dict[str, str]:
        """
        РђРґР°РїС‚РёРІРЅР°СЏ Р·Р°РіСЂСѓР·РєР° РєРѕРЅС‚РµРєСЃС‚Р° РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ РґР»РёРЅС‹ РґРёР°Р»РѕРіР°.
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
        """РЎС„РѕСЂРјРёСЂРѕРІР°С‚СЊ РµРґРёРЅС‹Р№ С‚РµРєСЃС‚РѕРІС‹Р№ РєРѕРЅС‚РµРєСЃС‚ РґР»СЏ LLM."""
        parts: List[str] = []

        if context.get("summary"):
            parts.append(
                "РљР РђРўРљРћР• Р Р•Р—Р®РњР• Р”РРђР›РћР“Рђ:\n"
                f"{context['summary']}\n\n---\n"
            )

        if context.get("semantic"):
            parts.append(context["semantic"].strip() + "\n---\n")

        if context.get("short_term"):
            parts.append(context["short_term"].strip() + "\n---\n")

        return "".join(parts).strip()

    def get_adaptive_context_text(self, current_question: str) -> str:
        """РџРѕР»СѓС‡РёС‚СЊ РіРѕС‚РѕРІС‹Р№ С‚РµРєСЃС‚ РєРѕРЅС‚РµРєСЃС‚Р° (short-term + semantic + summary)."""
        context = self.get_adaptive_context_for_llm(current_question)
        return self.format_context_for_llm(context)

    def _update_summary(self) -> None:
        """
        РћР±РЅРѕРІРёС‚СЊ СЂРµР·СЋРјРµ РґРёР°Р»РѕРіР° С‡РµСЂРµР· LLM.
        """
        if len(self.turns) < 5:
            return
        if not config.OPENAI_API_KEY:
            logger.warning("вљ пёЏ OPENAI_API_KEY РЅРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅ вЂ” summary РЅРµ РѕР±РЅРѕРІР»СЏРµС‚СЃСЏ")
            return

        logger.info(f"Updating conversation summary (turn #{len(self.turns)})...")

        try:
            recent_turns = self.turns[-10:]
            turns_text = ""
            for i, turn in enumerate(recent_turns, 1):
                turns_text += f"\nРҐРѕРґ {i}:\n"
                turns_text += f"РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ: {turn.user_input}\n"
                response = turn.bot_response or ""
                if len(response) > 200:
                    response = response[:200] + "..."
                turns_text += f"Р‘РѕС‚: {response}\n"
                if turn.user_state:
                    turns_text += f"РЎРѕСЃС‚РѕСЏРЅРёРµ: {turn.user_state}\n"

            summary_prompt = f"""РЎРѕР·РґР°Р№ РљР РђРўРљРћР• СЂРµР·СЋРјРµ РґРёР°Р»РѕРіР° (РјР°РєСЃРёРјСѓРј {config.SUMMARY_MAX_CHARS} СЃРёРјРІРѕР»РѕРІ, РїРѕ-СЂСѓСЃСЃРєРё).

Р’РєР»СЋС‡Рё:
- РљР»СЋС‡РµРІС‹Рµ С‚РµРјС‹, РєРѕС‚РѕСЂС‹Рµ РѕР±СЃСѓР¶РґР°Р»РёСЃСЊ
- РџСЂРѕРіСЂРµСЃСЃ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РІ РїРѕРЅРёРјР°РЅРёРё
- Р’Р°Р¶РЅС‹Рµ РёРЅСЃР°Р№С‚С‹ РёР»Рё РїСЂРѕСЂС‹РІС‹ (РµСЃР»Рё Р±С‹Р»Рё)
- РўРµРєСѓС‰РёР№ С„РѕРєСѓСЃ РґРёР°Р»РѕРіР°

Р”РРђР›РћР“ (РїРѕСЃР»РµРґРЅРёРµ 10 С…РѕРґРѕРІ):
{turns_text}

Р Р•Р—Р®РњР• (РєСЂР°С‚РєРѕ, РѕРґРЅРёРј РїР°СЂР°РіСЂР°С„РѕРј, Р±РµР· Р·Р°РіРѕР»РѕРІРєРѕРІ):"""

            from .llm_answerer import LLMAnswerer

            answerer = LLMAnswerer()
            if not answerer.client:
                logger.warning("вљ пёЏ LLM РєР»РёРµРЅС‚ РЅРµРґРѕСЃС‚СѓРїРµРЅ вЂ” summary РЅРµ РѕР±РЅРѕРІР»СЏРµС‚СЃСЏ")
                return

            response = answerer.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": summary_prompt}],
                **answerer._temperature_kwargs(config.LLM_MODEL, 0.3),
                **answerer._token_limit_kwargs(config.LLM_MODEL, 200)
            )

            summary_text = response.choices[0].message.content.strip()
            if len(summary_text) > config.SUMMARY_MAX_CHARS:
                summary_text = summary_text[:config.SUMMARY_MAX_CHARS].rstrip()

            self.summary = summary_text
            self.summary_updated_at = len(self.turns)

            logger.info(f"Summary updated: {len(self.summary)} chars")
            if self.session_manager and self.summary:
                self.session_manager.update_summary(self.user_id, self.summary)
            self.save_to_disk()
        except Exception as e:
            logger.error(f"Summary update error: {e}")

    def clear(self) -> None:
        """РћС‡РёСЃС‚РёС‚СЊ РёСЃС‚РѕСЂРёСЋ РґРёР°Р»РѕРіР° Рё СЃРѕС…СЂР°РЅРёС‚СЊ РїСѓСЃС‚РѕРµ СЃРѕСЃС‚РѕСЏРЅРёРµ."""
        logger.info(f"[MEMORY] clear_history user_id={self.user_id}")
        self.turns = []
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["total_turns"] = 0

        # === РќРћР’РћР•: РћС‡РёСЃС‚РёС‚СЊ summary ===
        self.summary = None
        self.summary_updated_at = None
        self.working_state = None

        # === РќРћР’РћР•: РћС‡РёСЃС‚РёС‚СЊ semantic memory ===
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
        logger.info(f"[MEMORY] history_cleared user_id={self.user_id}")

    def purge_user_data(self) -> None:
        """
        РџРѕР»РЅРѕСЃС‚СЊСЋ СѓРґР°Р»РёС‚СЊ РґР°РЅРЅС‹Рµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (GDPR):
        JSON, semantic cache Рё SQLite-СЃРµСЃСЃРёСЋ Р±РµР· Р°РІС‚Рѕ-РІРѕСЃСЃРѕР·РґР°РЅРёСЏ.
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
        РџРµСЂРµСЃРѕР·РґР°С‚СЊ semantic memory РЅР° РѕСЃРЅРѕРІРµ С‚РµРєСѓС‰РµР№ РёСЃС‚РѕСЂРёРё.
        """
        if not self.semantic_memory:
            logger.warning("вљ пёЏ Semantic memory РЅРµ РІРєР»СЋС‡РµРЅР°")
            return
        if not self.turns:
            logger.warning("вљ пёЏ РќРµС‚ С…РѕРґРѕРІ РґР»СЏ СЃРѕР·РґР°РЅРёСЏ СЌРјР±РµРґРґРёРЅРіРѕРІ")
            return

        logger.info(f"рџ”Ё РџРµСЂРµСЃРѕР·РґР°СЋ semantic memory РґР»СЏ {len(self.turns)} С…РѕРґРѕРІ...")
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
        logger.info("Semantic memory rebuilt")

    def get_primary_interests(self) -> List[str]:
        """
        РџРѕР»СѓС‡РёС‚СЊ РѕСЃРЅРѕРІРЅС‹Рµ РёРЅС‚РµСЂРµСЃС‹ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РЅР° РѕСЃРЅРѕРІРµ РёСЃС‚РѕСЂРёРё.
        РЎРѕСЂС‚РёСЂРѕРІРєР° РїРѕ С‡Р°СЃС‚РѕС‚Рµ СѓРїРѕРјРёРЅР°РЅРёСЏ РєРѕРЅС†РµРїС‚РѕРІ.
        
        Returns:
            РЎРїРёСЃРѕРє С‚РѕРї-5 РєРѕРЅС†РµРїС‚РѕРІ
        """
        interests: Dict[str, int] = {}
        
        for turn in self.turns:
            for concept in turn.concepts:
                interests[concept] = interests.get(concept, 0) + 1
        
        # РЎРѕСЂС‚РёСЂСѓРµРј РїРѕ С‡Р°СЃС‚РѕС‚Рµ
        sorted_interests = sorted(
            interests.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [concept for concept, _ in sorted_interests[:5]]
    
    def get_challenges(self) -> List[Dict]:
        """
        РџРѕР»СѓС‡РёС‚СЊ РѕСЃРЅРѕРІРЅС‹Рµ РІС‹Р·РѕРІС‹ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ (РѕС‚СЂРёС†Р°С‚РµР»СЊРЅР°СЏ РѕР±СЂР°С‚РЅР°СЏ СЃРІСЏР·СЊ).
        
        Returns:
            РЎРїРёСЃРѕРє С…РѕРґРѕРІ СЃ РЅРµРіР°С‚РёРІРЅРѕР№ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·СЊСЋ
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
        РџРѕР»СѓС‡РёС‚СЊ РёРЅСЃР°Р№С‚С‹ Рё РїСЂРѕСЂС‹РІС‹ (РїРѕР»РѕР¶РёС‚РµР»СЊРЅР°СЏ РѕР±СЂР°С‚РЅР°СЏ СЃРІСЏР·СЊ СЃ РІС‹СЃРѕРєРёРј СЂРµР№С‚РёРЅРіРѕРј).
        
        Returns:
            РЎРїРёСЃРѕРє С…РѕРґРѕРІ СЃ РїРѕР»РѕР¶РёС‚РµР»СЊРЅРѕР№ РѕР±СЂР°С‚РЅРѕР№ СЃРІСЏР·СЊСЋ Рё СЂРµР№С‚РёРЅРіРѕРј >= 4
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
        РџРѕР»СѓС‡РёС‚СЊ РєСЂР°С‚РєРѕРµ СЂРµР·СЋРјРµ РёСЃС‚РѕСЂРёРё РґРёР°Р»РѕРіР°.
        
        Returns:
            Dict СЃ РєР»СЋС‡РµРІС‹РјРё РјРµС‚СЂРёРєР°РјРё
        """
        interests = self.get_primary_interests()
        challenges = self.get_challenges()
        breakthroughs = self.get_breakthroughs()
        
        # РЎСЂРµРґРЅРёР№ СЂРµР№С‚РёРЅРі
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
            # === РќРћР’РћР•: Summary РґР°РЅРЅС‹Рµ ===
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
        РЈСЃС‚Р°РЅРѕРІРёС‚СЊ СѓСЂРѕРІРµРЅСЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
        
        Args:
            level: beginner / intermediate / advanced
        """
        self.metadata["user_level"] = level
        self.save_to_disk()


# Р“Р»РѕР±Р°Р»СЊРЅС‹Р№ РєСЌС€ РёРЅСЃС‚Р°РЅСЃРѕРІ РїР°РјСЏС‚Рё
_memory_instances: Dict[str, ConversationMemory] = {}


def get_conversation_memory(user_id: str = "default") -> ConversationMemory:
    """
    РџРѕР»СѓС‡РёС‚СЊ СЌРєР·РµРјРїР»СЏСЂ РїР°РјСЏС‚Рё РґРёР°Р»РѕРіР° РґР»СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
    РСЃРїРѕР»СЊР·СѓРµС‚ РєСЌС€ РґР»СЏ РѕРїС‚РёРјРёР·Р°С†РёРё.
    
    Args:
        user_id: ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
        
    Returns:
        ConversationMemory РґР»СЏ РґР°РЅРЅРѕРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
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




