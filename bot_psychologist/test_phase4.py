#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_phase4.py
==============

Тестирование Phase 4 — Adaptive State-Aware QA

Тестовые сценарии:
1. Новый пользователь (beginner) — первый вопрос
2. Продолжение диалога (память) — тот же пользователь
3. STAGNANT состояние (intermediate) — пользователь застрял
4. BREAKTHROUGH состояние (advanced) — пользователь с инсайтом
"""

import sys
import io
from pathlib import Path
import json

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import from package
from bot_agent import answer_question_adaptive

print("=" * 100)
print("[TEST] PHASE 4 - ADAPTIVE STATE-AWARE QA BOT")
print("=" * 100)

# Тестовые сценарии
test_scenarios = [
    {
        "query": "Что такое осознавание?",
        "user_id": "test_user_001",
        "user_level": "beginner",
        "description": "Новый пользователь, первый вопрос"
    },
    {
        "query": "Как интегрировать инсайт в повседневную жизнь?",
        "user_id": "test_user_001",  # Тот же пользователь — проверка памяти
        "user_level": "beginner",
        "description": "Тот же пользователь (проверка памяти)"
    },
    {
        "query": "Почему я застрял в практике? Ничего не меняется, топчусь на месте.",
        "user_id": "test_user_002",
        "user_level": "intermediate",
        "description": "Пользователь в состоянии STAGNANT"
    },
    {
        "query": "Я внезапно понял связь между паттернами и сознанием! Это был настоящий инсайт.",
        "user_id": "test_user_003",
        "user_level": "advanced",
        "description": "Пользователь в состоянии BREAKTHROUGH"
    }
]

passed = 0
failed = 0

for i, scenario in enumerate(test_scenarios, 1):
    print(f"\n{'='*100}")
    print(f"TEST {i}/{len(test_scenarios)}")
    print(f"{'='*100}")
    print(f"\n[Scenario]: {scenario['description']}")
    print(f"[Query]: {scenario['query']}")
    print(f"[User ID]: {scenario['user_id']}")
    print(f"[Level]: {scenario['user_level']}\n")
    
    try:
        result = answer_question_adaptive(
            query=scenario['query'],
            user_id=scenario['user_id'],
            user_level=scenario['user_level'],
            include_path_recommendation=True,
            include_feedback_prompt=True,
            debug=True
        )
        
        print(f"[OK] Status: {result['status']}")
        print(f"[TIME] Processing time: {result['processing_time_seconds']}s")
        
        # === Анализ состояния ===
        if result.get('state_analysis'):
            state = result['state_analysis']
            print(f"\n[STATE ANALYSIS]:")
            print(f"   Primary state: {state['primary_state']}")
            print(f"   Confidence: {state['confidence']:.2f}")
            print(f"   Emotional tone: {state.get('emotional_tone', 'N/A')}")
            print(f"   Depth: {state.get('depth', 'N/A')}")
            if state.get('recommendations'):
                print(f"   Recommendation: {state['recommendations'][0]}")
        
        # === Ответ ===
        print(f"\n[ANSWER]:")
        answer_preview = result['answer'][:400] + "..." if len(result['answer']) > 400 else result['answer']
        print(answer_preview)
        
        # === Рекомендация пути ===
        if result.get('path_recommendation'):
            path = result['path_recommendation']
            print(f"\n[PATH RECOMMENDATION]:")
            print(f"   Current state: {path['current_state']}")
            print(f"   Target state: {path['target_state']}")
            print(f"   Key focus: {path['key_focus']}")
            print(f"   Steps: {path['steps_count']}, Duration: {path['total_duration_weeks']} weeks")
            if path.get('first_step'):
                print(f"   First step: {path['first_step'].get('title', 'N/A')}")
        
        # === Запрос обратной связи ===
        if result.get('feedback_prompt'):
            print(f"\n[FEEDBACK PROMPT]:")
            print(f"   {result['feedback_prompt']}")
        
        # === Контекст памяти ===
        if result.get('metadata'):
            print(f"\n[METADATA]:")
            print(f"   Total turns: {result['metadata'].get('conversation_turns', 0)}")
            print(f"   Blocks used: {result['metadata'].get('blocks_used', 0)}")
        
        # === Источники ===
        if result.get('sources'):
            print(f"\n[SOURCES] ({len(result['sources'])} blocks):")
            for src in result['sources'][:2]:
                print(f"   * {src.get('title', 'N/A')}")
                print(f"     {src.get('youtube_link', 'N/A')}\n")
        
        # === DEBUG ===
        if result.get('debug'):
            print(f"\n[DEBUG INFO]:")
            if result['debug'].get('state_analysis'):
                print(f"   State Analysis: {json.dumps(result['debug']['state_analysis'], indent=4, ensure_ascii=False)}")
            if result['debug'].get('memory_summary'):
                print(f"   Memory Summary: {json.dumps(result['debug']['memory_summary'], indent=4, ensure_ascii=False)}")
        
        # Проверка успешности
        if result['status'] == 'success':
            passed += 1
            print(f"\n[PASSED] TEST {i}")
        else:
            failed += 1
            print(f"\n[PARTIAL] TEST {i} (status: {result['status']})")
    
    except Exception as e:
        failed += 1
        print(f"[FAILED] TEST {i}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 100)
print("[SUMMARY] PHASE 4 TEST RESULTS")
print("=" * 100)
print(f"Passed: {passed}/{len(test_scenarios)}")
print(f"Failed: {failed}/{len(test_scenarios)}")
print("=" * 100)

if failed == 0:
    print("[SUCCESS] ALL TESTS PASSED!")
else:
    print(f"[WARNING] {failed} tests need attention")

print("=" * 100)


