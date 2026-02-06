# bot_agent/semantic_memory.py
"""
Semantic Memory Module
======================

Семантический поиск по истории диалога с использованием эмбеддингов.
Позволяет находить релевантные прошлые обмены по смыслу, а не по хронологии.
"""

import logging
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class TurnEmbedding:
    """Эмбеддинг одного хода диалога."""

    turn_index: int
    user_input: str
    bot_response_preview: str
    user_state: Optional[str]
    concepts: List[str]
    timestamp: str
    embedding: np.ndarray


class SemanticMemory:
    """
    Семантический поиск по истории диалога.

    Использует sentence-transformers для создания векторных представлений
    прошлых обменов и семантического поиска.
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.turn_embeddings: List[TurnEmbedding] = []

        self._model = None
        self._model_loaded = False

        self.cache_dir = config.CACHE_DIR / "semantic_memory"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.embeddings_file = self.cache_dir / f"{user_id}_embeddings.npz"
        self.metadata_file = self.cache_dir / f"{user_id}_metadata.json"

        logger.debug(f"📦 SemanticMemory создан для пользователя: {user_id}")

    @property
    def model(self):
        """Lazy loading модели эмбеддингов."""
        if not self._model_loaded:
            self._load_model()
        return self._model

    def _load_model(self) -> None:
        """Загрузить модель sentence-transformers."""
        try:
            from sentence_transformers import SentenceTransformer

            model_name = config.EMBEDDING_MODEL
            logger.info(f"🤖 Загружаю модель эмбеддингов: {model_name}")

            self._model = SentenceTransformer(model_name)
            self._model_loaded = True

            logger.info("✅ Модель эмбеддингов загружена")
        except ImportError as exc:
            logger.error(
                "❌ sentence-transformers не установлен. "
                "Установите: pip install sentence-transformers"
            )
            raise exc
        except Exception as exc:
            logger.error(f"❌ Ошибка загрузки модели: {exc}")
            raise

    def add_turn_embedding(
        self,
        turn_index: int,
        user_input: str,
        bot_response: Optional[str],
        user_state: Optional[str],
        concepts: List[str],
        timestamp: str,
    ) -> None:
        """
        Создать и сохранить эмбеддинг для хода.

        Args:
            turn_index: Индекс хода (начиная с 1)
            user_input: Вопрос пользователя
            bot_response: Ответ бота
            user_state: Состояние пользователя
            concepts: Список концептов
            timestamp: Временная метка
        """
        response_preview = bot_response[:200] if bot_response else ""
        text_to_embed = f"{user_input} {response_preview}"

        try:
            embedding = self.model.encode(
                text_to_embed,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except Exception as exc:
            logger.error(f"❌ Ошибка создания эмбеддинга: {exc}")
            return

        turn_emb = TurnEmbedding(
            turn_index=turn_index,
            user_input=user_input,
            bot_response_preview=response_preview,
            user_state=user_state,
            concepts=concepts,
            timestamp=timestamp,
            embedding=embedding,
        )
        self.turn_embeddings.append(turn_emb)
        logger.debug(f"➕ Эмбеддинг добавлен для хода #{turn_index}")

    def search_similar_turns(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.7,
        exclude_last_n: int = 5,
    ) -> List[Tuple[TurnEmbedding, float]]:
        """
        Найти похожие прошлые обмены по семантике.

        Args:
            query: Текущий вопрос пользователя
            top_k: Количество результатов
            min_similarity: Минимальное косинусное сходство (0-1)
            exclude_last_n: Исключить последние N ходов (они уже в short-term)
        """
        if not self.turn_embeddings:
            logger.debug("🔍 Нет эмбеддингов для поиска")
            return []

        try:
            query_embedding = self.model.encode(
                query,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
        except Exception as exc:
            logger.error(f"❌ Ошибка создания эмбеддинга запроса: {exc}")
            return []

        search_pool = (
            self.turn_embeddings[:-exclude_last_n]
            if exclude_last_n > 0
            else self.turn_embeddings
        )

        similarities: List[Tuple[TurnEmbedding, float]] = []
        for turn_emb in search_pool:
            similarity = self._cosine_similarity(query_embedding, turn_emb.embedding)
            if similarity >= min_similarity:
                similarities.append((turn_emb, float(similarity)))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def get_context_for_llm(
        self,
        query: str,
        max_chars: int = 1000,
        top_k: int = 3,
        min_similarity: float = 0.7,
    ) -> str:
        """
        Получить отформатированный контекст релевантных прошлых обменов.
        """
        similar = self.search_similar_turns(
            query=query,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        if not similar:
            return ""

        context = "РЕЛЕВАНТНЫЕ ПРОШЛЫЕ ОБМЕНЫ:\n\n"
        current_len = len(context)

        for turn_emb, score in similar:
            entry = (
                f"[Сходство: {score:.2f}] Обмен #{turn_emb.turn_index}:\n"
                f"  Пользователь: {turn_emb.user_input}\n"
                f"  Бот: {turn_emb.bot_response_preview}"
            )
            if len(turn_emb.bot_response_preview) == 200:
                entry += "..."
            entry += "\n"

            if turn_emb.user_state:
                entry += f"  Состояние: {turn_emb.user_state}\n"
            if turn_emb.concepts:
                entry += f"  Концепты: {', '.join(turn_emb.concepts[:3])}\n"
            entry += "\n"

            if current_len + len(entry) > max_chars:
                if current_len > len("РЕЛЕВАНТНЫЕ ПРОШЛЫЕ ОБМЕНЫ:\n\n"):
                    break
                allowed = max_chars - current_len
                entry = entry[:max(0, allowed - 3)] + "..."
                if entry:
                    context += entry
                break

            context += entry
            current_len += len(entry)

        return context

    @staticmethod
    def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Косинусное сходство между двумя векторами."""
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    def save_to_disk(self) -> None:
        """Сохранить эмбеддинги и метаданные на диск."""
        if not self.turn_embeddings:
            logger.debug("⚠️ Нет эмбеддингов для сохранения")
            return

        try:
            embeddings_array = np.array(
                [turn_emb.embedding for turn_emb in self.turn_embeddings]
            )
            np.savez_compressed(self.embeddings_file, embeddings=embeddings_array)

            metadata = [
                {
                    "turn_index": turn_emb.turn_index,
                    "user_input": turn_emb.user_input,
                    "bot_response_preview": turn_emb.bot_response_preview,
                    "user_state": turn_emb.user_state,
                    "concepts": turn_emb.concepts,
                    "timestamp": turn_emb.timestamp,
                }
                for turn_emb in self.turn_embeddings
            ]

            with open(self.metadata_file, "w", encoding="utf-8") as file:
                json.dump(metadata, file, ensure_ascii=False, indent=2)

            logger.debug(
                f"💾 Semantic memory сохранена: {len(self.turn_embeddings)} эмбеддингов"
            )
        except Exception as exc:
            logger.error(f"❌ Ошибка сохранения semantic memory: {exc}")

    def load_from_disk(self) -> bool:
        """
        Загрузить эмбеддинги с диска.

        Returns:
            True если загрузка успешна, False если файлы не найдены
        """
        if not self.embeddings_file.exists() or not self.metadata_file.exists():
            logger.debug(f"📋 Новая semantic memory для пользователя {self.user_id}")
            return False

        try:
            data = np.load(self.embeddings_file)
            embeddings_array = data["embeddings"]

            with open(self.metadata_file, "r", encoding="utf-8") as file:
                metadata_list = json.load(file)

            self.turn_embeddings = []
            for i, meta in enumerate(metadata_list):
                self.turn_embeddings.append(
                    TurnEmbedding(
                        turn_index=meta["turn_index"],
                        user_input=meta["user_input"],
                        bot_response_preview=meta["bot_response_preview"],
                        user_state=meta.get("user_state"),
                        concepts=meta.get("concepts", []),
                        timestamp=meta["timestamp"],
                        embedding=embeddings_array[i],
                    )
                )

            logger.info(
                f"✅ Semantic memory загружена: {len(self.turn_embeddings)} эмбеддингов"
            )
            return True
        except Exception as exc:
            logger.error(f"❌ Ошибка загрузки semantic memory: {exc}")
            return False

    def rebuild_all_embeddings(self, turns_data: List[Dict]) -> None:
        """
        Пересоздать все эмбеддинги batch'ем.
        """
        if not turns_data:
            return

        logger.info(f"🔨 Пересоздаю {len(turns_data)} эмбеддингов...")

        try:
            texts: List[str] = []
            for turn in turns_data:
                response_preview = (
                    turn.get("bot_response", "")[:200] if turn.get("bot_response") else ""
                )
                texts.append(f"{turn['user_input']} {response_preview}")

            embeddings = self.model.encode(
                texts,
                batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True,
            )

            self.turn_embeddings = []
            for i, turn in enumerate(turns_data):
                response_preview = (
                    turn.get("bot_response", "")[:200] if turn.get("bot_response") else ""
                )
                self.turn_embeddings.append(
                    TurnEmbedding(
                        turn_index=i + 1,
                        user_input=turn["user_input"],
                        bot_response_preview=response_preview,
                        user_state=turn.get("user_state"),
                        concepts=turn.get("concepts", []),
                        timestamp=turn.get("timestamp", ""),
                        embedding=embeddings[i],
                    )
                )

            self.save_to_disk()
            logger.info(f"✅ Эмбеддинги пересозданы: {len(self.turn_embeddings)}")
        except Exception as exc:
            logger.error(f"❌ Ошибка пересоздания эмбеддингов: {exc}")

    def clear(self) -> None:
        """Очистить semantic memory."""
        self.turn_embeddings = []
        if self.embeddings_file.exists():
            self.embeddings_file.unlink()
        if self.metadata_file.exists():
            self.metadata_file.unlink()
        logger.info("🗑️ Semantic memory очищена")

    def get_stats(self) -> Dict:
        """Получить статистику semantic memory."""
        return {
            "total_embeddings": len(self.turn_embeddings),
            "model_loaded": self._model_loaded,
            "model_name": config.EMBEDDING_MODEL,
            "cache_dir": str(self.cache_dir),
            "embeddings_size_mb": (
                self.embeddings_file.stat().st_size / (1024 * 1024)
                if self.embeddings_file.exists()
                else 0
            ),
        }


_semantic_memory_instances: Dict[str, SemanticMemory] = {}


def get_semantic_memory(user_id: str = "default") -> SemanticMemory:
    """
    Получить экземпляр semantic memory для пользователя (singleton).
    """
    if user_id not in _semantic_memory_instances:
        semantic_mem = SemanticMemory(user_id)
        semantic_mem.load_from_disk()
        _semantic_memory_instances[user_id] = semantic_mem
    return _semantic_memory_instances[user_id]

