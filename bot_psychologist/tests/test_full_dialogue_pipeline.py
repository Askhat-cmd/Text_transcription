#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integration-style 7-turn dialogue test for the new answer pipeline."""

from dataclasses import dataclass

import bot_agent.answer_basic as answer_basic_module
import bot_agent.conversation_memory as memory_module
from bot_agent.config import config


@dataclass
class _DummyBlock:
    block_id: str
    title: str
    summary: str
    content: str
    document_title: str
    youtube_link: str
    start: int
    end: int
    video_id: str
    block_type: str = "theory"
    emotional_tone: str = "neutral"
    complexity_score: float = 0.3
    conceptual_depth: float = 0.4


class _DummyRetriever:
    def retrieve(self, query: str, top_k: int = 5):
        blocks = [
            _DummyBlock(
                block_id="b1",
                title="Опора",
                summary="Короткая опора в состоянии пустоты",
                content="Контент 1",
                document_title="Doc A",
                youtube_link="https://example.com/a",
                start=0,
                end=30,
                video_id="a",
                complexity_score=0.2,
            ),
            _DummyBlock(
                block_id="b2",
                title="Уточнение",
                summary="Уточняющий блок",
                content="Контент 2",
                document_title="Doc B",
                youtube_link="https://example.com/b",
                start=30,
                end=60,
                video_id="b",
                complexity_score=0.55,
            ),
            _DummyBlock(
                block_id="b3",
                title="Шаг",
                summary="Практический шаг",
                content="Контент 3",
                document_title="Doc C",
                youtube_link="https://example.com/c",
                start=60,
                end=90,
                video_id="c",
                complexity_score=0.35,
            ),
        ]
        return [(block, 0.92 - i * 0.1) for i, block in enumerate(blocks[:top_k])]


class _DummyResponseGenerator:
    def generate(self, query, blocks, **kwargs):
        mode = kwargs.get("mode", "PRESENCE")
        return {
            "answer": f"[{mode}] {query}",
            "model_used": "dummy-model",
            "tokens_used": 42,
            "error": None,
        }


def test_full_dialogue_7_turns_pipeline(monkeypatch, tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(config, "ENABLE_SEMANTIC_MEMORY", False)
    monkeypatch.setattr(config, "ENABLE_CONVERSATION_SUMMARY", False)
    monkeypatch.setattr(config, "ENABLE_SESSION_STORAGE", False)

    monkeypatch.setattr(answer_basic_module.data_loader, "load_all_data", lambda: None)
    monkeypatch.setattr(
        answer_basic_module.data_loader,
        "get_all_blocks",
        lambda: [object()],
    )
    monkeypatch.setattr(
        answer_basic_module.data_loader,
        "get_all_documents",
        lambda: [object()],
    )
    monkeypatch.setattr(answer_basic_module, "get_retriever", lambda: _DummyRetriever())
    monkeypatch.setattr(answer_basic_module, "ResponseGenerator", _DummyResponseGenerator)

    user_id = "it_full_dialogue_user"
    memory_module._memory_instances.pop(user_id, None)
    memory = memory_module.get_conversation_memory(user_id)
    memory.clear()

    messages = [
        "Я чувствую себя опустошенным.",
        "Как будто нет сил.",
        "Похоже это после провала проекта.",
        "Почему я понимаю, но ничего не меняю?",
        "Да, это похоже на правду.",
        "Что мне делать дальше?",
        "Спасибо, попробую.",
    ]

    modes = []
    for message in messages:
        result = answer_basic_module.answer_question_basic(
            message,
            user_id=user_id,
            use_semantic_memory=False,
        )
        assert result["status"] == "success"
        assert result["answer"]
        assert result["metadata"]["recommended_mode"]
        assert result["metadata"]["confidence_level"] in {"low", "medium", "high"}
        modes.append(result["metadata"]["recommended_mode"])

    memory_after = memory_module.get_conversation_memory(user_id)
    assert len(memory_after.turns) == 7
    assert len(modes) == 7

