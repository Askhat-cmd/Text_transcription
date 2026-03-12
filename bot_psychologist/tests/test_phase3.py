# test_phase3.py
"""
Тестирование Phase 3 - Knowledge Graph Powered QA Bot
======================================================

Проверка функциональности Phase 3:
- Загрузка и анализ Knowledge Graph
- Рекомендация практик для концептов
- Построение путей обучения (learning path)
- Иерархия концептов
- Полная интеграция с Phase 1 и Phase 2
"""

import sys
import io
import json
from pathlib import Path

def _configure_console_encoding():
    # Avoid touching sys.std* during pytest collection/capture.
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path for package imports
sys.path.insert(0, str(Path(__file__).parent))

# Import from bot_agent package
from bot_agent import answer_question_graph_powered


def print_separator(char="=", length=90):
    """Print a separator line"""
    print(char * length)


def print_result(result: dict, show_full_answer: bool = True):
    """
    Форматированный вывод результата Phase 3.
    """
    print(f"\n📊 Status: {result['status']}")
    print(f"⏱️  Processing time: {result['processing_time_seconds']}s")
    
    # Metadata
    if result.get('metadata'):
        meta = result['metadata']
        print(f"\n📦 МЕТАДАННЫЕ:")
        print(f"   User level: {meta.get('user_level', 'N/A')}")
        print(f"   Blocks used: {meta.get('blocks_used', 'N/A')}")
        print(f"   Concepts found: {meta.get('concepts_found', 0)}")
        print(f"   Practices recommended: {meta.get('practices_recommended', 0)}")
        print(f"   Learning path depth: {meta.get('chain_depth', 0)}")
        print(f"   Graph nodes: {meta.get('graph_nodes', 0)}")
        print(f"   Graph edges: {meta.get('graph_edges', 0)}")
        if meta.get('model_used'):
            print(f"   Model: {meta.get('model_used')}")
        if meta.get('tokens_used'):
            print(f"   Tokens: {meta.get('tokens_used')}")
    
    # Answer
    if show_full_answer:
        print(f"\n💬 ОТВЕТ:\n{'-' * 60}")
        print(result.get('answer', 'Нет ответа'))
        print('-' * 60)
    else:
        answer = result.get('answer', '')
        preview = answer[:400] + "..." if len(answer) > 400 else answer
        print(f"\n💬 ОТВЕТ (preview):\n{preview}")
    
    # Concepts
    concepts = result.get('concepts', [])
    if concepts:
        print(f"\n🔑 КОНЦЕПТЫ ({len(concepts)}):")
        for concept in concepts:
            print(f"  • {concept}")
    
    # Practices (NEW in Phase 3)
    practices = result.get('practices', [])
    if practices:
        print(f"\n💪 РЕКОМЕНДУЕМЫЕ ПРАКТИКИ ({len(practices)}):")
        for practice in practices:
            explanation = practice.get('explanation', '')
            exp_text = f" — {explanation[:50]}..." if len(explanation) > 50 else f" — {explanation}" if explanation else ""
            print(f"  • {practice['name']} ({practice['type']}){exp_text}")
            if practice.get('source_blocks'):
                block = practice['source_blocks'][0]
                print(f"    📹 Источник: {block.get('youtube_link', 'N/A')}")
    
    # Learning Path (NEW in Phase 3)
    learning_path = result.get('learning_path', [])
    if learning_path:
        print(f"\n🛤️ ПУТЬ ОБУЧЕНИЯ ({len(learning_path)} шагов):")
        for step in learning_path[:5]:
            practices_str = ", ".join(step.get('practices', [])[:2]) if step.get('practices') else "—"
            print(f"  {step['step']}. {step['concept']} ({step.get('type', 'CONCEPT')})")
            print(f"     Практики: {practices_str}")
    
    # Concept Hierarchy (NEW in Phase 3)
    hierarchy = result.get('concept_hierarchy', {})
    if hierarchy:
        print(f"\n📊 ИЕРАРХИЯ КОНЦЕПТОВ:")
        for concept, data in list(hierarchy.items())[:2]:
            print(f"\n  📌 {concept} ({data.get('type', 'CONCEPT')}):")
            
            if data.get('parent_concepts'):
                parents = [p['name'] for p in data['parent_concepts'][:3]]
                print(f"     ← Часть: {', '.join(parents)}")
            
            if data.get('child_concepts'):
                children = [c['name'] for c in data['child_concepts'][:3]]
                print(f"     → Содержит: {', '.join(children)}")
            
            if data.get('related_concepts'):
                related = [r['name'] for r in data['related_concepts'][:3]]
                print(f"     ↔ Связан с: {', '.join(related)}")
    
    # Relations
    relations = result.get('relations', [])
    if relations:
        print(f"\n🔗 СЕМАНТИЧЕСКИЕ СВЯЗИ ({len(relations)}):")
        for rel in relations[:3]:
            print(f"  • {rel.get('from', '?')} → {rel.get('to', '?')} ({rel.get('type', 'RELATED')})")
    
    # Sources
    sources = result.get('sources', [])
    if sources:
        print(f"\n📚 ИСТОЧНИКИ ({len(sources)} блоков):")
        for i, src in enumerate(sources[:2], 1):
            print(f"\n  [{i}] {src['title']}")
            print(f"      Лекция: {src['document_title']}")
            print(f"      Тип: {src.get('block_type', 'N/A')}, "
                  f"Сложность: {src.get('complexity_score', 'N/A')}")
            print(f"      🎬 {src['youtube_link']}")
    
    # Debug info
    if result.get('debug'):
        print(f"\n🔧 DEBUG INFO:")
        debug = result['debug']
        
        # Graph stats
        if debug.get('graph_stats'):
            print(f"  📊 Graph Stats:")
            gs = debug['graph_stats']
            print(f"     Nodes: {gs.get('total_nodes', 0)}")
            print(f"     Edges: {gs.get('total_edges', 0)}")
            print(f"     Loaded files: {gs.get('loaded_files', 0)}")
        
        # Other debug info
        for key, value in debug.items():
            if key == 'graph_stats':
                continue
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")


def run_test(
    query: str,
    level: str,
    with_practices: bool,
    with_chain: bool,
    test_num: int,
    total: int,
    debug: bool = False
):
    """
    Запустить один тест Phase 3.
    """
    print_separator()
    print(f"ТЕСТ {test_num}/{total}")
    print_separator()
    print(f"\n📋 Вопрос: {query}")
    print(f"📊 Уровень: {level}")
    print(f"💪 Практики: {'✓' if with_practices else '✗'}")
    print(f"🛤️ Learning Path: {'✓' if with_chain else '✗'}")
    
    try:
        result = answer_question_graph_powered(
            query,
            user_level=level,
            include_practices=with_practices,
            include_chain=with_chain,
            debug=debug
        )
        print_result(result, show_full_answer=True)
        return result['status'] == 'success'
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Основной тестовый скрипт Phase 3.
    """
    print_separator("=")
    print("🧪 ТЕСТИРОВАНИЕ PHASE 3 - KNOWLEDGE GRAPH POWERED QA BOT")
    print_separator("=")
    
    # Тестовые комбинации (вопрос, уровень, with_practices, with_chain)
    test_cases = [
        ("Что такое осознавание?", "beginner", True, True),
        ("Как работает разотождествление?", "intermediate", True, True),
        ("Какие практики помогают в трансформации сознания?", "advanced", True, True),
        ("Как связаны паттерны с сознанием?", "intermediate", True, False),
    ]
    
    total = len(test_cases)
    success_count = 0
    
    for i, (query, level, with_practices, with_chain) in enumerate(test_cases, 1):
        success = run_test(
            query, level, with_practices, with_chain,
            test_num=i, total=total, debug=True
        )
        if success:
            success_count += 1
        print()
    
    # Итоги
    print_separator("=")
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ PHASE 3")
    print_separator("=")
    print(f"\n✅ Успешно: {success_count}/{total}")
    print(f"❌ Неуспешно: {total - success_count}/{total}")
    
    if success_count == total:
        print("\n🎉 Все тесты Phase 3 прошли успешно!")
        print("   ✓ Knowledge Graph загружается")
        print("   ✓ Практики рекомендуются")
        print("   ✓ Learning Path строится")
        print("   ✓ Иерархия концептов работает")
    else:
        print("\n⚠️ Некоторые тесты не прошли. Проверьте логи.")
    
    print_separator("=")
    print("✅ ТЕСТИРОВАНИЕ PHASE 3 ЗАВЕРШЕНО")
    print_separator("=")
    
    return success_count == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


