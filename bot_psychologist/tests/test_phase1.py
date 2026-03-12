#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Phase 1 - Bot Psychologist QA
==================================

Тестирование Phase 1 бота: поиск по блокам + генерация ответов.

Запуск:
    cd bot_psychologist
    python test_phase1.py
"""

import sys
import io
from pathlib import Path

def _configure_console_encoding():
    # Avoid touching sys.std* during pytest collection/capture.
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add bot_agent to path
sys.path.insert(0, str(Path(__file__).parent))

from bot_agent.answer_basic import answer_question_basic, ask
from bot_agent.config import config


def print_separator(char="=", length=70):
    print(char * length)


def test_config():
    """Тест конфигурации"""
    print_separator()
    print("🔧 ТЕСТ КОНФИГУРАЦИИ")
    print_separator()
    
    print(config.info())
    
    try:
        config.validate()
        print("✅ Конфигурация валидна")
        return True
    except ValueError as e:
        print(f"⚠️ Проблемы с конфигурацией:\n{e}")
        return False


def test_data_loader():
    """Тест загрузки данных"""
    print_separator()
    print("📂 ТЕСТ ЗАГРУЗКИ ДАННЫХ")
    print_separator()
    
    from bot_agent.data_loader import data_loader
    
    try:
        data_loader.load_all_data()
        stats = data_loader.get_stats()
        
        print(f"📊 Статистика:")
        print(f"   Документов: {stats['total_documents']}")
        print(f"   Блоков: {stats['total_blocks']}")
        print(f"   Путь: {stats['sag_final_dir']}")
        
        if stats['total_blocks'] > 0:
            print("✅ Данные успешно загружены")
            return True
        else:
            print("⚠️ Нет данных для тестирования")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_retriever():
    """Тест поиска"""
    print_separator()
    print("🔍 ТЕСТ RETRIEVER")
    print_separator()
    
    from bot_agent.retriever import get_retriever
    
    try:
        retriever = get_retriever()
        retriever.build_index()
        
        test_query = "осознавание"
        results = retriever.retrieve(test_query, top_k=3)
        
        print(f"Запрос: '{test_query}'")
        print(f"Найдено блоков: {len(results)}")
        
        for i, (block, score) in enumerate(results, 1):
            print(f"\n  {i}. [{score:.3f}] {block.title}")
            print(f"     Лекция: {block.document_title}")
            print(f"     Таймкод: {block.start}—{block.end}")
        
        if results:
            print("\n✅ Retriever работает")
            return True
        else:
            print("\n⚠️ Нет результатов поиска")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qa_basic():
    """Полный тест QA"""
    print_separator()
    print("🧪 ТЕСТ ПОЛНОГО QA PIPELINE")
    print_separator()
    
    # Тестовые вопросы
    test_queries = [
        "Что такое осознавание?",
        "Как развить осознавание в повседневной жизни?",
        "Какие практики рекомендуются для начинающих?",
    ]
    
    results_summary = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'─'*70}")
        print(f"ТЕСТ {i}/{len(test_queries)}")
        print(f"{'─'*70}")
        print(f"\n📋 Вопрос: {query}\n")
        
        try:
            result = answer_question_basic(query, debug=True)
            
            print(f"Status: {result['status']}")
            print(f"Processing time: {result['processing_time_seconds']}s")
            print(f"Blocks used: {result['blocks_used']}")
            
            print(f"\n💬 ОТВЕТ:\n{result['answer'][:500]}...")
            
            if result.get('sources'):
                print(f"\n📚 ИСТОЧНИКИ ({len(result['sources'])} блоков):")
                for src in result['sources'][:2]:
                    print(f"  • {src['title']}")
                    print(f"    Таймкод: {src['start']}—{src['end']}")
                    print(f"    Ссылка: {src['youtube_link']}")
            
            results_summary.append({
                "query": query,
                "status": result['status'],
                "blocks": result['blocks_used'],
                "time": result['processing_time_seconds']
            })
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            results_summary.append({
                "query": query,
                "status": "error",
                "blocks": 0,
                "time": 0
            })
    
    # Итоговый отчёт
    print_separator()
    print("📊 ИТОГОВЫЙ ОТЧЁТ")
    print_separator()
    
    success_count = sum(1 for r in results_summary if r['status'] == 'success')
    print(f"Успешных тестов: {success_count}/{len(test_queries)}")
    
    for r in results_summary:
        status_icon = "✅" if r['status'] == 'success' else "⚠️" if r['status'] == 'partial' else "❌"
        print(f"  {status_icon} {r['query'][:40]}... ({r['blocks']} блоков, {r['time']}s)")
    
    return success_count == len(test_queries)


def main():
    """Главная функция тестирования"""
    _configure_console_encoding()
    print_separator("═")
    print("🧪 ТЕСТИРОВАНИЕ PHASE 1 - BOT PSYCHOLOGIST QA")
    print_separator("═")
    
    # Последовательные тесты
    tests = [
        ("Config", test_config),
        ("Data Loader", test_data_loader),
        ("Retriever", test_retriever),
    ]
    
    all_passed = True
    for name, test_func in tests:
        print()
        if not test_func():
            print(f"\n⚠️ Тест '{name}' не пройден. Продолжение тестирования...")
            all_passed = False
    
    # QA тест (требует API key)
    if config.OPENAI_API_KEY:
        print()
        if not test_qa_basic():
            all_passed = False
    else:
        print(f"\n⚠️ OPENAI_API_KEY не установлен. QA тест пропущен.")
        print("   Добавьте ключ в .env для полного тестирования.")
    
    # Финальный результат
    print()
    print_separator("═")
    if all_passed:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print("⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
    print_separator("═")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

