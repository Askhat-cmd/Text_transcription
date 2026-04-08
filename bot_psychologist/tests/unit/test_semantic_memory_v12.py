from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.config import config
from bot_agent.semantic_memory import SemanticMemory, TurnEmbedding


class _DummyEmbeddingModel:
    @staticmethod
    def embed_query(_text: str):
        return np.array([1.0, 0.0], dtype=np.float32)

    @staticmethod
    def embed_passages(texts):
        return [np.array([1.0, 0.0], dtype=np.float32) for _ in texts]


def _embedding(turn_index: int, vec) -> TurnEmbedding:
    return TurnEmbedding(
        turn_index=turn_index,
        user_input=f"user-{turn_index}",
        bot_response_preview=f"bot-{turn_index}",
        user_state="window",
        concepts=[],
        timestamp="2026-01-01T00:00:00",
        embedding=np.array(vec, dtype=np.float32),
    )


def test_semantic_search_returns_hits_from_third_turn(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    memory = SemanticMemory(user_id="u_sem_v12")
    memory._model = _DummyEmbeddingModel()
    memory._model_loaded = True
    memory.turn_embeddings = [
        _embedding(1, [1.0, 0.0]),
        _embedding(2, [0.0, 1.0]),
        _embedding(3, [1.0, 0.0]),
    ]

    hits = memory.search_similar_turns("тревога", top_k=3, min_similarity=0.6)
    assert len(hits) >= 1
    assert memory.last_hits_count >= 1


def test_semantic_exclude_window_keeps_candidates(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    memory = SemanticMemory(user_id="u_sem_window")
    memory.turn_embeddings = [_embedding(1, [1.0, 0.0]), _embedding(2, [1.0, 0.0])]
    assert memory._resolve_exclude_window(5) == 0
