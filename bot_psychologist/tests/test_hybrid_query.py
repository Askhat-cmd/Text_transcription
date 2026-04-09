#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for HybridQueryBuilder."""

from bot_agent.retrieval import HybridQueryBuilder
from bot_agent.working_state import WorkingState


def test_hybrid_query_preserves_question() -> None:
    builder = HybridQueryBuilder(max_chars=1500)

    question = "РџРѕС‡РµРјСѓ СЏ РІСЃС‘ РїРѕРЅРёРјР°СЋ, РЅРѕ РЅРёС‡РµРіРѕ РЅРµ РґРµР»Р°СЋ?"
    state = WorkingState(
        dominant_state="С„СЂСѓСЃС‚СЂР°С†РёСЏ",
        emotion="С‚СЂРµРІРѕРіР°",
        phase="РѕСЃРјС‹СЃР»РµРЅРёРµ",
        direction="РґРёР°РіРЅРѕСЃС‚РёРєР°",
    )

    hybrid_query = builder.build_query(
        current_question=question,
        conversation_summary="РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ Р·Р°РјРµС‡Р°РµС‚ РїРѕРІС‚РѕСЂСЏСЋС‰РµРµСЃСЏ Р·Р°СЃС‚СЂРµРІР°РЅРёРµ Рё РёР·Р±РµРіР°РЅРёРµ РґРµР№СЃС‚РІРёР№.",
        working_state=state,
        short_term_context="РћР±СЃСѓР¶РґР°Р»Рё СЃС‚СЂР°С… РѕС€РёР±РѕРє, РїСЂРѕРєСЂР°СЃС‚РёРЅР°С†РёСЋ Рё СѓСЃС‚Р°Р»РѕСЃС‚СЊ РѕС‚ РїРµСЂС„РµРєС†РёРѕРЅРёР·РјР°.",
    )

    lower = hybrid_query.lower()
    assert "QUESTION_ANCHOR:" in hybrid_query
    assert "QUESTION_ANCHOR_REPEAT:" in hybrid_query



def test_hybrid_query_keeps_anchor_when_trimmed() -> None:
    builder = HybridQueryBuilder(max_chars=220, short_term_chars=200, summary_chars=200)
    question = "Р§С‚Рѕ СЃРѕ РјРЅРѕР№ РїСЂРѕРёСЃС…РѕРґРёС‚?"
    long_text = " ".join(["РєРѕРЅС‚РµРєСЃС‚"] * 200)

    hybrid_query = builder.build_query(
        current_question=question,
        conversation_summary=long_text,
        short_term_context=long_text,
    )

    assert f"QUESTION_ANCHOR: {question}" in hybrid_query
    assert f"QUESTION_ANCHOR_REPEAT: {question}" in hybrid_query
    assert len(hybrid_query) <= 220


def test_hybrid_query_runtime_state_contract() -> None:
    builder = HybridQueryBuilder(max_chars=1200)

    hybrid_query = builder.build_query(
        current_question="РќСѓР¶РЅР° РїРѕРЅСЏС‚РЅР°СЏ СЃС‚СЂСѓРєС‚СѓСЂР° СЃР»РµРґСѓСЋС‰РµРіРѕ С€Р°РіР°.",
        working_state={
            "nss": "window",
            "request_function": "understand",
            "confidence": 0.85,
        },
    )

    assert "WORKING_STATE: nss=window fn=understand conf=0.85" in hybrid_query


def test_hybrid_query_does_not_emit_legacy_state_labels() -> None:
    builder = HybridQueryBuilder(max_chars=1200)

    hybrid_query = builder.build_query(
        current_question="РҐРѕС‡Сѓ РїСЂРѕРІРµСЂРёС‚СЊ С„РѕСЂРјР°С‚ СЂР°Р±РѕС‡РµРіРѕ СЃРѕСЃС‚РѕСЏРЅРёСЏ.",
        working_state={
            "dominant_state": "curious",
            "emotion": "contemplative",
            "phase": "exploration",
        },
    )

    lower = hybrid_query.lower()
    assert "СЃРѕСЃС‚РѕСЏРЅРёРµ:" not in lower
    assert "СЌРјРѕС†РёСЏ:" not in lower

def test_hybrid_query_includes_summary_excerpt_and_latest_user_turns() -> None:
    builder = HybridQueryBuilder(max_chars=2000)
    summary = "A" * 260

    hybrid_query = builder.build_query(
        current_question="How do I keep focus on the next step?",
        conversation_summary=summary,
        short_term_context="recent context",
        latest_user_turns=[
            "older question",
            "I keep delaying an important conversation",
            "what can I do today in 10 minutes?",
        ],
    )

    assert "SUMMARY_EXCERPT_200:" in hybrid_query
    assert "LATEST_USER_TURNS:" in hybrid_query
    assert "older question" not in hybrid_query
    assert "I keep delaying an important conversation" in hybrid_query
    assert "what can I do today in 10 minutes?" in hybrid_query
