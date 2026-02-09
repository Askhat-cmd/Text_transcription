#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for HybridQueryBuilder."""

from bot_agent.retrieval import HybridQueryBuilder
from bot_agent.working_state import WorkingState


def test_hybrid_query_preserves_question() -> None:
    builder = HybridQueryBuilder(max_chars=1500)

    question = "Почему я всё понимаю, но ничего не делаю?"
    state = WorkingState(
        dominant_state="фрустрация",
        emotion="тревога",
        phase="осмысление",
        direction="диагностика",
    )

    hybrid_query = builder.build_query(
        current_question=question,
        conversation_summary="Пользователь замечает повторяющееся застревание и избегание действий.",
        working_state=state,
        short_term_context="Обсуждали страх ошибок, прокрастинацию и усталость от перфекционизма.",
    )

    lower = hybrid_query.lower()
    assert "понима" in lower
    assert ("дела" in lower) or ("действ" in lower)
    assert "вопрос-якорь" in lower


def test_hybrid_query_keeps_anchor_when_trimmed() -> None:
    builder = HybridQueryBuilder(max_chars=220, short_term_chars=200, summary_chars=200)
    question = "Что со мной происходит?"
    long_text = " ".join(["контекст"] * 200)

    hybrid_query = builder.build_query(
        current_question=question,
        conversation_summary=long_text,
        short_term_context=long_text,
    )

    assert "ВОПРОС-ЯКОРЬ: Что со мной происходит?" in hybrid_query
    assert "СНОВА ВОПРОС-ЯКОРЬ: Что со мной происходит?" in hybrid_query
    assert len(hybrid_query) <= 220
